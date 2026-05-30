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
