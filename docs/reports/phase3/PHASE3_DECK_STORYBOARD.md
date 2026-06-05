# Phase 3 Sponsor Deck Storyboard

This document expands `PHASE3_SLIDE_PLAN.md` into a slide-by-slide production storyboard. It is still not the PowerPoint deck.

## Design principles

- Slide 1 must work as an executive dashboard and conversation hub.
- Each major claim should have a nearby evidence link or appendix path.
- The deck should be navigable non-linearly because sponsor discussion may jump around.
- Main slides should focus on impact; appendices should carry dense evidence.
- Canary pass should be framed as infrastructure readiness, not final model ranking.

## Slide 1 — Executive dashboard / so what?

Purpose:
Open with impact, status, funding ask, and the key decision.

Layout:
- Title across top.
- Four KPI cards across the middle:
  - 13 canary-green arms
  - 8 provider families
  - $44.72 estimated 5-task smoke
  - Clean contamination audits
- Bottom row: three decision boxes:
  - Fund smoke
  - Re-estimate from smoke
  - Then approve / defer full sweep

Main message:
Phase 3 is operational enough to proceed to funded smoke testing, but not yet mature enough to skip directly to the full sweep.

Evidence links:
- `docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md`
- `results/phase3/supplemental/canary_ledger.csv`
- `results/phase3/supplemental/phase3_cost_forecast_summary.json`

Likely sponsor questions:
- Which models are ready?
- Why not run the full sweep now?
- Are the costs reliable?
- What changed from Phase 1?
- How are we controlling contamination?

Jump targets:
- Slide 5 for ready arms.
- Slide 7 for contamination.
- Slide 8 for cost methodology.
- Appendix A for evidence links.

## Slide 2 — From Phase 1 to Phase 3

Purpose:
Show the evolution from a narrow benchmark to a provider-router benchmark platform.

Layout:
Two-column before/after.

Left:
Phase 1:
- 3 arms
- direct/provider-compatible routes
- 20 tasks × 3 attempts
- quality/cost/speed comparison

Right:
Phase 3:
- 13 active canary-green router arms
- LiteLLM router
- broader provider coverage
- staged canary → smoke → full sweep gates
- trajectory/evidence extraction

Main message:
Phase 3 is not just “more models”; it is a more scalable benchmark harness.

Evidence links:
- `docs/reports/phase3/PHASE3_SPONSOR_BRIEFING_SUPPORT.md`
- `docs/PHASE3_ROUTER_FINDINGS.md`

## Slide 3 — Architecture and control flow

Purpose:
Explain how the benchmark actually runs.

Layout:
Architecture diagram.

Flow:
Sponsor question → arm config → `scripts/run_arm.sh` → Harbor → Terminal-Bench 2.0 → Claude Code → LiteLLM → provider backend → result artifacts → audit/evidence extraction.

Main message:
Claude Code stays fixed as the agent harness; the model backend varies through the router.

Evidence links:
- `configs/arms/`
- `configs/router/litellm.config.yaml.example`
- `scripts/run_arm.sh`
- `scripts/extract_phase3_canary_evidence.py`

Visual asset:
Use or redraw the Mermaid architecture from `PHASE3_SPONSOR_BRIEFING_SUPPORT.md`.

## Slide 4 — Canary gate and task scope

Purpose:
Prevent overclaiming from one canary task.

Layout:
Left: what the canary exercises.
Right: what it does not prove.

Exercises:
- file reading
- file writing
- code execution
- verification
- end-to-end routing

Does not prove:
- full model quality
- cross-task robustness
- stable cost behavior
- long-run provider reliability

Main message:
A canary pass means “safe to smoke test,” not “best model.”

Evidence links:
- Example result JSON
- Example trajectory JSON
- `PHASE3_CANARY_EVIDENCE.md`

## Slide 5 — Current canary-green model matrix

Purpose:
Show readiness by provider/model.

Layout:
Grouped table by provider family.

Columns:
- Provider
- Router arm
- Backend model
- Canary cost
- Runtime
- Evidence path

Main message:
The active router matrix now spans Anthropic, DeepSeek, Gemini, OpenAI, xAI, Moonshot/Kimi, DashScope/Qwen, and Z.AI/GLM.

Evidence links:
- `results/phase3/supplemental/canary_ledger.csv`
- `docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md`

## Slide 6 — Historical blockers and recoveries

Purpose:
Frame failures as resolved infrastructure learnings.

Layout:
Recovery chain table.

Columns:
- Initial blocked arm
- Failure class
- Root issue
- Replacement/fix
- Current status

Rows:
- `router-grok-3` → `router-grok-build-0.1`
- `router-kimi-k2.5` → `router-kimi-k2.6`
- `router-qwen-3.5` → `router-qwen-3.7-plus`
- `router-glm-5` → `router-glm-5.1`

Main message:
Most early failures were access, quota, route, or tool-mode issues rather than benchmark-quality failures.

Evidence links:
- `docs/PHASE3_ROUTER_FINDINGS.md`
- `PHASE3_CANARY_EVIDENCE.md`

## Slide 7 — Contamination controls

Purpose:
Show that benchmark contamination risk is being actively controlled.

Layout:
Three-layer control stack.

Layer 1:
Tool denial:
- `WebSearch`
- `WebFetch`
- `EnterPlanMode`
- `ExitPlanMode`
- `AskUserQuestion`

Layer 2:
Audit:
- `scripts/audit_tool_usage.py`
- strict mode
- fail-on-available checks

Layer 3:
Reporting:
- evidence ledger
- result paths
- contamination notes

Main message:
Phase 3 treats contamination mitigation as a measurable control.

Evidence links:
- `scripts/audit_tool_usage.py`
- `BENCHMARK_CONTAMINATION.md`
- `PHASE3_CANARY_EVIDENCE.md`

## Slide 8 — Cost forecast and funding gate

Purpose:
Make the funding request concrete.

Layout:
Bar chart plus staged gate diagram.

Numbers:
- 5-task smoke: $44.72; reserve $89.44
- 20-task × 3: $536.64; reserve $804.97
- 25-task × 3: $670.80; reserve $1,006.21

Main message:
Approve smoke funding now; defer full-sweep approval until smoke gives real multi-task cost data.

Evidence links:
- `results/phase3/supplemental/phase3_cost_forecast_canary_scaled.csv`
- `results/phase3/supplemental/phase3_cost_forecast_summary.json`

## Slide 9 — Cost outliers and budget risk

Purpose:
Explain why smoke is needed before full sweep.

Layout:
Use `figures/phase3/canary_cost_by_arm.png`.

Main message:
Gemini Flash and GPT-5.5 were canary cost outliers. Smoke should determine whether they are persistently expensive or one-task artifacts.

Evidence links:
- `figures/phase3/canary_cost_by_arm.png`
- `canary_ledger.csv`

## Slide 10 — Recommended next actions

Purpose:
Close with a decision path.

Layout:
Numbered action ladder.

Actions:
1. Confirm smoke task list.
2. Secure smoke budget.
3. Run 5-task smoke across 13 active arms.
4. Regenerate evidence and cost forecast from smoke.
5. Decide on 20-task × 3 full sweep.
6. Decide whether to add newer/different tasks for contamination-risk mitigation.

Main message:
The next funded action is smoke, not full sweep.

## Appendix A — Evidence hub

Include direct links to:
- sponsor support doc
- canary evidence doc
- canary ledger CSV/JSON
- cost forecast CSV/JSON
- figures
- arm configs
- router config
- result directories

## Appendix B — Per-arm evidence table

Use the full canary-green arm table.

## Appendix C — Historical failed/superseded canaries

Use the resolved blocker table.

## Appendix D — Slide 1 Q&A jump map

Question:
Which models are ready?
Jump:
Slide 5 / Appendix B

Question:
What failed?
Jump:
Slide 6 / Appendix C

Question:
What will this cost?
Jump:
Slide 8 / Slide 9

Question:
How do we know web tools were blocked?
Jump:
Slide 7

Question:
Where is the raw evidence?
Jump:
Appendix A
