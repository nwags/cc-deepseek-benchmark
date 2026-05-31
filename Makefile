check:
	bash scripts/check.sh
	uv run pytest -q tests

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
	./scripts/run_arm.sh phase3-router $(ARM) --mode $(MODE)

.PHONY: phase3-canary
phase3-canary:
	$(MAKE) phase3-run ARM=$(ARM) MODE=canary

.PHONY: phase3-smoke
phase3-smoke:
	$(MAKE) phase3-run ARM=$(ARM) MODE=smoke
