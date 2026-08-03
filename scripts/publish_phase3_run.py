#!/usr/bin/env python3
"""Finalize one workspace-scoped Phase 3 Harbor run into canonical storage."""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.ingest_phase3_run_metadata import (
    build_manifest,
    create_r2_client,
    detect_arm,
    upload_artifacts_to_r2,
)
from scripts.lib.canonical_publication import (
    CanonicalVerificationError,
    PsycopgCanonicalDatabaseAdapter,
    publish_manifest_transactionally,
)
from scripts.lib.live_artifacts import (
    discover_run_dir,
    normalize_watch_roots,
    verify_manifest_local_artifacts,
    verify_manifest_r2_objects,
)
from scripts.lib.live_db import PostgresLiveStore, reconcile_database_spool
from scripts.lib.live_events import Redactor, safe_component, utc_now
from scripts.lib.path_safety import (
    PathBoundaryError,
    ensure_workspace_directory,
    ensure_workspace_output_path,
    resolve_under,
    resolved_workspace,
)
from scripts.lib.publication_eligibility import evaluate_canonical_eligibility
from scripts.lib.live_verification import (
    CompletedPublicationMismatch,
    apply_existing_canonical_artifacts,
    inspect_completed_publication,
    mark_live_run_publication,
    reconcile_progressive_artifacts,
)
from scripts.lib.phase3_freeze import assert_phase3_publication_allowed
from scripts.lib.publication_fingerprint import (
    publication_fingerprint as compute_publication_fingerprint,
)


R2_REQUIRED = (
    "R2_BUCKET",
    "R2_ENDPOINT_URL",
    "R2_ACCESS_KEY_ID",
    "R2_SECRET_ACCESS_KEY",
    "R2_REGION",
)


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--arm-id", required=True)
    parser.add_argument("--mode", required=True, choices=["canary", "smoke", "full", "ad-hoc"])
    parser.add_argument("--github-run-id", default=os.getenv("GITHUB_RUN_ID", ""))
    parser.add_argument(
        "--github-run-attempt",
        type=int,
        default=int(os.getenv("GITHUB_RUN_ATTEMPT", "1")),
    )
    parser.add_argument("--github-job", default=os.getenv("GITHUB_JOB", ""))
    parser.add_argument("--runner-name", default=os.getenv("RUNNER_NAME", ""))
    parser.add_argument(
        "--benchmark-status",
        choices=["completed", "failed", "interrupted"],
    )
    parser.add_argument("--phase", default="phase3")
    parser.add_argument("--suite-id")
    parser.add_argument("--workspace", default=os.getenv("GITHUB_WORKSPACE") or os.getcwd())
    parser.add_argument("--run-dir")
    parser.add_argument("--watch-root", action="append", default=[])
    parser.add_argument("--live-run-id")
    parser.add_argument("--discovery-context")
    parser.add_argument("--expected-trial-count", type=int)
    parser.add_argument("--manifest-out")
    parser.add_argument("--r2-prefix", default=os.getenv("R2_PREFIX", "phase3"))
    parser.add_argument("--upload-r2", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--insert-db", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument("--verify", action=argparse.BooleanOptionalAction, default=True)
    parser.add_argument(
        "--authorize-phase3-repair",
        action="store_true",
        help=(
            "Explicitly authorize a repair publication into a completed "
            "Phase 3 suite."
        ),
    )
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    if args.github_run_attempt <= 0:
        parser.error("--github-run-attempt must be positive")
    if args.expected_trial_count is not None and args.expected_trial_count < 0:
        parser.error("--expected-trial-count must be nonnegative")
    if not args.dry_run and args.verify and not args.insert_db:
        parser.error("--verify requires --insert-db")
    return args


def _default_watch_roots(workspace: Path, phase: str, arm_id: str, mode: str) -> list[Path]:
    storage_mode = "raw" if mode == "full" else mode
    return [
        workspace / "results" / phase / storage_mode / f"arm-{arm_id}",
        workspace / "results" / phase / "ad-hoc",
    ]


def _read_context(
    workspace: Path,
    live_run_id: str | None,
    discovery_context: str | None,
) -> dict[str, Any]:
    strict = discovery_context is not None
    if discovery_context:
        context_dir = ensure_workspace_directory(
            workspace / ".run" / "publish",
            workspace=workspace,
            label="publication context directory",
        )
        requested_path = Path(discovery_context)
        path = ensure_workspace_output_path(
            requested_path,
            workspace=workspace,
            label="publication discovery context",
        )
    else:
        if not live_run_id:
            return {}
        context_dir = workspace / ".run" / "live"
        if not context_dir.exists():
            return {}
        context_dir = ensure_workspace_directory(
            context_dir,
            workspace=workspace,
            label="live context directory",
        )
        path = ensure_workspace_output_path(
            context_dir
            / f"{safe_component(live_run_id, limit=180)}.context.json",
            workspace=workspace,
            label="live context",
        )
    if not path.exists():
        if strict:
            raise PathBoundaryError("publication discovery context does not exist")
        return {}
    try:
        path = resolve_under(
            path,
            workspace=workspace,
            parent=context_dir,
            require_file=True,
            label="publication context",
        )
        value = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, PathBoundaryError):
        if strict:
            raise PathBoundaryError("publication discovery context is unreadable")
        return {}
    if not isinstance(value, dict):
        if strict:
            raise PathBoundaryError("publication discovery context is invalid")
        return {}
    return value


def _write_json(path: Path, payload: dict[str, Any], *, workspace: Path) -> None:
    safe_path = ensure_workspace_output_path(
        path,
        workspace=workspace,
        create_parent=True,
        label="publication JSON",
    )
    temporary = ensure_workspace_output_path(
        safe_path.with_suffix(safe_path.suffix + ".tmp"),
        workspace=workspace,
        label="temporary publication JSON",
    )
    temporary.write_text(json.dumps(payload, indent=2, sort_keys=True, default=str) + "\n", encoding="utf-8")
    temporary.replace(safe_path)


def _required_environment(args: argparse.Namespace) -> list[str]:
    missing: list[str] = []
    if args.insert_db and not os.getenv("SUPABASE_DB_URL"):
        missing.append("SUPABASE_DB_URL")
    if args.upload_r2:
        missing.extend(name for name in R2_REQUIRED if not os.getenv(name))
    return missing


def _summary(
    *,
    status: str,
    args: argparse.Namespace,
    run_dir: Path | None,
    manifest_path: Path | None,
    state_path: Path,
    workspace: Path,
    **extra: Any,
) -> dict[str, Any]:
    def display(path: Path | None) -> str | None:
        if path is None:
            return None
        try:
            return path.resolve().relative_to(workspace).as_posix()
        except ValueError:
            return path.name

    return {
        "status": status,
        "arm_id": args.arm_id,
        "phase": args.phase,
        "mode": args.mode,
        "github_run_id": args.github_run_id or None,
        "github_run_attempt": args.github_run_attempt,
        "live_run_id": args.live_run_id,
        "run_dir": display(run_dir),
        "manifest_path": display(manifest_path),
        "state_path": display(state_path),
        **extra,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        workspace = resolved_workspace(Path(args.workspace))
        publish_dir = ensure_workspace_directory(
            workspace / ".run" / "publish",
            workspace=workspace,
            create=True,
            label="publication directory",
        )
    except (OSError, PathBoundaryError) as exc:
        print(
            json.dumps(
                {
                    "status": "unsafe_publication_path",
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            )
        )
        return 2
    state_stem = safe_component(
        args.live_run_id
        or f"{args.github_run_id or 'local'}-a{args.github_run_attempt}-{args.arm_id}-{args.mode}",
        limit=180,
    )
    try:
        state_path = ensure_workspace_output_path(
            publish_dir / f"{state_stem}.json",
            workspace=workspace,
            label="publication state",
        )
        manifest_path = ensure_workspace_output_path(
            Path(args.manifest_out)
            if args.manifest_out
            else publish_dir / f"{state_stem}.manifest.json",
            workspace=workspace,
            create_parent=bool(args.manifest_out),
            label="publication manifest",
        )
    except (OSError, PathBoundaryError) as exc:
        print(
            json.dumps(
                {
                    "status": "unsafe_publication_path",
                    "error_type": type(exc).__name__,
                },
                sort_keys=True,
            )
        )
        return 2
    redactor = Redactor.from_runtime_sources(workspace)

    try:
        context = _read_context(
            workspace,
            args.live_run_id,
            args.discovery_context,
        )
    except (OSError, PathBoundaryError) as exc:
        result = _summary(
            status="unsafe_live_context",
            args=args,
            run_dir=None,
            manifest_path=None,
            state_path=state_path,
            workspace=workspace,
            error_type=type(exc).__name__,
        )
        _write_json(state_path, result, workspace=workspace)
        print(json.dumps(result, sort_keys=True))
        return 2
    requested_roots = [Path(value) for value in args.watch_root]
    context_roots = [Path(value) for value in context.get("watch_roots") or []]
    roots = normalize_watch_roots(
        requested_roots
        or context_roots
        or _default_watch_roots(workspace, args.phase, args.arm_id, args.mode),
        workspace,
    )
    baseline = tuple(str(value) for value in context.get("baseline_run_dirs") or [])
    started_after = context.get("started_after_epoch")
    explicit_run_dir = Path(args.run_dir) if args.run_dir else None

    try:
        run_dir = discover_run_dir(
            workspace=workspace,
            watch_roots=roots,
            explicit_run_dir=explicit_run_dir,
            baseline_run_dirs=baseline,
            started_after_epoch=float(started_after) if started_after is not None else None,
            require_final_result=True,
        )
    except (ValueError, OSError) as exc:
        result = _summary(
            status="discovery_failed",
            args=args,
            run_dir=None,
            manifest_path=None,
            state_path=state_path,
            workspace=workspace,
            error_type=type(exc).__name__,
        )
        _write_json(state_path, result, workspace=workspace)
        print(json.dumps(result, sort_keys=True))
        return 1

    if run_dir is None:
        status = "dry_run_no_run_directory" if args.dry_run else "no_run_directory"
        result = _summary(
            status=status,
            args=args,
            run_dir=None,
            manifest_path=None,
            state_path=state_path,
            workspace=workspace,
        )
        _write_json(state_path, result, workspace=workspace)
        print(json.dumps(result, sort_keys=True))
        return 0 if args.dry_run else 1

    discovered_arm = detect_arm(run_dir)
    if discovered_arm != args.arm_id:
        result = _summary(
            status="arm_mismatch",
            args=args,
            run_dir=run_dir,
            manifest_path=None,
            state_path=state_path,
            workspace=workspace,
            discovered_arm_id=discovered_arm,
        )
        _write_json(state_path, result, workspace=workspace)
        print(json.dumps(result, sort_keys=True))
        return 1

    expected_trial_count: int | None = args.expected_trial_count
    try:
        if expected_trial_count is None and context.get("expected_trial_count") is not None:
            expected_trial_count = int(context["expected_trial_count"])
    except (TypeError, ValueError):
        expected_trial_count = None
    try:
        eligibility = evaluate_canonical_eligibility(
            run_dir,
            workspace=workspace,
            expected_trial_count=expected_trial_count,
            benchmark_status=args.benchmark_status
            or (
                str(context.get("benchmark_status"))
                if context.get("benchmark_status")
                else None
            ),
        )
    except (PathBoundaryError, OSError) as exc:
        result = _summary(
            status="ineligible",
            args=args,
            run_dir=run_dir,
            manifest_path=None,
            state_path=state_path,
            workspace=workspace,
            eligibility={
                "eligible": False,
                "reasons": [f"unsafe or unreadable result layout ({type(exc).__name__})"],
            },
        )
        _write_json(state_path, redactor.value(result), workspace=workspace)
        print(json.dumps(redactor.value(result), sort_keys=True))
        return 0 if args.dry_run else 1
    if not eligibility.eligible:
        if args.live_run_id and os.getenv("SUPABASE_DB_URL") and not args.dry_run:
            try:
                mark_live_run_publication(
                    db_url=os.environ["SUPABASE_DB_URL"],
                    live_run_id=args.live_run_id,
                    status="ineligible",
                    latest_message="Canonical publication eligibility checks failed",
                )
            except Exception:
                pass
        result = _summary(
            status="ineligible",
            args=args,
            run_dir=run_dir,
            manifest_path=None,
            state_path=state_path,
            workspace=workspace,
            eligibility=eligibility.as_dict(),
        )
        result = redactor.value(result)
        _write_json(state_path, result, workspace=workspace)
        print(json.dumps(result, sort_keys=True))
        return 0 if args.dry_run else 1

    missing = [] if args.dry_run else _required_environment(args)
    if missing:
        result = _summary(
            status="missing_required_environment",
            args=args,
            run_dir=run_dir,
            manifest_path=None,
            state_path=state_path,
            workspace=workspace,
            missing_variables=missing,
        )
        _write_json(state_path, result, workspace=workspace)
        print(json.dumps(result, sort_keys=True))
        return 2

    db_url = os.getenv("SUPABASE_DB_URL")
    try:
        manifest = build_manifest(
            run_dir,
            args.r2_prefix,
            logical_mode_override=args.mode,
            suite_id_override=args.suite_id,
            github_run_id=args.github_run_id or None,
            github_run_attempt=args.github_run_attempt,
            execution_scoped=bool(args.github_run_id),
            execution_identity=args.live_run_id,
            workspace=workspace,
        )
        manifest["run"].update(
            {
                "phase": args.phase,
                "runner_name": args.runner_name or None,
                "github_run_attempt": args.github_run_attempt,
                "github_job": args.github_job or None,
                "live_run_id": args.live_run_id,
            }
        )
        manifest["publication"] = {
            "live_run_id": args.live_run_id,
            "created_at": utc_now(),
            "progressive_artifacts_reconciled": 0,
            "database_spool_reconciled": 0,
            "database_spool_remaining": 0,
        }
        manifest = redactor.value(manifest)
        fingerprint = compute_publication_fingerprint(manifest)
        manifest["run"]["publication_fingerprint"] = fingerprint
        assert_phase3_publication_allowed(
            manifest,
            dry_run=args.dry_run,
            authorize_repair=args.authorize_phase3_repair,
        )

        if args.dry_run:
            _write_json(manifest_path, manifest, workspace=workspace)
            result = _summary(
                status="dry_run",
                args=args,
                run_dir=run_dir,
                manifest_path=manifest_path,
                state_path=state_path,
                workspace=workspace,
                trial_count=len(manifest["trials"]),
                artifact_count=len(manifest["artifacts"]),
                eligibility=eligibility.as_dict(),
            )
            _write_json(state_path, result, workspace=workspace)
            print(json.dumps(result, sort_keys=True))
            return 0

        r2_client: Any = None
        if args.upload_r2:
            r2_client = create_r2_client(
                endpoint_url=os.environ["R2_ENDPOINT_URL"],
                access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                region_name=os.environ["R2_REGION"],
            )

        local_integrity_errors = verify_manifest_local_artifacts(
            manifest,
            workspace=workspace,
            run_dir=run_dir,
        )
        if local_integrity_errors:
            raise RuntimeError(
                "canonical local artifact integrity verification failed for "
                f"{len(local_integrity_errors)} object(s)"
            )

        existing = None
        if args.insert_db and db_url:
            existing = inspect_completed_publication(
                db_url=db_url,
                manifest=manifest,
                live_run_id=args.live_run_id,
                publication_fingerprint=fingerprint,
            )
        if existing is not None:
            if r2_client is None:
                raise CompletedPublicationMismatch(
                    "completed publication replay requires R2 integrity verification"
                )
            apply_existing_canonical_artifacts(manifest, existing)
            r2_errors = verify_manifest_r2_objects(manifest, client=r2_client)
            if r2_errors:
                raise CompletedPublicationMismatch(
                    "completed canonical R2 artifact integrity differs"
                )
            verified_existing = inspect_completed_publication(
                db_url=db_url,
                manifest=manifest,
                live_run_id=args.live_run_id,
                publication_fingerprint=fingerprint,
                require_r2=True,
                r2_integrity_verified=True,
            )
            if verified_existing is None:
                raise CompletedPublicationMismatch(
                    "completed publication changed during replay verification"
                )
            _write_json(manifest_path, manifest, workspace=workspace)
            result = _summary(
                status="already_completed",
                args=args,
                run_dir=run_dir,
                manifest_path=manifest_path,
                state_path=state_path,
                workspace=workspace,
                trial_count=len(manifest["trials"]),
                artifact_count=len(manifest["artifacts"]),
                canonical_run_id=verified_existing.run_id,
                canonical_arm_run_id=verified_existing.arm_run_id,
                verification=verified_existing.verification,
                eligibility=eligibility.as_dict(),
                publication_fingerprint=fingerprint,
            )
            _write_json(state_path, result, workspace=workspace)
            print(json.dumps(result, sort_keys=True))
            return 0

        if args.live_run_id and db_url:
            spool_result = reconcile_database_spool(
                workspace
                / ".run"
                / "live"
                / f"{safe_component(args.live_run_id, limit=180)}.database-spool.ndjson",
                PostgresLiveStore(db_url),
                workspace=workspace,
            )
            manifest["publication"]["database_spool_reconciled"] = spool_result[
                "reconciled_items"
            ]
            manifest["publication"]["database_spool_remaining"] = spool_result[
                "remaining_items"
            ]
            reconciled = 0
            if r2_client is not None:
                reconciled = reconcile_progressive_artifacts(
                    manifest,
                    live_run_id=args.live_run_id,
                    db_url=db_url,
                    run_dir=run_dir,
                    workspace=workspace,
                    r2_client=r2_client,
                )
            manifest["publication"]["progressive_artifacts_reconciled"] = reconciled
        if args.upload_r2:
            upload_artifacts_to_r2(
                manifest,
                bucket=os.environ["R2_BUCKET"],
                endpoint_url=os.environ["R2_ENDPOINT_URL"],
                access_key_id=os.environ["R2_ACCESS_KEY_ID"],
                secret_access_key=os.environ["R2_SECRET_ACCESS_KEY"],
                region_name=os.environ["R2_REGION"],
                workspace=workspace,
                run_dir=run_dir,
                client=r2_client,
            )
            r2_errors = verify_manifest_r2_objects(manifest, client=r2_client)
            if r2_errors:
                raise RuntimeError(
                    f"canonical R2 integrity verification failed for {len(r2_errors)} object(s)"
                )
        r2_integrity_verified = bool(args.upload_r2)

        ids: dict[str, str] | None = None
        verification: dict[str, Any] | None = None
        publication_status = "completed"
        _write_json(manifest_path, manifest, workspace=workspace)
        if args.insert_db:
            local_integrity_errors = verify_manifest_local_artifacts(
                manifest,
                workspace=workspace,
                run_dir=run_dir,
            )
            if local_integrity_errors:
                raise RuntimeError(
                    "canonical local artifact integrity changed before database insertion"
            )
            assert db_url is not None
            ids, verification, publication_status = publish_manifest_transactionally(
                PsycopgCanonicalDatabaseAdapter(db_url),
                manifest=manifest,
                live_run_id=args.live_run_id,
                verify=args.verify,
                require_r2=args.upload_r2,
                r2_integrity_verified=r2_integrity_verified,
                publication_fingerprint=fingerprint,
            )

        result = _summary(
            status=publication_status,
            args=args,
            run_dir=run_dir,
            manifest_path=manifest_path,
            state_path=state_path,
            workspace=workspace,
            trial_count=len(manifest["trials"]),
            artifact_count=len(manifest["artifacts"]),
            reconciled_artifact_count=manifest["publication"]["progressive_artifacts_reconciled"],
            reconciled_database_item_count=manifest["publication"]["database_spool_reconciled"],
            remaining_database_spool_item_count=manifest["publication"]["database_spool_remaining"],
            canonical_run_id=ids["run_id"] if ids else None,
            canonical_arm_run_id=ids["arm_run_id"] if ids else None,
            verification=verification,
            eligibility=eligibility.as_dict(),
            publication_fingerprint=fingerprint,
        )
        _write_json(state_path, result, workspace=workspace)
        print(json.dumps(result, sort_keys=True))
        return 0
    except (Exception, SystemExit) as exc:
        if args.live_run_id and db_url:
            try:
                mark_live_run_publication(
                    db_url=db_url,
                    live_run_id=args.live_run_id,
                    status="failed",
                    latest_message=f"Canonical publication failed ({type(exc).__name__})",
                )
            except Exception:
                pass
        extra: dict[str, Any] = {}
        if isinstance(exc, CanonicalVerificationError):
            extra["verification"] = exc.verification
        result = _summary(
            status="failed",
            args=args,
            run_dir=run_dir,
            manifest_path=manifest_path if manifest_path.exists() else None,
            state_path=state_path,
            workspace=workspace,
            error_type=type(exc).__name__,
            **extra,
        )
        _write_json(state_path, result, workspace=workspace)
        print(json.dumps(result, sort_keys=True))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
