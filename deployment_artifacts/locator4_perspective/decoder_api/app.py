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

import cv2
import numpy as np
import torch
from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.concurrency import run_in_threadpool
from PIL import Image, ImageOps, UnidentifiedImageError
from torch.nn import functional as F
from torchvision.transforms.functional import to_tensor

from .codec_business_id_57 import parse_bch5_data


MODEL_NAME = "trustmark-q-57bit-real18-step113100-locator4-perspective"
EXPECTED_PAYLOAD_BITS = 57
NETWORK_CODEWORD_BITS = 100
EXPECTED_ECC_VERSION = 1
PERSPECTIVE_CANVAS_SIZE = 512
PERSPECTIVE_INNER_SQUARE_FRACTION = 0.49
LOCALIZED_VARIANTS = (
    (0.84, "colour"),
    (0.88, "grayscale"),
    (0.92, "colour"),
)
PERSPECTIVE_VARIANTS = (
    (0.46, 0.88, "colour", cv2.INTER_LINEAR, "bilinear"),
    (0.46, 0.88, "colour", cv2.INTER_CUBIC, "bicubic"),
    (0.48, 0.84, "colour", cv2.INTER_CUBIC, "bicubic"),
    (0.48, 0.88, "grayscale", cv2.INTER_CUBIC, "bicubic"),
    (0.49, 0.88, "grayscale", cv2.INTER_LINEAR, "bilinear"),
    (0.49, 0.92, "colour", cv2.INTER_CUBIC, "bicubic"),
)
PERSPECTIVE_RESAMPLED_VARIANTS = (
    (0.88, "grayscale"),
    (0.92, "colour"),
)


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


def _order_quad(points: np.ndarray) -> np.ndarray:
    """Return quadrilateral corners in top-left clockwise order."""
    points = np.asarray(points, dtype=np.float32).reshape(4, 2)
    sums = points.sum(axis=1)
    differences = np.diff(points, axis=1).reshape(-1)
    ordered = np.array(
        [
            points[np.argmin(sums)],
            points[np.argmin(differences)],
            points[np.argmax(sums)],
            points[np.argmax(differences)],
        ],
        dtype=np.float32,
    )
    if len(np.unique(ordered, axis=0)) != 4:
        raise ValueError("Perspective quadrilateral has duplicate corners")
    return ordered


def _find_inner_square(
    contours: tuple[np.ndarray, ...], outer: dict, inverse_scale: float
) -> dict | None:
    """Find the central white square, whose four corners define the homography."""
    outer_side = float(max(outer["width"], outer["height"]))
    outer_area = float(max(outer["area"], 1.0))
    outer_center_x = outer["x"] + outer["width"] * 0.5
    outer_center_y = outer["y"] + outer["height"] * 0.5
    candidates = []
    for contour in contours:
        x, y, box_width, box_height = cv2.boundingRect(contour)
        side = float(max(box_width, box_height))
        short_side = float(min(box_width, box_height))
        if not (0.35 * outer_side <= side <= 0.68 * outer_side):
            continue
        if short_side < 0.28 * outer_side:
            continue
        center_distance = np.hypot(
            x + box_width * 0.5 - outer_center_x,
            y + box_height * 0.5 - outer_center_y,
        ) / outer_side
        if center_distance > 0.16:
            continue

        area = float(cv2.contourArea(contour))
        if not (0.12 * outer_area <= area <= 0.42 * outer_area):
            continue
        perimeter = float(cv2.arcLength(contour, True))
        if perimeter <= 0:
            continue
        quad = cv2.approxPolyDP(
            cv2.convexHull(contour), 0.025 * perimeter, True
        )
        if len(quad) != 4 or not cv2.isContourConvex(quad):
            continue
        quad_area = float(abs(cv2.contourArea(quad)))
        rectangle = cv2.minAreaRect(quad)
        rectangle_area = float(rectangle[1][0] * rectangle[1][1])
        rectangularity = quad_area / max(rectangle_area, 1.0)
        if rectangularity < 0.72:
            continue

        ordered = _order_quad(quad.reshape(4, 2))
        edges = np.linalg.norm(ordered - np.roll(ordered, -1, axis=0), axis=1)
        edge_ratio = float(edges.max() / max(edges.min(), 1.0))
        if edge_ratio > 2.5:
            continue
        size_ratio = side / outer_side
        score = (
            3.0 * rectangularity
            - 2.0 * center_distance
            - abs(size_ratio - PERSPECTIVE_INNER_SQUARE_FRACTION)
        )
        candidates.append(
            {
                "quad": (ordered * inverse_scale).tolist(),
                "rectangularity": float(rectangularity),
                "center_distance": float(center_distance),
                "edge_ratio": edge_ratio,
                "score": float(score),
            }
        )
    if not candidates:
        return None
    return max(candidates, key=lambda item: item["score"])


def locate_logo(image: Image.Image) -> dict:
    """Locate the outer logo and an optional central square for rectification."""
    rgb = np.asarray(image.convert("RGB"))
    bgr = cv2.cvtColor(rgb, cv2.COLOR_RGB2BGR)
    height, width = bgr.shape[:2]
    resize_scale = min(1.0, 1024.0 / max(width, height))
    if resize_scale < 1.0:
        small = cv2.resize(
            bgr,
            (
                max(1, round(width * resize_scale)),
                max(1, round(height * resize_scale)),
            ),
            interpolation=cv2.INTER_AREA,
        )
    else:
        small = bgr

    gray = cv2.cvtColor(small, cv2.COLOR_BGR2GRAY)
    gray = cv2.GaussianBlur(gray, (5, 5), 0)
    _, mask = cv2.threshold(
        gray, 0, 255, cv2.THRESH_BINARY_INV | cv2.THRESH_OTSU
    )
    mask = cv2.morphologyEx(
        mask,
        cv2.MORPH_CLOSE,
        cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (3, 3)),
        iterations=1,
    )
    contours, _ = cv2.findContours(mask, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
    small_height, small_width = gray.shape
    min_dimension = float(min(small_width, small_height))
    image_center_x = small_width * 0.5
    image_center_y = small_height * 0.5
    candidates = []
    for contour_index, contour in enumerate(contours):
        x, y, box_width, box_height = cv2.boundingRect(contour)
        side = float(max(box_width, box_height))
        aspect = box_width / max(box_height, 1)
        area = float(cv2.contourArea(contour))
        perimeter = float(cv2.arcLength(contour, True))
        circularity = 4.0 * np.pi * area / max(perimeter * perimeter, 1e-6)
        fill = area / max(float(box_width * box_height), 1.0)
        if not (0.08 * min_dimension <= side <= 0.98 * min_dimension):
            continue
        if not (0.72 <= aspect <= 1.38):
            continue
        if circularity < 0.55 or fill < 0.35:
            continue
        box_center_x = x + box_width * 0.5
        box_center_y = y + box_height * 0.5
        center_distance = (
            np.hypot(
                box_center_x - image_center_x,
                box_center_y - image_center_y,
            )
            / min_dimension
        )
        size_fraction = side / min_dimension
        score = 3.0 * circularity + 0.35 * size_fraction - 1.4 * center_distance
        candidates.append(
            {
                "x": x,
                "y": y,
                "width": box_width,
                "height": box_height,
                "area": area,
                "circularity": float(circularity),
                "center_distance": float(center_distance),
                "score": float(score),
                "contour_index": contour_index,
            }
        )
    if not candidates:
        raise ValueError("No credible ceramic logo contour was found")

    best = max(candidates, key=lambda item: item["score"])
    inverse_scale = 1.0 / resize_scale
    inner_square = _find_inner_square(contours, best, inverse_scale)
    return {
        **best,
        "x": best["x"] * inverse_scale,
        "y": best["y"] * inverse_scale,
        "width": best["width"] * inverse_scale,
        "height": best["height"] * inverse_scale,
        "candidate_count": len(candidates),
        "perspective_quad": inner_square["quad"] if inner_square else None,
        "perspective_confidence": (
            inner_square["rectangularity"] if inner_square else None
        ),
        "perspective_edge_ratio": inner_square["edge_ratio"] if inner_square else None,
    }


def localized_square(
    image: Image.Image, location: dict, padding_factor: float
) -> Image.Image:
    """Crop a square around the detected outer logo contour."""
    center_x = location["x"] + location["width"] * 0.5
    center_y = location["y"] + location["height"] * 0.5
    side = max(location["width"], location["height"]) * padding_factor
    side = min(side, float(image.width), float(image.height))
    left = max(0.0, min(image.width - side, center_x - side * 0.5))
    top = max(0.0, min(image.height - side, center_y - side * 0.5))
    return image.crop((left, top, left + side, top + side))


def rectify_logo_perspective(image: Image.Image, location: dict) -> Image.Image:
    """Rectify the logo plane from the detected central square."""
    quad = location.get("perspective_quad")
    if quad is None:
        raise ValueError("No reliable perspective quadrilateral was found")
    source = _order_quad(np.asarray(quad, dtype=np.float32))
    canvas_size = PERSPECTIVE_CANVAS_SIZE
    inner_side = canvas_size * PERSPECTIVE_INNER_SQUARE_FRACTION
    margin = (canvas_size - inner_side) * 0.5
    destination = np.array(
        [
            [margin, margin],
            [canvas_size - margin, margin],
            [canvas_size - margin, canvas_size - margin],
            [margin, canvas_size - margin],
        ],
        dtype=np.float32,
    )
    matrix = cv2.getPerspectiveTransform(source, destination)
    rgb = np.asarray(image.convert("RGB"))
    rectified = cv2.warpPerspective(
        rgb,
        matrix,
        (canvas_size, canvas_size),
        flags=cv2.INTER_CUBIC,
        borderMode=cv2.BORDER_REPLICATE,
    )
    return Image.fromarray(rectified, mode="RGB")


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

    def _localized_candidate_batch(
        self,
        image: Image.Image,
        location: dict,
        *,
        perspective_rectified: bool = False,
    ) -> tuple[torch.Tensor, list[dict]]:
        candidates = []
        metadata = []
        for padding_factor, mode in LOCALIZED_VARIANTS:
            crop = localized_square(image, location, padding_factor)
            candidate = (
                ImageOps.grayscale(crop).convert("RGB")
                if mode == "grayscale"
                else crop
            )
            tensor = to_tensor(candidate).unsqueeze(0)
            candidates.append(
                F.interpolate(
                    tensor, size=(245, 245), mode="bilinear", align_corners=False
                )
            )
            metadata.append(
                {
                    "scale": padding_factor,
                    "shift_x": 0.0,
                    "shift_y": 0.0,
                    "resampling": (
                        f"perspective-localized-{mode}"
                        if perspective_rectified
                        else f"localized-{mode}"
                    ),
                    "localization_padding": padding_factor,
                    "localization_mode": mode,
                    "perspective_rectified": perspective_rectified,
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

    def _perspective_candidate_batch(
        self, image: Image.Image, location: dict
    ) -> tuple[torch.Tensor, list[dict]]:
        source = _order_quad(
            np.asarray(location["perspective_quad"], dtype=np.float32)
        )
        rgb = np.asarray(image.convert("RGB"))
        output_size = 245
        candidates = []
        metadata = []
        for inner_fraction, padding_factor, mode, interpolation, interpolation_name in (
            PERSPECTIVE_VARIANTS
        ):
            inner_side = output_size * inner_fraction / padding_factor
            margin = (output_size - inner_side) * 0.5
            destination = np.array(
                [
                    [margin, margin],
                    [output_size - margin, margin],
                    [output_size - margin, output_size - margin],
                    [margin, output_size - margin],
                ],
                dtype=np.float32,
            )
            matrix = cv2.getPerspectiveTransform(source, destination)
            warped = cv2.warpPerspective(
                rgb,
                matrix,
                (output_size, output_size),
                flags=interpolation,
                borderMode=cv2.BORDER_REPLICATE,
            )
            candidate = Image.fromarray(warped, mode="RGB")
            if mode == "grayscale":
                candidate = ImageOps.grayscale(candidate).convert("RGB")
            candidates.append(to_tensor(candidate).unsqueeze(0))
            metadata.append(
                {
                    "scale": padding_factor,
                    "shift_x": 0.0,
                    "shift_y": 0.0,
                    "resampling": (
                        f"perspective-{interpolation_name}-{mode}"
                        f"-inner{inner_fraction:.2f}"
                    ),
                    "localization_padding": padding_factor,
                    "localization_mode": mode,
                    "perspective_rectified": True,
                    "perspective_inner_fraction": inner_fraction,
                }
            )

        rectified = rectify_logo_perspective(image, location)
        rectified_location = {
            "x": 0.0,
            "y": 0.0,
            "width": float(rectified.width),
            "height": float(rectified.height),
        }
        for padding_factor, mode in PERSPECTIVE_RESAMPLED_VARIANTS:
            crop = localized_square(rectified, rectified_location, padding_factor)
            candidate = (
                ImageOps.grayscale(crop).convert("RGB")
                if mode == "grayscale"
                else crop
            )
            tensor = to_tensor(candidate).unsqueeze(0)
            candidates.append(
                F.interpolate(
                    tensor, size=(245, 245), mode="bilinear", align_corners=False
                )
            )
            metadata.append(
                {
                    "scale": padding_factor,
                    "shift_x": 0.0,
                    "shift_y": 0.0,
                    "resampling": f"perspective-two-pass-{mode}-inner0.49",
                    "localization_padding": padding_factor,
                    "localization_mode": mode,
                    "perspective_rectified": True,
                    "perspective_inner_fraction": (
                        PERSPECTIVE_INNER_SQUARE_FRACTION
                    ),
                }
            )
        return torch.cat(candidates, dim=0).to(self.device) * 2.0 - 1.0, metadata

    @torch.inference_mode()
    def decode_bytes(self, data: bytes) -> dict:
        started = time.perf_counter()
        image = self._image_from_bytes(data)
        try:
            location = locate_logo(image)
        except ValueError:
            location = None
            margins = torch.zeros(1)
            consensus = None
            attempts = 0
        else:
            localized_batch, localized_metadata = self._localized_candidate_batch(
                image, location
            )
            valid_candidates, margins = self._decode_candidates(
                localized_batch, localized_metadata
            )
            consensus = select_consensus(valid_candidates, min_agreement=1)
            attempts = len(localized_metadata)
            perspective_attempted = False
            perspective_margins = None
            if consensus is None and location.get("perspective_quad") is not None:
                perspective_batch, perspective_metadata = (
                    self._perspective_candidate_batch(image, location)
                )
                perspective_valid, perspective_margins = self._decode_candidates(
                    perspective_batch, perspective_metadata
                )
                consensus = select_consensus(perspective_valid, min_agreement=2)
                attempts += len(perspective_metadata)
                perspective_attempted = True

        if location is None:
            perspective_attempted = False
            perspective_margins = None
        if perspective_margins is not None:
            margins = torch.cat((margins, perspective_margins))

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
            "candidate_localization_padding": None,
            "candidate_localization_mode": None,
            "candidate_perspective_inner_fraction": None,
            "candidate_agreement": 0,
            "attempts": attempts,
            "alignment_fallback_used": False,
            "contrast_enhancement_used": False,
            "grayscale_fallback_used": False,
            "perspective_fallback_used": perspective_attempted,
            "perspective_rectification_available": (
                location is not None and location.get("perspective_quad") is not None
            ),
            "perspective_rectification_confidence": (
                round(location["perspective_confidence"], 4)
                if location is not None
                and location.get("perspective_confidence") is not None
                else None
            ),
            "perspective_rectification_edge_ratio": (
                round(location["perspective_edge_ratio"], 4)
                if location is not None
                and location.get("perspective_edge_ratio") is not None
                else None
            ),
            "localization_used": True,
            "localization_found": location is not None,
            "localization_bbox": (
                {
                    "x": round(location["x"], 2),
                    "y": round(location["y"], 2),
                    "width": round(location["width"], 2),
                    "height": round(location["height"], 2),
                }
                if location is not None
                else None
            ),
            "localization_candidate_count": (
                location["candidate_count"] if location is not None else 0
            ),
            "localized_variant_count": len(LOCALIZED_VARIANTS),
            "perspective_variant_count": (
                len(PERSPECTIVE_VARIANTS) + len(PERSPECTIVE_RESAMPLED_VARIANTS)
                if perspective_attempted
                else 0
            ),
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
                "candidate_localization_padding": best["localization_padding"],
                "candidate_localization_mode": best["localization_mode"],
                "candidate_perspective_inner_fraction": best.get(
                    "perspective_inner_fraction"
                ),
                "candidate_agreement": len(matches),
                "perspective_fallback_used": best["perspective_rectified"],
                "decode_stage": (
                    "perspective_rectified"
                    if best["perspective_rectified"]
                    else "localized_direct"
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
    version="2.2.0",
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
        "localization": "outer-logo-contour+inner-square-perspective-fallback",
        "localized_variants": len(LOCALIZED_VARIANTS),
        "perspective_variants": (
            len(PERSPECTIVE_VARIANTS) + len(PERSPECTIVE_RESAMPLED_VARIANTS)
        ),
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
