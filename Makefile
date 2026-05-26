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