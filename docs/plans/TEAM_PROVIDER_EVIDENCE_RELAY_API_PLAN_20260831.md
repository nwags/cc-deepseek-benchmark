# Team Provider Evidence Relay API Plan

Date: 2026-08-31

Status: planning only

Repository baseline:
`main@5e979154866b0b09e2c1086c99126c6b0b5092c2`

## 1. Purpose

Provide the benchmark team safe, limited access to first-party provider usage
and cost evidence without giving team members direct access to:

- provider billing consoles;
- account-owner privileges;
- provider browser sessions;
- high-privilege provider credentials.

The relay should run on a controlled VPS with the minimum provider access
required to capture evidence.

It exposes retained provider evidence documents plus safe metadata.

It is not a general provider-console proxy.

## 2. Acquisition priority

Prefer documented provider APIs when they expose adequate historical usage or
cost evidence.

Use dashboard exports when a comparable API is unavailable or as independent
verification.

Initial acquisition policy:

### OpenAI

Primary:

- Organization Usage API;
- Organization Costs API.

Optional supporting evidence:

- provider dashboard export.

### Google Gemini

Usage:

- Cloud Monitoring API.

Cost:

- Cloud Billing export to BigQuery;
- BigQuery API queries.

AI Studio browser automation is not the normal collection path.

### DeepSeek

Historical provider usage/cost evidence:

- scheduled provider Usage export from the provider dashboard.

Supporting evidence:

- provider balance snapshots where useful;
- benchmark-retained usage/accounting when available;
- applicable pricing evidence.

The DeepSeek collector must not require provider-native response usage to be
available through Harbor.

## 3. Continuous evidence feed

The relay should operate as a low-frequency evidence feed, not a per-request
observer.

Target cadence:

- scheduled provider capture about every 12 hours;
- optional benchmark-aware pre-stage capture;
- post-stage capture;
- delayed capture after reporting latency;
- monthly/final capture where useful.

A failed capture is an evidence gap.

It must never be converted into an assumption of zero usage or zero cost.

Every scheduler invocation must retain a capture-attempt record even when the
provider returns content whose SHA-256 exactly matches a prior capture.

An unchanged capture can reuse the existing immutable content object while
recording a new `unchanged_duplicate` capture result. This preserves evidence
that the scheduled acquisition actually ran and observed no provider-side
change.

## 4. Dashboard export automation

Provider-dashboard automation is acceptable when:

- the provider documents the export capability;
- no comparable historical API is available;
- automation does not bypass MFA, CAPTCHA, access control, or security
  mechanisms;
- browser/session state remains on the controlled VPS;
- session expiration fails visibly.

For DeepSeek, scheduled Usage export is a first-class initial adapter.

If the export is cumulative or current-month scoped:

- retain every export as a new immutable source snapshot;
- never overwrite the prior snapshot;
- never sum overlapping snapshots directly.

## 5. DeepSeek capture worker

Initial controlled worker behavior:

1. use an authenticated provider session on the VPS;
2. navigate only to the documented Usage/export flow;
3. select the intended reporting period;
4. request the export;
5. download the provider ZIP;
6. retain the exact ZIP bytes;
7. hash the ZIP;
8. hash relevant ZIP members;
9. identify the provider usage/amount material;
10. emit the generic source envelope;
11. retain earlier snapshots unchanged.

If reauthentication, CAPTCHA, MFA, or another access challenge occurs:

- stop;
- set capture status to `reauthentication_required`;
- notify the operator;
- do not attempt to bypass the provider control.

## 6. Capture versus normalization

The VPS capture worker should not make benchmark attribution decisions.

Its responsibilities are:

- obtain provider evidence;
- retain immutable source material;
- hash it;
- catalog it;
- expose safe metadata;
- make it retrievable to authorized team members and Task 0.

Normalization and reconciliation remain in the shared ingestion subsystem.

## 7. Shared generic source contract

The relay must use the same source-envelope contract consumed by:

- CLI import;
- dashboard import;
- provider API collectors;
- manual provider uploads.

Safe relay metadata should include:

- relay document ID;
- provider;
- evidence kind;
- capture method;
- capture timestamp;
- provider coverage start;
- provider coverage end;
- provider coverage timezone;
- source format;
- content type;
- byte size;
- SHA-256;
- parser availability;
- sanitized account/project/key/model dimensions where appropriate;
- overlap/supersession metadata where useful;
- capture status.

Never return:

- provider credentials;
- browser cookies;
- authorization headers;
- signed provider tokens;
- unrestricted object-store credentials;
- unsafe raw provider metadata.

### Acquisition manifests

Each retained API/query/export capture should also have a sanitized acquisition
manifest compatible with Task 0.

The relay catalog should therefore be able to describe, where applicable:

- adapter/version;
- requested provider interval and boundary semantics;
- safe query/filter/grouping parameters;
- pagination/page hashes;
- BigQuery query hash or safe canonical query information;
- DeepSeek reporting-period/export selection;
- provider timezone and data maturity;
- capture timing and outcome.

The manifest must contain no provider credentials or browser-session secrets.

## 8. Relay API

Keep the first API deliberately small.

Candidate read-only endpoints:

    GET /v1/providers
    GET /v1/documents
    GET /v1/documents/{document_id}
    GET /v1/documents/{document_id}/download

For the initial implementation, authenticated document downloads should be
served through the relay so authorization, rate limiting, and audit accounting
remain enforceable for the actual byte transfer.

Do not expose the private evidence bucket directly to normal relay users.
A future short-lived object-download mechanism would need equivalent
per-document authorization, expiry, and audit semantics before replacing relay
streaming.

Useful document filters:

- provider;
- evidence kind;
- capture method;
- captured-after;
- captured-before;
- provider coverage range;
- source hash.

Administrative capture/refresh actions, if introduced, must be separate from
normal team read access.

Do not provide:

- arbitrary URL fetching;
- arbitrary browser navigation;
- provider-console proxying;
- arbitrary commands;
- credential retrieval.

## 9. Authentication

Preferred access model:

1. private network overlay such as Tailscale or WireGuard;
2. individual team relay credentials;
3. HTTPS even over the private overlay where practical.

If the relay must be Internet-facing, place an identity-aware access layer in
front of it.

Provider credentials and relay user credentials must always be distinct.

Initial authorization roles should distinguish at least:

- `metadata_reader` — list and inspect sanitized document metadata;
- `evidence_reader` — download authorized retained provider evidence;
- `capture_admin` — operate or repair provider capture jobs.

Normal team users must not receive `capture_admin` merely because they can
download evidence.

Relay credentials must support:

- revocation;
- rotation;
- expiration where practical;
- server-side hashed/derived credential storage rather than recoverable
  plaintext bearer-token storage;
- explicit role/scope assignment.

Raw evidence downloads may contain sensitive provider/account identifiers even
when they contain no provider credential. Access to raw evidence should
therefore be narrower than access to sanitized metadata when appropriate.

## 10. Rate limiting

Strong rate limits are required.

The implementation must support at least:

- per-user requests/minute;
- per-user requests/hour;
- concurrent-download limit;
- per-download byte limit;
- per-user daily byte limit;
- global circuit breaker;
- provider capture limits independent of document-download limits.

Downloading a retained document must never trigger a live provider request.

Normal team users cannot force provider captures.

## 11. Audit logging

Record:

- authenticated relay identity;
- request timestamp;
- document ID;
- provider;
- requested action;
- response status;
- bytes returned;
- rate-limit outcome.

Never log:

- relay bearer tokens;
- provider API credentials;
- provider authorization headers;
- browser cookies;
- sensitive raw payload contents.

## 12. OpenAI adapter

Primary collection:

- Organization Usage API;
- Organization Costs API.

Retain native response pages/bundles before normalization.

Preserve supported grouping dimensions.

Do not assume that dimensions available in Usage are also available in Costs.

In particular, API-key-specific usage does not automatically make cost
API-key attributable.

Use provider project/window isolation where needed for defensible attribution.

Dashboard exports may serve as independent supporting evidence.

## 13. Google adapter

Usage:

- query Cloud Monitoring for Gemini / Generative Language usage metrics.

Cost:

- consume Cloud Billing export to BigQuery;
- query it through tightly scoped BigQuery credentials.

Billing export should be enabled before future paid benchmark stages where
possible.

Reporting latency and provider corrections must remain explicit.

The relay should preserve enough query metadata and result hashes to reproduce
what provider-side evidence was observed without exposing broad Google Cloud
access to team members.

## 14. DeepSeek adapter

The first historical DeepSeek provider adapter is dashboard-export based.

Scheduled exports should default to approximately every 12 hours, subject to
provider behavior and operational experience.

Repeated current-month exports are retained as overlapping snapshots.

A later normalization layer may compute defensible deltas when source
semantics permit, but the capture layer itself does not do benchmark
attribution.

A dedicated benchmark API key should be preferred when provider export
dimensions make that useful.

### Cross-provider isolation policy

Where operationally practical, capture should use benchmark-specific provider
dimensions that minimize unrelated account activity.

Examples include:

- bounded OpenAI benchmark project/API-key dimensions;
- bounded Google project/billing/monitoring dimensions;
- a dedicated DeepSeek benchmark API key.

The relay records the safe attribution dimensions in effect for the capture,
but never exposes credential values.

### Provider capability revalidation

Before enabling any real provider adapter, revalidate the provider's current
documented API/export capabilities, supported grouping dimensions, permissions,
and reporting latency.

The implementation must not assume that the provider interfaces researched
during planning remain unchanged indefinitely.

## 15. Capture status vocabulary

Initial statuses:

- `captured`;
- `unchanged_duplicate`;
- `provider_data_pending`;
- `reauthentication_required`;
- `provider_unavailable`;
- `rate_limited`;
- `parse_pending`;
- `failed`.

These describe capture state, not selected benchmark authority.

## 16. Interaction with Task 0

The relay provides source material to the generic ingestion subsystem.

Target dashboard flow:

    Provider Evidence Import
        |
        +-- Upload local provider export
        |
        +-- Import from Team Relay
                 |
                 v
          choose relay document
                 |
                 v
          verify source hash
                 |
                 v
          same generic ingest engine

The resulting canonical provider source should retain:

- relay document ID;
- provider source SHA;
- capture metadata;
- immutable source lineage.

The relay does not itself write selected benchmark reconciliations.

## 17. Secret-management boundary

Provider credentials and browser-session state must:

- remain on the controlled capture host or approved secret store;
- never be returned through the relay API;
- never be included in generic source envelopes;
- never be committed;
- never be logged.

The capture host should use minimum provider privileges needed for its adapter.

## 18. Deployment hardening

Initial deployment should include:

- separate process/container identity;
- least-privilege filesystem permissions;
- read-only application filesystem where practical;
- private evidence storage;
- no shell/debug HTTP endpoint;
- narrow outbound destinations where practical;
- bounded log retention;
- security-update process;
- evidence metadata backup/recovery procedure.

## 19. Failure behavior

All collection mechanisms fail closed.

Examples:

- expired DeepSeek session -> `reauthentication_required`;
- OpenAI API error -> retain prior evidence, record failure;
- Google billing lag -> `provider_data_pending`;
- source parse failure -> retain raw source, mark `parse_pending` or `failed`;
- rate limit -> record rate-limited capture without fabricating provider data.

Existing valid source evidence must never be destroyed because a later capture
fails.

## 20. Acceptance criteria

Before Task 1 is complete:

- every scheduler invocation leaves an auditable capture-attempt outcome;
- unchanged provider content can reuse physical bytes without losing the later
  capture event;
- acquisition manifests retain safe reproducibility metadata;
- metadata-reader, evidence-reader, and capture-admin boundaries are enforced;
- credential rotation and revocation are tested;
- unauthenticated access fails;
- relay users have individual identities;
- strong rate limits are enforced;
- provider credentials never appear in API responses;
- provider credentials never appear in logs;
- documents are immutable by ID/hash;
- identical captures are recognized without corrupting provenance;
- overlapping snapshots remain distinct;
- download hashes match catalog hashes;
- relay documents enter Task 0 through the same ingestion engine;
- DeepSeek reauthentication fails closed;
- OpenAI and Google collection failures preserve prior evidence;
- team document downloads do not trigger live provider requests;
- audit records capture access without secrets.

## 21. Implementation order

1. finalize shared source-envelope contract with Task 0;
2. define relay catalog schema;
3. build fixture-only local relay;
4. implement authentication;
5. implement rate limits;
6. implement immutable document storage;
7. implement provider adapters using sanitized fixtures;
8. connect relay import to Task 0;
9. security review;
10. perform low-volume real-provider tests only after explicit authorization;
11. productionize scheduled capture;
12. enable team access.

## 22. Stage 9 boundary

This document is a plan, not authorization to use provider credentials.

Planning, schema design, sanitized fixture development, and local relay
testing may proceed before real-provider authorization.

No real OpenAI, Google, DeepSeek, or other provider requests should be issued
until the prerequisite plans are reviewed and the project owner explicitly
authorizes the provider-collection stage.
