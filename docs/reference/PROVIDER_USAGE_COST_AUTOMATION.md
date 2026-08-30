# Provider Usage and Cost Automation

## Executive summary

This reference defines how `cc-deepseek-bench` should collect, normalize,
reconcile, and preserve provider-side usage and cost evidence.

It deliberately separates two questions:

1. **What does the provider expose?**
2. **What does this repository currently automate?**

Those are not interchangeable.

As of 2026-08-30, the generalized read-only provider collector supports only
Anthropic. Phase 3 also retains provider-specific historical ingestion for
DeepSeek, Gemini, Kimi, OpenAI, Qwen, and xAI. Some of those ingestors create
Migration-011 usage and cost reconciliations themselves.

Only DeepSeek, Gemini, and OpenAI have standalone
`reconcile_*_family_usage.py` programs. That is a historical implementation
shape, not a requirement that every provider receive a parallel standalone
reconciler.

Kimi, Qwen, and xAI perform their selected-run reconciliation inside their
later `ingest_*_provider_evidence.py` pipelines. Anthropic and GLM have
deliberate accepted normalized-absence states for the reviewed Phase 3
selected runs.

The intended future pipeline is:

    collect
      -> preserve first-party source evidence
      -> normalize provider observations
      -> reconcile to exact benchmark identity where supportable
      -> select qualified usage/cost authority
      -> review promotion evidence

Do not create extra standalone family reconcilers merely for filename
symmetry.

## Scope

Providers covered here:

- Anthropic
- DeepSeek
- Google Gemini
- OpenAI
- xAI / Grok
- Moonshot / Kimi
- Alibaba Cloud Model Studio / Qwen
- Z.AI / GLM

This reference covers:

- first-party usage evidence;
- first-party cost/billing evidence;
- credential class;
- granularity and attribution constraints;
- current repository automation;
- retained Phase 3 evidence state;
- recommended next automation step.

It does **not** redefine the frozen Phase 1, Phase 2, or Phase 3 results.

## Core evidence rules

### Provider capability is not repository implementation

A provider may expose a usable API even when the repository has no adapter for
it.

Conversely, a historical ingestion script may successfully preserve an export
without providing a reusable live collector.

Always describe these separately.

### Response usage is not historical provider billing

A completion response can establish request-level token usage without
establishing:

- account-level billed cost;
- historical completeness;
- credits or discounts;
- subscription overhead;
- invoice reconciliation.

Likewise, an account billing export does not automatically identify the exact
benchmark run that incurred the cost.

### Provider-window evidence is not selected-run authority by default

Account-, project-, API-key-, workspace-, model-, or day-level evidence may be
useful context.

It becomes selected-run authority only when the allocation is supportable and
reviewed.

Overlapping indistinguishable runs must not be synthetically divided merely to
produce a complete-looking table.

### Missing evidence is not zero

Missing provider usage or cost must remain missing, unresolved, qualified, or
accepted absence as appropriate.

Do not synthesize:

- zero provider spend;
- zero token usage;
- provider-observed model identity;
- per-trial allocation;
- per-outcome allocation.

### Raw harness accounting remains provenance

Migration 010 preserves `benchmark_trials.cost_usd` as immutable
harness-recorded artifact cost.

Provider evidence and Migration-011 reconciliations are additive authority
layers. They do not rewrite historical raw benchmark values.

### Collection does not itself select authority

A successful provider API request produces provider evidence.

It does not by itself establish:

- exact run attribution;
- current selected usage authority;
- current selected cost authority;
- permission to advance Canary to Smoke or Smoke to Full.

Those decisions belong to reconciliation and promotion review.

## Repository automation layers

### Generalized read-only collection

Current entry point:

    scripts/collect_provider_evidence.py

Current capability registry:

    scripts/provider_evidence/capability.py

Current provider adapters:

    scripts/provider_evidence/providers/anthropic.py

Only Anthropic is registered today.

The collector supports:

- plan-only credential/request inspection with no network request;
- read-only collection;
- non-overwriting private JSON output;
- source-page hashing;
- credential-value non-retention.

### Historical standalone family reconciliation

Retained programs:

    scripts/reconcile_deepseek_family_usage.py
    scripts/reconcile_gemini_family_usage.py
    scripts/reconcile_openai_family_usage.py

These came from the earlier Phase 3 provider-family reconciliation work.

They are historical reconciliation machinery, not the desired template for
every future provider.

### Migration-011 provider-evidence ingestion

Retained provider-specific ingestors:

    scripts/ingest_deepseek_provider_evidence.py
    scripts/ingest_gemini_provider_evidence.py
    scripts/ingest_kimi_provider_evidence.py
    scripts/ingest_openai_provider_evidence.py
    scripts/ingest_qwen_provider_evidence.py
    scripts/ingest_xai_provider_evidence.py

These validate reviewed evidence and construct some combination of:

- provider source rows;
- provider usage evidence;
- pricing snapshots;
- provider cost evidence;
- current usage reconciliations;
- current cost reconciliations;
- reconciliation-source links.

Kimi, Qwen, and xAI therefore **do have reconciliation logic** even though
there is no standalone `reconcile_kimi_family_usage.py`,
`reconcile_qwen_family_usage.py`, or `reconcile_xai_family_usage.py`.

### Accepted absence

No ingestion job should fabricate first-party selected-run evidence merely
because Migration 011 has tables for it.

Phase 3 explicitly accepts normalized absence for:

- four selected Anthropic arms;
- two selected GLM arms.

Anthropic absence means no retained first-party selected-run provider source
was available under the reviewed evidence and credential set.

GLM absence has two distinct causes:

- historical GLM 5.1 provider context is not allocable to the selected GLM 5.1
  run;
- comparable selected-run first-party evidence is not retained for GLM 5.2.

## Current capability matrix

| Provider | Current first-party usage path | Current first-party cost path | Elevated credential | Repo generalized collector | Phase 3 normalized selected-run state |
| --- | --- | --- | --- | --- | --- |
| Anthropic | Usage & Cost Admin API usage report | Usage & Cost Admin API cost report | Admin credential; repo currently requires `ANTHROPIC_ADMIN_API_KEY` | Yes | Accepted absence for 4 selected arms |
| DeepSeek | Per-response API `usage`; historical provider exports were retained in Phase 3 | Current balance API plus token pricing; no comparable historical billing-history API identified in reviewed current docs | Inference API key | No | 2 qualified rate estimates |
| Google Gemini | Per-response Gemini usage metadata | Google Cloud Billing export / billing reports | Gemini credential for inference; Cloud Billing IAM for billing export | No | 1 qualified rate estimate + 1 qualified lower bound |
| OpenAI | Organization Usage API | Organization Costs API | Organization Admin API credential | No | 2 exact provider-billed |
| xAI / Grok | Per-response usage plus Management API historical usage | Exact per-request `cost_in_usd_ticks`; Management API billing/usage | Inference API key plus separate Management key for management endpoints | No | 1 qualified lower bound |
| Moonshot / Kimi | Request/provider logs retained historically; no comparable public historical account usage API identified in the reviewed current docs | Current balance API as account context plus historical provider dashboard/export evidence and reviewed rate reconstruction; no comparable public historical billing API identified in the reviewed current docs | Kimi API credential | No | 2 qualified rate estimates |
| Alibaba / Qwen | Model response/harness usage plus Model Studio billing dimensions | Model Studio bill CSV and Alibaba BSS billing APIs | Model Studio API key for inference; Alibaba AccessKey/RAM permission for BSS | No | 1 qualified lower bound |
| Z.AI / GLM | Per-response `usage` token statistics | Console billing history documented; no comparable public historical billing API identified in the reviewed current docs | Z.AI API credential | No | Accepted absence for 2 selected arms |

"Not identified in the reviewed current docs" is intentionally narrower than
"does not exist." Recheck provider documentation before implementing a new
adapter.

## Anthropic

### Official provider capability

Current Claude Platform documentation exposes:

    GET /v1/organizations/usage_report/messages
    GET /v1/organizations/cost_report

Usage supports:

- `1m`, `1h`, and `1d` buckets;
- filtering/grouping by API key;
- workspace;
- model;
- service tier and additional dimensions.

The standard cost report currently supports:

- daily (`1d`) buckets;
- grouping by workspace;
- grouping by description.

The current provider documentation supports several Admin credential forms.

The repository adapter intentionally implements the narrower reviewed contract:

    ANTHROPIC_ADMIN_API_KEY

and validates the Admin-key prefix rather than accepting an ordinary inference
workspace key.

### Important cost limitation

The standard cost endpoint is not API-key allocable.

Therefore API-key-isolated usage does not by itself make cost run-allocable.

The existing adapter records this explicitly and requires workspace/day
isolation or another defensible allocation method.

Priority Tier cost is also not represented in the standard Claude Platform
cost endpoint.

### Current repository state

Implemented:

    scripts/provider_evidence/providers/anthropic.py

The collector already supports:

- request planning;
- pagination;
- usage collection;
- cost collection;
- source-page SHA-256;
- private non-overwriting output.

The reviewed project credential set did not contain the required Admin key, so
no retained first-party selected-run Anthropic source was normalized for the
closed Phase 3 selected runs.

### Next automation step

Do not redesign the adapter first.

Obtain or explicitly decline access to the required Admin credential.

Once available:

1. run plan-only collection for an isolated future Canary;
2. use distinguishable workspace/API-key dimensions;
3. collect usage and cost after the provider reporting delay;
4. preserve the raw first-party bundle privately;
5. normalize only supportable allocation;
6. perform reconciliation and promotion review.

### Official references

- https://platform.claude.com/docs/en/manage-claude/usage-cost-api
- https://platform.claude.com/docs/en/api/http/admin/usage_report/retrieve_messages
- https://platform.claude.com/docs/en/api/http/admin/cost_report/retrieve

## OpenAI

### Official provider capability

OpenAI exposes organization-level usage endpoints including:

    GET /v1/organization/usage/completions

Completions usage can be filtered or grouped by dimensions including:

- project ID;
- user ID;
- API-key ID;
- model;
- batch status;
- service tier.

Usage supports:

- `1m`;
- `1h`;
- `1d`;

with pagination.

Organization costs are exposed through:

    GET /v1/organization/costs

The current Costs API supports daily buckets and grouping by:

- project ID;
- line item.

OpenAI explicitly recommends Costs rather than usage-derived arithmetic as the
financial source for invoice-reconciling spend.

### Attribution consequence

Usage can be highly granular by API key and model.

Cost is not equivalently API-key-groupable in the current documented endpoint.

For future exact run cost, prefer a dedicated project or another independently
reviewable isolation boundary when practical.

Do not infer exact per-run billing merely because API-key usage is exact.

### Current repository state

Phase 3 retains:

    scripts/reconcile_openai_family_usage.py
    scripts/ingest_openai_provider_evidence.py

The selected GPT-5.4 and GPT-5.5 runs have exact normalized provider usage and
provider-billed cost.

The historical private provider exports remain outside Git; reviewed sanitized
manifests and normalized evidence retain their provenance.

### Next automation step

Add an OpenAI generalized provider adapter rather than extending the historical
CSV-specific reconciler.

The adapter should:

1. require an Admin credential;
2. query usage grouped by project/API key/model;
3. query Costs for the same bounded period/project;
4. preserve both responses independently;
5. never force usage and costs into false one-to-one granularity;
6. reconcile only after exact benchmark-run identity is known.

### Official reference

- https://platform.openai.com/docs/api-reference/usage

## DeepSeek

### Official provider capability

DeepSeek documents that actual token usage returned by the model response is
the source of truth for request token accounting.

It also exposes:

    GET /user/balance

The balance endpoint reports current available balance, including granted and
topped-up components.

A current balance is useful funding context; it is **not** historical
per-request billing evidence.

### Pricing changed after Phase 3

As of 2026-08-30, DeepSeek uses peak/off-peak prices for current V4 models.

The new pricing took effect on 2026-08-16.

Therefore a future cost reconstruction must retain request timestamps and apply
the rate effective at the request time.

Do not apply the old Phase 3 static rate table to future runs.

### Current repository state

Phase 3 retains:

    scripts/reconcile_deepseek_family_usage.py
    scripts/ingest_deepseek_provider_evidence.py

Historical provider archive rows validated retained smoke-window usage and
pricing arithmetic.

The selected Phase 3 full runs use:

    selected_usage_authority = harness_usage_validated
    selected_cost_relation = estimate

for both DeepSeek selected arms.

### Next automation step

Build a generalized DeepSeek adapter around prospective evidence rather than
the old archive format:

1. retain exact per-response usage;
2. retain model identity and request timestamp;
3. optionally sample balance before/after a deliberately isolated Canary as
   context only;
4. snapshot the effective official pricing contract;
5. reconstruct cost with time-aware peak/off-peak semantics;
6. keep reconstructed cost qualified unless stronger provider billing evidence
   is available.

### Official references

- https://api-docs.deepseek.com/quick_start/token_usage/
- https://api-docs.deepseek.com/api/get-user-balance/
- https://api-docs.deepseek.com/quick_start/pricing/

## Google Gemini

### Official provider capability

Gemini responses expose usage metadata.

Current documentation distinguishes token counts including:

- input/prompt tokens;
- cached-content tokens;
- output/candidate tokens;
- thinking tokens where applicable;
- total tokens.

Google Cloud Billing can automatically export billing information to BigQuery,
including standard or detailed usage cost and pricing data.

Cloud Billing export is a billing-account/project evidence source, not
automatically a Gemini benchmark-run identity source.

### Billing-export considerations

Cloud Billing export requires separate IAM and BigQuery setup.

The provider documents:

- possible reporting delay;
- initial catch-up/backfill behavior;
- different historical availability depending on dataset location and when
  export was enabled.

Enable billing export **before** future paid experiments if it will be part of
the evidence contract.

### Current repository state

Phase 3 retains:

    scripts/reconcile_gemini_family_usage.py
    scripts/ingest_gemini_provider_evidence.py

Historical Google billing evidence was billing-level rather than complete
selected-run provider token logging.

The current normalized selected Phase 3 states are:

- Gemini 3.1 Pro: qualified rate estimate;
- Gemini Flash: qualified lower bound.

### Next automation step

Use two independent channels:

1. capture exact response usage and request/model identity during execution;
2. ingest Google Cloud Billing export as independent first-party cost evidence.

Use a dedicated project or equivalent isolation where practical.

Do not assume a Cloud Billing row alone identifies an exact Claude Code trial.

### Official references

- https://ai.google.dev/gemini-api/docs/tokens
- https://ai.google.dev/gemini-api/docs/caching
- https://cloud.google.com/billing/docs/how-to/export-data-bigquery
- https://cloud.google.com/billing/docs/how-to/export-data-bigquery-tables/standard-usage

## xAI / Grok

### Official provider capability

xAI now exposes unusually strong prospective accounting evidence.

Every current inference response includes:

    usage.cost_in_usd_ticks

The provider documents this value as the actual amount billed for that request,
after applicable discounts and inclusive of relevant token/tool cost.

Conversion is:

    1 USD = 10,000,000,000 ticks

or:

    cost_usd = cost_in_usd_ticks / 10_000_000_000

For streaming APIs, retain the final usage-bearing response/chunk.

xAI also exposes a separate Management API requiring a Management key.

Current billing operations include:

    POST /v1/billing/teams/{team_id}/usage

for historical API usage over a bounded time period.

The Management API also exposes prepaid balance/balance changes and invoice
information.

### Current repository state

Phase 3 retains:

    scripts/ingest_xai_provider_evidence.py

There is no standalone family reconciliation script because the later ingestor
already creates Migration-011 usage and cost reconciliation state.

The selected `router-grok-build-0.1` Phase 3 run remains a qualified lower
bound because the retained selected-run evidence does not contain granular
provider usage or provider-billed request cost for the selected June 28 run,
the available provider-dashboard totals are not selected-run allocable, and
one selected trial remains unresolved.

xAI release notes date Cost Tracking, including `cost_in_usd_ticks`, to
2026-04-30, before that selected run. The field was not retained in this
benchmark evidence path for the run, so do not retroactively invent
request-level provider billing for the closed Phase 3 evidence set.

### Next automation step

xAI should be one of the highest-priority new generalized adapters.

For a future isolated run:

1. retain response request/model/usage identifiers;
2. retain `cost_in_usd_ticks` as integer first-party cost;
3. sum per-request cost without floating-point conversion until presentation;
4. query Management API historical usage for independent reconciliation;
5. preserve both evidence channels;
6. treat discrepancies as review targets rather than silently choosing one.

### Official references

- https://docs.x.ai/developers/cost-tracking
- https://docs.x.ai/developers/release-notes
- https://docs.x.ai/developers/rest-api-reference/management
- https://docs.x.ai/developers/rest-api-reference/management/billing
- https://docs.x.ai/console/usage

## Moonshot / Kimi

### Official provider capability reviewed

Kimi Open Platform provides the inference API used by the benchmark.

Current official documentation also exposes:

    GET /v1/users/me/balance

The endpoint reports available, voucher, and cash balances. This is current
account-funding context, not historical request usage or billed-cost evidence,
and it does not identify a benchmark run.

During the 2026-08-30 official-document review, no public historical
organization/account usage-and-cost API comparable to the current Anthropic,
OpenAI, or xAI management reporting endpoints was identified.

That statement is intentionally scoped to this review. It is **not** a claim
that such an API cannot exist or cannot be added later.

Recheck the provider documentation immediately before implementing the
collector.

### Current repository state

Phase 3 retains:

    scripts/ingest_kimi_provider_evidence.py
    scripts/recompute_kimi_k3_costs.py

The ingestor embeds reconciliation.

Historical Kimi request/provider evidence is retained as context but is not
silently promoted to selected-run provider billing where time-window
allocation is unsupported.

The selected normalized states are:

- Kimi K2.6: qualified rate estimate;
- Kimi K3: qualified rate estimate.

Both use:

    selected_usage_authority = harness_usage_validated

with reviewed provider-rate reconstruction.

### Next automation step

For future Kimi runs:

1. preserve complete inference response usage and provider request identifiers
   visible through the actual API/router path;
2. optionally capture current balance before/after a deliberately isolated run
   as account context, not as a substitute for billing history;
3. isolate the benchmark API key/account window where practical;
4. retain any first-party console/export evidence privately;
5. snapshot official pricing provenance at run time;
6. re-check whether a programmatic historical account usage/billing endpoint
   has become available;
7. keep cost qualified when provider billing cannot be directly allocated.

Do not revive the stale Kimi K3 `$30.8143194` provider-log reconstruction as
the current selected-run total. The current reviewed selected Kimi K3 cost is
`$26.570403`.

### Official references

- https://platform.kimi.ai/docs/overview
- https://platform.kimi.ai/docs/api/balance

## Alibaba Cloud Model Studio / Qwen

### Official provider capability

Model Studio billing details can be exported as CSV.

Current Model Studio documentation says billing can be traced through
dimensions including:

- API Key ID;
- workspace ID;
- model name;
- input/output billing type;
- invocation channel.

Alibaba Cloud also exposes billing data programmatically through BSS OpenAPI.

Relevant read operations include:

- `QueryBillOverview`;
- `QueryBill`;
- `QueryInstanceBill`;
- `QueryAccountBalance`.

Alibaba documents that finance APIs have reporting delay and do not provide
individual API-call-level usage records.

BSS access uses an Alibaba Cloud AccessKey and RAM permissions; read-only
billing access can use `AliyunBSSReadOnlyAccess`.

This credential is separate from the Model Studio inference API key.

### Current repository state

Phase 3 retains:

    scripts/ingest_qwen_provider_evidence.py

The ingestor embeds selected-run reconciliation.

Historical Alibaba billing evidence predates the selected Qwen run and
includes a Token Plan purchase.

The ingestor correctly separates subscription/account overhead from marginal
inference cost and does not relabel billing line items as API requests.

The selected Qwen 3.7 Plus state remains a qualified lower bound.

### Next automation step

Prospective automation should combine:

1. response/harness request usage;
2. Model Studio API-key/workspace isolation;
3. BSS bill retrieval or subscribed/exported bill evidence;
4. explicit separation of subscription/resource-plan overhead from marginal
   inference consumption.

Never infer individual API requests from BSS bill line items when the provider
does not expose that granularity.

### Official references

- https://www.alibabacloud.com/help/en/model-studio/bill-query-and-cost-management
- https://www.alibabacloud.com/help/en/user-center/bill-view
- https://www.alibabacloud.com/help/en/user-center/developer-reference/api-overview-1
- https://www.alibabacloud.com/help/en/user-center/developer-reference/api-calling-authorization

## Z.AI / GLM

### Official provider capability

Current Z.AI model responses expose usage statistics including:

- prompt tokens;
- cached prompt tokens where applicable;
- completion tokens;
- total tokens.

The current Z.AI FAQ documents billing history as delayed:

- billing history reflects daily consumption records;
- current-day consumption is not immediately visible;
- the displayed billing state may therefore lag actual requests.

During the 2026-08-30 official-document review, no public programmatic
historical billing API comparable to the current Anthropic, OpenAI, or xAI
reporting APIs was identified.

Again, "not identified" is not the same as "does not exist."

### Current repository state

There is deliberately no:

    scripts/ingest_glm_provider_evidence.py
    scripts/reconcile_glm_family_usage.py

for the selected Phase 3 closure state.

This is intentional.

Historical GLM 5.1 provider context cannot be allocated to the selected GLM
5.1 run.

Comparable selected-run first-party evidence is not retained for GLM 5.2.

Both selected GLM arms therefore remain:

    accepted_absence_glm_deliberate_empty

in the Migration-011 selected-run consistency contract.

### Next automation step

Do not backfill Phase 3 with synthetic evidence.

For a future GLM run:

1. persist complete response-level usage;
2. retain exact provider request/model identity where exposed;
3. isolate the API key/account window;
4. collect first-party billing history after the documented reporting delay;
5. re-check current Z.AI docs for a programmatic billing endpoint;
6. normalize only evidence that can actually be tied to the run.

### Official references

- https://docs.z.ai/api-reference/llm/chat-completion
- https://docs.z.ai/guides/capabilities/streaming
- https://docs.z.ai/help/faq

## Phase 3 normalized selected-run summary

The closed Phase 3 selected-run consistency contract contains 16 selected arms
across eight provider families.

Current normalized authority:

| Provider | Selected arms | Migration-011 selected-run state |
| --- | ---: | --- |
| Anthropic | 4 | Accepted normalized absence |
| DeepSeek | 2 | 2 qualified rate estimates |
| Google Gemini | 2 | 1 qualified rate estimate; 1 qualified lower bound |
| OpenAI | 2 | 2 exact provider-billed |
| xAI / Grok | 1 | 1 qualified lower bound |
| Moonshot / Kimi | 2 | 2 qualified rate estimates |
| Alibaba / Qwen | 1 | 1 qualified lower bound |
| Z.AI / GLM | 2 | Accepted normalized absence |

Totals:

    16 selected arms
    10 normalized reconciliation chains
    6 accepted normalized-absence arms
    2 exact provider-billed
    5 qualified rate estimates
    3 qualified lower bounds

These are closed Phase 3 evidence states.

Future collection capability does not retroactively modify them.

## Why only three standalone family reconcilers exist

The standalone reconciler filenames reflect the chronology of Phase 3.

The earlier reconciliation phase produced:

    reconcile_deepseek_family_usage.py
    reconcile_gemini_family_usage.py
    reconcile_openai_family_usage.py

Later provider-evidence work moved reconciliation into the ingestion layer.

Therefore:

| Provider | Standalone family reconciler | Reconciliation location |
| --- | --- | --- |
| DeepSeek | Yes | Historical family reconciler + later Migration-011 ingestor |
| Gemini | Yes | Historical family reconciler + later Migration-011 ingestor |
| OpenAI | Yes | Historical family reconciler + later Migration-011 ingestor |
| Kimi | No | Embedded in `ingest_kimi_provider_evidence.py` |
| Qwen | No | Embedded in `ingest_qwen_provider_evidence.py` |
| xAI | No | Embedded in `ingest_xai_provider_evidence.py` |
| Anthropic | No | Collector exists; reviewed selected runs retain accepted absence |
| GLM | No | Deliberate selected-run accepted absence |

Do not add standalone reconcilers solely to make this table symmetrical.

## Recommended collector expansion order

This order reflects current prospective evidentiary leverage, not model
priority.

### 1. Exercise the existing Anthropic collector when credential access exists

The implementation already exists.

The blocker is the correct Admin credential and safe run isolation.

### 2. Add xAI

xAI now offers exact per-request provider-billed cost plus a separate
historical Management API.

That combination can provide unusually strong prospective evidence.

### 3. Add OpenAI

The organization Usage and Costs APIs are mature and programmatic.

Preserve their different grouping granularities rather than pretending cost is
as API-key granular as usage.

### 4. Add Gemini

Capture request usage at execution and automate Cloud Billing evidence as an
independent channel.

Configure billing export before paid experiments.

### 5. Add DeepSeek

Capture exact response usage plus request timestamps.

Make reconstruction aware of effective pricing and peak/off-peak periods.

Treat balance only as account context.

### 6. Add Alibaba / Qwen

Combine request usage with Model Studio bill dimensions and BSS evidence.

Keep subscription/resource-plan overhead separate.

### 7. Add Moonshot / Kimi

Capture response/request evidence first and re-check the current platform for
a newly documented account reporting interface.

### 8. Add Z.AI / GLM

Capture response usage prospectively and preserve delayed first-party billing
evidence without inventing a programmatic history API.

## Desired generalized adapter contract

Future provider adapters should expose equivalent **conceptual** operations,
not falsely identical provider schemas.

Recommended provider contract:

    credential_preflight(...)
    request_plan(...)
    collect(...)

A collection bundle should retain, where available:

- provider;
- collection timestamp/window;
- provider endpoint/source identity;
- request plan;
- provider model identity;
- API-key/project/workspace dimensions;
- request IDs;
- token buckets;
- first-party request cost;
- account/project cost;
- currency/unit;
- reporting delay;
- pagination metadata;
- source-page/object hash;
- explicit limitations.

The bundle must distinguish:

    actual field absent
    field unsupported by provider
    credential unavailable
    collection failed
    evidence exists but is not run-allocable

These states must not collapse into `0`.

## Storage and privacy contract

Raw first-party provider exports may contain:

- API-key identifiers;
- user/project/workspace identifiers;
- account metadata;
- private billing information.

Do not commit such raw material by default.

Preferred workflow:

1. write private raw collection under an ignored location with restrictive
   permissions;
2. hash the raw bytes;
3. derive a sanitized normalized snapshot;
4. retain only the minimum source identifiers required for reproducibility;
5. run the strict secret scan before commit;
6. keep provider credential values out of logs and artifacts.

The existing Anthropic collector's exclusive non-overwriting private output is
a useful pattern.

## Future experiment collection contract

Before the first paid future experiment:

1. establish a distinguishable provider allocation boundary where possible;
2. snapshot provider capability and pricing;
3. collect a baseline provider state if useful;
4. run Canary;
5. collect provider evidence after the documented reporting delay;
6. reconcile Canary usage/cost;
7. review the Canary-to-Smoke promotion gate;
8. repeat for Smoke before Full.

Full is an experiment stage, not the point at which provider telemetry should
first be discovered.

## Relationship to promotion review

Provider collection and reconciliation feed promotion review.

They do not bypass it.

The durable review path remains:

    provider evidence
      -> current usage reconciliation
      -> current cost reconciliation
      -> reviewed promotion decision
      -> Planner read-only consumption

See:

- `docs/methodology/USAGE_AND_COST_EVIDENCE_MODEL.md`
- `docs/runbooks/EVIDENCE_PROMOTION_REVIEW.md`
- `db/migrations/phase3/011_provider_evidence_contract.sql`

## Future-phase boundary

This reference does not activate Phase 4 or Phase 5.

Before the first paid Phase 4 Canary:

- finalize the harness-version identity contract;
- review/migrate promotion authorization so experiment/suite/phase identity is
  safely scoped;
- ensure provider collectors needed for the selected arms are ready at Canary,
  not after Full.

Phase 5 procedure/planner-executor evidence remains later work after Phase 4.

## Source review date

Official provider documentation in this reference was rechecked on
**2026-08-30**.

Provider APIs and billing systems change.

Re-verify the cited official documentation before implementing or operating a
new collector.
