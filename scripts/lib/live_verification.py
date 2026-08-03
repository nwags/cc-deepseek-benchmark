from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping

from scripts.lib.live_artifacts import sha256_file, verify_r2_object
from scripts.lib.path_safety import resolve_under
from scripts.lib.publication_fingerprint import (
    artifact_fingerprint_records,
    trial_fingerprint_records,
)


class CompletedPublicationMismatch(RuntimeError):
    pass


@dataclass(frozen=True)
class ExistingCanonicalPublication:
    run_id: str
    arm_run_id: str
    publication_fingerprint: str
    artifacts: tuple[dict[str, Any], ...]
    verification: dict[str, Any]


def observed_suite_classification(observed: Mapping[str, Any]) -> str:
    valid_count = int(observed.get("valid_view_count") or 0)
    invalid_count = int(observed.get("invalid_row_count") or 0)
    if valid_count and invalid_count:
        return "contradictory"
    if valid_count:
        return "valid"
    if invalid_count:
        return "invalid"
    return "unclassified"


def validate_publication_counts(
    manifest: Mapping[str, Any],
    observed: Mapping[str, Any],
    *,
    require_r2: bool,
) -> list[str]:
    errors: list[str] = []
    expected_trials = len(manifest.get("trials") or [])
    expected_artifacts = len(manifest.get("artifacts") or [])
    if int(observed.get("arm_run_count") or 0) != 1:
        errors.append("expected exactly one canonical arm-run row")
    if int(observed.get("trial_count") or 0) != expected_trials:
        errors.append(
            f"canonical trial count mismatch: expected {expected_trials}, "
            f"observed {observed.get('trial_count')}"
        )
    if int(observed.get("artifact_count") or 0) != expected_artifacts:
        errors.append(
            f"canonical artifact count mismatch: expected {expected_artifacts}, "
            f"observed {observed.get('artifact_count')}"
        )
    if require_r2:
        if int(observed.get("r2_artifact_count") or 0) != expected_artifacts:
            errors.append(
                f"canonical R2 URI count mismatch: expected {expected_artifacts}, "
                f"observed {observed.get('r2_artifact_count')}"
            )
        if not bool(observed.get("r2_integrity_verified")):
            errors.append("canonical R2 objects were not integrity-verified")
    if int(observed.get("dashboard_arm_count") or 0) != 1:
        errors.append("canonical arm is not visible in benchmark.v_dashboard_arms")

    classification = observed_suite_classification(observed)
    if classification == "contradictory":
        errors.append("canonical arm run is classified as both valid and invalid")
    if int(observed.get("valid_view_count") or 0) > 1:
        errors.append("canonical arm run appears more than once in the valid view")
    if int(observed.get("invalid_row_count") or 0) > 1:
        errors.append("canonical arm run has duplicate invalid classifications")
    if bool(observed.get("live_link_expected")) and int(
        observed.get("live_link_count") or 0
    ) != 1:
        errors.append("live run is not linked to the canonical arm run")
    return errors


def reconcile_progressive_artifacts(
    manifest: dict[str, Any],
    *,
    live_run_id: str,
    db_url: str,
    run_dir: Path,
    workspace: Path,
    r2_client: Any,
) -> int:
    """Reuse only matching progressive objects verified through R2 metadata."""
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - CLI installs dependency
        raise RuntimeError("psycopg is required for progressive artifact reconciliation") from exc

    with psycopg.connect(db_url) as connection:
        with connection.cursor() as cursor:
            cursor.execute(
                """
                select relative_local_path, sha256, size_bytes, r2_uri
                from benchmark.live_artifacts
                where live_run_id = %s
                  and r2_uri is not null
                """,
                (live_run_id,),
            )
            progressive = {
                (relative_path, sha256, int(size_bytes)): r2_uri
                for relative_path, sha256, size_bytes, r2_uri in cursor.fetchall()
            }

    return apply_verified_progressive_artifacts(
        manifest,
        progressive_rows=[
            {
                "relative_local_path": relative_path,
                "sha256": sha256,
                "size_bytes": size_bytes,
                "r2_uri": r2_uri,
            }
            for (relative_path, sha256, size_bytes), r2_uri in progressive.items()
        ],
        run_dir=run_dir,
        workspace=workspace,
        r2_client=r2_client,
    )


def apply_verified_progressive_artifacts(
    manifest: dict[str, Any],
    *,
    progressive_rows: list[Mapping[str, Any]],
    run_dir: Path,
    workspace: Path,
    r2_client: Any,
) -> int:
    progressive = {
        (
            str(row.get("relative_local_path") or ""),
            str(row.get("sha256") or ""),
            int(row.get("size_bytes") or 0),
        ): str(row.get("r2_uri") or "")
        for row in progressive_rows
        if row.get("r2_uri")
    }
    matched = 0
    root = run_dir.resolve(strict=True)
    for artifact in manifest.get("artifacts") or []:
        local_path = resolve_under(
            workspace / str(artifact.get("local_path") or ""),
            workspace=workspace,
            parent=root,
            require_file=True,
            label="canonical artifact",
        )
        relative_path = local_path.relative_to(root).as_posix()
        sha256 = str(artifact.get("sha256") or "")
        size_bytes = int(artifact.get("size_bytes") or 0)
        if local_path.stat().st_size != size_bytes:
            continue
        if sha256_file(local_path, workspace=workspace, parent=root) != sha256:
            continue
        r2_uri = progressive.get((relative_path, sha256, size_bytes))
        if not r2_uri:
            continue
        verified, _reason = verify_r2_object(
            r2_client,
            uri=str(r2_uri),
            sha256=sha256,
            size_bytes=size_bytes,
        )
        if verified:
            artifact["r2_uri"] = r2_uri
            artifact["progressive_reconciled"] = True
            matched += 1
    return matched


def mark_live_run_publication(
    *,
    db_url: str,
    live_run_id: str,
    status: str,
    canonical_arm_run_id: str | None = None,
    latest_message: str | None = None,
    explicit_retry: bool = False,
) -> None:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - CLI installs dependency
        raise RuntimeError("psycopg is required for live publication state") from exc

    with psycopg.connect(db_url) as connection:
        with connection.cursor() as cursor:
            update_live_run_publication_with_cursor(
                cursor,
                live_run_id=live_run_id,
                status=status,
                canonical_arm_run_id=canonical_arm_run_id,
                latest_message=latest_message,
                explicit_retry=explicit_retry,
            )
        connection.commit()


def publication_transition(
    current: str | None,
    requested: str,
    *,
    explicit_retry: bool = False,
) -> str:
    if current in {"completed", "ineligible"}:
        return current
    if current == "failed":
        if explicit_retry and requested == "publishing":
            return "publishing"
        return "failed"
    return requested


def update_live_run_publication_with_cursor(
    cursor: Any,
    *,
    live_run_id: str,
    status: str,
    canonical_arm_run_id: str | None = None,
    latest_message: str | None = None,
    explicit_retry: bool = False,
    publication_fingerprint: str | None = None,
) -> str:
    cursor.execute(
        """
        select canonical_publication_status
        from benchmark.live_runs
        where live_run_id = %s
        for update
        """,
        (live_run_id,),
    )
    row = cursor.fetchone()
    if row is None:
        raise RuntimeError("live run does not exist for canonical publication")
    current = row[0]
    next_status = publication_transition(
        current,
        status,
        explicit_retry=explicit_retry,
    )
    if current in {"completed", "ineligible"}:
        return current
    if current == "failed" and next_status == "failed":
        return "failed"
    cursor.execute(
        """
        update benchmark.live_runs
        set canonical_publication_status = %(status)s,
            canonical_arm_run_id = coalesce(
                %(canonical_arm_run_id)s::uuid,
                canonical_arm_run_id
            ),
            latest_message = coalesce(
                %(latest_message)s,
                latest_message
            ),
            raw_metadata = case
                when %(publication_fingerprint)s::text is null
                    then raw_metadata
                else raw_metadata || jsonb_build_object(
                    'publication_fingerprint',
                    %(publication_fingerprint)s::text
                )
            end,
            status = case
                when status = 'finalized' then status
                when %(status)s::text = 'completed' then 'finalized'
                else status
            end,
            updated_at = now()
        where live_run_id = %(live_run_id)s
        """,
        {
            "status": next_status,
            "canonical_arm_run_id": canonical_arm_run_id,
            "latest_message": latest_message,
            "publication_fingerprint": publication_fingerprint,
            "live_run_id": live_run_id,
        },
    )
    return next_status


def _canonical_identity_rows(
    cursor: Any,
    *,
    manifest: Mapping[str, Any],
    arm_run_id: str | None,
) -> list[tuple[Any, ...]]:
    run = manifest["run"]
    run_label = str(
        run.get("run_label")
        or f"{run.get('arm_id')}/{run.get('run_timestamp')}"
    )
    parameters: list[Any] = [
        run.get("phase"),
        run.get("storage_mode") or run.get("mode"),
        run_label,
        run.get("arm_id"),
    ]
    arm_filter = ""
    if arm_run_id:
        arm_filter = "and arm_run.id = %s::uuid"
        parameters.append(arm_run_id)
    cursor.execute(
        f"""
        select
            benchmark_run.id,
            arm_run.id,
            benchmark_run.raw_metadata ->> 'publication_fingerprint',
            arm_run.raw_metadata ->> 'publication_fingerprint',
            arm_run.github_run_id,
            arm_run.raw_metadata ->> 'github_run_attempt'
        from benchmark.benchmark_arm_runs arm_run
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where benchmark_run.phase = %s
          and benchmark_run.mode = %s
          and benchmark_run.run_label = %s
          and arm_run.arm_id = %s
          {arm_filter}
        """,
        tuple(parameters),
    )
    return list(cursor.fetchall())


def inspect_completed_publication_with_cursor(
    cursor: Any,
    *,
    manifest: Mapping[str, Any],
    live_run_id: str | None,
    publication_fingerprint: str,
    require_r2: bool = False,
    r2_integrity_verified: bool = False,
) -> ExistingCanonicalPublication | None:
    live_fingerprint: str | None = None
    linked_arm_run_id: str | None = None
    if live_run_id:
        cursor.execute(
            """
            select
                canonical_publication_status,
                canonical_arm_run_id,
                raw_metadata ->> 'publication_fingerprint'
            from benchmark.live_runs
            where live_run_id = %s
            """,
            (live_run_id,),
        )
        live_row = cursor.fetchone()
        if live_row is None or live_row[0] != "completed":
            return None
        linked_arm_run_id = str(live_row[1]) if live_row[1] else None
        live_fingerprint = str(live_row[2]) if live_row[2] else None
        if not linked_arm_run_id:
            raise CompletedPublicationMismatch(
                "completed live publication has no canonical arm-run link"
            )
    else:
        run = manifest.get("run") or {}
        if not run.get("execution_scoped") or not run.get("github_run_id"):
            return None

    identity_rows = _canonical_identity_rows(
        cursor,
        manifest=manifest,
        arm_run_id=linked_arm_run_id,
    )
    if not identity_rows:
        if live_run_id:
            raise CompletedPublicationMismatch(
                "completed live publication has no exact canonical identity"
            )
        return None
    if len(identity_rows) != 1:
        raise CompletedPublicationMismatch(
            "completed publication has ambiguous canonical identity"
        )
    (
        run_id,
        arm_run_id,
        run_fingerprint,
        arm_fingerprint,
        github_run_id,
        github_run_attempt,
    ) = identity_rows[0]
    run = manifest["run"]
    expected_github_run_id = run.get("github_run_id")
    expected_attempt = run.get("github_run_attempt")
    if str(github_run_id or "") != str(expected_github_run_id or ""):
        raise CompletedPublicationMismatch(
            "completed canonical GitHub run identity differs"
        )
    if str(github_run_attempt or "") != str(expected_attempt or ""):
        raise CompletedPublicationMismatch(
            "completed canonical GitHub run attempt differs"
        )
    fingerprints = [run_fingerprint, arm_fingerprint]
    if live_run_id:
        fingerprints.append(live_fingerprint)
    if any(value != publication_fingerprint for value in fingerprints):
        raise CompletedPublicationMismatch(
            "completed publication fingerprint differs"
        )

    cursor.execute(
        """
        select raw_result
        from benchmark.benchmark_trials
        where arm_run_id = %s::uuid
        order by attempt_index, id
        """,
        (arm_run_id,),
    )
    stored_trials = [
        dict(row[0]) if isinstance(row[0], Mapping) else {}
        for row in cursor.fetchall()
    ]
    expected_trials = trial_fingerprint_records(manifest)
    actual_trials = trial_fingerprint_records(
        {"run": run, "trials": stored_trials}
    )
    if actual_trials != expected_trials:
        raise CompletedPublicationMismatch(
            "completed canonical trial evidence differs"
        )

    cursor.execute(
        """
        select artifact_type, local_path, sha256, size_bytes, r2_uri
        from benchmark.benchmark_artifacts
        where run_id = %s::uuid
        order by local_path, artifact_type, sha256
        """,
        (run_id,),
    )
    stored_artifacts = [
        {
            "artifact_type": artifact_type,
            "local_path": local_path,
            "sha256": sha256,
            "size_bytes": size_bytes,
            "r2_uri": r2_uri,
        }
        for artifact_type, local_path, sha256, size_bytes, r2_uri in cursor.fetchall()
    ]
    if artifact_fingerprint_records(
        {"run": run, "artifacts": stored_artifacts}
    ) != artifact_fingerprint_records(manifest):
        raise CompletedPublicationMismatch(
            "completed canonical artifact evidence differs"
        )
    if any(not artifact.get("r2_uri") for artifact in stored_artifacts):
        raise CompletedPublicationMismatch(
            "completed canonical artifact is missing its R2 URI"
        )

    verification = verify_canonical_publication_with_cursor(
        cursor,
        manifest=manifest,
        run_id=str(run_id),
        arm_run_id=str(arm_run_id),
        live_run_id=live_run_id,
        require_r2=require_r2,
        r2_integrity_verified=r2_integrity_verified,
    )
    if not verification["ok"]:
        raise CompletedPublicationMismatch(
            "completed canonical count, classification, dashboard, or link differs"
        )
    return ExistingCanonicalPublication(
        run_id=str(run_id),
        arm_run_id=str(arm_run_id),
        publication_fingerprint=publication_fingerprint,
        artifacts=tuple(stored_artifacts),
        verification=verification,
    )


def inspect_completed_publication(
    *,
    db_url: str,
    manifest: Mapping[str, Any],
    live_run_id: str | None,
    publication_fingerprint: str,
    require_r2: bool = False,
    r2_integrity_verified: bool = False,
) -> ExistingCanonicalPublication | None:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - CLI installs dependency
        raise RuntimeError(
            "psycopg is required for completed-publication preflight"
        ) from exc
    with psycopg.connect(db_url) as connection:
        with connection.cursor() as cursor:
            return inspect_completed_publication_with_cursor(
                cursor,
                manifest=manifest,
                live_run_id=live_run_id,
                publication_fingerprint=publication_fingerprint,
                require_r2=require_r2,
                r2_integrity_verified=r2_integrity_verified,
            )


def apply_existing_canonical_artifacts(
    manifest: dict[str, Any],
    existing: ExistingCanonicalPublication,
) -> None:
    run = manifest["run"]
    uri_by_identity: dict[tuple[Any, ...], str] = {}
    for stored in existing.artifacts:
        projected = artifact_fingerprint_records(
            {"run": run, "artifacts": [stored]}
        )[0]
        identity = (
            projected["path"],
            projected["artifact_type"],
            projected["sha256"],
            projected["size_bytes"],
        )
        uri = str(stored.get("r2_uri") or "")
        if not uri or identity in uri_by_identity:
            raise CompletedPublicationMismatch(
                "completed canonical artifact URI mapping is missing or ambiguous"
            )
        uri_by_identity[identity] = uri
    for artifact in manifest.get("artifacts") or []:
        projected = artifact_fingerprint_records(
            {"run": run, "artifacts": [artifact]}
        )[0]
        identity = (
            projected["path"],
            projected["artifact_type"],
            projected["sha256"],
            projected["size_bytes"],
        )
        uri = uri_by_identity.get(identity)
        if not uri:
            raise CompletedPublicationMismatch(
                "completed canonical artifact URI mapping differs"
            )
        artifact["r2_uri"] = uri


def verify_canonical_publication_with_cursor(
    cursor: Any,
    *,
    manifest: Mapping[str, Any],
    run_id: str,
    arm_run_id: str,
    live_run_id: str | None,
    require_r2: bool,
    r2_integrity_verified: bool,
) -> dict[str, Any]:
    run = manifest["run"]
    run_label = str(
        run.get("run_label")
        or f"{run.get('arm_id')}/{run.get('run_timestamp')}"
    )
    cursor.execute(
        """
        select count(*)
        from benchmark.benchmark_arm_runs arm_run
        join benchmark.benchmark_runs benchmark_run
          on benchmark_run.id = arm_run.run_id
        where benchmark_run.phase = %s
          and benchmark_run.mode = %s
          and benchmark_run.run_label = %s
          and arm_run.arm_id = %s
        """,
        (
            run.get("phase"),
            run.get("storage_mode") or run.get("mode"),
            run_label,
            run.get("arm_id"),
        ),
    )
    arm_run_count = cursor.fetchone()[0]
    cursor.execute(
        "select count(*) from benchmark.benchmark_trials where arm_run_id = %s::uuid",
        (arm_run_id,),
    )
    trial_count = cursor.fetchone()[0]
    cursor.execute(
        """
        select count(*), count(*) filter (where r2_uri is not null)
        from benchmark.benchmark_artifacts
        where run_id = %s::uuid
        """,
        (run_id,),
    )
    artifact_count, r2_artifact_count = cursor.fetchone()
    cursor.execute(
        "select count(*) from benchmark.v_dashboard_arms where arm_id = %s",
        (run.get("arm_id"),),
    )
    dashboard_arm_count = cursor.fetchone()[0]

    valid_view_count = 0
    invalid_row_count = 0
    if run.get("suite_id"):
        cursor.execute(
            """
            select count(*)
            from benchmark.v_valid_arm_run_summary
            where arm_run_id = %s::uuid
            """,
            (arm_run_id,),
        )
        valid_view_count = cursor.fetchone()[0]
        cursor.execute(
            """
            select count(*)
            from benchmark.benchmark_invalid_arm_runs
            where suite_id = %s
              and arm_id = %s
              and run_label = %s
            """,
            (run.get("suite_id"), run.get("arm_id"), run_label),
        )
        invalid_row_count = cursor.fetchone()[0]

    live_link_expected = live_run_id is not None
    live_link_count = 0
    if live_run_id:
        cursor.execute(
            """
            select count(*)
            from benchmark.live_runs
            where live_run_id = %s
              and canonical_arm_run_id = %s::uuid
            """,
            (live_run_id, arm_run_id),
        )
        live_link_count = cursor.fetchone()[0]

    observed = {
        "arm_run_count": arm_run_count,
        "trial_count": trial_count,
        "artifact_count": artifact_count,
        "r2_artifact_count": r2_artifact_count,
        "r2_integrity_verified": r2_integrity_verified,
        "dashboard_arm_count": dashboard_arm_count,
        "valid_view_count": valid_view_count,
        "invalid_row_count": invalid_row_count,
        "suite_classification": observed_suite_classification(
            {
                "valid_view_count": valid_view_count,
                "invalid_row_count": invalid_row_count,
            }
        ),
        "live_link_expected": live_link_expected,
        "live_link_count": live_link_count,
    }
    errors = validate_publication_counts(manifest, observed, require_r2=require_r2)
    return {**observed, "ok": not errors, "errors": errors}


def verify_canonical_publication(
    *,
    manifest: Mapping[str, Any],
    db_url: str,
    run_id: str,
    arm_run_id: str,
    live_run_id: str | None,
    require_r2: bool,
    r2_integrity_verified: bool,
) -> dict[str, Any]:
    try:
        import psycopg
    except ImportError as exc:  # pragma: no cover - CLI installs dependency
        raise RuntimeError("psycopg is required for canonical publication verification") from exc

    with psycopg.connect(db_url) as connection:
        with connection.cursor() as cursor:
            return verify_canonical_publication_with_cursor(
                cursor,
                manifest=manifest,
                run_id=run_id,
                arm_run_id=arm_run_id,
                live_run_id=live_run_id,
                require_r2=require_r2,
                r2_integrity_verified=r2_integrity_verified,
            )
