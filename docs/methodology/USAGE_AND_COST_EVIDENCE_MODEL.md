# Usage and Cost Evidence Model

Status: current methodology contract as of 2026-08-30.

This document defines how benchmark token usage and cost evidence must be
captured, reconciled, qualified, and promoted before decision-facing benchmark
results are treated as economically valid.

The contract is intentionally harness-agnostic.

Claude Code is the current benchmark harness and is the implementation through
which the motivating failure was discovered. Future work may use other coding
agents or execution harnesses. No harness-reported token or cost field is
authoritative merely because it exists or is numeric.

## Core invariant

A successful benchmark execution does not establish that its telemetry is
correct.

These are separate states:

    execution success
    telemetry availability
    model-identity validity
    usage validity
    cost validity
    benchmark-quality validity

A run may therefore be valid for task-quality analysis while remaining
unqualified for token-usage or cost comparison.

For example:

    benchmark_status = success
    usage_validation_status = mismatch
    cost_validation_status = unverified

must be representable without rewriting the successful benchmark result.

## Why this contract exists

Phase 3 provider-evidence review exposed a silent failure mode.

A historical routed DeepSeek execution could:

- send requests successfully to DeepSeek;
- complete the benchmark normally;
- record a plausible numeric cost;
- retain an Anthropic/Sonnet model identity in harness metadata;
- produce no immediate benchmark failure.

The resulting cost could therefore look ordinary while being materially wrong.

This is more dangerous than a hard failure because a hard failure is visible.
A plausible but incorrect cost can silently contaminate:

- total-spend comparisons;
- cost per attempt;
- cost per success;
- Pareto frontiers;
- sponsor conclusions;
- later empirical pricing reconstruction.

The permanent lesson is not "Claude Code cost can be wrong."

The permanent lesson is:

> Harness telemetry is evidence, not authority, until independently qualified.

## Three evidence layers

Every run can have three independent evidence families.

### 1. Harness evidence

Examples:

- harness-observed model;
- input tokens;
- cached tokens;
- output tokens;
- harness-reported cost;
- request/session metadata.

Current example: Claude Code through Harbor.

Future examples could include another coding agent, a custom harness, or another
benchmark runner.

Harness evidence must be preserved as immutable provenance even when later
shown to be inaccurate.

### 2. Provider usage evidence

Examples:

- provider request IDs;
- provider-observed model;
- ordinary input tokens;
- cache-read tokens;
- cache-creation/cache-write tokens;
- output tokens;
- request count;
- request timestamps;
- project/account usage exports;
- request logs.

Provider usage evidence is the independent branch used to validate token usage
and model identity.

### 3. Provider cost evidence

Examples:

- request-level billed charges;
- selected-run billed totals;
- provider invoices;
- dashboard totals;
- provider usage plus a pinned pricing snapshot;
- published rate tables;
- account-level spend context.

Provider cost evidence is the independent branch used to validate cost.

Provider usage evidence and provider cost evidence must not be collapsed into a
single generic "provider evidence" status.

## Two independent validation branches

### Usage validation branch

The usage branch asks:

> What token usage and model identity can we defend for this selected run?

It compares, where available:

    configured route model
    configured backend model
    harness-observed model
    provider-observed model

and:

    harness input tokens
    harness cache tokens
    harness output tokens

against provider-visible classes such as:

    provider ordinary input tokens
    provider cache-read tokens
    provider cache-creation/write tokens
    provider output tokens

The branch also records:

- provider request count;
- how many requests join to the selected arm run;
- how many requests join to exact trials;
- how many provider requests remain unallocated;
- completeness of the provider evidence;
- whether provider request timing overlaps the selected run;
- whether provider and configured model identities match.

Usage validation statuses are:

- `validated_exact`
- `validated_qualified`
- `provisional`
- `mismatch`
- `unverified`
- `unavailable`

`validated_qualified` means the evidence is usable but has explicit limitations.

`provisional` is allowed only during early qualification such as Canary and
must record its limitations.

### Cost validation branch

The cost branch asks:

> What is the best defensible cost authority for this selected run?

Possible evidence includes:

- harness-reported cost;
- provider request-level billed cost;
- provider selected-run billed cost;
- provider dashboard or invoice totals;
- provider-rate reconstruction from provider usage;
- provider-rate reconstruction from already validated harness usage;
- explicit lower bounds.

Cost validation statuses use the same high-level vocabulary:

- `validated_exact`
- `validated_qualified`
- `provisional`
- `mismatch`
- `unverified`
- `unavailable`

A numeric harness cost is never automatically `validated_exact`.

## Best-available cost authority

"Best available" does not mean that every provider must expose the same type of
billing evidence.

The preferred authority order is generally:

    provider billed charge allocated to exact request/trial/run
      >
    provider billed selected-run aggregate with defensible allocation
      >
    provider usage reconstructed with a pinned provider pricing snapshot
      >
    validated harness usage reconstructed with a pinned provider pricing snapshot
      >
    harness-reported cost independently validated against provider evidence
      >
    explicit provider-evidence lower bound
      >
    unresolved

This is not permission to substitute a broader provider total for cleaner
selected-run evidence.

A provider-family or account total that cannot be allocated remains context,
not selected-run cost.

A provider snapshot that predates the selected run cannot reconcile that run.

## Pricing reconstruction safety

Rate reconstruction is permitted only when the retained token classes are
sufficient to reproduce the provider's pricing rules.

For example, Harbor's current Claude Code conversion retains:

    prompt_tokens =
        provider input
        + cache read
        + cache creation

and:

    cached_tokens = cache read

This representation is sufficient for a provider whose pricing distinguishes
only cache-hit input from other input.

It is not sufficient when cache creation/write has its own price unless the
cache-creation quantity is retained separately elsewhere.

Pricing may also depend on:

- request-level context thresholds;
- model variants;
- time-dependent rates;
- batch versus interactive service;
- region;
- subscription or credit treatment.

A reconstruction that lacks a required pricing dimension must fail closed.

## Provider evidence storage

Provider evidence should be durable and queryable.

Large or immutable raw evidence should normally follow the existing project
artifact pattern:

    provider export / request log / invoice / snapshot
        -> immutable R2 object
        -> SHA-256
        -> R2 URI
        -> normalized Supabase evidence rows

Supabase should retain first-class normalized records for:

- provider evidence source provenance;
- provider usage evidence;
- provider pricing snapshots;
- provider cost evidence;
- usage reconciliations;
- cost reconciliations;
- Canary/Smoke promotion gates.

The current normalized schema and fail-closed promotion contract are implemented
by Migration 011:

    db/migrations/phase3/011_provider_evidence_contract.sql

The durable human-review operator path is:

    scripts/review_evidence_promotion.py

The provider source row must retain enough provenance to recover exactly which
provider artifact or provider record supported a conclusion.

Do not store:

- API keys;
- bearer tokens;
- authentication headers;
- secret-bearing request payloads.

Provider account/project references must be non-secret identifiers or sanitized
labels.

## Canary, Smoke, and Full are evidence gates

Canary and Smoke are not only execution-stability tests.

They are the calibration stages for usage and cost authority.

### Before Canary

For a new arm, identify:

- configured route identity;
- expected backend identity;
- provider evidence location;
- provider usage mechanism;
- provider billing mechanism;
- pricing source;
- expected cache/token classes;
- expected provider request identifiers;
- any known billing delay.

A dry run can validate command construction but cannot validate provider usage
or billed cost.

### Canary: establish evidence visibility and a candidate authority

A paid Canary should be the cheapest practical real provider execution.

Before Canary can advance to Smoke, verify:

- the request reaches the intended provider/backend;
- provider evidence for the request becomes visible;
- provider-observed model identity matches the intended backend;
- provider usage can be associated with the Canary run;
- a defensible usage authority is identified;
- a defensible cost-authority candidate is identified;
- required pricing semantics are known;
- any limitations are explicitly recorded.

Canary may advance with `provisional` usage or cost authority because Smoke is
the stage intended to test repeatability.

A Canary must not advance merely because:

- the benchmark task passed;
- the harness emitted tokens;
- the harness emitted a numeric cost.

### Smoke: validate repeatability and the best available authority

Smoke should exercise enough requests/tasks to validate:

- repeated provider request visibility;
- exact or defensible run allocation;
- model identity stability;
- token-class semantics;
- cache behavior;
- request-level pricing tiers;
- provider/harness usage deltas;
- cost reconstruction;
- provider billing behavior;
- missing or zero telemetry;
- timing and billing-window alignment.

Before Smoke can advance to Full:

    usage_validation_status
        must be validated_exact or validated_qualified

and:

    cost_validation_status
        must be validated_exact or validated_qualified

and:

- provider evidence must be visible for both branches;
- model identity must match;
- selected usage authority must be non-null;
- selected cost must be non-null;
- selected cost basis must not be an unvalidated harness estimate;
- every qualified limitation must be explicit.

`provisional` is not sufficient for Full.

### Full sweep

Full sweep is an experiment, not a telemetry-discovery stage.

A full sweep should inherit already reviewed:

- provider evidence capture mechanics;
- model-identity checks;
- usage authority;
- cost authority;
- pricing snapshot;
- allocation rules;
- provider-family limits.

If Full reveals a new usage or cost mismatch, economic qualification should
fail closed even if benchmark execution remains usable.

## Promotion state machine

The normal progression is:

    dry-run
       |
       v
    Canary
       |
       | evidence visible
       | model identity matched
       | usage authority established
       | cost authority candidate established
       v
    Smoke
       |
       | usage validated_exact / validated_qualified
       | cost validated_exact / validated_qualified
       | limitations explicit
       v
    Full

A policy waiver must never silently convert into an automatic pass.

The implemented promotion-review contract supports explicit `pass`, `blocked`,
and `waived` decisions.

A `waived` decision:

- requires an attributable reviewer and a non-empty waiver reason;
- is retained as review provenance;
- remains separate from an evidence-qualified `pass`;
- must derive `gate_decision_not_pass`;
- must leave `effective_can_advance = false`.

A later advancement requires a new reviewed `pass` that supersedes the waiver;
the waiver itself is never authorization.

## Promotion binding and staleness invariants

A promotion decision is valid only for one exact evidence chain.

The promotion gate must bind:

    arm
    source arm run
    source mode
    usage reconciliation
    cost reconciliation

to the same benchmark execution.

A gate must fail closed when:

- the source arm run belongs to another arm;
- the source arm run mode differs from the gate source mode;
- the usage reconciliation belongs to another arm run;
- the cost reconciliation belongs to another arm run;
- the usage reconciliation is no longer current;
- the cost reconciliation is no longer current.

Superseding either reconciliation therefore invalidates the effective
promotion status of an older gate until that gate is reviewed again against
the new evidence.

The database may retain a stale or mismatched gate as auditable provenance.
Retention is not authorization. Derived blocker codes must make the reason
visible and `effective_can_advance` must remain false.

### Durable review binding

The implemented durable review path adds an operator-side race/staleness
contract around those database invariants.

`--check-only` reads the exact source run, current usage reconciliation, current
cost reconciliation, and current promotion gate in a repeatable-read/read-only
transaction. It emits four mutation pins:

    expected_usage_reconciliation_id
    expected_cost_reconciliation_id
    expected_current_gate_id
    expected_state_sha256

The state SHA-256 covers material reviewed source-run, reconciliation,
limitation, and current-gate state.

`--rollback-only` and `--apply` require all four pins. They then:

1. acquire a transaction-scoped advisory lock for the arm/target-mode review
   slot;
2. re-read the exact state under lock;
3. reject stale UUIDs or a changed state fingerprint;
4. preserve prior gate rows as immutable history by superseding rather than
   deleting;
5. verify the inserted review through `benchmark.v_evidence_promotion_gate`.

Rollback-only mode rolls the proposed review back and uses a second connection
to prove the exact prior gate history was restored.

Apply mode commits once and uses a second connection to prove the new current
gate and historical supersession persisted exactly.

The operational procedure is:

    docs/runbooks/EVIDENCE_PROMOTION_REVIEW.md

Reconciliation states must also be internally consistent.

In particular:

- `validated_exact` cost requires an `exact` selected-cost relation;
- an explicit lower-bound cost basis requires a `lower_bound` relation;
- positive or provisional usage qualification requires a selected usage
  authority and matched provider model identity;
- positive or provisional cost qualification requires a selected,
  non-unresolved cost;
- unavailable provider usage is a reconciliation state, not a fabricated
  provider-usage evidence row containing placeholder request/token evidence;
- unavailable provider cost is a reconciliation state, not a fabricated
  provider-cost evidence row containing a placeholder dollar amount.

## Immediate warning and blocker conditions

The system should surface, and where appropriate block economic qualification
for, conditions including:

- nonzero token usage with zero harness cost;
- nonzero harness cost with zero or absent usage;
- configured route/model identity mismatch;
- provider-observed backend mismatch;
- custom/router alias not recognized by harness pricing;
- harness cost present before provider validation;
- provider request count lower than expected;
- provider usage materially different from harness usage;
- provider requests that cannot be allocated to the selected run;
- provider evidence that predates the selected run;
- provider-family aggregate incorrectly treated as selected-run spend;
- stale or unavailable pricing snapshot;
- request-level tier not reconstructable;
- cache-write classes lost by telemetry aggregation;
- provider billed cost materially different from rate reconstruction;
- missing provider evidence after an apparently successful benchmark run;
- trajectory present with zero usage;
- partial evidence displayed as exact.

These are telemetry/economic failures even if task execution succeeded.

## Harness-neutral implementation vocabulary

New code and schema should prefer:

- `harness_reported_usage`
- `harness_reported_cost`
- `provider_usage_evidence`
- `provider_cost_evidence`
- `selected_usage_authority`
- `selected_cost_basis`
- `usage_validation_status`
- `cost_validation_status`

rather than embedding `Claude Code` into the permanent data model.

Harness-specific details belong in provenance fields such as:

    harness_name
    harness_version

## Raw versus selected values

Never overwrite raw benchmark evidence merely because a later source is better.

The model should retain:

    harness reported value
    provider evidence
    reconciliation
    selected reviewed value

as separate layers.

This is why:

    benchmark_trials.cost_usd

remains immutable recorded harness/artifact evidence, while a separate
reconciliation layer determines selected decision-facing cost.

## Dashboard requirements

When this contract reaches the dashboard, it should make these states visible:

- harness usage versus provider usage;
- harness cost versus selected cost;
- usage validation status;
- cost validation status;
- provider evidence completeness;
- model-identity status;
- selected authority/basis;
- evidence limitations;
- Canary/Smoke promotion readiness;
- the exact source arm run and reconciliations behind a current gate;
- reviewed versus derived blocker state;
- whether the current gate is effectively authorizing advancement.

The current Planner is a read-only consumer of the fail-closed promotion view.
It may withhold Smoke/Full commands when effective advancement is absent, but it
does not write review decisions or dispatch benchmark work.

A successful benchmark must not receive a visually "green" economic status when
usage or cost remains unverified.

## Future harness experiments

This contract is especially important for future agent-harness comparisons.

Changing the harness can change:

- token aggregation;
- cache semantics;
- model naming;
- request retries;
- cost estimators;
- pricing tables;
- telemetry completeness.

Therefore a new harness requires Canary/Smoke telemetry qualification even when
the provider/backend itself has already been benchmarked through another
harness.

Provider validation is not permanently transferable across harnesses unless the
relevant telemetry path is demonstrably identical.

The current promotion-gate slot is keyed by arm and target mode. Before the
first paid Phase 4 Canary, review whether promotion authorization must also bind
explicit experiment/suite/phase identity so a prior experiment cannot authorize
a new harness experiment merely because an arm identifier is reused.

Phase 5 remains after Phase 4. Its planned procedure-level evidence and
planning-versus-execution economic split are not yet first-class canonical
schema dimensions and should not be guessed in advance.

## Operational rule

Before authorizing a new full sweep, answer two independent questions:

> Is the selected token usage authority defensible?

and:

> Is the selected cost authority defensible?

If either answer is no or unknown, do not represent Full as economically
qualified.

For the current durable review procedure, use:

    docs/runbooks/EVIDENCE_PROMOTION_REVIEW.md
