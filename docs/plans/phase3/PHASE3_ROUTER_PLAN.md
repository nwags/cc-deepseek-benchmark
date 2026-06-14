# Phase 3 Plan: Router-Mediated Claude Code Provider Expansion

## Status

Phase 3 is active.

This phase begins on branch `phase3` after Phase 1 and Phase 2 were frozen. The purpose is to test whether Claude Code can be used with additional model providers through a router/gateway layer while preserving the same broad Terminal-Bench / Harbor benchmark methodology.

## Research question

```text
What happens when Claude Code remains the agent harness, but non-Anthropic and non-DeepSeek providers are reached through a router-mediated Anthropic-compatible pathway?
```

Phase 3 is not just "more Phase 2 arms." It introduces a new routing layer. That means the system under test becomes:

```text
Harbor
  -> Terminal-Bench task
  -> Claude Code agent harness
  -> router/gateway
  -> provider/model backend
```

The router may affect tool calling, token accounting, latency, cost reporting, model-name metadata, error behavior, and request/response translation. For that reason, router-mediated results should be reported separately from native Phase 2 results.

## Goals

1. Establish a safe, reproducible router-mediated Claude Code workflow.
2. Run canary tests for selected provider/model arms.
3. Run smoke tests only after routing is confirmed.
4. Compare router-mediated control arms against native Phase 2 behavior.
5. Select a limited scored Phase 3 sweep only after canary and smoke evidence.
6. Preserve Phase 1 and Phase 2 outputs unchanged.

## Candidate routers / gateways

Phase 3 may evaluate one or more of:

- Claude Code Router
- Bifrost
- OpenRouter-compatible proxying
- provider-specific Anthropic-compatible adapters
- custom local shim if necessary

The selected router must support enough of Claude Code's expected Anthropic Messages API behavior to run Terminal-Bench tasks through Harbor.

## Planned router arms

Initial placeholder configs exist under `configs/arms/`.

New provider arms:

| Arm | Provider/model family | Placeholder backend model |
|---|---|---|
| `router-gpt-5.5` | OpenAI | `gpt-5.5` |
| `router-gpt-5.4` | OpenAI | `gpt-5.4` |
| `router-gpt-5.3` | OpenAI | `gpt-5.3` |
| `router-gemini-3.1-pro` | Google Gemini | `gemini-3.1-pro` |
| `router-grok-3` | xAI/Grok | `grok-3` |
| `router-kimi-k2.5` | Moonshot/Kimi | `kimi-k2.5` |
| `router-qwen-3.5` | Qwen | `qwen-3.5` |
| `router-glm-5` | Z.AI/GLM | `glm-5` |

Router-mediated control arms:

| Arm | Purpose |
|---|---|
| `router-anthropic-haiku` | Compare router-mediated Anthropic Haiku to native Phase 2 Haiku |
| `router-anthropic-sonnet` | Compare router-mediated Sonnet to native Phase 1/2 Sonnet |
| `router-anthropic-opus` | Compare router-mediated Opus to native Phase 2 Opus |
| `router-deepseek-pro` | Compare router-mediated DeepSeek Pro to direct Anthropic-compatible DeepSeek Pro |
| `router-deepseek-flash` | Compare router-mediated DeepSeek Flash to direct Anthropic-compatible DeepSeek Flash |

## Important placeholder caveat

Model slugs in the placeholder configs are not yet guaranteed to be the exact router/provider slugs.

Before any paid run, verify:

- exact provider model slug
- router config syntax
- authentication mechanism
- Anthropic-compatible base URL
- token/cost reporting fields
- observed model metadata
- whether tool-use translation works
- whether streaming output works with Claude Code
- whether Claude Code's tool loop remains stable

## Phase 3 design stages

### Stage 0: repo readiness

- Keep Phase 1 and Phase 2 frozen.
- Keep results phase-specific.
- Use config-driven scripts where possible.
- Add tests for config validity and frozen aggregate cost totals.
- Run `make check` and `make secret-scan`.

### Stage 1: router installation and hello-world canaries

For each router option:

1. Install router locally or configure hosted endpoint.
2. Confirm a trivial Claude Code prompt works.
3. Confirm a trivial Harbor/Claude Code canary works.
4. Confirm raw artifacts are written under `results/phase3/canary/`.
5. Confirm observed model metadata or router model metadata can be captured.
6. Confirm no secrets are written into result artifacts.

### Stage 2: model-specific canaries

Run a one-task canary for each candidate arm:

```bash
./scripts/run_arm.sh phase3-router <arm-id> --mode canary
```

Canary task file:

```text
configs/tasks/phase2-canary.txt
```

Expected result path:

```text
results/phase3/canary/<arm>/
```

Acceptance criteria:

- Harbor starts successfully.
- Claude Code starts successfully.
- Router routes to the intended provider/model.
- The task completes or fails as a model/task failure, not as a routing/setup failure.
- Observed model information is captured where possible.
- No secrets are written to logs.

### Stage 3: smoke tests

Run the 5-task smoke list for arms that pass canary:

```bash
./scripts/run_arm.sh phase3-router <arm-id> --mode smoke
```

Smoke task file:

```text
configs/tasks/phase2-smoke.txt
```

Expected result path:

```text
results/phase3/smoke/<arm>/
```

Smoke criteria:

- no systematic routing errors
- no systematic tool-use translation errors
- costs are plausible
- wall-clock times are plausible
- observed model metadata is recoverable or explicitly documented as unavailable

### Stage 4: select scored Phase 3 arms

Do not run every placeholder arm as a full 20-task x 3-attempt scored sweep by default.

Recommended first scored set after smoke tests:

- `router-anthropic-sonnet`
- `router-deepseek-pro`
- `router-gpt-5.4` or `router-gpt-5.5`
- `router-gemini-3.1-pro`
- `router-grok-3`
- `router-kimi-k2.5`
- `router-qwen-3.5`
- `router-glm-5`

This keeps the first scored router sweep broad but not unmanageably large.

## Source-of-truth paths

Phase 3 results:

```text
results/phase3/
```

Canary:

```text
results/phase3/canary/
```

Smoke:

```text
results/phase3/smoke/
```

Scored full sweep:

```text
results/phase3/raw/
```

Aggregate:

```text
results/phase3/combined.csv
```

Supplemental analysis:

```text
results/phase3/supplemental/
```

Figures:

```text
figures/phase3/
```

Reports:

```text
docs/reports/phase3/
```

## Metrics

Reuse Phase 2 metrics where possible:

- success
- reward
- wall-clock seconds
- agent execution seconds
- input tokens
- cache tokens
- output tokens
- provider-reported cost
- router-reported cost
- computed cost
- effective cost
- observed model
- router model
- exception type
- failure mode
- agent turns
- tool calls
- Bash calls
- edit/write calls
- read/search calls
- repeated Bash commands

New Phase 3 router-specific fields should include where available:

- router name
- router version
- router endpoint type
- backend provider
- backend model slug
- request ID / generation ID
- router-reported prompt tokens
- router-reported completion tokens
- router-reported cached tokens
- router-reported cost
- provider billing reconciliation status

## Cost-accounting plan

Phase 3 should preserve the Phase 1/2 lesson:

- Anthropic native costs can use provider-reported cost where available.
- DeepSeek direct costs should use computed cache-aware cost.
- Router-mediated costs need explicit validation.

For router arms, prefer this hierarchy:

1. exact per-request router/provider cost when available
2. router usage endpoint / generation stats when available
3. local deterministic estimate from token counts and versioned rate table
4. manual billing dashboard reconciliation for sanity checks

Every cost table should use an explicit `effective_cost_usd` field and explain how it was derived.

## Risks

- Router tool-use translation may break Claude Code behavior.
- Router model slugs may differ from public model names.
- Provider costs may not be visible per request.
- Cached-token accounting may not be exposed.
- Observed model metadata may be missing or ambiguous.
- Some providers may not support the required tool schema or streaming behavior.
- Router latency may dominate model latency.
- Provider rate limits may bias wall-clock time.
- Running too many full arms may exceed budget.

## Exit criteria

Phase 3 can be considered complete when:

- selected router canaries are run and documented
- selected smoke tests are run and documented
- one scored router-mediated sweep is completed or consciously deferred
- `results/phase3/combined.csv` exists if a scored sweep is run
- Phase 3 report explains router methodology separately from Phase 2
- costs are traceable and clearly caveated
- secrets scan passes
- Phase 1 and Phase 2 results remain unchanged

## Deliverables

Minimum deliverables:

- populated router configs
- canary/smoke runbook updates
- canary/smoke results or documented setup blockers
- Phase 3 analysis notes
- Phase 3 report if a scored sweep is run

Preferred deliverables:

- scored Phase 3 aggregate
- router cost-audit script
- compact trial summarizer
- router compatibility matrix
- recommendation on which providers are worth full sweeps

<!-- phase3-2026-06-12-alignment:start -->
## 2026-06-12 alignment: current Phase 3 scope

The active Phase 3 scope is router-mediated model/provider evaluation with Claude Code fixed as the agent harness. The immediate work is no longer arbitrary model addition; it is:

1. runner fleet / sweep / ad-hoc planner,
2. dashboard improvement and usage guidance,
3. hosted NVIDIA NIM route-readiness,
4. documentation alignment.

Planner run types are `canary`, `smoke`, `full-sweep`, and `ad-hoc`. The current workflow input still uses `mode=full`; planner UI may label this as `full-sweep` but should dispatch `mode=full` until the workflow is renamed.

Do not add self-hosted NIM, local open-weight serving, or new local model infrastructure in this phase. Existing hosted arms remain in the matrix.
<!-- phase3-2026-06-12-alignment:end -->

## NVIDIA NIM removed from active plan

Hosted NVIDIA NIM is no longer planned for Phase 3 route-readiness or canary work. The active plan should focus on the already canary-green router arms, dashboard/planner maturity, ad-hoc diagnostics, and smoke planning. NIM should only be reconsidered through official paid/quota-approved access.
