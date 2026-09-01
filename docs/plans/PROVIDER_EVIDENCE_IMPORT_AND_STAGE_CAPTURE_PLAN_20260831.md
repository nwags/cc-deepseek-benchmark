# Provider Evidence Import and Stage Capture Plan

Date: 2026-08-31

Status: planning only

Repository baseline:
`main@5e979154866b0b09e2c1086c99126c6b0b5092c2`

## 1. Purpose

Build a general provider-evidence acquisition and ingestion system that can
accept first-party usage and cost evidence from:

- provider APIs;
- automated provider-dashboard exports;
- manually downloaded provider exports;
- a team evidence relay;
- direct authenticated dashboard import/upload.

The design must preserve a strict separation among:

1. immutable provider source evidence;
2. normalized provider observations;
3. benchmark attribution and reconciliation;
4. selected decision-facing authority.

Collection or import must never automatically make evidence authoritative.

## 2. Existing state

The current Provider Evidence routes are read-only:

- `/provider-evidence`
- `/provider-evidence/[sourceId]`

They read normalized Migration-011 provider evidence already present in
Postgres.

They deliberately do not:

- call provider APIs;
- access provider credentials;
- upload arbitrary provider files;
- write database state;
- edit reconciliations;
- make promotion decisions.

Historical provider-specific Phase 3 ingestion programs exist, but they are
reviewed-evidence pipelines rather than a generic ingestion architecture.

The new system must preserve the existing browser's read-only research
semantics while adding a separate authenticated import workflow.

## 3. Primary architecture

Use one ingestion contract regardless of evidence origin.

    provider API
         |
    dashboard export
         |
    manual upload
         |
    team relay
         |
         v
    immutable source capture
         |
         v
    generic source envelope
         |
         v
    provider-specific parser
         |
         v
    normalized observations
         |
         v
    reconciliation
         |
         v
    promotion / reviewed authority

Do not build incompatible ingestion models for:

- CLI input;
- dashboard upload;
- relay input;
- API collection;
- provider dashboard exports.

## 4. Harbor and Terminal-Bench independence

Provider evidence collection must not depend on provider-native response usage
being observable inside:

- Claude Code;
- Harbor;
- Terminal-Bench;
- LiteLLM or another compatibility/router layer.

Provider-native response objects may be transformed, summarized, partially
retained, or lost, particularly for failed or interrupted trials.

Harness-retained cost/token evidence remains an independent evidence channel.

Where request-level usage survives in benchmark artifacts, it can be compared
against provider-side evidence, but it is not required for provider evidence
collection or reconciliation.

## 5. Evidence layers

### 5.1 Immutable source snapshot

A source snapshot is the exact provider-produced or provider-retrieved evidence
captured at one point in time.

Examples include:

- OpenAI Usage API response bundle;
- OpenAI Costs API response bundle;
- Google Cloud Monitoring query result;
- Google Cloud Billing / BigQuery query result;
- DeepSeek Usage export ZIP;
- provider CSV export;
- manual provider capture.

When source bytes exist, preserve them before normalization.

Raw private provider material must not be committed to Git.

Every retained source must be hash-bound.

### 5.2 Capture event, source snapshot, and content identity

Do not collapse three different identities into one record:

- a **capture event** records that a scheduled, benchmark-aware, relay, or
  manual acquisition attempt occurred, including its requested scope, start
  and completion times, adapter version, and outcome;
- a **source snapshot** records the logical provider evidence observed by that
  capture event;
- a **content object** represents immutable retained bytes and is identified by
  a cryptographic content hash.

Physical raw-byte storage may be deduplicated safely by SHA-256.

Capture history must not be deduplicated away.

If a scheduled DeepSeek export at T2 has exactly the same bytes as the export
captured at T1, the T2 capture event must still be retained. It may point to
the already-retained content object and carry an `unchanged_duplicate` result.

This allows the system to distinguish:

- no capture was attempted;
- capture failed;
- capture succeeded but provider data was unchanged;
- capture succeeded and provider data changed.

### 5.3 Generic provider source envelope

The first generic source schema should contain at least:

- schema version;
- provider;
- evidence kind;
- capture method;
- capture timestamp;
- provider coverage start;
- provider coverage end;
- provider coverage timezone;
- provider account scope where safely retained;
- provider project/workspace scope where safely retained;
- provider API-key scope where safely retained;
- provider/model dimensions;
- source format;
- content type;
- byte size;
- SHA-256;
- capture-event identifier;
- logical source-snapshot identifier;
- immutable private object URI;
- provider reference;
- exact coverage-boundary semantics when known;
- provider reporting or data-maturity state when known;
- sanitized acquisition-manifest reference or hash;
- privacy classification;
- parser identifier;
- parser version;
- normalization status.

Initial capture-method vocabulary:

- `provider_api`;
- `provider_export`;
- `dashboard_capture`;
- `manual_upload`;
- `relay_download`.

Provider-native metadata that is unsafe for normal dashboard display remains
private or must pass through the existing sanitization layer.

### 5.4 Normalized observations

Usage observations should support, when available:

- provider;
- provider model;
- observation interval;
- account/project/workspace/API-key dimensions;
- request count;
- ordinary input tokens;
- cache-read input tokens;
- cache-creation input tokens;
- output tokens;
- provider-specific reasoning/thinking dimensions;
- allocation scope;
- completeness status;
- limitations.

Cost observations should support, when available:

- provider;
- observation interval;
- account/project/workspace dimensions;
- provider line item or SKU;
- amount;
- currency;
- credits or adjustments;
- billed versus rate-reconstructed semantics;
- allocation scope;
- completeness status;
- limitations.

Provider-specific fields must not be forced into false equivalence solely to
fit a common table.

### 5.5 Acquisition manifest

API- and query-derived evidence must retain a sanitized acquisition manifest
sufficient to explain and reproduce what was requested without retaining
credentials.

As applicable, the manifest should record:

- provider adapter and adapter version;
- endpoint or provider operation class;
- requested coverage interval;
- whether interval boundaries are inclusive or exclusive;
- provider/reporting timezone;
- sanitized grouping and filter parameters;
- pagination order and page count;
- SHA-256 for retained response pages or archive members;
- BigQuery query text or a canonical query hash plus safe parameters;
- provider request/job identifiers when safe and useful;
- capture start and completion times;
- provider-reported publication/settlement state when available.

Credential values, authorization headers, cookies, and secret-bearing query
parameters must never enter the acquisition manifest.

## 6. Snapshot versus observation versus reconciliation

The system must distinguish:

### Source snapshot

What the provider showed at a specific capture time.

### Observation

A normalized fact extracted from one source snapshot.

### Reconciliation

The benchmark interpretation relating one or more observations to a benchmark
run, arm, provider window, or other scope.

This distinction is especially important for cumulative or overlapping
provider exports.

## 7. Overlapping and cumulative snapshots

Repeated provider captures may cover the same month or provider reporting
window.

Example:

    DeepSeek August export captured at T1
    DeepSeek August export captured at T2
    DeepSeek August export captured at T3

These are immutable snapshots of overlapping source scope.

They must not automatically be summed.

A derived delta may be produced only when:

- source semantics support subtraction;
- relevant grouping dimensions are equivalent;
- reporting-period boundaries are compatible;
- provider corrections or restatements are considered;
- neither source is incomplete in a way that invalidates the delta.

A derived delta must retain lineage to both source snapshots.

The original snapshots remain immutable provenance.

## 8. Capture cadence

Provider evidence should accumulate continuously instead of existing only as a
post-Full-Sweep reconciliation task.

Default target cadence:

- scheduled capture approximately every 12 hours;
- explicit pre-stage capture when useful;
- post-stage capture;
- delayed follow-up capture after provider reporting latency;
- monthly/final reconciliation where provider settlement requires it.

The schedule is deliberately low frequency.

It should gather provider evidence without coupling the capture service to
individual benchmark requests.

## 9. Canary / Smoke / Full policy

The intended stage workflow is:

    pre-stage capture where useful
        ->
    Canary
        ->
    post-Canary capture
        ->
    normalize / reconcile / promotion review
        ->
    Smoke
        ->
    post-Smoke capture
        ->
    normalize / reconcile / promotion review
        ->
    Full
        ->
    post-Full capture
        ->
    delayed provider capture
        ->
    final reconciliation

A provider reporting delay must not be represented as zero usage or zero cost.

Promotion review may explicitly record a state such as
`provider_evidence_pending` when benchmark execution is otherwise healthy but
provider evidence has not yet settled.

Collection success alone does not authorize stage promotion.

Promotion handling must distinguish provider publication latency from a broken
evidence path:

- when pre/post capture succeeds but the provider has not yet published
  settled data, promotion review may carry `provider_evidence_pending`;
- such a pending state may permit continued staged execution only when
  benchmark execution checks pass, a conservative cost/budget bound remains
  available, and the reviewer records the limitation explicitly;
- `reauthentication_required`, repeated capture failure, an unexplained
  collection gap, or loss of the expected provider evidence path is a
  materially stronger condition and should block ordinary automatic
  promotion until resolved or explicitly overridden by the project owner;
- no pending state may be presented as provider-reconciled cost;
- final provider-reconciled/public reporting requires settled provider
  evidence or an explicit reviewed accepted-absence/limitation state.

## 10. Initial provider acquisition policy

### OpenAI

Primary:

- Organization Usage API;
- Organization Costs API.

Supporting independent evidence:

- dashboard exports where useful.

Provider-native response bundles should be preserved before normalization.

### Google Gemini

Usage primary:

- Cloud Monitoring API.

Cost primary:

- Cloud Billing export;
- BigQuery API over the export.

AI Studio dashboard automation should normally be verification/fallback rather
than the primary unattended path.

Reporting latency must be modeled explicitly.

### DeepSeek

Historical provider evidence:

- scheduled provider Usage dashboard export is a first-class source.

Supporting evidence:

- balance snapshots;
- retained benchmark-side accounting when available;
- applicable provider pricing.

DeepSeek provider evidence must not depend on response-level `usage` surviving
the Claude Code / Harbor path.

Repeated current-month exports are overlapping snapshots, not additive
statements.

Dedicated benchmark API keys should be preferred where they materially improve
provider-export attribution.

### Provider isolation policy

Across providers, prefer benchmark-specific attribution dimensions whenever
the provider and project structure make them operationally practical.

Examples include:

- a dedicated OpenAI benchmark project and/or API-key dimension;
- a dedicated Google Cloud project or similarly bounded billing/monitoring
  dimension;
- a dedicated DeepSeek benchmark API key.

Isolation does not itself prove exact run attribution, but it reduces unrelated
account activity and makes provider-window reconciliation materially stronger.

The benchmark must record which provider-side isolation dimensions were in
effect for each stage without exposing credentials.

## 11. Generic CLI contract

Implement the generic CLI ingestion foundation before the dashboard write
workflow.

Candidate shape:

    provider-evidence import FILE --plan
    provider-evidence import FILE --check-only
    provider-evidence import FILE --rollback-only
    provider-evidence import FILE --apply

The final executable name can change, but these safety semantics should remain.

Required behavior:

- never overwrite raw source evidence;
- hash source before normalization;
- detect duplicate source hashes;
- validate source size and type;
- identify provider and parser explicitly;
- fail closed on ambiguous parser/provider detection;
- support plan-only operation without mutation;
- support rollback-only validation;
- perform permanent writes only through explicit apply;
- verify committed state from a second connection;
- retain source-to-observation lineage;
- never select decision-facing authority merely because import succeeded.

## 12. Dashboard import workflow

Add a distinct authenticated route such as:

    /provider-evidence/import

Do not turn the existing shared read-only `queryRows()` path into a general
database writer.

The import workflow should use a distinct server-side write boundary and a
restricted database role.

All uploaded or relay-supplied bytes must be treated as untrusted input before
parsing.

At minimum, the import boundary must:

- allowlist supported source/archive formats;
- validate content using more than the filename extension;
- enforce compressed and uncompressed byte limits;
- enforce archive member-count limits;
- reject archive path traversal, absolute paths, and unsafe links;
- bound parser CPU time and memory;
- never execute uploaded content;
- never render active provider HTML or document scripting directly;
- isolate provider parsers from the dashboard web process where practical;
- retain a safely captured raw source when appropriate while marking
  normalization failed or pending rather than partially applying it.

Initial UI behavior should support:

- upload provider export;
- offer an `Import from Team Relay` action for choosing a relay document;
- inspect source metadata;
- preview SHA-256 and duplicate status;
- preview parser selection;
- preview normalized observations;
- identify source scope;
- associate benchmark run/arm context only when supportable;
- explicit apply;
- navigate to the resulting Provider Evidence source.

The UI must distinguish:

- captured;
- normalized;
- reconciled;
- selected authority.

## 13. Private object storage

Raw provider evidence remains private.

For each source:

1. receive or capture bytes;
2. compute SHA-256;
3. validate type and size;
4. store using a non-overwriting private object key;
5. record immutable source metadata;
6. normalize from the retained source;
7. verify stored-object/source linkage.

Object keys must not contain secrets.

Signed object-store credentials or provider credentials must never appear in
normal dashboard output.

## 14. Database safety

The research dashboard remains read-only.

Write-capable ingestion should use:

- a separate database boundary;
- explicit transactions;
- advisory locking where needed;
- duplicate protection;
- deterministic verification;
- rollback testing;
- second-connection post-commit verification.

Any schema change must be additive.

Frozen Phase 1, Phase 2, and Phase 3 benchmark result artifacts must not be
rewritten.

## 15. Reconciliation semantics

A source or observation is evidence, not authority.

Reconciliation determines whether evidence is:

- exact-run attributable;
- arm-run attributable;
- provider-window context;
- account-only context;
- exact billed;
- rate reconstructed;
- lower bound;
- unresolved;
- accepted absence.

Overlapping provider activity must not be synthetically divided merely to
complete a table.

Missing evidence remains missing.

## 16. Acceptance criteria

Before Task 0 is complete:

- every scheduled/manual acquisition retains a capture-event record even when
  identical raw bytes reuse a previously retained content object;
- acquisition manifests reproduce the safe request/query/export scope;
- interval boundary and maturity semantics are retained when provider data
  exposes them;
- hostile archive fixtures, traversal attempts, and resource-exhaustion
  fixtures fail closed;
- a provider source can enter through CLI;
- identical raw input is detected safely by SHA;
- raw bytes are retained privately;
- raw source bytes are not committed;
- normalized observations retain exact source lineage;
- rollback mode proves zero persistence;
- apply mode verifies committed state from a second connection;
- relay documents use the same ingestion engine;
- dashboard uploads use the same ingestion engine;
- imported sources appear in Provider Evidence;
- importing alone does not select authority;
- private provider metadata is not exposed;
- existing read-only Provider Evidence browsing remains intact;
- dashboard tests, typecheck, and production build pass;
- project checks, secret scan, review-output scan, and diff check pass.

## 17. Implementation order

1. finalize generic source-envelope schema;
2. finalize normalized observation contract;
3. define provider-specific extension rules;
4. implement source/parser registry;
5. implement generic CLI plan/check/rollback/apply path;
6. integrate private object storage;
7. integrate relay source acquisition;
8. implement dashboard import workflow;
9. connect to reconciliation review;
10. document stage-capture operations;
11. validate with synthetic/sanitized provider fixtures;
12. conduct low-volume real-provider smoke tests only after explicit
    authorization.

## 18. Stage 9 boundary

This document is a plan, not authorization to access provider credentials or
issue provider API requests.

Real-provider collection remains blocked until the prerequisite plans are
reviewed and the project owner explicitly authorizes that stage.
