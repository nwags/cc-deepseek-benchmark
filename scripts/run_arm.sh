#!/usr/bin/env bash
set -euo pipefail

# Config-driven Harbor arm runner.
#
# Examples:
#   ./scripts/run_arm.sh phase2 anthropic-sonnet --mode canary --dry-run
#   ./scripts/run_arm.sh phase3-router router-gemini-flash --mode smoke --dry-run
#
# Defaults to canary mode for safety.

python -m scripts.lib.harbor "$@"
