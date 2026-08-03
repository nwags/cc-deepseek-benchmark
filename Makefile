REVIEW_OUTPUT_DIR ?= results/manual_verification/comprehensive_review_20260731

.PHONY: check review-output-scan

check:
	bash scripts/check.sh
	cd apps/dashboard && npm run test:trial-analysis
	uv run pytest -q tests
	$(MAKE) review-output-scan

review-output-scan:
	@if [ -d "$(REVIEW_OUTPUT_DIR)" ]; then \
		python3 scripts/scan_comprehensive_review_outputs.py "$(REVIEW_OUTPUT_DIR)"; \
	else \
		printf 'review_output_scan\tskipped_missing_directory\t%s\n' "$(REVIEW_OUTPUT_DIR)"; \
	fi

secret-scan:
	bash scripts/secret_scan.sh

test:
	uv run pytest -q tests

aggregate-phase1:
	uv run python scripts/aggregate_phase.py phase1

aggregate-phase2:
	uv run python scripts/aggregate_phase.py phase2

aggregate-phase3:
	uv run python scripts/aggregate_phase.py phase3

status:
	git status --short

AUDIT_ROOTS ?= results/phase3
HARDENED_AUDIT_ROOTS ?= results/phase3/raw results/phase3/smoke

.PHONY: contamination-audit
contamination-audit:
	uv run python scripts/audit_tool_usage.py results/phase1 results/phase2 results/phase3

.PHONY: contamination-audit-strict
contamination-audit-strict:
	uv run python scripts/audit_tool_usage.py --strict $(AUDIT_ROOTS)

.PHONY: contamination-audit-phase3-hardened
contamination-audit-phase3-hardened:
	uv run python scripts/audit_tool_usage.py --strict --fail-on-available $(HARDENED_AUDIT_ROOTS)


ARM ?= router-anthropic-sonnet
MODE ?= canary
PHASE ?= phase3
SUITE_ID ?= phase3-full-20
RUNS ?=
DEST ?= tmp/eval-artifacts/wave
RUN_DIRS_FILE ?= tmp/eval_wave_run_dirs.tsv
ARMS ?=
MANIFEST_DIR ?= tmp/eval-ingest-manifests
ARTIFACT_PREFIX ?= $(PHASE)
R2_PREFIX ?= $(PHASE)
OVERWRITE ?= 0
DRY_RUN ?= 0
INSPECT_LOCAL ?= 0
LOCAL_ROOTS ?= $(DEST)
SKIP_MISSING_RUN_DIRS ?= false
INVALID_RUNS_FILE ?= configs/eval_invalid_runs.local.tsv
MISSING_INVALID_RUNS_OK ?= 0
EVAL_REMOTE_HOSTS ?= vps1 vps2
EVAL_REMOTE_VPS1_HOST ?= bench@51.81.81.176
EVAL_REMOTE_VPS1_AS_USER ?=
EVAL_REMOTE_VPS1_RUNNER_DIRS ?= /home/bench/actions-runner /home/bench/actions-runner-slot2 /home/bench/actions-runner-slot3
EVAL_REMOTE_VPS2_HOST ?= ubuntu@135.148.42.89
EVAL_REMOTE_VPS2_AS_USER ?= sudo -iu bench
EVAL_REMOTE_VPS2_RUNNER_DIRS ?= /home/bench/actions-runner-slot4 /home/bench/actions-runner-slot5 /home/bench/actions-runner-slot6
EVAL_REMOTE_FIND_LIMIT ?= 80
EVAL_REMOTE_RESCUE_DEST ?= tmp/eval-remote-rescue
EVAL_REMOTE_CLEAN_CONFIRM ?= 0
EVAL_DB_PY ?= uv run --with 'psycopg[binary]' python
EVAL_INGEST_PY ?= uv run --with boto3 --with 'psycopg[binary]' python
EVAL_GH_PY ?= uv run python
OVERWRITE_FLAG = $(if $(filter 1 true yes,$(OVERWRITE)),--overwrite,)
INGEST_FLAGS = $(if $(filter 1 true yes,$(DRY_RUN)),--dry-run,--upload-r2 --insert-db)
INSPECT_LOCAL_FLAG = $(if $(filter 1 true yes,$(INSPECT_LOCAL)),--inspect-local,)
LOCAL_ROOT_ARGS = $(if $(filter 1 true yes,$(INSPECT_LOCAL)),$(foreach root,$(LOCAL_ROOTS),--local-root "$(root)"),)
SKIP_MISSING_RUN_DIRS_FLAG = $(if $(filter 1 true yes,$(SKIP_MISSING_RUN_DIRS)),--skip-missing-run-dirs,)
MISSING_INVALID_RUNS_OK_FLAG = $(if $(filter 1 true yes,$(MISSING_INVALID_RUNS_OK)),--missing-invalid-runs-ok,)
EVAL_REMOTE_ENV = EVAL_REMOTE_HOSTS="$(EVAL_REMOTE_HOSTS)" EVAL_REMOTE_VPS1_HOST="$(EVAL_REMOTE_VPS1_HOST)" EVAL_REMOTE_VPS1_AS_USER="$(EVAL_REMOTE_VPS1_AS_USER)" EVAL_REMOTE_VPS1_RUNNER_DIRS="$(EVAL_REMOTE_VPS1_RUNNER_DIRS)" EVAL_REMOTE_VPS2_HOST="$(EVAL_REMOTE_VPS2_HOST)" EVAL_REMOTE_VPS2_AS_USER="$(EVAL_REMOTE_VPS2_AS_USER)" EVAL_REMOTE_VPS2_RUNNER_DIRS="$(EVAL_REMOTE_VPS2_RUNNER_DIRS)" EVAL_REMOTE_FIND_LIMIT="$(EVAL_REMOTE_FIND_LIMIT)" EVAL_REMOTE_RESCUE_DEST="$(EVAL_REMOTE_RESCUE_DEST)" EVAL_REMOTE_CLEAN_CONFIRM="$(EVAL_REMOTE_CLEAN_CONFIRM)"

.PHONY: litellm-up
litellm-up:
	./scripts/ensure_litellm_proxy.sh

.PHONY: litellm-down
litellm-down:
	./scripts/stop_litellm_proxy.sh

.PHONY: litellm-status
litellm-status:
	@set -e; \
	key="$$(grep '^LITELLM_MASTER_KEY=' .secrets/litellm.env | cut -d= -f2-)"; \
	curl -fsS -H "Authorization: Bearer $$key" http://127.0.0.1:4000/v1/models | python -m json.tool | sed -n '1,80p'

.PHONY: phase3-dry-run
phase3-dry-run:
	./scripts/run_arm.sh phase3-router $(ARM) --mode $(MODE) --dry-run

.PHONY: phase3-run
phase3-run: litellm-up
	@case "$(ARM)" in *sanitized*) $(MAKE) sanitizer-up ;; esac
	./scripts/run_arm.sh phase3-router $(ARM) --mode $(MODE)

.PHONY: phase3-canary
phase3-canary:
	$(MAKE) phase3-run ARM=$(ARM) MODE=canary

.PHONY: phase3-smoke
phase3-smoke:
	$(MAKE) phase3-run ARM=$(ARM) MODE=smoke

.PHONY: eval-suite-summary
eval-suite-summary:
	@set -e; \
	if [ -f .secrets/supabase.env ]; then set -a; . .secrets/supabase.env; set +a; fi; \
	$(EVAL_DB_PY) scripts/eval_quality_audit.py suite-summary \
	  --suite-id "$(SUITE_ID)" \
	  --arms "$(ARMS)"

.PHONY: eval-suite-summary-valid
eval-suite-summary-valid:
	@set -e; \
	if [ -f .secrets/supabase.env ]; then set -a; . .secrets/supabase.env; set +a; fi; \
	$(EVAL_DB_PY) scripts/eval_quality_audit.py suite-summary-valid \
	  --suite-id "$(SUITE_ID)" \
	  --arms "$(ARMS)" \
	  --invalid-runs-file "$(INVALID_RUNS_FILE)" $(MISSING_INVALID_RUNS_OK_FLAG)

.PHONY: eval-arm-run-summary
eval-arm-run-summary:
	@set -e; \
	if [ -f .secrets/supabase.env ]; then set -a; . .secrets/supabase.env; set +a; fi; \
	$(EVAL_DB_PY) scripts/eval_quality_audit.py arm-run-summary \
	  --suite-id "$(SUITE_ID)" \
	  --arms "$(ARMS)"

.PHONY: eval-arm-run-summary-valid
eval-arm-run-summary-valid:
	@set -e; \
	if [ -f .secrets/supabase.env ]; then set -a; . .secrets/supabase.env; set +a; fi; \
	$(EVAL_DB_PY) scripts/eval_quality_audit.py arm-run-summary-valid \
	  --suite-id "$(SUITE_ID)" \
	  --arms "$(ARMS)" \
	  --invalid-runs-file "$(INVALID_RUNS_FILE)" $(MISSING_INVALID_RUNS_OK_FLAG)

.PHONY: eval-exception-audit
eval-exception-audit:
	@set -e; \
	if [ -f .secrets/supabase.env ]; then set -a; . .secrets/supabase.env; set +a; fi; \
	$(EVAL_DB_PY) scripts/eval_quality_audit.py exception-audit \
	  --suite-id "$(SUITE_ID)" \
	  --arms "$(ARMS)" \
	  $(INSPECT_LOCAL_FLAG) \
	  $(LOCAL_ROOT_ARGS)

.PHONY: eval-list-artifacts
eval-list-artifacts:
	$(EVAL_GH_PY) scripts/eval_wave.py list-artifacts \
	  --runs "$(RUNS)" \
	  --suite-id "$(SUITE_ID)" \
	  --phase "$(PHASE)" \
	  --artifact-prefix "$(ARTIFACT_PREFIX)"

.PHONY: eval-download-wave
eval-download-wave:
	$(EVAL_GH_PY) scripts/eval_wave.py download-wave \
	  --runs "$(RUNS)" \
	  --dest "$(DEST)" \
	  --phase "$(PHASE)" \
	  --suite-id "$(SUITE_ID)" \
	  --artifact-prefix "$(ARTIFACT_PREFIX)" \
	  $(OVERWRITE_FLAG)

.PHONY: eval-discover-wave
eval-discover-wave:
	$(EVAL_GH_PY) scripts/eval_wave.py discover-wave \
	  --runs "$(RUNS)" \
	  --dest "$(DEST)" \
	  --phase "$(PHASE)" \
	  --suite-id "$(SUITE_ID)" \
	  --artifact-prefix "$(ARTIFACT_PREFIX)" \
	  --run-dirs-file "$(RUN_DIRS_FILE)" \
	  --arms "$(ARMS)" $(SKIP_MISSING_RUN_DIRS_FLAG)

.PHONY: eval-manifest-wave
eval-manifest-wave:
	$(EVAL_GH_PY) scripts/eval_wave.py manifest-wave \
	  --run-dirs-file "$(RUN_DIRS_FILE)" \
	  --manifest-dir "$(MANIFEST_DIR)" \
	  --suite-id "$(SUITE_ID)" \
	  --phase "$(PHASE)" \
	  --r2-prefix "$(R2_PREFIX)"

.PHONY: eval-ingest-wave
eval-ingest-wave:
	@set -e; \
	if [ -f .secrets/supabase.env ]; then set -a; . .secrets/supabase.env; set +a; fi; \
	if [ -f .secrets/r2.env ]; then set -a; . .secrets/r2.env; set +a; fi; \
	$(EVAL_INGEST_PY) scripts/eval_wave.py ingest-wave \
	  --run-dirs-file "$(RUN_DIRS_FILE)" \
	  --manifest-dir "$(MANIFEST_DIR)" \
	  --suite-id "$(SUITE_ID)" \
	  --phase "$(PHASE)" \
	  --r2-prefix "$(R2_PREFIX)" \
	  $(INGEST_FLAGS)

.PHONY: eval-remote-runner-status
eval-remote-runner-status:
	$(EVAL_REMOTE_ENV) bash scripts/eval_remote_ops.sh status

.PHONY: eval-remote-find-results
eval-remote-find-results:
	$(EVAL_REMOTE_ENV) bash scripts/eval_remote_ops.sh find-results

.PHONY: eval-remote-rescue-results
eval-remote-rescue-results:
	$(EVAL_REMOTE_ENV) bash scripts/eval_remote_ops.sh rescue-results

.PHONY: eval-harbor-cache-clean
eval-harbor-cache-clean:
	$(EVAL_REMOTE_ENV) bash scripts/eval_remote_ops.sh harbor-cache-clean

.PHONY: phase3-suite-summary
phase3-suite-summary: eval-suite-summary

.PHONY: phase3-suite-summary-valid
phase3-suite-summary-valid: eval-suite-summary-valid

.PHONY: phase3-arm-run-summary
phase3-arm-run-summary: eval-arm-run-summary

.PHONY: phase3-arm-run-summary-valid
phase3-arm-run-summary-valid: eval-arm-run-summary-valid

.PHONY: phase3-exception-audit
phase3-exception-audit: eval-exception-audit

.PHONY: phase3-list-artifacts
phase3-list-artifacts: eval-list-artifacts

.PHONY: phase3-download-wave
phase3-download-wave: eval-download-wave

.PHONY: phase3-discover-wave
phase3-discover-wave: eval-discover-wave

.PHONY: phase3-manifest-wave
phase3-manifest-wave: eval-manifest-wave

.PHONY: phase3-ingest-wave
phase3-ingest-wave: eval-ingest-wave


.PHONY: sanitizer-up
sanitizer-up: litellm-up
	./scripts/ensure_anthropic_sanitizer_proxy.sh

.PHONY: sanitizer-down
sanitizer-down:
	./scripts/stop_anthropic_sanitizer_proxy.sh

.PHONY: sanitizer-status
sanitizer-status:
	@set -e; \
	key="$$(grep '^LITELLM_MASTER_KEY=' .secrets/litellm.env | cut -d= -f2-)"; \
	curl -fsS -H "Authorization: Bearer $$key" http://127.0.0.1:4010/v1/models | python -m json.tool | sed -n '1,80p'
