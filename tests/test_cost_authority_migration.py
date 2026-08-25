from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MIGRATION = (
    ROOT
    / "db/migrations/phase3/010_cost_authority_semantics.sql"
)


def migration_text() -> str:
    return MIGRATION.read_text(encoding="utf-8")


def normalized_sql() -> str:
    return " ".join(migration_text().split())


def test_migration_preserves_raw_harness_cost_contract():
    sql = normalized_sql().lower()

    assert "benchmark_trials.cost_usd remains immutable" in (
        migration_text().lower()
    )

    forbidden = (
        "update benchmark.benchmark_trials",
        "alter table benchmark.benchmark_trials",
        "delete from benchmark.benchmark_trials",
        "insert into benchmark.benchmark_trials",
    )

    for statement in forbidden:
        assert statement not in sql


def test_trial_gap_is_null_when_adjusted_cost_is_unresolved():
    sql = normalized_sql().lower()

    assert (
        "when c.adjusted_cost_usd is null then null::numeric"
        in sql
    )

    assert (
        "c.adjusted_cost_usd "
        "- coalesce(c.recorded_cost_usd, 0::numeric)"
        in sql
    )


def test_aggregate_gap_excludes_unresolved_recorded_cost():
    sql = normalized_sql().lower()

    guarded_recorded_sum = (
        "sum(recorded_cost_usd) filter "
        "( where adjusted_cost_usd is not null )"
    )

    assert sql.count(guarded_recorded_sum) == 2


def test_migration_replaces_only_derived_cost_views():
    sql = normalized_sql().lower()

    expected_views = (
        "benchmark.v_trial_adjusted_cost_coverage",
        "benchmark.v_arm_adjusted_cost_coverage",
        "benchmark.v_arm_outcome_cost_breakdown",
    )

    for view in expected_views:
        assert f"create or replace view {view}" in sql

    assert sql.count("create or replace view") == 3
    assert "drop view" not in sql
    assert "drop table" not in sql


def test_unresolved_rows_remain_counted_as_unresolved():
    sql = normalized_sql().lower()

    assert (
        "count(*) filter ( where adjusted_cost_usd is null )"
        "::integer as unresolved_cost_count"
        in sql
    )


def test_recorded_cost_remains_visible_as_separate_evidence():
    sql = normalized_sql().lower()

    assert (
        "sum(recorded_cost_usd), 0::numeric "
        ") as recorded_cost_usd"
        in sql
    )
    assert (
        "sum(adjusted_cost_usd), 0::numeric "
        ") as adjusted_known_cost_usd"
        in sql
    )


def test_view_comments_document_authority_semantics():
    text = migration_text()

    assert (
        "recorded harness cost may exist while selected adjusted cost "
        "remains unresolved"
        in text
    )
    assert (
        "excludes recorded harness cost from rows whose authoritative "
        "adjusted cost is unresolved"
        in text
    )
