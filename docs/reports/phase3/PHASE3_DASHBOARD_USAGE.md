# Phase 3 Dashboard Usage Guide

The dashboard is the Phase 3 operating console. It should make benchmark state visible and help generate reviewable dispatch payloads, but it should not silently mutate benchmark configuration or promote ad-hoc results into scored results.

## Operating rule

Use the dashboard as a read-only console unless a planner-generated dispatch is explicitly reviewed and launched through GitHub Actions.

Do not use dashboard actions to overwrite Phase 1 or Phase 2 baselines. Do not promote ad-hoc runs into scored Phase 3 results without explicit review.

## Pages and intended use

### Overview

Use the overview page for current Phase 3 status: run count, trial count, canary coverage, smoke readiness, cost coverage, runner readiness, and open blockers.

### Runs

Use the runs page to inspect imported run roots by phase, mode, arm, status, pass rate, runtime, cost, and artifact coverage. Run detail pages should be the first stop when debugging a specific benchmark attempt.

### Arms

Use the arms page to inspect model/backend routes: active or superseded status, canary result, smoke result, known blockers, observed model, provider route, and cost coverage.

### Tasks

Use the tasks page to inspect task-level pass/fail patterns and decide whether a task belongs in canary, smoke, full-sweep, or ad-hoc diagnostics.

### Artifacts

Use the artifacts page to find raw run files, logs, verifier output, trajectories, rewards, GitHub artifact references, and R2-backed artifact metadata. Signed R2 download links should be served only through server-side routes.

### Runner Fleet

Use the runner fleet page to confirm execution readiness before dispatch: runner online/offline state, labels, Docker readiness, firewall doctor status, LiteLLM readiness, hosted-NIM readiness, and any future GPU/self-hosted-NIM labels.

### Sweep Planner

Use the sweep planner to generate reviewable GitHub Actions payloads for `canary`, `smoke`, `full-sweep`, and `ad-hoc` runs. The planner should estimate cost, runtime, runner requirements, and expected artifact destinations before the run is launched.

### Ad-hoc Planner

Use the ad-hoc planner for one-off diagnostics: a single arm, task, attempt, route, or failure-mode investigation. Ad-hoc results are not part of the scored matrix unless explicitly promoted.

### Cost Coverage / Audit

Use the cost coverage view to distinguish:
- valid provider-metered runs,
- zero-token infrastructure failures,
- missing-cost rows,
- and usage-recorded but cost-missing anomalies.

### Provider / Route Readiness

Use provider readiness to track direct API probes, LiteLLM route probes, Claude Code route probes, Harbor canaries, and blockers such as gated models or missing account access.

## Ad-hoc planner status

The dashboard planner may describe ad-hoc diagnostics, but the dashboard remains read-only and does not launch runs.

Script-level ad-hoc support exists through `scripts/run_arm.sh` using `--task-id`, `--task-file`, and `--ad-hoc-label`. GitHub Actions workflow inputs for task overrides now exist on the Phase 3 branch. The dashboard should still treat ad-hoc commands as review-only and non-scored unless explicitly promoted.
