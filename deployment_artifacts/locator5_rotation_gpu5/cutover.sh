#!/usr/bin/env bash
set -euo pipefail

OLD_ROOT=/data0/liyanlei/ceramic_watermark/services/decoder_gpu7_real18_locator5_rotation_20260816
NEW_ROOT=/data0/liyanlei/ceramic_watermark/services/decoder_gpu5_real18_locator5_rotation_20260817
PORT=28765
SHADOW_PORT=28565
PY=/data0/liyanlei/ceramic_watermark/envs/miniconda/bin/python
EXPECTED_MODEL=trustmark-q-57bit-real18-step113100-locator5-perspective-rotation
EXPECTED_CHECKPOINT_SHA=834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef
stamp="$(date +%Y%m%d-%H%M%S)"

pid_for_port() {
  ss -ltnp 2>/dev/null | sed -n "s/.*:${1}.*pid=\([0-9]*\).*/\1/p" | head -1
}

stop_pid() {
  local pid="$1"
  kill "$pid"
  for _ in $(seq 1 20); do
    if ! kill -0 "$pid" 2>/dev/null; then
      return
    fi
    sleep 0.25
  done
  kill -KILL "$pid"
}

assert_health() {
  local raw
  raw="$(curl -fsS --max-time 10 "http://127.0.0.1:${PORT}/healthz")"
  "$PY" -c '
import json
import sys
payload = json.load(sys.stdin)
expected_model, expected_sha = sys.argv[1:]
assert payload["status"] == "ok", payload
assert payload["model"] == expected_model, payload
assert payload["checkpoint_step"] == 113100, payload
assert payload["checkpoint_sha256"] == expected_sha, payload
assert payload["device"] == "cuda:0", payload
assert payload["localized_variants"] == 3, payload
assert payload["perspective_variants"] == 12, payload
assert payload["rotation_variants"] == 36, payload
print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
' "$EXPECTED_MODEL" "$EXPECTED_CHECKPOINT_SHA" <<<"$raw"
}

start_root() {
  local root="$1"
  local gpu="$2"
  local log="$3"
  nohup setsid env CERAMIC_GPU="$gpu" CERAMIC_PORT="$PORT" "$root/run.sh" \
    >"$log" 2>&1 < /dev/null &
  echo $!
}

rollback() {
  local current
  current="$(pid_for_port "$PORT")"
  if [ -n "$current" ]; then
    stop_pid "$current"
  fi
  local rollback_log="$OLD_ROOT/logs/rollback-gpu5-$stamp.log"
  local rollback_pid
  rollback_pid="$(start_root "$OLD_ROOT" 7 "$rollback_log")"
  sleep 8
  kill -0 "$rollback_pid"
  assert_health >/dev/null
  echo "ROLLBACK_PID=$rollback_pid" >&2
}

test -x "$OLD_ROOT/run.sh"
test -x "$NEW_ROOT/run.sh"
test -x "$NEW_ROOT/verify.sh"
test "$(sha256sum "$NEW_ROOT/models/checkpoint_decoder_57bit_real18_legacy_pilot3_step600.pt" | awk '{print $1}')" = "$EXPECTED_CHECKPOINT_SHA"

old_pid="$(pid_for_port "$PORT")"
test -n "$old_pid"
test "$(readlink -f "/proc/$old_pid/cwd")" = "$OLD_ROOT"
grep -zqx 'CUDA_VISIBLE_DEVICES=7' "/proc/$old_pid/environ"
assert_health >/dev/null

shadow_pid="$(pid_for_port "$SHADOW_PORT")"
test -n "$shadow_pid"
test "$(readlink -f "/proc/$shadow_pid/cwd")" = "$NEW_ROOT"
grep -zqx 'CUDA_VISIBLE_DEVICES=5' "/proc/$shadow_pid/environ"

stop_pid "$old_pid"
production_log="$NEW_ROOT/logs/production-$stamp.log"
new_pid="$(start_root "$NEW_ROOT" 5 "$production_log")"

ready=0
for _ in $(seq 1 40); do
  sleep 0.5
  if ! kill -0 "$new_pid" 2>/dev/null; then
    break
  fi
  if assert_health >/dev/null 2>&1; then
    ready=1
    break
  fi
done

if [ "$ready" -ne 1 ]; then
  tail -80 "$production_log" >&2 || true
  rollback
  exit 1
fi

if ! CERAMIC_PORT="$PORT" "$NEW_ROOT/verify.sh"; then
  tail -80 "$production_log" >&2 || true
  rollback
  exit 1
fi

test "$(readlink -f "/proc/$new_pid/cwd")" = "$NEW_ROOT"
grep -zqx 'CUDA_VISIBLE_DEVICES=5' "/proc/$new_pid/environ"
echo "$new_pid" >"$NEW_ROOT/service.pid"
stop_pid "$shadow_pid"

echo "ACTIVE_PID=$new_pid"
echo "ACTIVE_CWD=$(readlink -f "/proc/$new_pid/cwd")"
assert_health
nvidia-smi --query-gpu=index,memory.used,utilization.gpu --format=csv,noheader -i 5,7
