# Phase 3 Sponsor Deck Content Source

This file is the source text for the eventual Phase 3 sponsor deck. It is more specific than the storyboard and should be used to build the PowerPoint deck.

## Slide 1 — Executive dashboard / so what?

Title:
Phase 3 Router Benchmark: Canary-Green, Multi-Provider, Ready for Funded Smoke

Subtitle:
Claude Code remains the fixed agent harness; LiteLLM routes the same benchmark flow across 13 canary-green model arms spanning 8 provider families.

KPI cards:
- 13 canary-green arms
- 8 provider families
- $44.72 estimated 5-task smoke
- Clean contamination audits

Main takeaway:
Phase 3 is operational enough to proceed to funded smoke testing, but the full sweep should wait until smoke results replace canary-scaled cost estimates.

Decision path:
1. Fund 5-task smoke.
2. Use smoke results to update model/provider cost estimates.
3. Then approve, resize, or defer the full sweep.

Visual:
PPT-native dashboard layout.

Evidence links:
- docs/reports/phase3/PHASE3_EXECUTIVE_DASHBOARD_SPEC.md
- docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md
- results/phase3/supplemental/canary_ledger.csv
- results/phase3/supplemental/phase3_cost_forecast_summary.json

Speaker notes:
Lead with impact before implementation detail. The key message is not “all models are ranked”; it is “the infrastructure gate is now green enough to justify funded smoke testing.”

## Slide 2 — From Phase 1 to Phase 3

Title:
From Three-Arm Baseline to Multi-Provider Router Harness

Bullets:
- Phase 1 compared three direct/provider-compatible arms.
- Phase 3 keeps Claude Code fixed as the agent harness.
- LiteLLM adds a router layer for provider/model expansion.
- Canary-first execution catches auth, quota, route, schema, and tool-mode failures before expensive runs.
- Results remain separated under results/phase3.

Visual:
Simple before/after architecture comparison.

Evidence links:
- docs/reports/phase3/PHASE3_ROUTER_FINDINGS.md
- configs/router/litellm.config.yaml.example
- configs/arms/

Speaker notes:
Emphasize methodological continuity: Claude Code remains fixed, so the experiment is still about backend/model behavior through a controlled harness.

## Slide 3 — Router benchmark architecture

Title:
Phase 3 Router Benchmark Architecture

Bullets:
- Harbor orchestrates Terminal-Bench task execution.
- Claude Code performs the agent workflow inside the benchmark environment.
- LiteLLM routes Anthropic-compatible requests to provider backends.
- Provider responses flow back through LiteLLM to Claude Code and Harbor.
- Results are audited and converted into evidence ledgers and figures.

Visual asset:
figures/phase3/deck_assets/phase_3_router_benchmark_architecture_diagram.png

Evidence links:
- scripts/run_arm.sh
- configs/router/litellm.config.yaml.example
- scripts/audit_tool_usage.py
- scripts/extract_phase3_canary_evidence.py

Speaker notes:
Mention that the request and response flow is bidirectional between Claude Code, LiteLLM, and provider backends. The arrows in the figure should be interpreted as workflow and response loops, not one-way-only pipes.

## Slide 4 — Canary gate and task scope

Title:
The Canary Is an Infrastructure Readiness Gate, Not a Final Ranking

Bullets:
- Canary task: Terminal-Bench 2.0 modernize-scientific-stack.
- Exercises file reads, file writes, command execution, and verification.
- Small enough to run before smoke/full sweeps.
- Pass means routing/config/tool controls are ready for smoke.
- Pass does not mean the model has been quality-ranked across the benchmark.

Visual:
Canary gate funnel: direct provider probe → router probe → Harbor canary → audit → smoke eligibility.

Evidence links:
- docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md
- results/phase3/canary/
- docs/reports/phase3/PHASE3_SPONSOR_BRIEFING_SUPPORT.md

Speaker notes:
This slide prevents overclaiming. The correct sponsor takeaway is that infrastructure is ready for a funded smoke layer.

## Slide 5 — Current canary-green model arms

Title:
13 Active Router Arms Are Canary-Green

Bullets:
- Passing arms span Anthropic, DeepSeek, Gemini, OpenAI, xAI, Moonshot/Kimi, DashScope/Qwen, and Z.AI/GLM.
- All active current arms completed the canary task with reward 1.0.
- Historical blocked routes are retained as engineering evidence but are not current blockers.

Visual:
Provider/model matrix with PASS status.

Evidence links:
- results/phase3/supplemental/canary_ledger.csv
- docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md

Speaker notes:
Keep the table readable. Put dense per-arm token and path detail in the appendix.

## Slide 6 — Provider-specific engineering lessons

Title:
Most Early Failures Were Infrastructure Issues, Not Model-Quality Failures

Bullets:
- Gemini required route correction and no-plan tool mitigation.
- Qwen required Singapore endpoint and model-access normalization.
- xAI required funding/access recovery and updated model selection.
- Moonshot/Kimi required updated model selection and awareness of temperature/max-token behavior.
- Z.AI/GLM required funding/access recovery and updated model route.

Visual:
Issue → diagnosis → fix → current status table.

Evidence links:
- docs/reports/phase3/PHASE3_ROUTER_FINDINGS.md
- configs/router/litellm.config.yaml.example
- configs/arms/

Speaker notes:
Frame this as de-risking. Each failure sharpened the runbook and reduced full-sweep surprise risk.

## Slide 7 — Contamination controls

Title:
Benchmark Contamination Is Controlled Explicitly

Bullets:
- Router arms deny WebSearch and WebFetch.
- Router arms also deny EnterPlanMode, ExitPlanMode, and AskUserQuestion where applicable.
- Canary audits showed no actual WebSearch/WebFetch tool-use events.
- Passing canaries had clean contamination audits.
- Remaining contamination risk should be addressed with careful task selection and possible expanded/newer task coverage.

Visual asset:
figures/phase3/deck_assets/benchmark_contamination_risks_and_mitigations.png

Evidence links:
- BENCHMARK_CONTAMINATION.md
- scripts/audit_tool_usage.py
- docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md

Speaker notes:
Avoid saying contamination risk is zero. Say the known web/tool exposure path is controlled and audited.

## Slide 8 — Canary cost breakdown

Title:
Canary Costs Vary Strongly by Provider and Model

Bullets:
- Active passing canary cost sum: about $8.944.
- GPT-5.5 and Gemini Flash were the largest canary cost outliers.
- Low canary cost arms included DeepSeek Pro, GLM 5.1, and DeepSeek Flash.
- One canary task is not enough to lock the full budget.
- Smoke is needed to distinguish persistent cost patterns from one-task artifacts.

Visual asset:
figures/phase3/deck_assets/phase_3_canary_cost_breakdown.png

Evidence links:
- results/phase3/supplemental/canary_ledger.csv
- results/phase3/supplemental/phase3_cost_forecast_canary_scaled.csv
- results/phase3/supplemental/phase3_cost_forecast_summary.json

Speaker notes:
This is the main funding-risk slide. The sponsor should see why staged funding is prudent.

## Slide 9 — Funding gate and forecast

Title:
Recommended Gate: Fund Smoke Before Full Sweep

Bullets:
- 5-task smoke estimate: $44.72; recommended reserve: $89.44.
- 20-task × 3-attempt full sweep estimate: $536.64; reserve: $804.97.
- 25-task × 3-attempt expanded sweep estimate: $670.80; reserve: $1,006.21.
- Smoke results should replace canary-scaled estimates before full-sweep approval.
- Expanded sweep can add coverage or mitigate contamination risk after the 20-task sweep.

Visual:
Funding ladder: canary complete → smoke funding → smoke results → full sweep decision → optional expanded sweep.

Evidence links:
- results/phase3/supplemental/phase3_cost_forecast_summary.json
- docs/reports/phase3/PHASE3_SPONSOR_BRIEFING_SUPPORT.md

Speaker notes:
The ask is not “fund everything now.” The ask is “fund the next statistically and financially sensible gate.”

## Slide 10 — Recommended next actions

Title:
Next Actions

Bullets:
- Confirm the exact 5-task smoke set.
- Confirm budget approval for smoke plus reserve.
- Run smoke across the 13 active green router arms.
- Re-run evidence extraction after smoke.
- Replace canary-scaled estimates with smoke-scaled estimates.
- Decide whether to proceed to 20-task full sweep or expanded task coverage.

Visual:
Checklist with ownership/status columns.

Evidence links:
- RUNBOOK.md
- docs/reports/phase3/PHASE3_DECK_STORYBOARD.md
- docs/reports/phase3/PHASE3_EXECUTIVE_DASHBOARD_SPEC.md

Speaker notes:
Close by making the decision concrete: approve smoke funding and task list.

## Appendix A — Metrics plan

Title:
Metrics Collected and Planned

Bullets:
- Reward/pass rate.
- Exceptions and error classes.
- Runtime/wall-clock.
- Token usage: input, cache, output.
- Cost by arm, provider, and task.
- Tool exposure and actual tool-use audit.
- Trajectory evidence for qualitative failure analysis.
- Provider/model observed route metadata.

Visual asset:
figures/phase3/deck_assets/phase_3_metrics_plan_overview.png

Evidence links:
- scripts/extract_phase3_canary_evidence.py
- results/phase3/supplemental/canary_ledger.csv
- results/phase3/canary/

Speaker notes:
This appendix supports deeper technical questions without cluttering main slides.

## Appendix B — Evidence hub

Title:
Evidence and Reproducibility Hub

Bullets:
- Canary evidence report.
- Canary ledger CSV/JSON.
- Cost forecast CSV/JSON.
- Router and arm configs.
- Result directories.
- Contamination notes.
- Runbook and artifact policy.

Evidence links:
- docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md
- results/phase3/supplemental/canary_ledger.csv
- results/phase3/supplemental/canary_ledger.json
- results/phase3/supplemental/phase3_cost_forecast_canary_scaled.csv
- results/phase3/supplemental/phase3_cost_forecast_summary.json
- configs/router/litellm.config.yaml.example
- configs/arms/
- BENCHMARK_CONTAMINATION.md
- RUNBOOK.md
- ARTIFACT_POLICY.md

Speaker notes:
This slide is for non-linear sponsor discussion. It should be reachable from Slide 1 if the deck format supports links.
