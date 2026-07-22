#!/usr/bin/env bash
set -euo pipefail

usage() {
  echo "Usage: scripts/stop_arm_runtime_services.sh <arm_id>" >&2
}

if [[ "$#" -ne 1 ]]; then
  usage
  exit 2
fi

ARM_ID="$1"
ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

CONFIG_DIR="${ARM_CONFIG_DIR:-configs/arms}"
CONFIG_FILE="$CONFIG_DIR/${ARM_ID}.yaml"
DRY_RUN="${ARM_RUNTIME_SERVICES_DRY_RUN:-0}"
PYTHON_RUNNER="${PYTHON_RUNNER:-uv run python}"

run_python() {
  local runner=()
  read -r -a runner <<< "$PYTHON_RUNNER"
  "${runner[@]}" "$@"
}

if [[ ! -f "$CONFIG_FILE" ]]; then
  echo "Arm config not found: $CONFIG_FILE" >&2
  exit 1
fi

runtime_services_text="$(run_python - "$CONFIG_FILE" <<'PY'
from __future__ import annotations

import sys
from pathlib import Path

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required to read arm runtime_services metadata.") from exc

path = Path(sys.argv[1])
data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
services = data.get("runtime_services") or []
if not isinstance(services, list):
    raise SystemExit(f"{path}: runtime_services must be a list")
for service in services:
    if not isinstance(service, str) or not service.strip():
        raise SystemExit(f"{path}: runtime_services entries must be non-empty strings")
    print(service.strip())
PY
)"

runtime_services=()
if [[ -n "$runtime_services_text" ]]; then
  mapfile -t runtime_services <<< "$runtime_services_text"
fi

if [[ "${#runtime_services[@]}" -eq 0 ]]; then
  echo "No runtime services declared for arm: $ARM_ID"
  exit 0
fi

for service in "${runtime_services[@]}"; do
  case "$service" in
    anthropic-sanitizer)
      if [[ "$DRY_RUN" == "1" || "$DRY_RUN" == "true" || "$DRY_RUN" == "yes" ]]; then
        echo "Would stop runtime service for $ARM_ID: anthropic-sanitizer"
      else
        echo "Stopping runtime service for $ARM_ID: anthropic-sanitizer"
        ./scripts/stop_anthropic_sanitizer_proxy.sh
      fi
      ;;
    *)
      echo "Unknown runtime service '$service' declared for arm $ARM_ID in $CONFIG_FILE" >&2
      exit 1
      ;;
  esac
done
