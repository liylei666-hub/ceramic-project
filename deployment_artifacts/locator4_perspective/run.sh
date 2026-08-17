#!/usr/bin/env bash
set -euo pipefail

SERVICE_ROOT=/data0/liyanlei/ceramic_watermark/services/decoder_gpu7_real18_locator4_perspective_20260816
PROJECT_ROOT=/data0/liyanlei/ceramic_watermark/experiments/trustmark_q_production4096_20260720/runtime_root
CHECKPOINT="$SERVICE_ROOT/models/checkpoint_decoder_57bit_real18_legacy_pilot3_step600.pt"
EXPECTED_CHECKPOINT_SHA=834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef
EXPECTED_APP_SHA=9da3108669da59585f21b67e05a916888179ffd0977c1a7e00a59911259486b8
PY=/data0/liyanlei/ceramic_watermark/envs/miniconda/bin/python
PORT="${CERAMIC_PORT:-28765}"
GPU="${CERAMIC_GPU:-7}"

cd "$SERVICE_ROOT"
test -x "$PY"
test -d "$PROJECT_ROOT/src"
test "$(sha256sum "$CHECKPOINT" | awk '{print $1}')" = "$EXPECTED_CHECKPOINT_SHA"
test "$(sha256sum decoder_api/app.py | awk '{print $1}')" = "$EXPECTED_APP_SHA"
test -s credentials/ceramic_api_token
test -d vendor/cv2
chmod 600 credentials/ceramic_api_token

exec env \
  CUDA_VISIBLE_DEVICES="$GPU" \
  PYTHONPATH="$SERVICE_ROOT/vendor${PYTHONPATH:+:$PYTHONPATH}" \
  CERAMIC_ROOT="$PROJECT_ROOT" \
  CERAMIC_CHECKPOINT="$CHECKPOINT" \
  CERAMIC_CHECKPOINT_SHA256="$EXPECTED_CHECKPOINT_SHA" \
  CERAMIC_DEVICE=cuda:0 \
  CERAMIC_REQUIRE_API_TOKEN=1 \
  CERAMIC_REQUIRE_IMAGE_SHA256=1 \
  CERAMIC_MAX_UPLOAD_BYTES=52428800 \
  CERAMIC_MAX_IMAGE_PIXELS=50000000 \
  CREDENTIALS_DIRECTORY="$SERVICE_ROOT/credentials" \
  "$PY" -m uvicorn decoder_api.app:app \
    --host 127.0.0.1 \
    --port "$PORT" \
    --workers 1 \
    --log-level info
