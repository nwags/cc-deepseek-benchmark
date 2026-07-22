#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

ENV_FILE="${LITELLM_ENV_FILE:-.secrets/litellm.env}"
PORT="${LITELLM_PORT:-4000}"
HOST="${LITELLM_HOST:-0.0.0.0}"
HEALTH_URL="${LITELLM_HEALTH_URL:-http://127.0.0.1:${PORT}/v1/models}"

RUN_DIR="${LITELLM_RUN_DIR:-.run/litellm}"
LOG_FILE="$RUN_DIR/litellm.log"
PID_FILE="$RUN_DIR/litellm.pid"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "Missing $ENV_FILE"
  echo "Create it from configs/router/litellm.env.example."
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
  echo "LiteLLM proxy is already reachable at $HEALTH_URL"
  exit 0
fi

if [[ -f "$PID_FILE" ]]; then
  old_pid="$(cat "$PID_FILE" || true)"
  if [[ -n "${old_pid:-}" ]] && kill -0 "$old_pid" 2>/dev/null; then
    echo "LiteLLM process $old_pid exists but health check failed."
    echo "See $LOG_FILE"
  else
    rm -f "$PID_FILE"
  fi
fi

echo "Starting LiteLLM proxy in the background"
echo "  host: $HOST"
echo "  port: $PORT"
echo "  log:  $LOG_FILE"

LITELLM_HOST="$HOST" LITELLM_PORT="$PORT" \
  nohup ./scripts/start_litellm_proxy.sh >"$LOG_FILE" 2>&1 &

pid="$!"
echo "$pid" > "$PID_FILE"

for _ in $(seq 1 60); do
  if is_ready; then
    echo "LiteLLM proxy is ready at $HEALTH_URL"
    echo "pid: $pid"
    exit 0
  fi
  sleep 1
done

echo "LiteLLM proxy did not become ready within 60s."
echo "Last 120 log lines:"
tail -120 "$LOG_FILE" || true
exit 1
