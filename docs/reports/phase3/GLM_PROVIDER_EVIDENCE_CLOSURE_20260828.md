# GLM Provider Evidence Closure — 2026-08-28

## Status

Z.AI/GLM provider-evidence review is closed for the two retained Phase 3 GLM arms:

1. `router-glm-5.1`
2. `router-glm-5.2`

This closure is deliberately **documentation-only**. No GLM provider-evidence rows are
ingested into the normalized database because the reviewed inventory found no retained
raw/first-party provider candidate that can be safely allocated to either selected run.

The older June 19 GLM 5.1 billing aggregate remains historical component evidence. It
must not be promoted into selected-run provider usage or selected-run provider billing.

No migration, importer apply, database mutation, or historical benchmark-result rewrite
is part of this closure.

## Reviewed inventory

Read-only private inventory audit:

- path: `.run/review/glm-provider-inventory-20260828-01.json`
- SHA-256:
  `52abb855f23ce1ef6ef30fe5877798e40ccaf698826f3093bf6fb893f06b156f`
- inventory helper SHA-256:
  `6bb01ce76488aef6e50dc388e872678775f94474fc70257e4e6647ccac39444e`
- provider: `zai-glm`
- database mode: read-only
- database writes: none
- migration run: false
- apply run: false
- raw provider candidate count: `0`
- GLM normalized target state: `glm_empty`

The inventory was executed from:

- branch: `phase3-provider-evidence-ingestion-20260825`
- commit: `668b8c991cc35d542be08ab04a907bf0e8c992dc`
- subject: `Document Qwen provider evidence ingestion`

The repository was unchanged by the inventory.

## Canonical selected runs

### GLM 5.1

- arm: `router-glm-5.1`
- arm-run UUID: `b255bb32-7aab-4808-94ec-b22a53bbb016`
- selected run: `router-glm-5.1/2026-06-28__13-28-50`
- selected input tokens: `1,002,002`
- selected cached input tokens: `0`
- selected output tokens: `892,921`
- selected total retained tokens: `1,894,923`

### GLM 5.2

- arm: `router-glm-5.2`
- arm-run UUID: `bdfb1124-95d5-4dad-a3fd-2d5f6fe9601d`
- selected run: `router-glm-5.2/2026-06-19__13-47-51`
- selected input tokens: `2,026,466`
- selected cached input tokens: `0`
- selected output tokens: `1,378,323`
- selected total retained tokens: `3,404,789`

These selected-run values are retained harness accounting. They are not provider-observed
selected-run usage.

## Historical GLM 5.1 provider context

The June 19 component evidence classifies the previously uploaded `KimiUsage` artifact as
Z.AI/GLM rather than Moonshot/Kimi and records the model as `glm-5.1`.

Historical aggregate:

| Charge type | Tokens | Cost |
| --- | ---: | ---: |
| Input | `1,543,476` | `$2.160866` |
| Cache | `1,639,488` | `$0.426267` |
| Output | `115,285` | `$0.507254` |
| **Total** | **`3,298,249`** | **`$3.094387`** |

Committed historical component sources:

- `docs/reports/phase3/PHASE3_USAGE_RESOLUTION_2026-06-19.md`
- `results/phase3/provider_usage/normalized/provider_usage_resolution_2026-06-19.csv`

Those sources historically use `provider-billing-resolved` for the GLM 5.1 aggregate.
That wording is preserved as historical component evidence; it is not reinterpreted here
as proof that the aggregate belongs to the canonical June 28 selected run.

The historical aggregate has no safe selected-run allocation in the reviewed evidence
inventory. In particular, its token geometry is not the selected-run harness geometry:

- historical aggregate tokens: `3,298,249`
- selected GLM 5.1 retained tokens: `1,894,923`
- historical cache tokens: `1,639,488`
- selected GLM 5.1 cached input tokens: `0`
- historical output tokens: `115,285`
- selected GLM 5.1 output tokens: `892,921`

The mismatch does not make the historical billing evidence invalid. It means the
historical aggregate cannot be equated with the canonical selected run without a
supported allocation bridge that the retained evidence does not provide.

No comparable first-party provider aggregate was found for the selected GLM 5.2 run.

## Normalized database inventory

The read-only GLM-scoped inventory found zero rows in every provider-evidence target:

| Table | GLM rows |
| --- | ---: |
| `benchmark_provider_evidence_sources` | `0` |
| `benchmark_provider_usage_evidence` | `0` |
| `benchmark_provider_pricing_snapshots` | `0` |
| `benchmark_provider_cost_evidence` | `0` |
| `benchmark_usage_reconciliations` | `0` |
| `benchmark_usage_reconciliation_sources` | `0` |
| `benchmark_cost_reconciliations` | `0` |
| `benchmark_cost_reconciliation_sources` | `0` |
| `benchmark_evidence_promotion_gates` | `0` |

The target state is therefore intentionally `glm_empty`.

## Evidence semantics and no-ingestion decision

The provider-evidence schema is intended to preserve provenance and allocation scope.
A historical provider aggregate must not be attached to a selected arm-run merely
because the provider/model family is compatible.

For GLM, the reviewed facts are:

- historical first-party billing context exists for `glm-5.1`;
- the historical aggregate is not safely allocable to the canonical selected GLM 5.1 run;
- no retained raw provider candidate is available for a new normalized source ingestion;
- no selected-run provider request log is available;
- no selected-run provider token allocation is available;
- no selected-run provider-billed amount is available;
- no retained provider evidence supports a selected-run pricing reconstruction here;
- GLM 5.2 has no retained first-party provider candidate in the reviewed inventory.

Accordingly, this pass does **not** create:

- a sanitized GLM supplemental provider snapshot;
- a GLM provider-evidence importer;
- provider usage rows;
- provider pricing rows;
- provider cost rows;
- usage reconciliation rows;
- cost reconciliation rows;
- evidence-promotion gates.

This is a deliberate non-ingestion decision, not a missing execution step.

## Selected-run interpretation

For both retained GLM arms:

- selected harness usage remains the retained benchmark accounting;
- provider-observed selected-run usage is unavailable;
- provider-billed selected-run cost is unavailable from the reviewed retained evidence;
- the historical `$3.094387` GLM 5.1 aggregate is not selected-run billing authority;
- no provider-evidence promotion is justified by the current retained source set.

Any dashboard/report surface that distinguishes historical provider context from
selected-run cost should preserve that distinction.

## Historical-source preservation

The June 19 component evidence is not rewritten or deleted by this closure.

That matters because the earlier report correctly established two durable facts:

1. the artifact previously labeled `KimiUsage` belongs to Z.AI/GLM, not Kimi; and
2. its GLM 5.1 billing aggregate is `3,298,249` tokens and `$3.094387`.

The new conclusion is narrower: the later selected-run/provider-evidence normalization
cannot safely allocate that aggregate to the canonical selected run.

Preserving both records makes the change in evidentiary interpretation explicit rather
than silently altering historical documentation.

## Privacy and retention

This closure commits no raw provider export and no private credential-bearing material.

The private inventory audit remains under ignored `.run/review` storage and is referenced
only by SHA-256.

The closure report contains only sanitized identifiers, aggregate benchmark metadata,
historical aggregate values already committed to the repository, and private-audit
hash provenance.

## Reopening criteria

GLM provider-evidence normalization should be reopened only if materially stronger
first-party evidence becomes available, for example:

- provider request-level records with model and timestamp/request identifiers sufficient
  to allocate requests to a selected run;
- a provider billing export with a proven selected-run time/model scope;
- another first-party source that creates a reviewable allocation bridge between provider
  evidence and a canonical selected arm-run.

Any reopening should be handled as a new reviewed addition/repair with its own source
hashes, dry-run/rollback checks where applicable, and independent verification.

## Closure

GLM provider-evidence normalization is closed for the current retained evidence set.

The durable state is:

- two canonical selected GLM arms remain in benchmark accounting;
- historical GLM 5.1 billing evidence remains historical component context;
- no historical aggregate is synthesized into selected-run provider evidence;
- GLM 5.2 receives no unsupported provider evidence;
- all nine GLM-scoped normalized provider-evidence targets remain empty;
- no database writes are required or performed;
- no migration or apply path exists for this closure;
- future normalization requires new first-party evidence with stronger allocation
  provenance.
