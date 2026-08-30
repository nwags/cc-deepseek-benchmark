# Evidence Promotion Review Runbook

Status: current operator procedure as of 2026-08-30.

This runbook describes how a human reviewer records durable evidence-promotion
decisions for the benchmark's Canary -> Smoke -> Full progression.

It is the operational companion to:

```text
docs/methodology/USAGE_AND_COST_EVIDENCE_MODEL.md
```

The methodology document defines what evidence is sufficient. This runbook
defines how to inspect and record the resulting review safely.

## 1. Scope and safety boundary

The current durable review path is:

```text
provider evidence
    |
    v
normalized usage / cost evidence
    |
    v
current usage + cost reconciliations
    |
    v
human promotion review
    |
    v
benchmark.benchmark_evidence_promotion_gates
    |
    v
benchmark.v_evidence_promotion_gate
    |
    v
read-only Planner
```

The review CLI is:

```text
scripts/review_evidence_promotion.py
```

The Planner and the CLI have different responsibilities:

- the **Planner** reads current promotion evidence and withholds Smoke/Full
  commands when effective advancement is absent;
- the **CLI** is the explicit durable mutation path for recording a reviewed
  promotion decision;
- neither mechanism is protected workflow dispatch;
- neither mechanism activates Phase 4 or Phase 5.

Do not create provider evidence, reconciliations, or promotion gates merely to
make a test pass or to make an arm appear eligible.

## 2. Transition model

There are only two current promotion transitions:

| Target mode | Required source mode |
|---|---|
| `smoke` | `canary` |
| `full` | `smoke` |

The CLI derives source mode from `--target-mode`; there is no independent
`--source-mode` argument.

The normal research progression is:

```text
Canary
  |
  | provider evidence + model identity + candidate usage/cost authority
  v
qualitative review
  |
  v
Smoke
  |
  | exact/qualified usage + exact/qualified cost
  v
qualitative review
  |
  v
Full
```

The evidence gate is necessary but is not a substitute for qualitative review.

## 3. Prerequisites

Before using the durable review CLI, confirm:

1. the exact source arm run is known;
2. the source run is the intended Canary or Smoke execution;
3. provider evidence has already been collected/ingested where available;
4. current usage and cost reconciliations exist for the exact source arm run;
5. model identity and evidence limitations have been reviewed;
6. the reviewer knows whether the intended decision is `pass`, `blocked`, or
   `waived`;
7. `SUPABASE_DB_URL` is available as a server-side/local environment secret.

Never pass the database URL on the command line.

Do not commit that value or paste it into review artifacts.

## 4. Quick start: Plan -> Check -> Rollback -> Apply

Use placeholders until the exact arm/run identity has been reviewed:

```bash
ARM_ID='<canonical-arm-id>'
SOURCE_ARM_RUN_ID='<exact-arm-run-uuid>'
TARGET_MODE='smoke'   # smoke or full
DECISION='pass'       # pass, blocked, or waived
REVIEWED_BY='<reviewer-identity>'
```

### Step 1: Plan

`--plan` validates the requested decision and arguments without accessing the
database:

```bash
uv run python scripts/review_evidence_promotion.py \
  --plan \
  --arm-id "$ARM_ID" \
  --source-arm-run-id "$SOURCE_ARM_RUN_ID" \
  --target-mode "$TARGET_MODE" \
  --decision "$DECISION" \
  --reviewed-by "$REVIEWED_BY"
```

This is argument validation only. It does not establish that the provider
evidence or reconciliations are sufficient.

### Step 2: Check

`--check-only` performs read-only inspection in a repeatable-read transaction:

```bash
uv run python scripts/review_evidence_promotion.py \
  --check-only \
  --arm-id "$ARM_ID" \
  --source-arm-run-id "$SOURCE_ARM_RUN_ID" \
  --target-mode "$TARGET_MODE" \
  --decision "$DECISION" \
  --reviewed-by "$REVIEWED_BY"
```

Review all returned evidence, not only `recordable`.

The result includes:

```text
source_evidence
evidence_blocker_codes
current_gate
mutation_pins
```

The mutation pins are:

```text
expected_usage_reconciliation_id
expected_cost_reconciliation_id
expected_current_gate_id
expected_state_sha256
```

`expected_current_gate_id` is the exact current gate UUID, or the literal
`none` when no current gate existed.

For a requested `pass`, `--check-only` exits nonzero when the evidence
qualification is insufficient. Do not convert that into a pass manually.

### Step 3: Rollback-only verification

Copy the exact four mutation pins from the same `--check-only` result.

```bash
uv run python scripts/review_evidence_promotion.py \
  --rollback-only \
  --arm-id "$ARM_ID" \
  --source-arm-run-id "$SOURCE_ARM_RUN_ID" \
  --target-mode "$TARGET_MODE" \
  --decision "$DECISION" \
  --reviewed-by "$REVIEWED_BY" \
  --expected-usage-reconciliation-id '<uuid-from-check>' \
  --expected-cost-reconciliation-id '<uuid-from-check>' \
  --expected-current-gate-id '<uuid-or-none-from-check>' \
  --expected-state-sha256 '<sha256-from-check>'
```

Rollback-only mode:

1. acquires the transaction-scoped advisory review lock;
2. re-reads the evidence chain and current gate under lock;
3. verifies all exact pins;
4. performs the proposed supersession/insert inside the transaction;
5. verifies the fail-closed database view;
6. rolls the transaction back;
7. opens a second connection;
8. proves the exact previous gate history was restored.

A successful rollback-only run must report that persistent gate history was
unchanged.

### Step 4: Apply

Only after reviewing the check-only and rollback-only results should the same
review be durably applied:

```bash
uv run python scripts/review_evidence_promotion.py \
  --apply \
  --arm-id "$ARM_ID" \
  --source-arm-run-id "$SOURCE_ARM_RUN_ID" \
  --target-mode "$TARGET_MODE" \
  --decision "$DECISION" \
  --reviewed-by "$REVIEWED_BY" \
  --expected-usage-reconciliation-id '<uuid-from-check>' \
  --expected-cost-reconciliation-id '<uuid-from-check>' \
  --expected-current-gate-id '<uuid-or-none-from-check>' \
  --expected-state-sha256 '<sha256-from-check>'
```

Apply mode:

1. takes the same advisory lock;
2. re-verifies the same exact reviewed state;
3. supersedes the previous current gate when one exists;
4. inserts the new reviewed decision;
5. verifies the fail-closed view before commit;
6. commits once;
7. uses a second connection to verify the persisted current gate and history.

If any pin has changed, stop and run `--check-only` again.

## 5. Decision guide

### `pass`

Use `pass` only when the evidence chain satisfies the transition's qualification
contract and the qualitative review supports advancement.

A pass:

- cannot include reviewed blocker codes;
- cannot include a waiver reason;
- must pass the database's derived fail-closed checks;
- becomes authorization only when `effective_can_advance = true`.

Canary -> Smoke can use:

```text
validated_exact
validated_qualified
provisional
```

where required limitations are explicit.

Smoke -> Full requires:

```text
validated_exact
validated_qualified
```

for both usage and cost.

`provisional` is not Full-eligible.

### `blocked`

Use `blocked` when the reviewer has identified a reason not to advance.

At least one explicit blocker code is required.

Example:

```bash
uv run python scripts/review_evidence_promotion.py \
  --plan \
  --arm-id "$ARM_ID" \
  --source-arm-run-id "$SOURCE_ARM_RUN_ID" \
  --target-mode "$TARGET_MODE" \
  --decision blocked \
  --blocker-code qualitative.provider_identity_unclear \
  --reviewed-by "$REVIEWED_BY"
```

Blocker codes should be stable, concise, and evidence-oriented.

A blocked decision is durable provenance. It is not authorization.

### `waived`

Use `waived` only when the reviewer needs to retain an explicit policy/exception
record.

A non-empty waiver reason is required:

```bash
uv run python scripts/review_evidence_promotion.py \
  --plan \
  --arm-id "$ARM_ID" \
  --source-arm-run-id "$SOURCE_ARM_RUN_ID" \
  --target-mode "$TARGET_MODE" \
  --decision waived \
  --waiver-reason 'Documented exception; advancement remains disabled.' \
  --reviewed-by "$REVIEWED_BY"
```

A waiver is **not** a pass.

The fail-closed view derives `gate_decision_not_pass`, so a waived decision must
remain:

```text
effective_can_advance = false
```

This is deliberate. Waivers preserve provenance without silently weakening the
evidence contract.

## 6. Why the exact pins exist

A promotion review is valid only for the exact state that the human reviewed.

The CLI therefore pins:

### Usage reconciliation UUID

Protects against a newly superseded usage/model-identity conclusion.

### Cost reconciliation UUID

Protects against a newly superseded economic conclusion.

### Current gate UUID or `none`

Protects against another reviewer changing promotion history after the check.

### State SHA-256

Protects material reviewed fields that may change without changing the three
UUID identities above.

The state fingerprint covers the material source-run, reconciliation,
limitation, and current-gate state used by the review.

If any material state changes, mutation must fail closed.

## 7. Concurrency and advisory locking

Mutation modes acquire a transaction-scoped PostgreSQL advisory lock for:

```text
arm_id + target_mode
```

The lock prevents two cooperating reviewers using this tool from concurrently
mutating the same current-gate slot.

The lock is not a replacement for the exact mutation pins.

After acquiring the lock, the CLI re-reads the state and checks the pins again.
A concurrent evidence or gate change therefore invalidates the attempted
mutation rather than being silently overwritten.

## 8. Immutable history and supersession

Promotion history is append-oriented.

When a new review supersedes an existing current gate:

```text
old row: is_current = false
new row: is_current = true
```

The old row is not deleted.

The permanent apply verifier checks that:

- gate history grew by exactly one row;
- pre-existing historical rows did not change;
- only the previously current row was demoted;
- the new row is the exact current gate.

Historical provenance and current authorization are therefore separate
concepts.

## 9. Fail-closed database verification

The authoritative derived promotion state is:

```text
benchmark.v_evidence_promotion_gate
```

It checks, among other conditions:

- gate currentness;
- decision state;
- reviewed blockers;
- source arm/run consistency;
- source-mode consistency;
- usage/cost reconciliation binding;
- reconciliation currentness;
- provider evidence visibility;
- provider model identity;
- selected usage authority;
- selected cost/basis/relation;
- transition-specific validation level.

`effective_can_advance` is true only when the derived blocker set is empty.

Retaining a historical or waived gate never makes it effective authorization.

## 10. Planner relationship

The dashboard Planner is a read-only consumer of current promotion evidence.

For the current progression:

- Canary needs no predecessor promotion gate;
- Smoke expects a current Canary -> Smoke gate;
- Full expects a current Smoke -> Full gate.

When the required effective gate is absent, the Planner withholds the
corresponding run commands.

The Planner does not:

- insert or update promotion gates;
- alter provider evidence;
- alter reconciliations;
- dispatch workflows;
- convert a waiver into a pass.

The explicit durable mutation path remains this CLI.

## 11. Troubleshooting and recovery

### Stale reconciliation pins

Symptom:

```text
current usage reconciliation changed after review
```

or:

```text
current cost reconciliation changed after review
```

Response:

1. do not retry with the old UUIDs;
2. rerun `--check-only`;
3. review the new evidence chain and limitations;
4. use only the newly emitted pins.

### Current gate changed after check

Symptom:

```text
current promotion gate changed after review
```

Another review changed the current gate after the original inspection.

Response:

1. stop;
2. rerun `--check-only`;
3. inspect the newly current gate;
4. make a new review decision from that state.

### State fingerprint changed

Symptom:

```text
reviewed promotion state changed after check-only
```

A material reviewed field changed.

Do not attempt to reconstruct the old fingerprint. Rerun the review from
`--check-only`.

### Rollback restoration failed

Symptom:

```text
rollback-only review did not restore exact gate history
```

Treat this as an integration-safety failure.

Do not proceed to `--apply`.

Inspect the database state and the review implementation before any new
mutation.

### `commit_state = not_committed`

The CLI did not record a successful database commit.

For mutation failures in this state, the implementation attempts transaction
rollback before returning the failure.

Resolve the reported problem and run a fresh `--check-only` before preparing
another mutation.

### `commit_state = committed`

The database commit call returned successfully.

Interpret this together with the overall result status:

- `status = applied` means the commit succeeded **and** the subsequent
  second-connection verification of the persisted current gate/history passed;
- `status = failed` with `commit_state = committed` means the write may already
  be durable but a later post-commit verification failed.

In the failed/committed case, do not blindly retry `--apply`.

Instead:

1. inspect the current gate for the exact arm/target pair;
2. inspect the promotion-gate history;
3. inspect `benchmark.v_evidence_promotion_gate`;
4. determine whether the intended review was persisted;
5. reconcile the observed state before any further mutation.

`commit_state = committed` alone is therefore not proof that every post-commit
verification succeeded.

### `commit_state = unknown`

This is the most important recovery case.

Do **not** blindly retry `--apply`.

A connection or process failure may have occurred during the commit boundary.

Instead:

1. run a fresh read-only inspection;
2. inspect the current gate and gate history for the exact arm/target pair;
3. determine whether the intended new review already exists and is current;
4. inspect `benchmark.v_evidence_promotion_gate`;
5. reconcile the observed state before deciding whether another apply is
   appropriate.

Retrying without resolving an unknown commit state can create misleading review
history.

## 12. Worked examples

### Eligible Canary -> Smoke pass

Use the exact Canary arm-run UUID.

`--check-only` should show:

```text
usage validation: validated_exact / validated_qualified / provisional
cost validation: validated_exact / validated_qualified / provisional
provider evidence visible
model identity matched
selected usage authority present
selected cost/basis/relation present
```

After qualitative review, run rollback-only and then apply using the exact pins.

The resulting gate is effective only if the database view has no derived
blockers.

### Qualitative blocker

Provider evidence may satisfy the structural evidence checks while qualitative
inspection finds a meaningful problem.

Record:

```text
decision = blocked
blocker_code = qualitative.<stable-reason>
```

The decision remains auditable and non-authorizing.

### Explicit waiver

Record:

```text
decision = waived
waiver_reason = <documented reason>
```

A waiver remains non-authorizing. If actual advancement is later desired, a new
review must supersede it with an evidence-qualified `pass`.

### Reconciliation changes after review

If a reconciliation is superseded between check-only and mutation, the old
mutation pins fail.

This is expected.

Review the new reconciliation instead of attempting to force the old decision.

### Concurrent review

If another reviewer changes the gate while an operator is preparing a mutation,
the current-gate pin and state fingerprint become stale.

The advisory lock plus re-check prevents the prepared review from silently
overwriting the new state.

## 13. Future Phase 4 and Phase 5 boundary

The current promotion-gate schema uses one current slot keyed by:

```text
arm_id + target_mode
```

That is sufficient for the closed Phase 3 context.

Before the first paid Phase 4 Canary, review whether promotion authorization
must additionally bind explicit experiment/suite/phase identity so a prior
experiment's current gate cannot authorize a new experiment that happens to
reuse an arm identifier.

Phase 4 also needs an explicit harness-version contract.

Phase 5 remains after Phase 4 and is expected to add procedure-level evidence
such as plan artifacts/planner transcripts and separable planning-versus-
execution usage/cost. Do not invent those schema semantics before Phase 5 is
designed.

## 14. Related documentation

Normative methodology:

```text
docs/methodology/USAGE_AND_COST_EVIDENCE_MODEL.md
```

Dashboard/data model:

```text
apps/dashboard/src/app/data-model/page.tsx
docs/diagrams/DASHBOARD_DATA_MODEL_20260830.mmd
```

Future-phase roadmap:

```text
docs/guides/PROJECT_HANDOFF_AND_FUTURE_ROADMAP.md
```

Repository operating guide:

```text
docs/runbooks/RUNBOOK.md
```
