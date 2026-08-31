# Provider Evidence

## Purpose

Provider Evidence is the source-centric browser for normalized provider-side
usage, pricing, cost, and reconciliation provenance.

Use it when the research question is:

- what provider-side evidence supports a selected usage or cost interpretation;
- which source records participate in a usage or cost reconciliation;
- whether a pricing snapshot belongs to the same source or a different source;
- how a provider evidence source connects to an exact run or arm;
- what evidence exists without treating source presence itself as selected
  authority.

The principal route is:

    /provider-evidence

One source record can be opened at:

    /provider-evidence/[sourceId]

Provider Evidence is an evidence browser. It is **not** a provider collector,
provider API client, reconciliation editor, or promotion-decision writer.

## Evidence authority

The page reads the normalized Migration-011 provider-evidence model:

    benchmark_provider_evidence_sources
      -> benchmark_provider_usage_evidence
      -> benchmark_provider_pricing_snapshots
      -> benchmark_provider_cost_evidence
      -> usage/cost reconciliation source links
      -> usage/cost reconciliations

A provider source row establishes provenance and context. It does not by itself
mean that its usage or cost is the selected authority for a benchmark run.

The reconciliation rows retain the decision-facing:

- validation state;
- selected usage authority;
- selected cost basis;
- selected cost relation;
- model-identity evidence;
- limitations;
- source roles.

Raw harness-recorded cost remains separate historical provenance. The browser
does not rewrite it.

## Population

The Provider Evidence index is a dynamic source inventory over normalized
provider-evidence records currently present in the canonical database.

It is not the fixed 16-arm reviewed Phase 3 denominator.

Sources may represent different evidentiary scopes, including:

- selected-run or provider-window evidence;
- account-window exports;
- usage exports;
- billing exports;
- request logs;
- manual captures;
- pricing snapshots.

A source can legitimately support more than one reconciliation, and one
reconciliation can legitimately depend on several source records.

## Index controls

The index can filter by:

- provider;
- evidence kind;
- source scope;
- integrity state;
- phase;
- arm;
- run;
- free-text search.

Pagination is source-centric. Matching sources are paged before related
context is expanded so a source with many linked rows does not distort the
page boundary.

## Source detail

Source detail exposes the normalized evidence that can safely be shown for one
provider source:

- source provenance;
- normalized provider usage;
- normalized provider cost;
- pricing snapshots owned by the source;
- usage reconciliations linked to the source;
- cost reconciliations linked to the source;
- every supporting evidence source attached to those reconciliations;
- the referenced pricing snapshot and pricing-source link when pricing comes
  from another provider-evidence source;
- related run, arm, trial, or artifact links where that relationship exists.

### Cross-source reconciliation is normal

Do not assume that the source being viewed owns every record required by its
reconciliation.

A cost reconciliation can use:

- one source for usage or billing context;
- another source for pricing;
- additional supporting source records.

The detail page therefore shows the complete reconciliation source chain and
resolves the pricing source independently.

That relationship is evidence, not duplication.

## Privacy and read-only boundary

The browser deliberately does **not** render arbitrary raw provider responses
or `raw_metadata`.

Raw provider material can contain:

- account identifiers;
- workspace/project identifiers;
- billing identifiers;
- API-key identifiers;
- private provider metadata.

Displayed source URIs, provider references, notes, labels, and structured
pricing content pass through the dashboard's sanitization/redaction layer.

Operational database reads enter through the shared dashboard query boundary,
which executes each query inside an explicit read-only transaction.

The Provider Evidence browser:

- does not write database state;
- does not modify reconciliations;
- does not call provider APIs;
- does not access provider API credentials.

## Presentation precision

Provider Evidence follows the dashboard-wide presentation contract:

- no displayed numeric value may request more than four fractional digits;
- values that require limiting are truncated toward zero, not rounded;
- an intentional one-, two-, or three-decimal display remains lower precision;
- raw database, generated, reviewed, and retained evidence precision is not
  changed;
- IDs, hashes, model names, timestamps, and other identifiers are not decimal
  data and are not rewritten;
- unavailable or null evidence remains unavailable and is never converted to
  zero.

Structured pricing data displayed to a reader follows the same
presentation-only decimal ceiling.

## Freshness semantics

A provider source's `captured_at` describes evidence capture/publication
provenance.

It is not the benchmark execution completion time.

Do not interpret the latest provider-evidence capture as the latest benchmark
run, and do not apply execution-freshness semantics to a provider source merely
because it has a recent capture timestamp.

## Important caveats

- Provider evidence present does not automatically mean exact provider billing.
- Provider-window or account-window evidence is not automatically allocable to
  one selected run.
- A pricing snapshot is evidence about applicable rates, not proof of billed
  spend.
- Aggregate provider cost must not be fabricated into unsupported trial or
  outcome allocations.
- Accepted normalized absence does not mean zero usage or zero cost.
- A current reconciliation can depend on multiple provider-evidence sources.
- Historical and superseded source/reconciliation records remain provenance;
  current state should not erase them.

## Common workflows

### Trace a selected cost

    Overview or Cross-phase
      -> Cost Coverage
      -> exact selected run / evidence class
      -> Provider Evidence
      -> source detail
      -> current cost reconciliation
      -> complete supporting-source chain
      -> pricing snapshot / pricing source

### Trace provider usage

    exact run or arm
      -> Provider Evidence
      -> normalized usage evidence
      -> usage reconciliation
      -> selected usage authority
      -> model-identity and limitation fields

### Investigate a disagreement

When harness accounting and provider-side evidence differ:

1. identify the exact run;
2. inspect every linked source rather than choosing one convenient record;
3. check source scope and provider window;
4. inspect the selected reconciliation state;
5. inspect the pricing source independently;
6. preserve any allocation limitation in the conclusion.

## Evidence tracing

A useful default chain is:

    provider evidence source
      -> normalized usage/cost/pricing evidence
      -> reconciliation source roles
      -> current or historical reconciliation
      -> exact arm/run context
      -> reviewed decision-facing interpretation

Use Artifacts when the question is about retained benchmark execution bytes.
Use Provider Evidence when the question is about normalized provider-side
provenance and reconciliation.

## Related documentation

- [Dashboard Research Guide](../DASHBOARD_RESEARCH_GUIDE.md)
- [Cost Coverage page guide](COST_COVERAGE.md)
- [Artifacts page guide](ARTIFACTS.md)
- [Data Model page guide](DATA_MODEL.md)
- [Architecture page guide](ARCHITECTURE.md)
- [Usage and Cost Evidence Model](../../methodology/USAGE_AND_COST_EVIDENCE_MODEL.md)
- [Provider Usage and Cost Automation](../../reference/PROVIDER_USAGE_COST_AUTOMATION.md)
- [Evidence Promotion Review](../../runbooks/EVIDENCE_PROMOTION_REVIEW.md)
