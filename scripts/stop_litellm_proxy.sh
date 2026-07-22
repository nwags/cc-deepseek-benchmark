#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_DIR="${LITELLM_RUN_DIR:-.run/litellm}"
PID_FILE="$RUN_DIR/litellm.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No LiteLLM pid file found at $PID_FILE"
  exit 0
fi

pid="$(cat "$PID_FILE" || true)"

if [[ -z "${pid:-}" ]]; then
  rm -f "$PID_FILE"
  echo "Removed empty pid file."
  exit 0
fi

if kill -0 "$pid" 2>/dev/null; then
  echo "Stopping LiteLLM proxy pid $pid"
  kill "$pid" 2>/dev/null || true
  sleep 2
  if kill -0 "$pid" 2>/dev/null; then
    echo "Process still running; sending SIGKILL"
    kill -9 "$pid" 2>/dev/null || true
  fi
else
  echo "LiteLLM pid $pid is not running."
fi

rm -f "$PID_FILE"
