-- Provider usage/cost evidence and Canary/Smoke promotion contract.
--
-- This migration is additive. It does not rewrite benchmark_trials,
-- benchmark_arm_runs, historical cost coverage, or frozen reviewed results.
--
-- Large raw provider artifacts should normally live in R2. Supabase stores
-- normalized provider evidence plus immutable provenance (artifact reference,
-- URI, SHA-256, provider reference, capture window).
--
-- Usage validation and cost validation are intentionally independent.

create table if not exists benchmark.benchmark_provider_evidence_sources (
    id uuid primary key default gen_random_uuid(),
    provider text not null,
    arm_run_id uuid references benchmark.benchmark_arm_runs(id)
        on delete set null,
    artifact_id uuid references benchmark.benchmark_artifacts(id)
        on delete set null,
    evidence_kind text not null,
    source_scope text not null,
    source_uri text,
    provider_reference text,
    source_sha256 text,
    size_bytes bigint,
    source_format text,
    provider_window_started_at timestamptz,
    provider_window_finished_at timestamptz,
    captured_at timestamptz not null default now(),
    integrity_status text not null default 'unverified',
    notes text,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    check (
        evidence_kind in (
            'usage_export',
            'billing_export',
            'request_log',
            'dashboard_snapshot',
            'invoice',
            'pricing_snapshot',
            'provider_api_response',
            'manual_capture'
        )
    ),
    check (
        source_scope in (
            'request',
            'trial',
            'arm_run',
            'model_window',
            'provider_window',
            'account_window',
            'pricing_snapshot',
            'other'
        )
    ),
    check (
        integrity_status in (
            'sha256_verified',
            'provider_api_record',
            'provider_dashboard_snapshot',
            'manual_unverified',
            'unverified'
        )
    ),
    check (
        source_sha256 is null
        or source_sha256 ~ '^[0-9a-f]{64}$'
    ),
    check (size_bytes is null or size_bytes >= 0),
    check (
        provider_window_finished_at is null
        or provider_window_started_at is null
        or provider_window_finished_at >= provider_window_started_at
    ),
    check (
        artifact_id is not null
        or source_uri is not null
        or provider_reference is not null
    )
);

create unique index if not exists
    idx_provider_evidence_source_sha256
on benchmark.benchmark_provider_evidence_sources (
    provider,
    source_sha256
)
where source_sha256 is not null;

create index if not exists idx_provider_evidence_source_provider
on benchmark.benchmark_provider_evidence_sources (
    provider,
    captured_at desc
);

create table if not exists benchmark.benchmark_provider_usage_evidence (
    id uuid primary key default gen_random_uuid(),
    source_id uuid not null
        references benchmark.benchmark_provider_evidence_sources(id)
        on delete cascade,
    arm_run_id uuid references benchmark.benchmark_arm_runs(id)
        on delete set null,
    trial_id uuid references benchmark.benchmark_trials(id)
        on delete set null,
    provider_request_id text,
    provider_model text,
    request_started_at timestamptz,
    request_finished_at timestamptz,
    ordinary_input_tokens bigint,
    cache_read_input_tokens bigint,
    cache_creation_input_tokens bigint,
    output_tokens bigint,
    request_count integer not null default 1,
    allocation_scope text not null,
    completeness_status text not null,
    notes text,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    check (
        allocation_scope in (
            'exact_trial',
            'exact_arm_run',
            'model_window',
            'provider_window',
            'account_window',
            'unallocated'
        )
    ),
    check (
        completeness_status in (
            'complete',
            'partial',
            'aggregate_only'
        )
    ),
    check (
        ordinary_input_tokens is null
        or ordinary_input_tokens >= 0
    ),
    check (
        cache_read_input_tokens is null
        or cache_read_input_tokens >= 0
    ),
    check (
        cache_creation_input_tokens is null
        or cache_creation_input_tokens >= 0
    ),
    check (output_tokens is null or output_tokens >= 0),
    check (request_count > 0),
    check (
        request_finished_at is null
        or request_started_at is null
        or request_finished_at >= request_started_at
    )
);

create unique index if not exists
    idx_provider_usage_request_identity
on benchmark.benchmark_provider_usage_evidence (
    source_id,
    provider_request_id
)
where provider_request_id is not null;

create index if not exists idx_provider_usage_arm_run
on benchmark.benchmark_provider_usage_evidence (arm_run_id);

create index if not exists idx_provider_usage_trial
on benchmark.benchmark_provider_usage_evidence (trial_id);

create table if not exists benchmark.benchmark_provider_pricing_snapshots (
    id uuid primary key default gen_random_uuid(),
    source_id uuid not null
        references benchmark.benchmark_provider_evidence_sources(id)
        on delete restrict,
    provider text not null,
    provider_model text not null,
    currency text not null default 'USD',
    effective_from timestamptz,
    effective_until timestamptz,
    pricing_semantics text not null,
    pricing_rules jsonb not null,
    official_source_uri text,
    notes text,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    check (
        effective_until is null
        or effective_from is null
        or effective_until >= effective_from
    )
);

create index if not exists idx_provider_pricing_model
on benchmark.benchmark_provider_pricing_snapshots (
    provider,
    provider_model,
    effective_from
);

create table if not exists benchmark.benchmark_provider_cost_evidence (
    id uuid primary key default gen_random_uuid(),
    source_id uuid not null
        references benchmark.benchmark_provider_evidence_sources(id)
        on delete cascade,
    arm_run_id uuid references benchmark.benchmark_arm_runs(id)
        on delete set null,
    trial_id uuid references benchmark.benchmark_trials(id)
        on delete set null,
    pricing_snapshot_id uuid
        references benchmark.benchmark_provider_pricing_snapshots(id)
        on delete set null,
    provider_model text,
    cost_kind text not null,
    amount_usd numeric not null,
    currency text not null default 'USD',
    allocation_scope text not null,
    completeness_status text not null,
    notes text,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    check (
        cost_kind in (
            'provider_request_billed',
            'provider_arm_run_billed',
            'provider_dashboard_total',
            'provider_invoice_total',
            'provider_rate_reconstruction',
            'account_spend',
            'overhead',
            'credit_adjustment'
        )
    ),
    check (
        amount_usd >= 0
        or cost_kind = 'credit_adjustment'
    ),
    check (
        allocation_scope in (
            'exact_trial',
            'exact_arm_run',
            'model_window',
            'provider_window',
            'account_window',
            'unallocated'
        )
    ),
    check (
        completeness_status in (
            'complete',
            'partial',
            'aggregate_only'
        )
    )
);

create index if not exists idx_provider_cost_arm_run
on benchmark.benchmark_provider_cost_evidence (arm_run_id);

create index if not exists idx_provider_cost_trial
on benchmark.benchmark_provider_cost_evidence (trial_id);

create table if not exists benchmark.benchmark_usage_reconciliations (
    id uuid primary key default gen_random_uuid(),
    arm_run_id uuid not null
        references benchmark.benchmark_arm_runs(id)
        on delete cascade,
    reconciliation_version text not null,
    is_current boolean not null default true,
    harness_name text,
    harness_version text,
    configured_route_model text,
    configured_backend_model text,
    harness_observed_model text,
    provider_observed_model text,
    model_identity_status text not null,
    harness_input_tokens bigint,
    harness_cache_tokens bigint,
    harness_output_tokens bigint,
    provider_ordinary_input_tokens bigint,
    provider_cache_read_input_tokens bigint,
    provider_cache_creation_input_tokens bigint,
    provider_output_tokens bigint,
    provider_request_count integer,
    matched_provider_request_count integer,
    unallocated_provider_request_count integer,
    provider_evidence_visible boolean not null default false,
    selected_usage_authority text not null default 'none',
    validation_status text not null,
    limitation_codes text[] not null default '{}'::text[],
    notes text,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    reviewed_at timestamptz,
    check (
        model_identity_status in (
            'matched',
            'mismatch',
            'unknown'
        )
    ),
    check (
        selected_usage_authority in (
            'provider_request_usage',
            'provider_aggregate_usage',
            'harness_usage_validated',
            'none'
        )
    ),
    check (
        validation_status in (
            'validated_exact',
            'validated_qualified',
            'provisional',
            'mismatch',
            'unverified',
            'unavailable'
        )
    ),
    check (
        validation_status not in (
            'validated_qualified',
            'provisional'
        )
        or cardinality(limitation_codes) > 0
    ),
    check (
        validation_status in (
            'unverified',
            'unavailable'
        )
        or provider_evidence_visible
    ),
    check (
        validation_status not in (
            'validated_exact',
            'validated_qualified',
            'provisional'
        )
        or (
            provider_evidence_visible
            and model_identity_status = 'matched'
            and selected_usage_authority <> 'none'
        )
    ),
    check (
        provider_request_count is null
        or provider_request_count >= 0
    ),
    check (
        matched_provider_request_count is null
        or matched_provider_request_count >= 0
    ),
    check (
        unallocated_provider_request_count is null
        or unallocated_provider_request_count >= 0
    )
);

create unique index if not exists
    idx_usage_reconciliation_current
on benchmark.benchmark_usage_reconciliations (arm_run_id)
where is_current;

create table if not exists
    benchmark.benchmark_usage_reconciliation_sources (
    reconciliation_id uuid not null
        references benchmark.benchmark_usage_reconciliations(id)
        on delete cascade,
    source_id uuid not null
        references benchmark.benchmark_provider_evidence_sources(id)
        on delete restrict,
    evidence_role text not null,
    primary key (reconciliation_id, source_id, evidence_role),
    check (
        evidence_role in (
            'request_usage',
            'aggregate_usage',
            'model_identity',
            'context'
        )
    )
);

create table if not exists benchmark.benchmark_cost_reconciliations (
    id uuid primary key default gen_random_uuid(),
    arm_run_id uuid not null
        references benchmark.benchmark_arm_runs(id)
        on delete cascade,
    reconciliation_version text not null,
    is_current boolean not null default true,
    harness_name text,
    harness_version text,
    harness_reported_cost_usd numeric,
    provider_billed_cost_usd numeric,
    provider_rate_reconstructed_cost_usd numeric,
    selected_cost_usd numeric,
    selected_cost_basis text not null default 'none',
    selected_cost_relation text not null default 'unresolved',
    validation_status text not null,
    provider_evidence_visible boolean not null default false,
    pricing_snapshot_id uuid
        references benchmark.benchmark_provider_pricing_snapshots(id)
        on delete set null,
    limitation_codes text[] not null default '{}'::text[],
    notes text,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    reviewed_at timestamptz,
    check (
        selected_cost_basis in (
            'provider_billed',
            'provider_request_billed',
            'provider_rate_reconstructed_provider_usage',
            'provider_rate_reconstructed_harness_usage_validated',
            'harness_reported_validated',
            'lower_bound_provider_evidence',
            'none'
        )
    ),
    check (
        selected_cost_relation in (
            'exact',
            'estimate',
            'lower_bound',
            'unresolved'
        )
    ),
    check (
        validation_status in (
            'validated_exact',
            'validated_qualified',
            'provisional',
            'mismatch',
            'unverified',
            'unavailable'
        )
    ),
    check (
        validation_status not in (
            'validated_qualified',
            'provisional'
        )
        or cardinality(limitation_codes) > 0
    ),
    check (
        validation_status in (
            'unverified',
            'unavailable'
        )
        or provider_evidence_visible
    ),
    check (
        validation_status not in (
            'validated_exact',
            'validated_qualified',
            'provisional'
        )
        or (
            provider_evidence_visible
            and selected_cost_usd is not null
            and selected_cost_basis <> 'none'
            and selected_cost_relation <> 'unresolved'
        )
    ),
    check (
        validation_status <> 'validated_exact'
        or selected_cost_relation = 'exact'
    ),
    check (
        selected_cost_basis <> 'lower_bound_provider_evidence'
        or selected_cost_relation = 'lower_bound'
    ),
    check (
        (
            selected_cost_usd is null
            and selected_cost_basis = 'none'
            and selected_cost_relation = 'unresolved'
        )
        or (
            selected_cost_usd is not null
            and selected_cost_usd >= 0
            and selected_cost_basis <> 'none'
            and selected_cost_relation <> 'unresolved'
        )
    ),
    check (
        validation_status not in (
            'mismatch',
            'unverified',
            'unavailable'
        )
        or selected_cost_usd is null
    )
);

create unique index if not exists
    idx_cost_reconciliation_current
on benchmark.benchmark_cost_reconciliations (arm_run_id)
where is_current;

create table if not exists
    benchmark.benchmark_cost_reconciliation_sources (
    reconciliation_id uuid not null
        references benchmark.benchmark_cost_reconciliations(id)
        on delete cascade,
    source_id uuid not null
        references benchmark.benchmark_provider_evidence_sources(id)
        on delete restrict,
    evidence_role text not null,
    primary key (reconciliation_id, source_id, evidence_role),
    check (
        evidence_role in (
            'billed',
            'rate_reconstruction',
            'pricing',
            'lower_bound',
            'context'
        )
    )
);

create table if not exists benchmark.benchmark_evidence_promotion_gates (
    id uuid primary key default gen_random_uuid(),
    arm_id text not null
        references benchmark.benchmark_arms(arm_id),
    source_arm_run_id uuid not null
        references benchmark.benchmark_arm_runs(id)
        on delete cascade,
    source_mode text not null,
    target_mode text not null,
    usage_reconciliation_id uuid not null
        references benchmark.benchmark_usage_reconciliations(id)
        on delete restrict,
    cost_reconciliation_id uuid not null
        references benchmark.benchmark_cost_reconciliations(id)
        on delete restrict,
    decision text not null default 'blocked',
    blocker_codes text[] not null default '{}'::text[],
    waiver_reason text,
    reviewed_by text,
    reviewed_at timestamptz,
    is_current boolean not null default true,
    notes text,
    raw_metadata jsonb not null default '{}'::jsonb,
    created_at timestamptz not null default now(),
    check (
        (
            source_mode = 'canary'
            and target_mode = 'smoke'
        )
        or (
            source_mode = 'smoke'
            and target_mode = 'full'
        )
    ),
    check (
        decision in (
            'pass',
            'blocked',
            'waived'
        )
    ),
    check (
        decision <> 'pass'
        or cardinality(blocker_codes) = 0
    ),
    check (
        decision <> 'blocked'
        or cardinality(blocker_codes) > 0
    ),
    check (
        decision <> 'waived'
        or nullif(btrim(waiver_reason), '') is not null
    )
);

create unique index if not exists
    idx_evidence_promotion_gate_current
on benchmark.benchmark_evidence_promotion_gates (
    arm_id,
    target_mode
)
where is_current;

create or replace view benchmark.v_evidence_promotion_gate as
with joined as (
    select
        gate.id as gate_id,
        gate.arm_id,
        gate.source_arm_run_id,
        gate.source_mode,
        gate.target_mode,
        gate.decision,
        gate.blocker_codes,
        gate.waiver_reason,
        gate.is_current as gate_is_current,
        gate.reviewed_by,
        gate.reviewed_at,
        gate.notes,
        gate.created_at,

        source_run.arm_id as source_run_arm_id,
        source_run.logical_mode as source_run_logical_mode,

        usage.id as usage_reconciliation_id,
        usage.arm_run_id as usage_arm_run_id,
        usage.is_current as usage_reconciliation_is_current,
        usage.validation_status as usage_validation_status,
        usage.selected_usage_authority,
        usage.provider_evidence_visible
            as usage_provider_evidence_visible,
        usage.model_identity_status,
        usage.limitation_codes as usage_limitation_codes,

        cost.id as cost_reconciliation_id,
        cost.arm_run_id as cost_arm_run_id,
        cost.is_current as cost_reconciliation_is_current,
        cost.validation_status as cost_validation_status,
        cost.selected_cost_usd,
        cost.selected_cost_basis,
        cost.selected_cost_relation,
        cost.provider_evidence_visible
            as cost_provider_evidence_visible,
        cost.limitation_codes as cost_limitation_codes
    from benchmark.benchmark_evidence_promotion_gates gate
    join benchmark.benchmark_arm_runs source_run
      on source_run.id = gate.source_arm_run_id
    join benchmark.benchmark_usage_reconciliations usage
      on usage.id = gate.usage_reconciliation_id
    join benchmark.benchmark_cost_reconciliations cost
      on cost.id = gate.cost_reconciliation_id
),
qualified as (
    select
        joined.*,
        array_remove(
            array[
                case
                    when gate_is_current is not true
                    then 'gate_not_current'
                end,
                case
                    when decision <> 'pass'
                    then 'gate_decision_not_pass'
                end,
                case
                    when cardinality(blocker_codes) > 0
                    then 'reviewed_blockers_present'
                end,
                case
                    when source_run_arm_id is distinct from arm_id
                    then 'source_run_arm_mismatch'
                end,
                case
                    when source_run_logical_mode
                         is distinct from source_mode
                    then 'source_run_mode_mismatch'
                end,
                case
                    when usage_arm_run_id
                         is distinct from source_arm_run_id
                    then 'usage_reconciliation_wrong_arm_run'
                end,
                case
                    when cost_arm_run_id
                         is distinct from source_arm_run_id
                    then 'cost_reconciliation_wrong_arm_run'
                end,
                case
                    when usage_reconciliation_is_current is not true
                    then 'usage_reconciliation_not_current'
                end,
                case
                    when cost_reconciliation_is_current is not true
                    then 'cost_reconciliation_not_current'
                end,
                case
                    when usage_provider_evidence_visible is not true
                    then 'provider_usage_evidence_not_visible'
                end,
                case
                    when cost_provider_evidence_visible is not true
                    then 'provider_cost_evidence_not_visible'
                end,
                case
                    when model_identity_status <> 'matched'
                    then 'provider_model_identity_not_matched'
                end,
                case
                    when selected_usage_authority = 'none'
                    then 'selected_usage_authority_missing'
                end,
                case
                    when selected_cost_usd is null
                    then 'selected_cost_missing'
                end,
                case
                    when selected_cost_basis = 'none'
                    then 'selected_cost_basis_missing'
                end,
                case
                    when selected_cost_relation = 'unresolved'
                    then 'selected_cost_relation_unresolved'
                end,
                case
                    when source_mode = 'canary'
                     and target_mode = 'smoke'
                     and usage_validation_status not in (
                         'validated_exact',
                         'validated_qualified',
                         'provisional'
                     )
                    then 'canary_usage_not_smoke_eligible'
                end,
                case
                    when source_mode = 'canary'
                     and target_mode = 'smoke'
                     and cost_validation_status not in (
                         'validated_exact',
                         'validated_qualified',
                         'provisional'
                     )
                    then 'canary_cost_not_smoke_eligible'
                end,
                case
                    when source_mode = 'smoke'
                     and target_mode = 'full'
                     and usage_validation_status not in (
                         'validated_exact',
                         'validated_qualified'
                     )
                    then 'smoke_usage_not_full_sweep_qualified'
                end,
                case
                    when source_mode = 'smoke'
                     and target_mode = 'full'
                     and cost_validation_status not in (
                         'validated_exact',
                         'validated_qualified'
                     )
                    then 'smoke_cost_not_full_sweep_qualified'
                end
            ]::text[],
            null
        ) as derived_blocker_codes
    from joined
)
select
    gate_id,
    arm_id,
    source_arm_run_id,
    source_mode,
    target_mode,
    decision,
    blocker_codes,
    derived_blocker_codes,
    waiver_reason,

    source_run_arm_id,
    source_run_logical_mode,

    usage_reconciliation_id,
    usage_arm_run_id,
    usage_reconciliation_is_current,
    usage_validation_status,
    selected_usage_authority,
    usage_provider_evidence_visible,
    model_identity_status,
    usage_limitation_codes,

    cost_reconciliation_id,
    cost_arm_run_id,
    cost_reconciliation_is_current,
    cost_validation_status,
    selected_cost_usd,
    selected_cost_basis,
    selected_cost_relation,
    cost_provider_evidence_visible,
    cost_limitation_codes,

    cardinality(derived_blocker_codes) = 0
        as effective_can_advance,

    reviewed_by,
    reviewed_at,
    notes,
    created_at
from qualified;

comment on table benchmark.benchmark_provider_evidence_sources is
    'Provenance for provider-supplied usage, billing, pricing, request-log, invoice, or dashboard evidence. Large raw bytes normally live in R2 and are referenced here by artifact/URI/hash.';

comment on column
    benchmark.benchmark_provider_evidence_sources.provider_reference is
    'Non-secret provider record/project/export reference only. Never store API keys, bearer tokens, or authentication material.';

comment on table benchmark.benchmark_provider_usage_evidence is
    'Normalized provider usage evidence. Cache-read and cache-creation/write token classes remain separate so pricing safety can be evaluated.';

comment on table benchmark.benchmark_provider_cost_evidence is
    'Normalized provider cost evidence. Context/account totals remain distinguishable from exact trial or arm-run allocation.';

comment on table benchmark.benchmark_usage_reconciliations is
    'Independent reconciliation of harness usage/model identity against provider usage evidence.';

comment on table benchmark.benchmark_cost_reconciliations is
    'Independent reconciliation of harness-reported cost against provider billing, provider usage, and pinned pricing evidence.';

comment on table benchmark.benchmark_evidence_promotion_gates is
    'Reviewed Canary-to-Smoke and Smoke-to-Full evidence gate. Waivers are recorded but do not automatically become an effective pass.';

comment on view benchmark.v_evidence_promotion_gate is
    'Fail-closed promotion status. The gate, source arm run, usage reconciliation, and cost reconciliation must refer to the same current evidence chain. Canary may use documented provisional authority to reach Smoke; Full requires validated exact or qualified usage and cost authority.';
