#!/usr/bin/env bash
set -euo pipefail

NEW_ROOT=/data0/liyanlei/ceramic_watermark/services/decoder_gpu7_real18_locator4_perspective_20260816
OLD_ROOT=/data0/liyanlei/ceramic_watermark/services/decoder_gpu7_real18_locator3_20260816
PORT=28765
PY=/data0/liyanlei/ceramic_watermark/envs/miniconda/bin/python
EXPECTED_MODEL=trustmark-q-57bit-real18-step113100-locator4-perspective
OLD_MODEL=trustmark-q-57bit-real18-step113100-locator3
EXPECTED_CHECKPOINT_SHA=834d33d4666921f1ae6416d5c3a9d08a7ac60dc9dc21f4ce907caa5923e1d6ef
EXPECTED_APP_SHA=9da3108669da59585f21b67e05a916888179ffd0977c1a7e00a59911259486b8
stamp="$(date +%Y%m%d-%H%M%S)"

pid_for_port() {
  ss -ltnp 2>/dev/null | sed -n "s/.*:${1}.*pid=\([0-9]*\).*/\1/p" | head -1
}

stop_pid() {
  local pid="$1"
  kill "$pid"
  sleep 2
  if kill -0 "$pid" 2>/dev/null; then
    kill -KILL "$pid"
  fi
}

assert_new_health() {
  local raw
  raw="$(curl -fsS --max-time 10 "http://127.0.0.1:$PORT/healthz")"
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
assert payload["perspective_variants"] == 8, payload
print(json.dumps(payload, ensure_ascii=False, sort_keys=True))
' "$EXPECTED_MODEL" "$EXPECTED_CHECKPOINT_SHA" <<<"$raw"
}

rollback() {
  local current
  current="$(pid_for_port "$PORT")"
  if [ -n "$current" ]; then
    stop_pid "$current"
  fi
  nohup setsid "$OLD_ROOT/run.sh" \
    >"$OLD_ROOT/logs/rollback-perspective-$stamp.log" 2>&1 < /dev/null &
  sleep 8
  local raw
  raw="$(curl -fsS --max-time 10 "http://127.0.0.1:$PORT/healthz")"
  grep -q "$OLD_MODEL" <<<"$raw"
  grep -q "$EXPECTED_CHECKPOINT_SHA" <<<"$raw"
  echo "ROLLBACK_HEALTH=$raw"
}

test -x "$NEW_ROOT/run.sh"
test -x "$NEW_ROOT/verify.sh"
test "$(sha256sum "$NEW_ROOT/decoder_api/app.py" | awk '{print $1}')" = "$EXPECTED_APP_SHA"
test "$(sha256sum "$NEW_ROOT/models/checkpoint_decoder_57bit_real18_legacy_pilot3_step600.pt" | awk '{print $1}')" = "$EXPECTED_CHECKPOINT_SHA"

old_health="$(curl -fsS --max-time 10 "http://127.0.0.1:$PORT/healthz")"
grep -q "$OLD_MODEL" <<<"$old_health"
grep -q "$EXPECTED_CHECKPOINT_SHA" <<<"$old_health"
old_pid="$(pid_for_port "$PORT")"
test -n "$old_pid"
test "$(readlink -f "/proc/$old_pid/cwd")" = "$OLD_ROOT"

stop_pid "$old_pid"
production_log="$NEW_ROOT/logs/production-$stamp.log"
nohup setsid "$NEW_ROOT/run.sh" >"$production_log" 2>&1 < /dev/null &
new_pid=$!
sleep 8

if ! kill -0 "$new_pid" 2>/dev/null; then
  tail -80 "$production_log" >&2
  rollback
  exit 1
fi
if ! assert_new_health; then
  tail -80 "$production_log" >&2
  rollback
  exit 1
fi
if ! "$NEW_ROOT/verify.sh"; then
  tail -80 "$production_log" >&2
  rollback
  exit 1
fi

echo "$new_pid" > "$NEW_ROOT/service.pid"
echo "ACTIVE_PID=$new_pid"
echo "ACTIVE_CWD=$(readlink -f "/proc/$new_pid/cwd")"
nvidia-smi -i 7 --query-compute-apps=pid,process_name,used_memory --format=csv,noheader
