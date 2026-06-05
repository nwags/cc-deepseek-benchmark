# Phase 3 Deck Production Manifest

This manifest describes how to turn the Phase 3 markdown evidence, storyboard, content source, and visual assets into the sponsor-facing slide deck.

It is not the slide deck. It is the production checklist for building the deck.

## Source of truth

Primary narrative source:

- `docs/reports/phase3/PHASE3_DECK_CONTENT.md`

Supporting planning documents:

- `docs/reports/phase3/PHASE3_DECK_STORYBOARD.md`
- `docs/reports/phase3/PHASE3_SLIDE_PLAN.md`
- `docs/reports/phase3/PHASE3_EXECUTIVE_DASHBOARD_SPEC.md`
- `docs/reports/phase3/PHASE3_SPONSOR_BRIEFING_SUPPORT.md`
- `docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md`

Generated evidence and data:

- `results/phase3/supplemental/canary_ledger.csv`
- `results/phase3/supplemental/canary_ledger.json`
- `results/phase3/supplemental/phase3_cost_forecast_canary_scaled.csv`
- `results/phase3/supplemental/phase3_cost_forecast_summary.json`

Visual assets:

- `figures/phase3/deck_assets/phase_3_router_benchmark_architecture_diagram.png`
- `figures/phase3/deck_assets/benchmark_contamination_risks_and_mitigations.png`
- `figures/phase3/deck_assets/phase_3_canary_cost_breakdown.png`
- `figures/phase3/deck_assets/phase_3_metrics_plan_overview.png`

## Intended deck outputs

Recommended output paths:

- Editable deck: `docs/reports/phase3/Phase3_Router_Benchmark_Sponsor_Deck.pptx`
- Review PDF: `docs/reports/phase3/Phase3_Router_Benchmark_Sponsor_Deck.pdf`

Do not commit draft exports unless they are intentionally ready for sponsor review.

## Slide inventory

| Slide | Title | Source | Primary visual | Notes |
|---:|---|---|---|---|
| 1 | Executive dashboard / so what? | `PHASE3_EXECUTIVE_DASHBOARD_SPEC.md`, `PHASE3_DECK_CONTENT.md` | PPT-native dashboard | Must act as conversation hub with clickable KPI cards and jump links |
| 2 | From Phase 1 to Phase 3 | `PHASE3_DECK_CONTENT.md` | PPT-native before/after flow | Show Phase 1 direct arms versus Phase 3 router arms |
| 3 | Router benchmark architecture | `PHASE3_DECK_CONTENT.md` | `phase_3_router_benchmark_architecture_diagram.png` | Add transparent link overlays for Harbor, Claude Code, LiteLLM, providers, results, audit/evidence |
| 4 | Canary gate and task scope | `PHASE3_DECK_CONTENT.md` | PPT-native gate diagram | Emphasize canary is readiness gate, not final model ranking |
| 5 | Current canary-green model arms | `PHASE3_CANARY_EVIDENCE.md` | Compact matrix/table | Show 13 active green arms and 8 provider families |
| 6 | Provider-specific engineering lessons | `PHASE3_ROUTER_FINDINGS.md`, `PHASE3_DECK_CONTENT.md` | Issue-to-resolution table | Frame failures as infrastructure learnings |
| 7 | Contamination controls | `PHASE3_DECK_CONTENT.md` | `benchmark_contamination_risks_and_mitigations.png` | Highlight denied tools and audit path |
| 8 | Canary cost breakdown | `PHASE3_DECK_CONTENT.md` | `phase_3_canary_cost_breakdown.png` | Explain model/provider cost spread and outliers |
| 9 | Funding gate and forecast | `PHASE3_DECK_CONTENT.md` | PPT-native decision path plus cost callouts | Lead to smoke funding request |
| 10 | Recommended next actions | `PHASE3_DECK_CONTENT.md` | Checklist | Close with concrete decision |
| Appendix A | Metrics plan | `PHASE3_DECK_CONTENT.md` | `phase_3_metrics_plan_overview.png` | Use for deeper technical Q&A |
| Appendix B | Evidence hub | `PHASE3_DECK_CONTENT.md` | Link hub | Should be reachable from Slide 1 |

## Slide 1 production requirements

Slide 1 should be built as PPT-native shapes rather than a static image.

Required KPI cards:

- `13 canary-green arms`
- `8 provider families`
- `$44.72 estimated 5-task smoke`
- `Clean contamination audits`

Required decision path:

1. Fund 5-task smoke.
2. Use smoke results to update model/provider cost estimates.
3. Then approve, resize, or defer the full sweep.

Suggested clickable jump targets:

- Current green arms -> Slide 5
- Cost methodology / forecast -> Slides 8 and 9
- Contamination controls -> Slide 7
- Architecture -> Slide 3
- Evidence hub -> Appendix B

## Link overlay plan

PNG assets do not carry embedded object links by default. Add links at the slide layer using transparent shapes or redraw selected elements as PPT-native shapes.

Recommended overlays:

### Slide 3 architecture

- Harbor / Terminal-Bench -> `RUNBOOK.md`
- Arm configs -> `configs/arms/`
- LiteLLM router -> `configs/router/litellm.config.yaml.example`
- Results -> `results/phase3/canary/`
- Audit/evidence extraction -> `scripts/audit_tool_usage.py` and `scripts/extract_phase3_canary_evidence.py`
- Canary evidence report -> `docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md`

### Slide 7 contamination

- Denied tool controls -> `BENCHMARK_CONTAMINATION.md`
- Audit script -> `scripts/audit_tool_usage.py`
- Evidence ledger -> `docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md`

### Slides 8/9 costs

- Cost forecast summary -> `results/phase3/supplemental/phase3_cost_forecast_summary.json`
- Cost forecast CSV -> `results/phase3/supplemental/phase3_cost_forecast_canary_scaled.csv`
- Canary ledger -> `results/phase3/supplemental/canary_ledger.csv`

### Appendix B evidence hub

Use direct links to all key support files listed in this manifest.

## Cost claims to preserve

Use the current canary-scaled rough-order estimates unless smoke results have replaced them:

- Active passing canary cost sum: about `$8.944`
- 5-task smoke estimate: `$44.72`
- 5-task smoke reserve: `$89.44`
- 20-task x 3-attempt full sweep estimate: `$536.64`
- 20-task x 3-attempt full sweep reserve: `$804.97`
- 25-task x 3-attempt expanded sweep estimate: `$670.80`
- 25-task x 3-attempt expanded sweep reserve: `$1,006.21`

Important caveat:

- These are canary-scaled estimates. Smoke results should become the new source of truth before approving the full sweep.

## Speaker-note themes

Use these themes consistently:

- Canary pass means infrastructure readiness, not final model ranking.
- Early failures were mostly auth, quota, route, access, or tool-mode failures.
- Claude Code remains fixed as the agent harness.
- LiteLLM adds provider/model routing breadth.
- Benchmark contamination is actively controlled and audited.
- The funding ask is staged: fund smoke first, then decide on the full sweep.

## Pre-export QA checklist

Before exporting the deck:

- Confirm all slide numbers and appendix references are correct.
- Confirm all KPI values match `PHASE3_CANARY_EVIDENCE.md`.
- Confirm all cost values match `phase3_cost_forecast_summary.json`.
- Confirm no secrets, API keys, raw env values, or private account identifiers appear.
- Confirm links resolve within the repo or exported review package.
- Confirm PNG assets are readable at presentation scale.
- Confirm Slide 1 works as a non-linear navigation hub.
- Confirm the deck says canary readiness, not full benchmark ranking.
- Run `make check`.
- Run `make secret-scan`.

## Git hygiene

Recommended validation before committing deck-related changes:

    git status --short
    git diff --check
    make check
    make secret-scan

Recommended commit message:

    git commit -m "Add Phase 3 deck production manifest"
