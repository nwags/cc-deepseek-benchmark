#!/usr/bin/env python3
"""Backfill timestamped Phase 3 Harbor run roots into manifests/R2/Postgres.

This wrapper discovers only timestamped run-root directories like:

  results/phase3/canary/arm-router-x/2026-06-04__12-40-42

It excludes nested per-task trial directories and passes sponsor-facing logical
mode/suite metadata to the ingestion script.
"""

from __future__ import annotations

import argparse
import re
import subprocess
from pathlib import Path


TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}__\d{2}-\d{2}-\d{2}")

MODE_TO_STORAGE_DIR = {
    "canary": "canary",
    "smoke": "smoke",
    "full": "raw",
    "raw": "raw",
}

MODE_TO_SUITE_ID = {
    "canary": "phase3-canary-1",
    "smoke": "phase3-smoke-5",
    "full": "phase3-full-20",
    "raw": "phase3-full-20",
}


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def discover_run_dirs(root: Path, modes: list[str]) -> list[tuple[Path, str]]:
    run_dirs: list[tuple[Path, str]] = []
    for mode in modes:
        storage_dir = MODE_TO_STORAGE_DIR[mode]
        mode_dir = root / "results" / "phase3" / storage_dir
        if not mode_dir.exists():
            continue

        for result_json in sorted(mode_dir.glob("arm-*/*/result.json")):
            run_dir = result_json.parent
            if TIMESTAMP_RE.fullmatch(run_dir.name):
                logical_mode = "full" if mode == "raw" else mode
                run_dirs.append((run_dir, logical_mode))

    return sorted(run_dirs, key=lambda item: item[0])


def safe_manifest_name(run_dir: Path) -> str:
    return run_dir.as_posix().replace("/", "_").replace(":", "_") + ".json"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--mode",
        action="append",
        choices=["canary", "smoke", "full", "raw"],
        help="Logical mode to backfill. Can be repeated. Defaults to canary and smoke.",
    )
    parser.add_argument("--manifest-dir", default="/tmp/phase3-backfill-manifests")
    parser.add_argument("--upload-r2", action="store_true")
    parser.add_argument("--insert-db", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--print-only", action="store_true", help="Only print discovered run roots.")
    args = parser.parse_args()

    root = repo_root()
    modes = args.mode or ["canary", "smoke"]
    run_dirs = discover_run_dirs(root, modes)
    if args.limit is not None:
        run_dirs = run_dirs[: args.limit]

    print(f"Timestamped Phase 3 run roots found: {len(run_dirs)}")
    for run_dir, logical_mode in run_dirs:
        print(f"{run_dir.relative_to(root)} logical_mode={logical_mode} suite_id={MODE_TO_SUITE_ID[logical_mode]}")

    if args.print_only:
        return 0

    manifest_dir = Path(args.manifest_dir)
    manifest_dir.mkdir(parents=True, exist_ok=True)

    failures = 0
    ingest_script = root / "scripts" / "ingest_phase3_run_metadata.py"

    for run_dir, logical_mode in run_dirs:
        rel = run_dir.relative_to(root)
        manifest_out = manifest_dir / safe_manifest_name(rel)
        suite_id = MODE_TO_SUITE_ID[logical_mode]

        print()
        print(f"=== BACKFILL: {rel} logical_mode={logical_mode} suite_id={suite_id} ===")

        cmd = [
            "python",
            str(ingest_script),
            "--run-dir",
            str(rel),
            "--manifest-out",
            str(manifest_out),
            "--logical-mode",
            logical_mode,
            "--suite-id",
            suite_id,
        ]
        if args.upload_r2:
            cmd.append("--upload-r2")
        if args.insert_db:
            cmd.append("--insert-db")

        proc = subprocess.run(cmd, cwd=root)
        if proc.returncode != 0:
            print(f"FAILED: {rel}")
            failures += 1

    print()
    print(f"Backfill failures: {failures}")
    return 0 if failures == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
