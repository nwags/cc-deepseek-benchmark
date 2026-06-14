# Phase 3 Alignment Update - 2026-06-12

This note aligns the Phase 3 router benchmark documentation around the current implementation state and the next execution gates.

## Current status

Phase 3 remains a router-mediated Claude Code backend benchmark using Harbor and Terminal-Bench. The benchmark keeps Claude Code as the fixed agent harness while LiteLLM routes Anthropic-compatible Claude Code traffic to provider backends.

Phase 1 and Phase 2 remain frozen baselines. Phase 3 outputs stay under `results/phase3/...`.

## Current active focus

The active Phase 3 work now has four tracks:

1. Runner fleet / sweep / one-off planner.
2. Dashboard improvement and dashboard usage guidance.
3. Provider/route readiness and smoke planning.
4. Phase 3 documentation review and alignment.

Hosted NVIDIA NIM is retired from the active Phase 3 plan. Locally hosted open-weight models and self-hosted NVIDIA NIM remain tabled until there is a separate GPU/local-serving infrastructure plan. Existing hosted/open-weight-adjacent arms already in the matrix remain in place.

## Planner run types

The planner supports four run types:

| Planner run type | Meaning | Scored status |
|---|---|---|
| `canary` | One known canary task. Infrastructure/model-route gate. | Readiness evidence, not final scoring. |
| `smoke` | Small multi-task gate. Next benchmark milestone after canary. | Preliminary benchmark evidence. |
| `full-sweep` | Large multi-task benchmark battery. | Phase 3 scored source-of-truth when approved and completed. |
| `ad-hoc` | One-off diagnostic run for a model, task, route, or runner issue. | Not scored unless explicitly promoted. |

Implementation note: the current GitHub Actions workflow input uses `mode=full`. The dashboard/planner may display `full-sweep`, but dispatch should map that label to workflow mode `full` unless the workflow is later renamed.

## Current model/route findings to preserve

- Anthropic Fable 5: first canary attempt timed out because Harbor containers could not reach host LiteLLM through the Docker bridge. After the persistent UFW fix, the rerun canary passed.
- Anthropic Mythos 5: direct Anthropic API probe returned HTTP 404 / `not_found_error` for `claude-mythos-5`; treat as gated/unavailable for this account.
- Anthropic OpusPlan: already investigated in Phase 2 as canary/discovery evidence. The alias was accepted, but observed execution looked Sonnet-only and did not show a visible true Plan Mode cycle. Do not rerun it as a normal Phase 3 model arm.
- Hosted NVIDIA NIM: retired from the active Phase 3 plan; revisit only under official paid/quota-approved access.
- Self-hosted NIM and locally hosted open-weight coding models: tabled.

## Runner requirements

Phase 3 runner readiness includes the usual toolchain checks plus Docker-to-host LiteLLM reachability. VPS runners with UFW enabled need persistent Docker bridge allow rules for host port 4000. The runner doctor now checks that path.

## Next benchmark gate

The next benchmark gate is the Phase 3 smoke path, not arbitrary new model canaries. Any future provider layer should first receive explicit approval, then pass direct API probe, LiteLLM route probe, Claude Code route probe, and Harbor canary before entering smoke planning.
