import argparse
import sqlite3

from scripts.eval_quality_audit import InvalidRun, SchemaInfo, invalid_run_filter


SUITE_ID = "phase3-full-20"
GEMINI_ARM = "router-gemini-3.1-pro"
OPUS_ARM = "router-anthropic-opus"
GEMINI_INVALID_LABEL = "router-gemini-3.1-pro/2026-06-30__01-23-54"
GEMINI_VALID_LABEL = "router-gemini-3.1-pro/2026-06-30__14-57-05"
OPUS_INVALID_LABEL = "router-anthropic-opus/2026-06-28__13-28-56"


def schema_info() -> SchemaInfo:
    return SchemaInfo(
        columns={
            "benchmark_runs": {"id", "run_label"},
            "benchmark_arm_runs": {
                "id",
                "run_id",
                "arm_id",
                "suite_id",
                "provider_run_id",
            },
        }
    )


def invalid_runs() -> list[InvalidRun]:
    return [
        InvalidRun(
            suite_id=SUITE_ID,
            arm_id=OPUS_ARM,
            run_label=OPUS_INVALID_LABEL,
            provider_run_id="28323747982",
            reason="usage limit",
        ),
        InvalidRun(
            suite_id=SUITE_ID,
            arm_id=GEMINI_ARM,
            run_label=GEMINI_INVALID_LABEL,
            provider_run_id="28413826034",
            reason="provider limit",
        ),
    ]


def sqlite_sql(sql: str) -> str:
    return sql.replace("%s", "?")


def seed_db() -> sqlite3.Connection:
    conn = sqlite3.connect(":memory:")
    conn.row_factory = sqlite3.Row
    conn.executescript(
        """
        create table benchmark_runs (
          id text primary key,
          run_label text
        );
        create table benchmark_arm_runs (
          id text primary key,
          run_id text,
          arm_id text,
          suite_id text,
          provider_run_id text
        );
        create table benchmark_trials (
          id text primary key,
          run_id text,
          arm_id text,
          reward integer
        );
        """
    )
    conn.executemany(
        "insert into benchmark_runs (id, run_label) values (?, ?)",
        [
            ("gemini-invalid", GEMINI_INVALID_LABEL),
            ("gemini-valid", GEMINI_VALID_LABEL),
            ("opus-invalid", OPUS_INVALID_LABEL),
        ],
    )
    conn.executemany(
        """
        insert into benchmark_arm_runs
          (id, run_id, arm_id, suite_id, provider_run_id)
        values (?, ?, ?, ?, ?)
        """,
        [
            ("ar-gemini-invalid", "gemini-invalid", GEMINI_ARM, SUITE_ID, "28413826034"),
            ("ar-gemini-valid", "gemini-valid", GEMINI_ARM, SUITE_ID, None),
            ("ar-opus-invalid", "opus-invalid", OPUS_ARM, SUITE_ID, "28323747982"),
        ],
    )
    conn.executemany(
        "insert into benchmark_trials (id, run_id, arm_id, reward) values (?, ?, ?, ?)",
        [
            ("t-gi-1", "gemini-invalid", GEMINI_ARM, 1),
            ("t-gi-2", "gemini-invalid", GEMINI_ARM, 0),
            ("t-gv-1", "gemini-valid", GEMINI_ARM, 1),
            ("t-gv-2", "gemini-valid", GEMINI_ARM, 1),
            ("t-gv-3", "gemini-valid", GEMINI_ARM, 0),
            ("t-op-1", "opus-invalid", OPUS_ARM, 0),
        ],
    )
    return conn


def invalid_filter(params: list[object]) -> str:
    args = argparse.Namespace(_invalid_runs=invalid_runs())
    return sqlite_sql(invalid_run_filter(schema_info(), args, params))


def test_valid_only_arm_run_summary_keeps_valid_rerun_for_same_arm():
    conn = seed_db()
    params: list[object] = [SUITE_ID, GEMINI_ARM]
    sql = f"""
        select r.run_label
        from benchmark_runs r
        join benchmark_arm_runs ar on ar.run_id = r.id
        where ar.suite_id = ?
          and ar.arm_id = ?
          {invalid_filter(params)}
        order by r.run_label
    """

    rows = conn.execute(sql, params).fetchall()

    assert [row["run_label"] for row in rows] == [GEMINI_VALID_LABEL]


def test_valid_only_suite_summary_aggregates_only_valid_rerun_for_arm():
    conn = seed_db()
    params: list[object] = [SUITE_ID]
    sql = f"""
        select
          ar.arm_id,
          count(t.id) as trial_count,
          sum(case when coalesce(t.reward, 0) > 0 then 1 else 0 end) as success_count
        from benchmark_trials t
        join benchmark_runs r on r.id = t.run_id
        join benchmark_arm_runs ar on ar.run_id = t.run_id and ar.arm_id = t.arm_id
        where ar.suite_id = ?
          {invalid_filter(params)}
        group by ar.arm_id
        order by ar.arm_id
    """

    rows = conn.execute(sql, params).fetchall()

    assert [dict(row) for row in rows] == [
        {"arm_id": GEMINI_ARM, "trial_count": 3, "success_count": 2}
    ]


def test_valid_only_arm_run_summary_excludes_single_invalid_opus_run():
    conn = seed_db()
    params: list[object] = [SUITE_ID, OPUS_ARM]
    sql = f"""
        select r.run_label
        from benchmark_runs r
        join benchmark_arm_runs ar on ar.run_id = r.id
        where ar.suite_id = ?
          and ar.arm_id = ?
          {invalid_filter(params)}
        order by r.run_label
    """

    rows = conn.execute(sql, params).fetchall()

    assert rows == []
