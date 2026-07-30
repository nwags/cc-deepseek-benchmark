#!/usr/bin/env python3
"""Run a benchmark command with durable local and optional shared live evidence.

The stream contains observable process activity, heartbeats, trial state, and
publication state. It does not label stdout or stderr as private model reasoning.
Database and R2 publication are opt-in for ordinary local use.
"""

from __future__ import annotations

import argparse
import os
import queue
import signal
import subprocess
import sys
import threading
import time
from pathlib import Path
from typing import Any, TextIO

if __package__ in {None, ""}:
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from scripts.lib.live_artifacts import (
    ProgressiveR2Uploader,
    normalize_watch_roots,
    required_r2_environment,
    snapshot_run_dirs,
)
from scripts.lib.live_db import BatchedDatabasePublisher, PostgresLiveStore
from scripts.lib.live_events import (
    BoundedQueue,
    LocalEventWriter,
    Redactor,
    SharedOutputSampler,
    deterministic_live_run_id,
    safe_component,
    utc_now,
    workspace_metadata,
)
from scripts.lib.live_supervision import ProgressiveRunMonitor
from scripts.lib.path_safety import (
    PathBoundaryError,
    ensure_workspace_directory,
    resolved_workspace,
)


def _positive_float(value: str) -> float:
    parsed = float(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def _positive_int(value: str) -> int:
    parsed = int(value)
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be positive")
    return parsed


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run a benchmark command with local NDJSON and optional shared supervision."
    )
    parser.add_argument("--arm-id", required=True)
    parser.add_argument("--mode", required=True)
    parser.add_argument("--phase", required=True)
    parser.add_argument("--run-kind", default="")
    parser.add_argument("--scored", action=argparse.BooleanOptionalAction, default=None)
    parser.add_argument("--live-run-id", "--run-id", dest="live_run_id", default="")
    parser.add_argument("--github-run-id", default=os.getenv("GITHUB_RUN_ID", ""))
    parser.add_argument(
        "--github-run-attempt",
        type=int,
        default=int(os.getenv("GITHUB_RUN_ATTEMPT", "1")),
    )
    parser.add_argument("--github-job", default=os.getenv("GITHUB_JOB", ""))
    parser.add_argument("--runner-name", default=os.getenv("RUNNER_NAME", ""))
    parser.add_argument("--workspace", default=os.getenv("GITHUB_WORKSPACE") or os.getcwd())
    parser.add_argument("--live-dir", default=".run/live")
    parser.add_argument("--watch-root", action="append", default=[])
    parser.add_argument("--expected-trial-count", type=int)
    parser.add_argument(
        "--database-events",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument(
        "--progressive-artifacts",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument("--database-batch-size", type=_positive_int, default=75)
    parser.add_argument("--database-flush-seconds", type=_positive_float, default=7.5)
    parser.add_argument("--database-output-sample-every", type=_positive_int, default=5)
    parser.add_argument("--database-output-retention", type=_positive_int, default=500)
    parser.add_argument("--heartbeat-seconds", type=_positive_float, default=25.0)
    parser.add_argument("--artifact-scan-seconds", type=_positive_float, default=10.0)
    parser.add_argument("--artifact-stability-seconds", type=float, default=15.0)
    parser.add_argument("--r2-prefix", default=os.getenv("R2_PREFIX", "phase3"))
    parser.add_argument(
        "--dry-run-metadata",
        action="store_true",
        help="Mark this execution as a non-scored dry run; the child command remains authoritative.",
    )
    parser.add_argument(
        "--canonical-publication-expected",
        action=argparse.BooleanOptionalAction,
        default=False,
    )
    parser.add_argument("command", nargs=argparse.REMAINDER)
    args = parser.parse_args(argv)

    if args.command and args.command[0] == "--":
        args.command = args.command[1:]
    if not args.command:
        parser.error("command is required after --")
    if args.github_run_attempt <= 0:
        parser.error("--github-run-attempt must be positive")
    if args.expected_trial_count is not None and args.expected_trial_count < 0:
        parser.error("--expected-trial-count must be nonnegative")
    if args.artifact_stability_seconds < 0:
        parser.error("--artifact-stability-seconds must be nonnegative")
    return args


def _reader_thread(
    pipe: TextIO,
    stream_name: str,
    output: TextIO,
    events: BoundedQueue,
    redactor: Redactor,
) -> None:
    try:
        for line in iter(pipe.readline, ""):
            safe_line = redactor.text(line, limit=16_000)
            output.write(safe_line)
            output.flush()
            events.offer((stream_name, safe_line.rstrip("\n")))
    finally:
        while not events.put((stream_name, None), timeout=0.1):
            pass


def _default_watch_roots(workspace: Path, phase: str, arm_id: str, mode: str) -> list[Path]:
    phase_dir = "phase3" if phase.startswith("phase3") else phase
    storage_mode = "raw" if mode == "full" else mode
    return [
        workspace / "results" / phase_dir / storage_mode / f"arm-{arm_id}",
        workspace / "results" / phase_dir / "ad-hoc",
    ]


def _exit_code(returncode: int) -> int:
    return 128 + abs(returncode) if returncode < 0 else returncode


def _run_row(
    *,
    args: argparse.Namespace,
    live_run_id: str,
    workspace: Path,
    redactor: Redactor,
    run_kind: str,
    scored: bool,
    status: str,
    started_at: str,
    **updates: Any,
) -> dict[str, Any]:
    return {
        "live_run_id": live_run_id,
        "github_run_id": args.github_run_id or None,
        "github_run_attempt": args.github_run_attempt,
        "github_job": args.github_job or None,
        "runner_name": args.runner_name or None,
        **workspace_metadata(workspace),
        "arm_id": args.arm_id,
        "phase": args.phase,
        "mode": args.mode,
        "run_kind": run_kind,
        "scored": scored,
        "status": status,
        "live_publication_status": "running" if args.database_events else "disabled",
        "progressive_artifact_status": "running" if args.progressive_artifacts else "disabled",
        "canonical_publication_status": (
            "pending" if args.canonical_publication_expected and scored else "not_requested"
        ),
        "command_summary": {"argv": redactor.command(args.command)},
        "expected_trial_count": args.expected_trial_count,
        "started_at": started_at,
        "last_heartbeat_at": started_at,
        "raw_metadata": {
            "supervisor": "scripts/run_arm_live.py",
            "dry_run": args.dry_run_metadata,
        },
        **updates,
    }


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        workspace = resolved_workspace(Path(args.workspace))
        live_dir = ensure_workspace_directory(
            Path(args.live_dir),
            workspace=workspace,
            create=True,
            label="live event directory",
        )
    except (OSError, PathBoundaryError):
        print("live workspace path is invalid", file=sys.stderr)
        return 2

    redactor = Redactor.from_runtime_sources(workspace)
    run_kind = "dry-run" if args.dry_run_metadata else (args.run_kind or args.mode)
    scored = (
        args.scored
        if args.scored is not None
        else run_kind not in {"dry-run", "ad-hoc", "diagnostic"}
    )
    live_run_id = safe_component(
        args.live_run_id
        or deterministic_live_run_id(
            github_run_id=args.github_run_id,
            github_run_attempt=args.github_run_attempt,
            runner_name=args.runner_name,
            arm_id=args.arm_id,
            mode=args.mode,
        ),
        fallback="live-run",
        limit=180,
    )
    requested_roots = [Path(value) for value in args.watch_root]
    watch_roots = normalize_watch_roots(
        requested_roots or _default_watch_roots(workspace, args.phase, args.arm_id, args.mode),
        workspace,
    )
    baseline = snapshot_run_dirs(watch_roots, workspace=workspace)
    started_epoch = time.time()
    started_at = utc_now()
    metadata = {
        "arm_id": args.arm_id,
        "mode": args.mode,
        "phase": args.phase,
        "run_kind": run_kind,
        "scored": scored,
        "github_run_id": args.github_run_id or None,
        "github_run_attempt": args.github_run_attempt,
        "github_job": args.github_job or None,
        "runner_name": args.runner_name or None,
        **workspace_metadata(workspace),
    }

    writer = LocalEventWriter(
        live_run_id=live_run_id,
        out_dir=live_dir,
        metadata=metadata,
        redactor=redactor,
        workspace=workspace,
    )
    context_payload = {
        **metadata,
        "live_run_id": live_run_id,
        "watch_roots": [
            path.relative_to(workspace).as_posix() for path in watch_roots
        ],
        "baseline_run_dirs": list(baseline),
        "started_after_epoch": started_epoch,
        "expected_trial_count": args.expected_trial_count,
        "command": redactor.command(args.command),
    }
    writer.write_context(context_payload)

    publisher: BatchedDatabasePublisher | None = None
    db_url = os.getenv("SUPABASE_DB_URL")
    if args.database_events and db_url:
        publisher = BatchedDatabasePublisher(
            store=PostgresLiveStore(
                db_url,
                process_output_retention=args.database_output_retention,
            ),
            spool_path=live_dir / f"{live_run_id}.database-spool.ndjson",
            batch_size=args.database_batch_size,
            flush_seconds=args.database_flush_seconds,
            warning_callback=lambda message: writer.emit(
                "publication_warning",
                message=message,
                publish_shared=False,
                publication="database",
            ),
            redactor=redactor,
            workspace=workspace,
        )
        publisher.start()
        publisher.submit_run(
            _run_row(
                args=args,
                live_run_id=live_run_id,
                workspace=workspace,
                redactor=redactor,
                run_kind=run_kind,
                scored=scored,
                status="starting",
                started_at=started_at,
            )
        )
        writer.set_sink(publisher.submit_event)

    uploader: ProgressiveR2Uploader | None = None
    missing_r2, r2_env = required_r2_environment()
    if args.progressive_artifacts and not missing_r2:
        uploader = ProgressiveR2Uploader(
            bucket=r2_env["R2_BUCKET"],
            endpoint_url=r2_env["R2_ENDPOINT_URL"],
            access_key_id=r2_env["R2_ACCESS_KEY_ID"],
            secret_access_key=r2_env["R2_SECRET_ACCESS_KEY"],
            region=r2_env["R2_REGION"],
        )

    writer.emit(
        "run_started",
        status="running",
        database_events=bool(publisher),
        progressive_artifacts=bool(uploader),
        expected_trial_count=args.expected_trial_count,
    )
    if args.database_events and not db_url:
        writer.emit(
            "publication_warning",
            message="live database publication disabled; missing SUPABASE_DB_URL",
            missing_variables=["SUPABASE_DB_URL"],
        )
    if args.progressive_artifacts and missing_r2:
        writer.emit(
            "publication_warning",
            message="progressive R2 publication disabled; required variables are missing",
            missing_variables=missing_r2,
        )

    monitor: ProgressiveRunMonitor | None = None
    if watch_roots and not args.dry_run_metadata and (publisher or uploader):
        monitor = ProgressiveRunMonitor(
            live_run_id=live_run_id,
            workspace=workspace,
            watch_roots=watch_roots,
            baseline_run_dirs=baseline,
            started_after_epoch=started_epoch,
            arm_id=args.arm_id,
            phase=args.phase,
            mode=args.mode,
            github_run_id=args.github_run_id or None,
            github_run_attempt=args.github_run_attempt,
            runner_name=args.runner_name or None,
            writer=writer,
            publisher=publisher,
            uploader=uploader,
            r2_prefix=args.r2_prefix,
            scan_seconds=args.artifact_scan_seconds,
            stability_seconds=args.artifact_stability_seconds,
        )
        monitor.start()

    process: subprocess.Popen[str] | None = None
    interrupted_signal: int | None = None
    old_handlers: dict[int, Any] = {}

    def forward_signal(signum: int, _frame: Any) -> None:
        nonlocal interrupted_signal
        interrupted_signal = signum
        if process is not None and process.poll() is None:
            try:
                os.killpg(process.pid, signum)
            except (AttributeError, ProcessLookupError, PermissionError):
                process.send_signal(signum)

    for signum in (signal.SIGINT, signal.SIGTERM):
        old_handlers[signum] = signal.getsignal(signum)
        signal.signal(signum, forward_signal)

    returncode = 127
    try:
        process = subprocess.Popen(
            args.command,
            cwd=workspace,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            start_new_session=True,
        )
        events = BoundedQueue(max_size=1_000)
        assert process.stdout is not None
        assert process.stderr is not None
        readers = [
            threading.Thread(
                target=_reader_thread,
                args=(process.stdout, "stdout", sys.stdout, events, redactor),
                daemon=True,
            ),
            threading.Thread(
                target=_reader_thread,
                args=(process.stderr, "stderr", sys.stderr, events, redactor),
                daemon=True,
            ),
        ]
        for thread in readers:
            thread.start()

        closed_streams: set[str] = set()
        output_sampler = SharedOutputSampler(
            sample_every=args.database_output_sample_every
        )
        last_heartbeat = time.monotonic()
        reported_drops = 0
        while len(closed_streams) < 2:
            try:
                stream_name, line = events.get(timeout=0.5)
            except queue.Empty:
                stream_name, line = "", ""

            if stream_name:
                if line is None:
                    closed_streams.add(stream_name)
                else:
                    writer.emit(
                        "process_output_chunk",
                        stream=stream_name,
                        message=line,
                        publish_shared=output_sampler.should_publish(),
                    )

            now = time.monotonic()
            if events.dropped > reported_drops:
                dropped_delta = events.dropped - reported_drops
                reported_drops = events.dropped
                writer.emit(
                    "publication_warning",
                    message="observable output queue reached its bound",
                    dropped_output_chunks=dropped_delta,
                )
            if now - last_heartbeat >= args.heartbeat_seconds:
                writer.emit(
                    "heartbeat",
                    message="benchmark process is running",
                    returncode=process.poll(),
                )
                if publisher:
                    publisher.submit_run(
                        _run_row(
                            args=args,
                            live_run_id=live_run_id,
                            workspace=workspace,
                            redactor=redactor,
                            run_kind=run_kind,
                            scored=scored,
                            status="running",
                            started_at=started_at,
                            last_heartbeat_at=utc_now(),
                            elapsed_seconds=round(time.monotonic() - writer.started, 3),
                            event_count=writer.sequence,
                        )
                    )
                last_heartbeat = now

        returncode = process.wait()
        for thread in readers:
            thread.join(timeout=1.0)
    except OSError as exc:
        writer.emit(
            "exception",
            message=f"unable to start wrapped command ({type(exc).__name__})",
            status="failed",
        )
    finally:
        for signum, handler in old_handlers.items():
            signal.signal(signum, handler)

    if monitor:
        monitor.stop(timeout=min(args.artifact_scan_seconds + 2.0, 15.0), final_scan=True)

    benchmark_status = (
        "interrupted"
        if interrupted_signal is not None
        else ("completed" if returncode == 0 else "failed")
    )
    final_status = benchmark_status
    if interrupted_signal is not None:
        writer.emit(
            "exception",
            message=f"supervisor received signal {interrupted_signal}",
            status="interrupted",
            signal=interrupted_signal,
        )
    elif returncode != 0:
        writer.emit(
            "exception",
            status="failed",
            returncode=returncode,
            message="wrapped command exited non-zero",
        )
    writer.emit(
        "run_finished",
        status=final_status,
        benchmark_status=benchmark_status,
        returncode=returncode,
        interrupted_signal=interrupted_signal,
        **(monitor.aggregate_row() if monitor else {}),
    )
    writer.write_context(
        {
            **context_payload,
            "benchmark_status": benchmark_status,
            "returncode": returncode,
            "finished_at": utc_now(),
        }
    )

    if publisher:
        aggregate = monitor.aggregate_row() if monitor else {}
        publisher.submit_run(
            _run_row(
                args=args,
                live_run_id=live_run_id,
                workspace=workspace,
                redactor=redactor,
                run_kind=run_kind,
                scored=scored,
                status=final_status,
                started_at=started_at,
                benchmark_status=benchmark_status,
                live_publication_status="completed",
                progressive_artifact_status=(
                    "degraded"
                    if monitor and monitor.warning_count
                    else ("completed" if args.progressive_artifacts else "disabled")
                ),
                finished_at=utc_now(),
                last_heartbeat_at=utc_now(),
                elapsed_seconds=round(time.monotonic() - writer.started, 3),
                returncode=returncode,
                event_count=writer.sequence,
                **aggregate,
            )
        )
        flushed = publisher.stop(timeout=12.0)
        if not flushed or publisher.failed_count:
            writer.emit(
                "publication_warning",
                message="live database publication finished with locally spooled items",
                publish_shared=False,
                failed_item_count=publisher.failed_count,
            )

    writer.close()
    print(f"live events: {writer.event_path}")
    print(f"latest live index: {writer.latest_path}")
    return _exit_code(returncode)


if __name__ == "__main__":
    raise SystemExit(main())
