# Phase 3 release candidate / merge-readiness note

## Status

Phase 3 is prepared as a release candidate on branch `phase3`.

This note is a merge-readiness artifact only. It does not modify `main`. The frozen Phase 1 baseline remains intact unless an explicit merge/replacement step is performed later.

## Current branch policy

- `main`: frozen Phase 1 baseline.
- `phase3`: current Phase 3 benchmark/reporting branch.
- Phase 1 and Phase 2 aggregate source files remain frozen.
- Phase 3 reporting artifacts live under `docs/reports/phase3/` and `results/phase3/reporting/`.

## New closeout artifacts

- `docs/reports/phase3/PHASE3_COMPREHENSIVE_ANALYSIS_20260716.md`
- `docs/reports/phase3/PHASE3_ROUTER_EFFECT_COMPARISON_20260716.md`
- `docs/reports/phase3/PHASE3_CLOSEOUT_INDEX_20260714.md`
- `docs/reports/phase3/PHASE3_CROSS_PHASE_COMPARISON_20260714.md`
- `docs/reports/phase3/PHASE3_CROSS_PHASE_TASK_AUDIT_20260714.md`
- `docs/reports/phase3/PHASE3_COST_COVERAGE_20260712.md`
- `docs/reports/phase3/PHASE3_SPONSOR_SUMMARY_20260713.md`
- `docs/reports/phase3/PHASE3_BENCHMARK_ANALYSIS_20260713.md`
- `docs/reports/phase3/PHASE3_DATABRICKS_COMPARISON_20260713.md`
- `configs/tasks/phase3_task_taxonomy.tsv`
- `results/phase3/reporting/router_effect_comparison_20260716.tsv`
- `results/phase3/reporting/phase3_task_family_arm_matrix_20260716.tsv`
- `results/phase3/reporting/phase3_arm_behavior_profile_20260716.tsv`

## Key validation claims

- Phase 3 valid full-suite set: 15 arms x 60 trials = 900 scored trials.
- Cross-phase comparison now includes Phase 1, Phase 2, and Phase 3.
- Phase 1/2 adjusted-cost coverage is derived retrospectively without modifying frozen source aggregates.
- Task-suite audit confirms Phase 1, Phase 2, and Phase 3 use the same 20 tasks.
- Every scored arm across Phase 1, Phase 2, and Phase 3 has 20 tasks x 3 attempts = 60 trials.
- Phase 3 routing path remains explicitly labeled as LiteLLM/router-mediated.
- Comprehensive analysis now includes router-associated comparison, task-family performance, cost efficiency, wastage, and arm behavior profiles.

## Required pre-merge checks

Run from the repo root:

    python -m py_compile \
      scripts/generate_cross_phase_adjusted_comparison.py \
      scripts/generate_cross_phase_task_audit.py \
      scripts/generate_phase3_frontier_html.py \
      scripts/generate_phase3_comprehensive_analysis.py

    bash scripts/check.sh
    uv run pytest -q tests
    bash scripts/secret_scan.sh
    git diff --check
    git status --short --untracked-files=all

Expected result:

- syntax checks pass
- project check passes
- pytest passes
- secret scan passes
- diff check passes
- working tree is clean

## Recent pushed closeout commits

    323e195a Fix Phase 3 comprehensive analysis EOF whitespace
    6214849c Add Phase 3 comprehensive analysis
    d2aca6ca Document Phase 3 main dry-run merge
    d8e2788b Add Phase 3 main merge plan
    aa6c61c2 Fix sponsor summary EOF whitespace
    77c2e85b Add Phase 3 closeout index
    c4e28c88 Add Phase 3 frontier and report artifacts
    ceb7e30c Normalize task ids in cross-phase task audit
    18497389 Add cross-phase task suite audit
    1cbca403 Add cross-phase adjusted cost comparison
    55ec2862 Add Databricks comparison memo

## Merge note

Do not merge or reset `main` until explicitly approved. When approved, prefer a deliberate reviewed merge plan rather than an accidental fast-forward or branch overwrite.
