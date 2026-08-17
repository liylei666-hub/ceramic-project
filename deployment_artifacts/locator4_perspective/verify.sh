#!/usr/bin/env bash
set -euo pipefail

ROOT=/data0/liyanlei/ceramic_watermark/services/decoder_gpu7_real18_locator4_perspective_20260816
PORT=28765
PY=/data0/liyanlei/ceramic_watermark/envs/miniconda/bin/python
TOKEN="$(<"$ROOT/credentials/ceramic_api_token")"

expected_ids=(
  07904250117247165 12981790906431892 83363101128357672
  79004350725792387 06025190128495580 94651640806240324
  39278151015366274 26778730711905577 78726210227612037
  13008440616423633 21359300828395828 67850040219427680
  08022061102620554 09366360614692060 43506140108674762
  49923300722637137 52525170930578677 91321270129575785
)

passed=0
for index in "${!expected_ids[@]}"; do
  number="$(printf '%02d' "$((index + 1))")"
  image="$ROOT/samples/$number.png"
  image_sha="$(sha256sum "$image" | awk '{print $1}')"
  raw="$(curl -fsS --max-time 20 \
    -H "x-ceramic-token: $TOKEN" \
    -H "x-image-sha256: $image_sha" \
    -F payload_bits=57 \
    -F "image=@$image" \
    "http://127.0.0.1:$PORT/decode")"
  "$PY" -c '
import json
import sys
payload = json.load(sys.stdin)
expected, number = sys.argv[1:]
assert payload["detected"] is True, payload
assert payload["business_id"] == expected, payload
assert payload["decode_stage"] == "localized_direct", payload
assert payload["attempts"] == 3, payload
assert payload["localization_found"] is True, payload
assert payload["perspective_fallback_used"] is False, payload
assert payload["perspective_rectification_available"] is True, payload
print(f"{number}: {expected} ({payload['"'"'processing_ms'"'"']} ms)")
' "${expected_ids[$index]}" "$number" <<<"$raw"
  passed=$((passed + 1))
done

echo "REAL18_PASSED=$passed/18"

perspective_passed=0
perspective_used=0
for index in "${!expected_ids[@]}"; do
  number="$(printf '%02d' "$((index + 1))")"
  for level in 18 24 30; do
    image="$ROOT/perspective_samples/${number}_p${level}.png"
    image_sha="$(sha256sum "$image" | awk '{print $1}')"
    raw="$(curl -fsS --max-time 20 \
      -H "x-ceramic-token: $TOKEN" \
      -H "x-image-sha256: $image_sha" \
      -F payload_bits=57 \
      -F "image=@$image" \
      "http://127.0.0.1:$PORT/decode")"
    stage="$($PY -c '
import json
import sys
payload = json.load(sys.stdin)
expected, name = sys.argv[1:]
assert payload["detected"] is True, payload
assert payload["business_id"] == expected, payload
assert payload["decode_stage"] in ("localized_direct", "perspective_rectified"), payload
assert payload["attempts"] in (3, 11), payload
assert payload["perspective_rectification_available"] is True, payload
if payload["decode_stage"] == "perspective_rectified":
    assert payload["attempts"] == 11, payload
    assert payload["perspective_fallback_used"] is True, payload
    assert payload["candidate_agreement"] >= 2, payload
print(payload["decode_stage"])
' "${expected_ids[$index]}" "${number}_p${level}" <<<"$raw")"
    if [ "$stage" = "perspective_rectified" ]; then
      perspective_used=$((perspective_used + 1))
    fi
    perspective_passed=$((perspective_passed + 1))
  done
done

test "$perspective_used" -ge 1
echo "PERSPECTIVE_PASSED=$perspective_passed/54"
echo "PERSPECTIVE_FALLBACK_RECOVERIES=$perspective_used"

board_names=(board_01_09.jpg board_10_18.jpg)
board_ids=(06025190128495580 09366360614692060)
for index in "${!board_names[@]}"; do
  image="$ROOT/samples/${board_names[$index]}"
  image_sha="$(sha256sum "$image" | awk '{print $1}')"
  raw="$(curl -fsS --max-time 20 \
    -H "x-ceramic-token: $TOKEN" \
    -H "x-image-sha256: $image_sha" \
    -F payload_bits=57 \
    -F "image=@$image" \
    "http://127.0.0.1:$PORT/decode")"
  "$PY" -c '
import json
import sys
payload = json.load(sys.stdin)
expected, name = sys.argv[1:]
assert payload["detected"] is True, payload
assert payload["business_id"] == expected, payload
assert payload["decode_stage"] == "localized_direct", payload
assert payload["attempts"] == 3, payload
print(name, payload["business_id"], payload["processing_ms"])
' "${board_ids[$index]}" "${board_names[$index]}" <<<"$raw"
done
echo "BOARD_PASSED=2/2"

for negative in unwatermarked_negative.png blank.png; do
  image="$ROOT/samples/$negative"
  image_sha="$(sha256sum "$image" | awk '{print $1}')"
  raw="$(curl -fsS --max-time 20 \
    -H "x-ceramic-token: $TOKEN" \
    -H "x-image-sha256: $image_sha" \
    -F payload_bits=57 \
    -F "image=@$image" \
    "http://127.0.0.1:$PORT/decode")"
  "$PY" -c '
import json
import sys
payload = json.load(sys.stdin)
assert payload["detected"] is False, payload
assert payload["business_id"] is None, payload
assert payload["ecc_valid"] is False and payload["crc_valid"] is False, payload
print(sys.argv[1], payload["attempts"], payload["processing_ms"])
' "$negative" <<<"$raw"
done
