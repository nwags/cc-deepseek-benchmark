#!/usr/bin/env bash
set -euo pipefail

# Current benchmark helper scripts.
python -m py_compile scripts/aggregate_phase.py
python -m py_compile scripts/generate_figures.py
python -m py_compile scripts/summarize_trials.py
python -m py_compile scripts/audit_tool_usage.py
python -m py_compile scripts/anthropic_sanitizer_proxy.py
python -m py_compile scripts/eval_wave.py
python -m py_compile scripts/eval_quality_audit.py
python -m py_compile scripts/generate_phase3_qualitative_audit.py
python -m py_compile scripts/classify_phase3_exception_artifacts.py
python -m py_compile scripts/classify_phase3_normal_failures.py
python -m py_compile scripts/run_qualitative_reporting.py
python -m py_compile scripts/ingest_phase3_run_metadata.py
python -m py_compile scripts/run_arm_live.py
python -m py_compile scripts/publish_phase3_run.py
python -m py_compile scripts/apply_live_supervision_migration.py
python -m py_compile scripts/verify_live_supervision_postgres.py
python -m py_compile scripts/lib/live_events.py
python -m py_compile scripts/lib/live_db.py
python -m py_compile scripts/lib/canonical_publication.py
python -m py_compile scripts/lib/live_artifacts.py
python -m py_compile scripts/lib/live_supervision.py
python -m py_compile scripts/lib/live_verification.py
python -m py_compile scripts/lib/path_safety.py
python -m py_compile scripts/lib/phase3_freeze.py
python -m py_compile scripts/lib/publication_fingerprint.py
python -m py_compile scripts/lib/publication_eligibility.py

bash -n scripts/run_arm.sh
bash -n scripts/check.sh
bash -n scripts/secret_scan.sh
bash -n scripts/ensure_arm_runtime_services.sh
bash -n scripts/stop_arm_runtime_services.sh
bash -n scripts/eval_remote_ops.sh

# Optional legacy syntax check while old-scripts remains as migration backup.
# These are not the preferred entry points, but syntax-checking them is cheap.
if [[ -d scripts/old-scripts ]]; then
  find scripts/old-scripts -maxdepth 1 -type f -name '*.sh' -print0 \
    | xargs -0 -r -n1 bash -n

  find scripts/old-scripts -maxdepth 1 -type f -name '*.py' -print0 \
    | xargs -0 -r -n1 python -m py_compile
fi

echo "check passed"
