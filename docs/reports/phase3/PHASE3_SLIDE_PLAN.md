# Phase 3 Sponsor Slide Plan

Source docs:
- PHASE3_SPONSOR_BRIEFING_SUPPORT.md
- PHASE3_CANARY_EVIDENCE.md

## Deck goal

Explain the Phase 3 router benchmark status, why it matters, what is ready, what risks remain, and what funding is needed before smoke/full sweeps.

## Slide 1 — Executive dashboard / so what?

Headline:
Phase 3 converted the benchmark from a 3-arm comparison into a canary-verified, multi-provider router harness.

Key bullets:
- 13 active router arms are canary-green.
- 8 provider families are covered.
- Failures were mostly access/config/quota/tool-mode issues, not model-quality failures.
- WebSearch/WebFetch/Plan/User-question tools are denied where applicable.
- Recommended next gate: funded 5-task smoke.
- Estimated 5-task smoke: $44.72; reserve: $89.44.
- Estimated 20-task × 3 full sweep: $536.64; reserve: $804.97.
- Estimated 25-task × 3 expanded sweep: $670.80; reserve: $1,006.21.

Fast-jump links:
- Current green arms
- Cost methodology
- Contamination controls
- Historical blockers
- Evidence ledger

Visual:
Executive dashboard with four headline metrics:
13 green arms / 8 providers / $44.72 smoke estimate / clean contamination audits.

## Slide 2 — What changed from Phase 1 to Phase 3?

Message:
Phase 1 compared three direct/provider-compatible arms. Phase 3 adds a router layer and broadens provider coverage while keeping Claude Code fixed as the agent harness.

Visual:
Before/after architecture.

## Slide 3 — Architecture and control flow

Message:
Claude Code remains the fixed agent harness. LiteLLM routes model calls to provider backends. Harbor runs Terminal-Bench and captures results.

Visual:
Sponsor request → arm config → run_arm.sh → Harbor → Claude Code → LiteLLM → providers → results → audit/evidence extraction.

## Slide 4 — Canary gate and benchmark scope

Message:
The canary is an infrastructure readiness test, not a quality ranking.

Task:
modernize-scientific-stack

Why useful:
- Reads files
- Writes files
- Runs code
- Verifies behavior
- Exercises end-to-end routing cheaply

## Slide 5 — Current canary-green model matrix

Message:
13 arms are ready for funded smoke testing.

Visual:
Table grouped by provider:
Anthropic, DeepSeek, Gemini, OpenAI, xAI, Moonshot/Kimi, DashScope/Qwen, Z.AI/GLM.

## Slide 6 — Historical blockers and recoveries

Message:
The failed routes are now engineering history, not current blockers.

Examples:
- Grok 3 → Grok Build 0.1 after funding/model route normalization
- Kimi K2.5 → Kimi K2.6 after funding/model update
- Qwen 3.5 → Qwen 3.7 Plus after Singapore endpoint/model access
- GLM 5 → GLM 5.1 after funding/model update

## Slide 7 — Contamination controls

Message:
Contamination mitigation is now built into the router methodology.

Evidence:
- WebSearch/WebFetch denied
- EnterPlanMode/ExitPlanMode/AskUserQuestion denied where applicable
- Canary audits clean
- audit_tool_usage.py reproducible

## Slide 8 — Cost forecast and funding gate

Message:
Do not jump straight to full sweep. Run smoke first to replace canary-scaled estimates with real multi-task costs.

Numbers:
- 5-task smoke: $44.72; 2x reserve $89.44
- 20-task × 3: $536.64; 1.5x reserve $804.97
- 25-task × 3: $670.80; 1.5x reserve $1,006.21

Visual:
Bar chart: smoke / full sweep / expanded sweep.

## Slide 9 — Cost outliers and budget risk

Message:
Gemini Flash and GPT-5.5 were high-cost canary outliers; smoke should test whether that persists.

Visual:
Canary cost by arm figure.

## Slide 10 — Recommended next actions

1. Confirm smoke task list.
2. Secure smoke funding.
3. Run 5-task smoke across 13 active arms.
4. Regenerate evidence/cost forecast from smoke results.
5. Decide whether to approve 20-task × 3 sweep.
6. Decide whether expanded/newer tasks are needed for contamination-risk mitigation.

## Appendix A — Evidence links

Include:
- sponsor briefing support doc
- canary evidence ledger
- canary_ledger.csv/json
- cost forecast files
- figures
- configs/arms
- litellm router config
- result directories

## Appendix B — Per-arm evidence table

Use the current canary-green table from PHASE3_SPONSOR_BRIEFING_SUPPORT.md.

## Appendix C — Historical failed/superseded canaries

Use historical blocker table, clearly labeled as resolved/superseded.
