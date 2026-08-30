from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "db/migrations/phase3/011_provider_evidence_contract.sql"
)


def text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def sql() -> str:
    return " ".join(text().lower().split())


def test_contract_is_additive_and_does_not_rewrite_benchmark_results():
    value = sql()

    forbidden = (
        "update benchmark.benchmark_trials",
        "delete from benchmark.benchmark_trials",
        "alter table benchmark.benchmark_trials",
        "update benchmark.benchmark_arm_runs",
        "delete from benchmark.benchmark_arm_runs",
    )

    for fragment in forbidden:
        assert fragment not in value


def test_provider_source_preserves_r2_hash_and_provider_provenance():
    value = sql()

    assert "benchmark_provider_evidence_sources" in value
    assert "artifact_id uuid" in value
    assert "source_uri text" in value
    assert "source_sha256 text" in value
    assert "provider_reference text" in value
    assert "integrity_status text" in value


def test_usage_and_cost_evidence_are_separate_tables():
    value = sql()

    assert (
        "benchmark.benchmark_provider_usage_evidence"
        in value
    )
    assert (
        "benchmark.benchmark_provider_cost_evidence"
        in value
    )


def test_provider_usage_preserves_cache_creation_as_distinct_class():
    value = sql()

    assert "ordinary_input_tokens bigint" in value
    assert "cache_read_input_tokens bigint" in value
    assert "cache_creation_input_tokens bigint" in value
    assert "output_tokens bigint" in value


def test_pricing_snapshots_are_first_class_and_rule_capable():
    value = sql()

    assert (
        "benchmark.benchmark_provider_pricing_snapshots"
        in value
    )
    assert "pricing_semantics text not null" in value
    assert "pricing_rules jsonb not null" in value
    assert "effective_from timestamptz" in value


def test_usage_and_cost_reconciliation_are_independent():
    value = sql()

    assert "benchmark.benchmark_usage_reconciliations" in value
    assert "benchmark.benchmark_cost_reconciliations" in value
    assert "selected_usage_authority text" in value
    assert "selected_cost_basis text" in value
    assert "usage_reconciliation_id uuid not null" in value
    assert "cost_reconciliation_id uuid not null" in value


def test_qualified_or_provisional_evidence_requires_limitations():
    value = sql()

    expected = (
        "validation_status not in "
        "( 'validated_qualified', 'provisional' ) "
        "or cardinality(limitation_codes) > 0"
    )

    assert value.count(expected) == 2


def test_unvalidated_or_mismatched_cost_cannot_be_selected():
    value = sql()

    assert (
        "validation_status not in "
        "( 'mismatch', 'unverified', 'unavailable' ) "
        "or selected_cost_usd is null"
        in value
    )


def test_canary_may_use_provisional_authority_for_smoke():
    value = sql()

    assert "source_mode = 'canary'" in value
    assert "target_mode = 'smoke'" in value

    assert (
        "canary_usage_not_smoke_eligible"
        in value
    )
    assert (
        "canary_cost_not_smoke_eligible"
        in value
    )

    # Provisional authority is permitted only on the Canary -> Smoke
    # transition, where later Smoke runs validate repeatability.
    assert value.count("'provisional'") >= 4

def test_full_sweep_gate_does_not_accept_provisional_authority():
    value = sql()

    usage_rule = (
        "when source_mode = 'smoke' "
        "and target_mode = 'full' "
        "and usage_validation_status not in "
        "( 'validated_exact', 'validated_qualified' ) "
        "then 'smoke_usage_not_full_sweep_qualified'"
    )
    cost_rule = (
        "when source_mode = 'smoke' "
        "and target_mode = 'full' "
        "and cost_validation_status not in "
        "( 'validated_exact', 'validated_qualified' ) "
        "then 'smoke_cost_not_full_sweep_qualified'"
    )

    assert usage_rule in value
    assert cost_rule in value

    assert "'provisional'" not in usage_rule
    assert "'provisional'" not in cost_rule

def test_full_gate_requires_provider_visibility_identity_and_selected_cost():
    value = sql()

    required_blockers = (
        (
            "when usage_provider_evidence_visible is not true "
            "then 'provider_usage_evidence_not_visible'"
        ),
        (
            "when cost_provider_evidence_visible is not true "
            "then 'provider_cost_evidence_not_visible'"
        ),
        (
            "when model_identity_status <> 'matched' "
            "then 'provider_model_identity_not_matched'"
        ),
        (
            "when selected_usage_authority = 'none' "
            "then 'selected_usage_authority_missing'"
        ),
        (
            "when selected_cost_usd is null "
            "then 'selected_cost_missing'"
        ),
        (
            "when selected_cost_basis = 'none' "
            "then 'selected_cost_basis_missing'"
        ),
        (
            "when selected_cost_relation = 'unresolved' "
            "then 'selected_cost_relation_unresolved'"
        ),
    )

    for blocker_rule in required_blockers:
        assert blocker_rule in value

def test_waiver_is_recorded_but_not_an_automatic_effective_pass():
    value = sql()

    assert (
        "decision in ( 'pass', 'blocked', 'waived' )"
        in value
    )

    # Any non-pass reviewed decision becomes an explicit derived blocker.
    # A waiver therefore remains visible provenance but cannot silently
    # become effective authorization.
    assert (
        "when decision <> 'pass' "
        "then 'gate_decision_not_pass'"
        in value
    )

    assert (
        "cardinality(derived_blocker_codes) = 0 "
        "as effective_can_advance"
        in value
    )

def test_current_reconciliations_and_gates_are_unique_per_target():
    value = sql()

    assert "idx_usage_reconciliation_current" in value
    assert "idx_cost_reconciliation_current" in value
    assert "idx_evidence_promotion_gate_current" in value
    assert "where is_current" in value


def test_positive_usage_status_requires_matched_selected_authority():
    value = sql()

    assert (
        "model_identity_status = 'matched' "
        "and selected_usage_authority <> 'none'"
        in value
    )


def test_positive_cost_status_requires_selected_resolved_cost():
    value = sql()

    assert (
        "selected_cost_usd is not null "
        "and selected_cost_basis <> 'none' "
        "and selected_cost_relation <> 'unresolved'"
        in value
    )


def test_validated_exact_cost_requires_exact_relation():
    value = sql()

    assert (
        "validation_status <> 'validated_exact' "
        "or selected_cost_relation = 'exact'"
        in value
    )


def test_lower_bound_basis_requires_lower_bound_relation():
    value = sql()

    assert (
        "selected_cost_basis <> 'lower_bound_provider_evidence' "
        "or selected_cost_relation = 'lower_bound'"
        in value
    )


def test_unavailable_cost_is_reconciliation_state_not_fake_cost_row():
    value = sql()

    start = value.index(
        "create table if not exists "
        "benchmark.benchmark_provider_cost_evidence"
    )
    end = value.index(
        "create index if not exists idx_provider_cost_arm_run",
        start,
    )
    cost_evidence = value[start:end]

    assert "'complete'" in cost_evidence
    assert "'partial'" in cost_evidence
    assert "'aggregate_only'" in cost_evidence
    assert "'unavailable'" not in cost_evidence


def test_promotion_view_binds_reconciliations_to_exact_source_run():
    value = sql()

    assert (
        "usage_arm_run_id is distinct from source_arm_run_id"
        in value
    )
    assert (
        "cost_arm_run_id is distinct from source_arm_run_id"
        in value
    )

    assert "usage_reconciliation_wrong_arm_run" in value
    assert "cost_reconciliation_wrong_arm_run" in value


def test_promotion_view_requires_current_reconciliations():
    value = sql()

    assert "usage_reconciliation_is_current is not true" in value
    assert "cost_reconciliation_is_current is not true" in value
    assert "usage_reconciliation_not_current" in value
    assert "cost_reconciliation_not_current" in value


def test_promotion_view_binds_arm_and_mode_to_source_run():
    value = sql()

    assert "source_run_arm_id is distinct from arm_id" in value
    assert (
        "source_run_logical_mode is distinct from source_mode"
        in value
    )
    assert "source_run_arm_mismatch" in value
    assert "source_run_mode_mismatch" in value


def test_promotion_view_exposes_derived_fail_closed_blockers():
    value = sql()

    assert "derived_blocker_codes" in value
    assert (
        "cardinality(derived_blocker_codes) = 0 "
        "as effective_can_advance"
        in value
    )


def test_unavailable_usage_is_reconciliation_state_not_fake_usage_row():
    value = sql()

    start = value.index(
        "create table if not exists "
        "benchmark.benchmark_provider_usage_evidence"
    )
    end = value.index(
        "create unique index if not exists "
        "idx_provider_usage_request_identity",
        start,
    )
    usage_evidence = value[start:end]

    assert "'complete'" in usage_evidence
    assert "'partial'" in usage_evidence
    assert "'aggregate_only'" in usage_evidence
    assert "'unavailable'" not in usage_evidence
