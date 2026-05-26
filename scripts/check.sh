#!/usr/bin/env bash
set -euo pipefail

# Current Phase 3 migration scripts.
python -m py_compile scripts/aggregate_phase.py
python -m py_compile scripts/generate_figures.py
python -m py_compile scripts/summarize_trials.py

bash -n scripts/run_arm.sh
bash -n scripts/check.sh
bash -n scripts/secret_scan.sh

# Optional legacy syntax check while old-scripts remains as migration backup.
# These are not the preferred entry points, but syntax-checking them is cheap.
if [[ -d scripts/old-scripts ]]; then
  find scripts/old-scripts -maxdepth 1 -type f -name '*.sh' -print0 \
    | xargs -0 -r -n1 bash -n

  find scripts/old-scripts -maxdepth 1 -type f -name '*.py' -print0 \
    | xargs -0 -r -n1 python -m py_compile
fi

echo "check passed"
