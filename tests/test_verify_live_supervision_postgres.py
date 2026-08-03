from __future__ import annotations

import json
import sys
from types import SimpleNamespace
from pathlib import Path

import pytest

import scripts.verify_live_supervision_postgres as integration


class RelationCursor:
    def __init__(self, present: set[str]) -> None:
        self.present = present
        self.relation = ""

    def __enter__(self) -> RelationCursor:
        return self

    def __exit__(self, *_args: object) -> None:
        return None

    def execute(self, _sql: str, params: tuple[str]) -> None:
        self.relation = params[0]

    def fetchone(self) -> tuple[str | None]:
        return (
            self.relation if self.relation in self.present else None,
        )


class RelationConnection:
    def __init__(self, present: set[str]) -> None:
        self.present = present

    def cursor(self) -> RelationCursor:
        return RelationCursor(self.present)


def test_integration_runner_requires_explicit_rollback_only() -> None:
    with pytest.raises(SystemExit):
        integration.parse_args([])
    assert integration.parse_args(["--rollback-only"]).rollback_only is True


def test_integration_runner_refuses_permanently_applied_migration() -> None:
    with pytest.raises(
        integration.IntegrationSafetyError,
        match="already appears permanently applied",
    ):
        integration.assert_migration_not_permanently_applied(
            RelationConnection({"benchmark.live_runs"})
        )


def test_integration_runner_accepts_absent_live_schema() -> None:
    integration.assert_migration_not_permanently_applied(
        RelationConnection(set())
    )


def test_missing_database_url_never_prints_a_secret(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    migration = tmp_path / "009.sql"
    migration.write_text("select 1;\n")
    monkeypatch.setattr(integration, "MIGRATION_PATH", migration)
    monkeypatch.delenv("SUPABASE_DB_URL", raising=False)

    assert integration.main(["--rollback-only"]) == 2
    output = json.loads(capsys.readouterr().out)
    assert output["status"] == "failed"
    assert output["failed_stage"] == "preflight"
    assert output["error_type"] == "MissingEnvironmentError"
    assert output["zero_persistence_counts"] == {}
    assert output["migration_sha256"] == integration.migration_sha256(
        migration
    )


def test_synthetic_manifest_has_unique_non_phase3_identity() -> None:
    first = integration.synthetic_manifest("one")
    second = integration.synthetic_manifest("two")
    assert first["run"]["phase"] == "live-supervision-integration"
    assert first["run"]["run_label"] != second["run"]["run_label"]
    assert first["run"]["publication_fingerprint"]


class SyntheticPostgresError(Exception):
    sqlstate = "42P18"


def test_failure_result_reports_stage_and_sqlstate_without_message() -> None:
    secret = "postgresql://user:password@example.invalid/database"
    result = integration.failure_result(
        migration_digest="digest",
        failed_stage="success_publication",
        exc=SyntheticPostgresError(secret),
        zero_persistence_counts={"success_live_runs": 0},
    )
    assert result == {
        "migration_sha256": "digest",
        "status": "failed",
        "failed_stage": "success_publication",
        "error_type": "SyntheticPostgresError",
        "sqlstate": "42P18",
        "zero_persistence_counts": {"success_live_runs": 0},
    }
    assert secret not in json.dumps(result)


def test_main_reports_preflight_stage_without_connection_details(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    secret_url = "postgresql://user:password@example.invalid/database"
    migration = tmp_path / "009.sql"
    migration.write_text("select 1;\n")
    monkeypatch.setattr(integration, "MIGRATION_PATH", migration)
    monkeypatch.setenv("SUPABASE_DB_URL", secret_url)

    def fail_connect(_db_url: str) -> None:
        raise SyntheticPostgresError(secret_url)

    monkeypatch.setitem(
        sys.modules,
        "psycopg",
        SimpleNamespace(connect=fail_connect),
    )
    assert integration.main(["--rollback-only"]) == 1
    output_text = capsys.readouterr().out
    output = json.loads(output_text)
    assert output["failed_stage"] == "preflight"
    assert output["error_type"] == "SyntheticPostgresError"
    assert output["sqlstate"] == "42P18"
    assert secret_url not in output_text
