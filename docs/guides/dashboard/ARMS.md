# Arms page guide

## Executive summary

Arms is a broad all-imported model/backend inventory, not a leaderboard. Canary, smoke, diagnostic,
legacy, invalid, and full evidence can all contribute. The page is also where canonical
`agent_harness` identity is surfaced when recorded, making the existing harness dimension visible
without activating a future harness-comparison phase.

## Route and implementation

- Dashboard route: `/arms`.
- Page source: `apps/dashboard/src/app/arms/page.tsx`.

## Data sources

- Supabase all-imported arm aggregates through `getArmRows()`.
- All-imported freshness from the latest included arm execution.
- Canonical arm metadata provides provider family, backend identity, and `agent_harness`.

## Population and authority

- Every imported run for an arm can contribute regardless of canary/smoke/full/diagnostic/legacy
  classification or validity.
- The pass rate therefore does not share the reviewed Overview denominator.
- Recorded cost is summed from captured raw cost rows; missing rows make it a displayed lower bound.

## How to read the page

- Use Arms to discover what arm identities exist and how much imported evidence is attached to each.
- Read model/provider/harness identity separately from performance aggregates.
- Use the links to Runs, Trial Quality, and Artifacts before making a quality claim.

## Controls and filters

- There are no page-level filters.
- Per-arm links open Trial Quality and Artifacts filtered to that arm, while Runs opens the
  canonical execution index.

## Caveats and non-inferences

- Do not rank models from the all-imported pass-rate column.
- A high run count can reflect diagnostics rather than more full-suite evidence.
- `agent_harness` being present is canonical identity, not evidence that Phase 4 is active.
- Recorded lower-bound cost is not equivalent to current selected/provider-aware Cost Coverage.

## Common workflows

- Use Arms when checking model/provider/harness identity or finding all evidence associated with an
  arm.
- For fair performance comparison, move to Overview/Cross-phase or an exact valid full-suite run.

## Evidence tracing

- Arm row → Runs → exact arm run → trial/artifact evidence.
- Arm recorded-cost warning → Cost Coverage for reviewed cost authority.

## Related documentation

- [Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md) for the cross-page research workflow
  and evidence-reading order.
- [Runs page guide](RUNS.md).
- [Cost Coverage page guide](COST_COVERAGE.md).
- [Project Handoff and Future Roadmap](../PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md).
