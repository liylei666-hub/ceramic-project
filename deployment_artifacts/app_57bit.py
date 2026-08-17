#!/usr/bin/env python3
"""FastAPI service for the 57-bit ceramic TrustMark-Q decoder."""

from __future__ import annotations

import gc
import hashlib
import io
import os
import re
import secrets
import sys
import threading
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass
from pathlib import Path

import torch
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image, ImageEnhance, ImageOps, UnidentifiedImageError
from torch.nn import functional as F
from torchvision.transforms.functional import to_tensor

from .codec_business_id_57 import parse_bch5_data


MODEL_NAME = "trustmark-q-57bit-900k-real18-legacy-adapt-pilot3-step600-candidate"
EXPECTED_PAYLOAD_BITS = 57
NETWORK_CODEWORD_BITS = 100
EXPECTED_ECC_VERSION = 1
DEFAULT_CROP_SCALES = (1.0, 0.9, 0.8, 0.7, 0.6)
FINE_ALIGNMENT_GEOMETRIES = (
    (0.96, 0.0, 0.0),
    (0.96, -0.01, 0.0),
    (0.96, 0.01, 0.0),
    (0.96, 0.0, -0.01),
    (0.96, 0.0, 0.01),
    (0.94, 0.0, 0.0),
    (0.98, 0.0, 0.0),
)
FINE_ALIGNMENT_RESAMPLING = (
    ("bilinear", Image.Resampling.BILINEAR),
    ("bicubic", Image.Resampling.BICUBIC),
)
FINE_ALIGNMENT_MIN_AGREEMENT = 2
CONTRAST_ENHANCEMENT_FACTORS = (1.25, 1.5)
CONTRAST_ENHANCEMENT_MIN_AGREEMENT = 2
GRAYSCALE_FALLBACK_SCALES = (1.0, 0.92, 0.9, 0.84, 0.8, 0.7, 0.6)
GRAYSCALE_FALLBACK_MIN_AGREEMENT = 2


@dataclass(frozen=True)
class Settings:
    root: Path
    checkpoint: Path
    device: str
    max_upload_bytes: int
    max_image_pixels: int
    checkpoint_sha256: str | None
    api_token: str | None
    require_api_token: bool
    require_image_sha256: bool

    @classmethod
    def from_env(cls) -> "Settings":
        root = Path(os.environ.get("CERAMIC_ROOT", ".")).resolve()
        checkpoint_value = os.environ.get("CERAMIC_CHECKPOINT")
        if not checkpoint_value:
            raise RuntimeError("CERAMIC_CHECKPOINT is required")
        checkpoint = Path(checkpoint_value).resolve()
        device = os.environ.get(
            "CERAMIC_DEVICE", "cuda" if torch.cuda.is_available() else "cpu"
        )
        credentials_directory = os.environ.get("CREDENTIALS_DIRECTORY")
        api_token = os.environ.get("CERAMIC_API_TOKEN")
        if not api_token and credentials_directory:
            credential_path = Path(credentials_directory) / "ceramic_api_token"
            if credential_path.is_file():
                api_token = credential_path.read_text(encoding="utf-8").strip()
        require_api_token = os.environ.get("CERAMIC_REQUIRE_API_TOKEN", "0") == "1"
        require_image_sha256 = os.environ.get("CERAMIC_REQUIRE_IMAGE_SHA256", "0") == "1"
        if require_api_token and not api_token:
            raise RuntimeError("API token is required but no credential was loaded")
        return cls(
            root=root,
            checkpoint=checkpoint,
            device=device,
            max_upload_bytes=int(
                os.environ.get("CERAMIC_MAX_UPLOAD_BYTES", 50 * 1024 * 1024)
            ),
            max_image_pixels=int(
                os.environ.get("CERAMIC_MAX_IMAGE_PIXELS", 50_000_000)
            ),
            checkpoint_sha256=os.environ.get("CERAMIC_CHECKPOINT_SHA256"),
            api_token=api_token,
            require_api_token=require_api_token,
            require_image_sha256=require_image_sha256,
        )


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def centered_square(image: Image.Image, scale: float) -> Image.Image:
    width, height = image.size
    side = max(1, round(min(width, height) * scale))
    left = (width - side) // 2
    top = (height - side) // 2
    return image.crop((left, top, left + side, top + side))


def aligned_square(
    image: Image.Image,
    scale: float,
    shift_x: float,
    shift_y: float,
    resampling: Image.Resampling,
) -> Image.Image:
    """Rectify a slightly shifted square crop through a stable 512px stage."""
    width, height = image.size
    side = float(min(width, height)) * scale
    center_x = width * 0.5 + shift_x * side
    center_y = height * 0.5 + shift_y * side
    left = center_x - side * 0.5
    top = center_y - side * 0.5
    right = center_x + side * 0.5
    bottom = center_y + side * 0.5
    # Pillow QUAD order: upper-left, lower-left, lower-right, upper-right.
    quad = (left, top, left, bottom, right, bottom, right, top)
    return image.transform(
        (512, 512), Image.Transform.QUAD, quad, resample=resampling
    )


def fine_alignment_specs() -> list[dict]:
    return [
        {
            "scale": scale,
            "shift_x": shift_x,
            "shift_y": shift_y,
            "resampling": resampling_name,
            "resampling_value": resampling_value,
        }
        for scale, shift_x, shift_y in FINE_ALIGNMENT_GEOMETRIES
        for resampling_name, resampling_value in FINE_ALIGNMENT_RESAMPLING
    ]


def select_consensus(
    valid_candidates: list[dict], min_agreement: int
) -> tuple[str, list[dict], dict] | None:
    if not valid_candidates:
        return None
    grouped: dict[str, list[dict]] = {}
    for candidate in valid_candidates:
        grouped.setdefault(candidate["identifier"], []).append(candidate)
    identifier, matches = max(
        grouped.items(),
        key=lambda pair: (
            len(pair[1]),
            max(item["decoder_margin"] for item in pair[1]),
        ),
    )
    if len(matches) < min_agreement:
        return None
    return identifier, matches, max(
        matches, key=lambda item: item["decoder_margin"]
    )


class TrustMarkDecoder:
    def __init__(self, settings: Settings) -> None:
        if not settings.checkpoint.is_file():
            raise RuntimeError(f"Checkpoint not found: {settings.checkpoint}")
        if not (settings.root / "src").is_dir():
            raise RuntimeError(f"Project source not found under: {settings.root}")

        checkpoint_sha256 = file_sha256(settings.checkpoint)
        if (
            settings.checkpoint_sha256
            and checkpoint_sha256.lower() != settings.checkpoint_sha256.lower()
        ):
            raise RuntimeError("Checkpoint SHA-256 does not match deployment contract")

        sys.path.insert(0, str(settings.root / "src"))
        from trustmark import TrustMark

        self.settings = settings
        self.checkpoint_sha256 = checkpoint_sha256
        self.device = torch.device(settings.device)
        self.lock = threading.Lock()
        self.tm = TrustMark(
            use_ECC=True,
            verbose=False,
            secret_len=NETWORK_CODEWORD_BITS,
            device=str(self.device),
            model_type="Q",
            encoding_type=TrustMark.Encoding.BCH_5,
            loadRemover=False,
        )
        checkpoint = torch.load(settings.checkpoint, map_location="cpu")
        self.checkpoint_step = int(checkpoint.get("step", -1))
        self.decoder = self.tm.decoder.decoder.to(self.device).eval()
        self.decoder.load_state_dict(checkpoint["decoder"], strict=True)
        self.tm.encoder = None
        del checkpoint
        gc.collect()
        if self.device.type == "cuda":
            torch.cuda.empty_cache()

    def _image_from_bytes(self, data: bytes) -> Image.Image:
        try:
            with Image.open(io.BytesIO(data)) as source:
                width, height = source.size
                if width <= 0 or height <= 0:
                    raise ValueError("Image dimensions are invalid")
                if width * height > self.settings.max_image_pixels:
                    raise ValueError("Image dimensions are too large")
                image = ImageOps.exif_transpose(source).convert("RGB")
                image.load()
        except (UnidentifiedImageError, OSError, ValueError) as exc:
            raise ValueError(f"Invalid image: {exc}") from exc
        return image

    def _coarse_candidate_batch(
        self, image: Image.Image
    ) -> tuple[torch.Tensor, list[dict]]:
        candidates = []
        metadata = []
        for scale in DEFAULT_CROP_SCALES:
            crop = centered_square(image, scale)
            tensor = to_tensor(crop).unsqueeze(0)
            candidates.append(
                F.interpolate(
                    tensor, size=(245, 245), mode="bilinear", align_corners=False
                )
            )
            metadata.append(
                {
                    "scale": scale,
                    "shift_x": 0.0,
                    "shift_y": 0.0,
                    "resampling": "direct-bilinear",
                }
            )
        return torch.cat(candidates, dim=0).to(self.device) * 2.0 - 1.0, metadata

    def _fine_candidate_batch(
        self, image: Image.Image
    ) -> tuple[torch.Tensor, list[dict]]:
        candidates = []
        metadata = []
        for spec in fine_alignment_specs():
            crop = aligned_square(
                image,
                spec["scale"],
                spec["shift_x"],
                spec["shift_y"],
                spec["resampling_value"],
            )
            tensor = to_tensor(crop).unsqueeze(0)
            candidates.append(
                F.interpolate(
                    tensor, size=(245, 245), mode="bilinear", align_corners=False
                )
            )
            metadata.append(
                {
                    "scale": spec["scale"],
                    "shift_x": spec["shift_x"],
                    "shift_y": spec["shift_y"],
                    "resampling": spec["resampling"],
                }
            )
        return torch.cat(candidates, dim=0).to(self.device) * 2.0 - 1.0, metadata

    def _contrast_candidate_batch(
        self, image: Image.Image
    ) -> tuple[torch.Tensor, list[dict]]:
        """构造最后一级的对比度增强候选，不改变前两级候选。"""
        batches = []
        metadata: list[dict] = []
        for factor in CONTRAST_ENHANCEMENT_FACTORS:
            enhanced = ImageEnhance.Contrast(image).enhance(factor)
            coarse_batch, coarse_metadata = self._coarse_candidate_batch(enhanced)
            fine_batch, fine_metadata = self._fine_candidate_batch(enhanced)
            for item in coarse_metadata + fine_metadata:
                item["contrast_factor"] = factor
            batches.extend((coarse_batch, fine_batch))
            metadata.extend(coarse_metadata + fine_metadata)
        return torch.cat(batches, dim=0), metadata

    def _grayscale_candidate_batch(
        self, image: Image.Image
    ) -> tuple[torch.Tensor, list[dict]]:
        """最后仅搜索少量灰度尺度候选，并要求至少两个候选一致。"""
        grayscale = ImageOps.grayscale(image).convert("RGB")
        candidates = []
        metadata = []
        for scale in GRAYSCALE_FALLBACK_SCALES:
            crop = centered_square(grayscale, scale)
            tensor = to_tensor(crop).unsqueeze(0)
            candidates.append(
                F.interpolate(
                    tensor, size=(245, 245), mode="bilinear", align_corners=False
                )
            )
            metadata.append(
                {
                    "scale": scale,
                    "shift_x": 0.0,
                    "shift_y": 0.0,
                    "resampling": "grayscale-direct-bilinear",
                }
            )
        return torch.cat(candidates, dim=0).to(self.device) * 2.0 - 1.0, metadata

    def _decode_candidates(
        self, batch: torch.Tensor, metadata: list[dict]
    ) -> tuple[list[dict], torch.Tensor]:
        with self.lock:
            logits = self.decoder(batch)
        predicted = logits > 0
        margins = torch.sigmoid(logits).sub(0.5).abs().mul(2.0).mean(dim=1)
        decoded = self.tm.ecc.decode_bitstream(
            predicted.to(torch.uint8).cpu().numpy(), MODE="binary"
        )

        valid_candidates = []
        for index, item in enumerate(decoded):
            recovered, ecc_ok, version = item
            if not (bool(ecc_ok) and int(version) == EXPECTED_ECC_VERSION):
                continue
            try:
                identifier = parse_bch5_data(recovered)
            except ValueError:
                continue
            valid_candidates.append(
                {
                    "identifier": identifier.decimal,
                    "enterprise_code": identifier.enterprise,
                    "date_code": identifier.date,
                    "serial_number": identifier.serial,
                    "payload_bits": recovered[:EXPECTED_PAYLOAD_BITS],
                    "bch_data_bits": recovered,
                    **metadata[index],
                    "decoder_margin": float(margins[index].item()),
                }
            )
        return valid_candidates, margins

    @torch.inference_mode()
    def decode_bytes(self, data: bytes) -> dict:
        started = time.perf_counter()
        image = self._image_from_bytes(data)
        coarse_batch, coarse_metadata = self._coarse_candidate_batch(image)
        valid_candidates, margins = self._decode_candidates(
            coarse_batch, coarse_metadata
        )
        consensus = select_consensus(valid_candidates, min_agreement=1)
        attempts = len(coarse_metadata)
        fallback_used = False
        contrast_enhancement_used = False
        grayscale_fallback_used = False

        if consensus is None:
            fallback_used = True
            fine_batch, fine_metadata = self._fine_candidate_batch(image)
            fine_valid, fine_margins = self._decode_candidates(
                fine_batch, fine_metadata
            )
            attempts += len(fine_metadata)
            margins = torch.cat((margins, fine_margins))
            consensus = select_consensus(
                fine_valid, min_agreement=FINE_ALIGNMENT_MIN_AGREEMENT
            )

        if consensus is None:
            contrast_enhancement_used = True
            contrast_batch, contrast_metadata = self._contrast_candidate_batch(image)
            contrast_valid, contrast_margins = self._decode_candidates(
                contrast_batch, contrast_metadata
            )
            attempts += len(contrast_metadata)
            margins = torch.cat((margins, contrast_margins))
            consensus = select_consensus(
                contrast_valid, min_agreement=CONTRAST_ENHANCEMENT_MIN_AGREEMENT
            )

        if consensus is None:
            grayscale_fallback_used = True
            grayscale_batch, grayscale_metadata = self._grayscale_candidate_batch(image)
            grayscale_valid, grayscale_margins = self._decode_candidates(
                grayscale_batch, grayscale_metadata
            )
            attempts += len(grayscale_metadata)
            margins = torch.cat((margins, grayscale_margins))
            consensus = select_consensus(
                grayscale_valid, min_agreement=GRAYSCALE_FALLBACK_MIN_AGREEMENT
            )

        result = {
            "detected": False,
            "payload_bits": None,
            "bch_data_bits": None,
            "payload_bits_count": EXPECTED_PAYLOAD_BITS,
            "business_id": None,
            "product_code": None,
            "product_id": None,
            "enterprise_code": None,
            "date_code": None,
            "serial_number": None,
            "ecc_valid": False,
            "crc_valid": False,
            "ecc_version": EXPECTED_ECC_VERSION,
            "protocol": "57bit-crc4-bch5",
            "decoder_margin": float(margins.max().item()),
            "candidate_scale": None,
            "candidate_shift_x": None,
            "candidate_shift_y": None,
            "candidate_resampling": None,
            "candidate_contrast_factor": None,
            "candidate_agreement": 0,
            "attempts": attempts,
            "alignment_fallback_used": fallback_used,
            "contrast_enhancement_used": contrast_enhancement_used,
            "grayscale_fallback_used": grayscale_fallback_used,
            "decode_stage": None,
            "image": {"width": image.width, "height": image.height},
            "model": MODEL_NAME,
            "checkpoint_step": self.checkpoint_step,
            "processing_ms": round((time.perf_counter() - started) * 1000, 1),
        }
        if consensus is None:
            return result

        identifier, matches, best = consensus
        result.update(
            {
                "detected": True,
                "payload_bits": best["payload_bits"],
                "bch_data_bits": best["bch_data_bits"],
                "business_id": identifier,
                # Keep both legacy display fields populated for the current Mini Program.
                "product_code": identifier,
                "product_id": identifier,
                "enterprise_code": best["enterprise_code"],
                "date_code": best["date_code"],
                "serial_number": best["serial_number"],
                "ecc_valid": True,
                "crc_valid": True,
                "decoder_margin": best["decoder_margin"],
                "candidate_scale": best["scale"],
                "candidate_shift_x": best["shift_x"],
                "candidate_shift_y": best["shift_y"],
                "candidate_resampling": best["resampling"],
                "candidate_contrast_factor": best.get("contrast_factor"),
                "candidate_agreement": len(matches),
                "decode_stage": (
                    "grayscale_fallback"
                    if grayscale_fallback_used
                    else (
                        "contrast_enhancement"
                        if contrast_enhancement_used
                        else ("fine_alignment" if fallback_used else "coarse")
                    )
                ),
            }
        )
        return result


async def read_upload(upload: UploadFile, limit: int) -> bytes:
    chunks = []
    size = 0
    while True:
        chunk = await upload.read(1024 * 1024)
        if not chunk:
            break
        size += len(chunk)
        if size > limit:
            raise HTTPException(status_code=413, detail="Image exceeds upload limit")
        chunks.append(chunk)
    if size == 0:
        raise HTTPException(status_code=400, detail="Image file is empty")
    return b"".join(chunks)


@asynccontextmanager
async def lifespan(app: FastAPI):
    settings = Settings.from_env()
    app.state.settings = settings
    app.state.decoder = TrustMarkDecoder(settings)
    yield


app = FastAPI(
    title="Ceramic 57-bit Watermark Decoder",
    version="2.0.0",
    docs_url=None,
    redoc_url=None,
    lifespan=lifespan,
)


@app.get("/healthz")
async def healthz(request: Request) -> dict:
    decoder: TrustMarkDecoder = request.app.state.decoder
    return {
        "status": "ok",
        "model": MODEL_NAME,
        "protocol": "57bit-crc4-bch5",
        "payload_bits": EXPECTED_PAYLOAD_BITS,
        "checkpoint_step": decoder.checkpoint_step,
        "checkpoint_sha256": decoder.checkpoint_sha256,
        "device": str(decoder.device),
    }


@app.post("/decode")
async def decode(
    request: Request,
    image: UploadFile = File(...),
    payload_bits: int = Form(EXPECTED_PAYLOAD_BITS),
) -> dict:
    settings: Settings = request.app.state.settings
    presented_token = request.headers.get("x-ceramic-token", "")
    if settings.api_token and not secrets.compare_digest(
        presented_token.encode("utf-8"), settings.api_token.encode("utf-8")
    ):
        raise HTTPException(status_code=401, detail="Invalid API token")
    # The existing cloud function may still send 40. Both values route to the
    # only active decoder, which is strictly BCH-5/57-bit.
    if payload_bits not in (40, EXPECTED_PAYLOAD_BITS):
        raise HTTPException(status_code=422, detail="payload_bits must be 57")
    content_type = (image.content_type or "").lower()
    if content_type and not content_type.startswith("image/"):
        raise HTTPException(status_code=415, detail="Uploaded file must be an image")
    data = await read_upload(image, settings.max_upload_bytes)
    actual_sha256 = hashlib.sha256(data).hexdigest()
    expected_sha256 = request.headers.get("x-image-sha256", "").lower()
    if settings.require_image_sha256 and not expected_sha256:
        raise HTTPException(status_code=400, detail="X-Image-SHA256 is required")
    if expected_sha256:
        if not re.fullmatch(r"[0-9a-f]{64}", expected_sha256):
            raise HTTPException(status_code=400, detail="X-Image-SHA256 is invalid")
        if not secrets.compare_digest(actual_sha256, expected_sha256):
            raise HTTPException(status_code=422, detail="Image SHA-256 mismatch")
    decoder: TrustMarkDecoder = request.app.state.decoder
    try:
        result = await run_in_threadpool(decoder.decode_bytes, data)
        result["input_sha256"] = actual_sha256
        result["requested_payload_bits"] = payload_bits
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
