#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

RUN_DIR="${SANITIZER_RUN_DIR:-.run/anthropic-sanitizer}"
PID_FILE="$RUN_DIR/sanitizer.pid"

if [[ ! -f "$PID_FILE" ]]; then
  echo "No sanitizer PID file at $PID_FILE"
  exit 0
fi

pid="$(cat "$PID_FILE" || true)"

if [[ -z "${pid:-}" ]]; then
  rm -f "$PID_FILE"
  echo "Empty sanitizer PID file removed."
  exit 0
fi

if kill -0 "$pid" 2>/dev/null; then
  echo "Stopping Anthropic sanitizer proxy pid $pid"
  kill "$pid"
else
  echo "Sanitizer pid $pid is not running."
fi

rm -f "$PID_FILE"
