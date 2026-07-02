#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${LITELLM_ENV_FILE:-.secrets/litellm.env}"
PORT="${SANITIZER_PORT:-4010}"
HOST="${SANITIZER_HOST:-0.0.0.0}"
LITELLM_UPSTREAM_PORT="${LITELLM_PORT:-4000}"
UPSTREAM="${SANITIZER_UPSTREAM:-http://127.0.0.1:${LITELLM_UPSTREAM_PORT}}"
HEALTH_URL="${SANITIZER_HEALTH_URL:-http://127.0.0.1:${PORT}/v1/models}"

RUN_DIR="${SANITIZER_RUN_DIR:-.run/anthropic-sanitizer}"
LOG_FILE="$RUN_DIR/sanitizer.log"
PID_FILE="$RUN_DIR/sanitizer.pid"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE"
  exit 1
fi

set -a
source "$ENV_FILE"
set +a

: "${LITELLM_MASTER_KEY:?LITELLM_MASTER_KEY is required in $ENV_FILE}"

mkdir -p "$RUN_DIR"

is_ready() {
  curl -fsS \
    -H "Authorization: Bearer ${LITELLM_MASTER_KEY}" \
    "$HEALTH_URL" >/dev/null 2>&1
}

if is_ready; then
  echo "Anthropic sanitizer proxy is already reachable at $HEALTH_URL"
  exit 0
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" || true)"
  if [[ -n "${old_pid:-}" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "Stopping stale sanitizer process $old_pid"
    kill "$old_pid" 2>/dev/null || true
    sleep 1
  fi
  rm -f "$PID_FILE"
fi

echo "Starting Anthropic sanitizer proxy in the background"
echo "  host:     $HOST"
echo "  port:     $PORT"
echo "  upstream: $UPSTREAM"
echo "  log:      $LOG_FILE"

SANITIZER_HOST="$HOST" \
SANITIZER_PORT="$PORT" \
SANITIZER_UPSTREAM="$UPSTREAM" \
  nohup uv run python scripts/anthropic_sanitizer_proxy.py >"$LOG_FILE" 2>&1 &

pid="$!"
echo "$pid" > "$PID_FILE"

for _ in $(seq 1 60); do
  if is_ready; then
    echo "Anthropic sanitizer proxy is ready at $HEALTH_URL"
    echo "pid: $pid"
    exit 0
  fi
  sleep 1
done

echo "Anthropic sanitizer proxy did not become ready."
echo "See $LOG_FILE"
exit 1
