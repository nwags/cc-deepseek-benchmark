# Phase 3 main merge plan

## Purpose

This document prepares a reviewed plan for updating main from the Phase 3 release-candidate branch.

It is a planning artifact only. It does not perform the merge.

## Current branch roles

- main: frozen Phase 1 baseline.
- phase3: current release-candidate branch with Phase 3 results, cross-phase comparisons, cost coverage, closeout artifacts, and release-readiness notes.

## Required pre-merge artifacts

- docs/reports/phase3/PHASE3_RELEASE_CANDIDATE_20260715.md
- docs/reports/phase3/PHASE3_CLOSEOUT_INDEX_20260714.md
- docs/reports/phase3/PHASE3_CROSS_PHASE_COMPARISON_20260714.md
- docs/reports/phase3/PHASE3_CROSS_PHASE_TASK_AUDIT_20260714.md
- results/phase3/reporting/phase3_closeout_artifact_audit_20260715.tsv
- results/phase3/reporting/phase3_main_merge_impact_20260715.txt

## Pre-merge checks

Run from phase3 before any merge approval:

    python -m py_compile scripts/generate_cross_phase_adjusted_comparison.py scripts/generate_cross_phase_task_audit.py scripts/generate_phase3_frontier_html.py scripts/audit_phase3_closeout_artifacts.py
    uv run python scripts/audit_phase3_closeout_artifacts.py
    bash scripts/check.sh
    uv run pytest -q tests
    bash scripts/secret_scan.sh
    git diff --check
    git status --short --untracked-files=all

Expected result:

- all checks pass
- no raw secrets detected
- working tree clean

## Merge strategy options

### Option A: reviewed merge commit

Use a merge commit from phase3 into main after review. This preserves branch history and makes the transition explicit.

### Option B: fast-forward main

Only use this if main has not diverged and the intent is to make Phase 3 the direct successor of the frozen baseline.

### Option C: keep main frozen and tag phase3

Use this if Phase 1 should remain the default branch for now. In this case, tag phase3 as a release candidate and avoid changing main.

## Dry-run merge result

A temporary worktree dry-run merge from origin/main to origin/phase3 was performed on 2026-07-15.

Result:

- one expected conflict: .github/workflows/phase3-arm-dispatch.yml
- conflict resolved during dry-run by taking the origin/phase3 version
- remaining unmerged file count after resolution: 0
- cached dry-run merge shortstat: 8227 files changed, 1744860 insertions, 28 deletions
- compact evidence file: results/phase3/reporting/phase3_main_dryrun_merge_summary_20260715.txt

## Recommendation

Do not update main until explicitly approved. The next safe action is a dry-run merge in a temporary worktree to check for conflicts and produce a final merge-readiness note.
