# Phase 3 Executive Dashboard Slide Spec

This document specifies Slide 1 of the Phase 3 sponsor deck. Slide 1 should be built as a PPT-native dashboard, not as a flat image, so KPI cards and navigation targets can become clickable.

## Slide purpose

Answer the sponsor's immediate "so what?" question before any architecture or implementation detail.

Core message:

> Phase 3 is operational enough to proceed to funded smoke testing, but the full sweep should wait until smoke results replace canary-scaled cost estimates.

## Recommended title

Phase 3 Router Benchmark: Canary-Green, Multi-Provider, Ready for Funded Smoke

## Subtitle

Claude Code remains the fixed agent harness; LiteLLM now routes the same benchmark flow across 13 canary-green model arms spanning 8 provider families.

## Dashboard layout

### Top band: headline

Use a concise headline across the top:

- `13 canary-green arms across 8 provider families`
- `Clean contamination audits on passing canaries`
- `Next decision: fund 5-task smoke before full sweep`

### Middle band: four KPI cards

| KPI | Value | Supporting detail | Jump target |
|---|---:|---|---|
| Canary-green arms | 13 | All active current router arms passed the canary task | Current canary-green arms |
| Provider families | 8 | Anthropic, DeepSeek, Gemini, OpenAI, xAI, Moonshot, DashScope/Qwen, Z.AI/GLM | Model-arm matrix |
| 5-task smoke estimate | $44.72 | 2x reserve: $89.44 | Cost methodology |
| Contamination audit | Clean | No WebSearch/WebFetch events in passing canaries | Contamination controls |

### Lower band: decision path

Use three horizontal boxes:

1. Fund 5-task smoke
2. Re-estimate cost from smoke results
3. Approve, resize, or defer full sweep

The lower band should make it clear that the immediate ask is not "fund everything"; it is "fund the smoke layer so we can price the full sweep responsibly."

## Slide 1 evidence links

Add slide-level links or appendix references to:

- `docs/reports/phase3/PHASE3_CANARY_EVIDENCE.md`
- `docs/reports/phase3/PHASE3_SPONSOR_BRIEFING_SUPPORT.md`
- `results/phase3/supplemental/canary_ledger.csv`
- `results/phase3/supplemental/phase3_cost_forecast_summary.json`
- `figures/phase3/deck_assets/phase_3_canary_cost_breakdown.png`
- `figures/phase3/deck_assets/benchmark_contamination_risks_and_mitigations.png`

## Speaker notes

Suggested narration:

Phase 3 has moved the benchmark from a three-arm comparison into a router-mediated, multi-provider harness while keeping Claude Code fixed as the agent. The immediate result is that 13 current router arms are canary-green across 8 provider families. That does not mean we have ranked model quality yet; it means routing, authentication, model slugs, tool controls, and basic end-to-end execution are now good enough to justify funded smoke testing.

The recommended next gate is a 5-task smoke run. The current canary-scaled estimate is about $44.72, with a conservative 2x reserve of about $89.44. We should not approve the full 20-task × 3-attempt sweep until the smoke layer gives us provider-specific cost behavior across multiple tasks.

## Design notes

- Build KPI cards as editable shapes.
- Use hyperlinks on the KPI cards if producing a PowerPoint or Google Slides deck.
- Avoid dense tables on Slide 1.
- Put detailed arm-level costs and evidence in later slides or appendix.
- Use architecture/cost/contamination PNGs as supporting thumbnails only if space allows.
