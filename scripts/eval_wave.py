#!/usr/bin/env python3
"""Operate on GitHub Actions artifact waves for benchmark eval suites.

The tool is intentionally eval-suite oriented: suite metadata identifies the
phase, logical mode, storage mode, artifact prefix, and expected trial count
when checked-in config is available. Downloaded artifacts, manifests, and
run-dir lists stay under tmp/ by default.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

try:
    import yaml
except ImportError:  # pragma: no cover - exercised only in minimal envs.
    yaml = None

from scripts.ingest_phase3_run_metadata import build_manifest, ensure_timestamped_run_dir


TIMESTAMP_RE = re.compile(r"\d{4}-\d{2}-\d{2}__\d{2}-\d{2}-\d{2}")
MODE_NAME_RE = r"canary|smoke|full|raw|ad-hoc"


@dataclass(frozen=True)
class RunSpec:
    run_id: str
    arm_id: str


@dataclass(frozen=True)
class RunDirRow:
    run_id: str
    arm_id: str
    run_dir: Path


@dataclass(frozen=True)
class EvalContext:
    suite_id: str | None
    phase: str | None
    logical_mode: str | None
    storage_mode: str | None
    expected_trials: int | None
    artifact_prefix: str | None
    r2_prefix: str | None


def repo_root() -> Path:
    return ROOT


def split_words(value: str | None) -> list[str]:
    if not value:
        return []
    return [part for part in value.replace("\n", " ").split(" ") if part.strip()]


def parse_run_specs(value: str | None) -> list[RunSpec]:
    specs: list[RunSpec] = []
    for token in split_words(value):
        if ":" not in token:
            raise SystemExit(f"RUNS entries must look like <github_run_id>:<arm_id>; got {token!r}")
        run_id, arm_id = token.split(":", 1)
        run_id = run_id.strip()
        arm_id = arm_id.strip()
        if not run_id or not arm_id:
            raise SystemExit(f"Invalid RUNS entry: {token!r}")
        specs.append(RunSpec(run_id=run_id, arm_id=arm_id))
    return specs


def parse_arms(value: str | None) -> list[str]:
    return split_words(value)


def env_int(name: str) -> int | None:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        return None
    try:
        return int(value)
    except ValueError as exc:
        raise SystemExit(f"{name} must be an integer; got {value!r}") from exc


def run_command(args: list[str], *, cwd: Path | None = None) -> str:
    try:
        proc = subprocess.run(
            args,
            cwd=cwd,
            check=True,
            text=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
    except FileNotFoundError as exc:
        raise SystemExit(f"Command not found: {args[0]}") from exc
    except subprocess.CalledProcessError as exc:
        stderr = exc.stderr.strip()
        stdout = exc.stdout.strip()
        detail = stderr or stdout or f"exit code {exc.returncode}"
        raise SystemExit(f"Command failed: {' '.join(args)}\n{detail}") from exc
    return proc.stdout


def gh_json(args: list[str], *, cwd: Path | None = None) -> Any:
    text = run_command(["gh", *args], cwd=cwd)
    if not text.strip():
        return None
    try:
        return json.loads(text)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"gh returned non-JSON output for {' '.join(args)}: {exc}") from exc


def current_repo() -> str:
    data = gh_json(["repo", "view", "--json", "owner,name"], cwd=repo_root())
    return f"{data['owner']['login']}/{data['name']}"


def load_yaml_dict(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    if yaml is None:
        raise SystemExit("PyYAML is required to read eval-suite and phase configs.")
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    if not isinstance(data, dict):
        raise SystemExit(f"YAML config must be a mapping: {path}")
    return data


def try_load_yaml_dict(path: Path) -> dict[str, Any]:
    try:
        return load_yaml_dict(path)
    except Exception:
        return {}


def load_suite_config(suite_id: str | None) -> dict[str, Any]:
    if not suite_id:
        return {}
    return load_yaml_dict(ROOT / "configs" / "eval_suites" / f"{suite_id}.yaml")


def load_suite_db_metadata(suite_id: str | None) -> dict[str, Any]:
    db_url = os.getenv("SUPABASE_DB_URL")
    if not suite_id or not db_url:
        return {}
    try:
        import psycopg
        from psycopg.rows import dict_row
    except ImportError:
        return {}

    try:
        with psycopg.connect(db_url, row_factory=dict_row, connect_timeout=5) as conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    select suite_id, phase, suite_type, raw_metadata
                    from benchmark.benchmark_eval_suites
                    where suite_id = %s
                    """,
                    (suite_id,),
                )
                row = cur.fetchone()
                if not row:
                    return {}
                cur.execute(
                    """
                    select count(*)::int as task_count
                    from benchmark.benchmark_eval_suite_items
                    where suite_id = %s
                    """,
                    (suite_id,),
                )
                count_row = cur.fetchone()
    except Exception:
        return {}

    metadata: dict[str, Any] = {
        "suite_id": row.get("suite_id"),
        "phase": row.get("phase"),
        "suite_type": row.get("suite_type"),
        "raw_metadata": row.get("raw_metadata") or {},
    }
    if count_row and count_row.get("task_count"):
        metadata["_task_count"] = count_row["task_count"]
    return metadata


def load_suite_metadata(suite_id: str | None) -> dict[str, Any]:
    config = load_suite_config(suite_id)
    if config and config.get("phase") and config.get("suite_type") and suite_task_count(config) is not None:
        return config
    db_metadata = load_suite_db_metadata(suite_id)
    if not db_metadata:
        return config
    merged = dict(db_metadata)
    merged.update(config)
    return merged


def load_phase_config(phase: str | None) -> dict[str, Any]:
    if not phase:
        return {}

    exact = ROOT / "configs" / "phases" / f"{phase}.yaml"
    if exact.exists():
        return try_load_yaml_dict(exact)

    results_root = f"results/{phase}"
    for path in sorted((ROOT / "configs" / "phases").glob("*.yaml")):
        data = try_load_yaml_dict(path)
        if data.get("phase_id") == phase or data.get("results_root") == results_root:
            return data
    return {}


def count_task_file(path_text: str | None) -> int | None:
    if not path_text:
        return None
    path = Path(path_text)
    if not path.is_absolute():
        path = ROOT / path
    if not path.exists():
        return None
    count = 0
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if line and not line.startswith("#"):
            count += 1
    return count


def suite_task_count(suite_config: dict[str, Any]) -> int | None:
    db_task_count = suite_config.get("_task_count")
    if db_task_count is not None:
        return int(db_task_count)
    tasks = suite_config.get("tasks")
    if isinstance(tasks, list):
        return len(tasks)
    return count_task_file(suite_config.get("source_task_file"))


def infer_expected_trials(
    *,
    suite_config: dict[str, Any],
    phase_config: dict[str, Any],
    logical_mode: str | None,
) -> int | None:
    explicit = suite_config.get("expected_trials")
    if explicit is not None:
        return int(explicit)

    task_count = suite_task_count(suite_config)
    if task_count is None:
        return None

    suite_attempts = suite_config.get("n_attempts")
    if suite_attempts is not None:
        attempts = int(suite_attempts)
    elif logical_mode in {"canary", "smoke"}:
        attempts = 1
    else:
        attempts = int(phase_config.get("n_attempts", 1) or 1)
    return task_count * attempts


def storage_mode_for(logical_mode: str | None, phase_config: dict[str, Any]) -> str | None:
    if not logical_mode:
        return None
    subdirs = phase_config.get("mode_results_subdirs")
    if isinstance(subdirs, dict) and logical_mode in subdirs:
        return str(subdirs[logical_mode])
    if logical_mode == "full":
        return "raw"
    return logical_mode


def resolve_context(args: argparse.Namespace) -> EvalContext:
    suite_id = getattr(args, "suite_id", None) or os.getenv("SUITE_ID")
    suite_config = load_suite_metadata(suite_id)

    phase = getattr(args, "phase", None) or os.getenv("PHASE") or suite_config.get("phase")
    logical_mode = (
        getattr(args, "logical_mode", None)
        or os.getenv("LOGICAL_MODE")
        or suite_config.get("suite_type")
    )
    phase_config = load_phase_config(phase)
    storage_mode = getattr(args, "storage_mode", None) or storage_mode_for(logical_mode, phase_config)

    expected_trials = getattr(args, "expected_trials", None)
    if expected_trials is None:
        expected_trials = infer_expected_trials(
            suite_config=suite_config,
            phase_config=phase_config,
            logical_mode=logical_mode,
        )

    artifact_prefix = (
        getattr(args, "artifact_prefix", None)
        or os.getenv("ARTIFACT_PREFIX")
        or phase
        or suite_config.get("phase")
    )
    r2_prefix = getattr(args, "r2_prefix", None) or os.getenv("R2_PREFIX") or phase

    return EvalContext(
        suite_id=suite_id,
        phase=phase,
        logical_mode=logical_mode,
        storage_mode=storage_mode,
        expected_trials=expected_trials,
        artifact_prefix=artifact_prefix,
        r2_prefix=r2_prefix,
    )


def infer_artifact_arm(name: str, run_id: str, artifact_prefix: str | None) -> str | None:
    if artifact_prefix:
        pattern = rf"^{re.escape(artifact_prefix)}-(?P<arm>.+)-(?P<mode>{MODE_NAME_RE})-{re.escape(str(run_id))}$"
        match = re.fullmatch(pattern, name)
        if match:
            return match.group("arm")

    match = re.fullmatch(rf"(?P<prefix>.+?)-(?P<arm>.+)-(?P<mode>{MODE_NAME_RE})-(?P<run_id>\d+)$", name)
    if not match or match.group("run_id") != str(run_id):
        return None
    return match.group("arm")


def artifact_name_matches(name: str, run_id: str, arm_id: str, artifact_prefix: str | None) -> bool:
    inferred = infer_artifact_arm(name, run_id, artifact_prefix)
    return inferred == arm_id


def list_recent_completed_runs(
    *,
    repo: str,
    workflow: str,
    limit: int,
    branch: str | None,
) -> list[dict[str, Any]]:
    cmd = [
        "run",
        "list",
        "--repo",
        repo,
        "--workflow",
        workflow,
        "--status",
        "completed",
        "--json",
        "databaseId,conclusion,displayTitle,headBranch,status,createdAt,updatedAt,url",
        "-L",
        str(limit),
    ]
    if branch:
        cmd.extend(["--branch", branch])
    data = gh_json(cmd, cwd=repo_root())
    return data or []


def list_run_artifacts(*, repo: str, run_id: str) -> list[dict[str, Any]]:
    data = gh_json(
        [
            "api",
            f"repos/{repo}/actions/runs/{run_id}/artifacts?per_page=100",
        ],
        cwd=repo_root(),
    )
    return list((data or {}).get("artifacts") or [])


def command_list_artifacts(args: argparse.Namespace) -> int:
    context = resolve_context(args)
    repo = args.repo or current_repo()
    specs = parse_run_specs(args.runs)

    if not specs:
        runs = list_recent_completed_runs(
            repo=repo,
            workflow=args.workflow,
            limit=args.limit,
            branch=args.branch,
        )
        discovered: list[RunSpec] = []
        for run in runs:
            run_id = str(run.get("databaseId") or "")
            if not run_id:
                continue
            for artifact in list_run_artifacts(repo=repo, run_id=run_id):
                arm_id = infer_artifact_arm(str(artifact.get("name") or ""), run_id, context.artifact_prefix)
                if arm_id:
                    discovered.append(RunSpec(run_id=run_id, arm_id=arm_id))
        specs = discovered

    write_tsv_header(
        [
            "run_id",
            "arm_id",
            "artifact_name",
            "size_in_bytes",
            "expired",
            "created_at",
            "expires_at",
        ],
        enabled=not args.no_header,
    )
    for spec in specs:
        for artifact in list_run_artifacts(repo=repo, run_id=spec.run_id):
            name = str(artifact.get("name") or "")
            if not artifact_name_matches(name, spec.run_id, spec.arm_id, context.artifact_prefix):
                continue
            write_tsv_row(
                [
                    spec.run_id,
                    spec.arm_id,
                    name,
                    artifact.get("size_in_bytes"),
                    artifact.get("expired"),
                    artifact.get("created_at"),
                    artifact.get("expires_at"),
                ]
            )
    return 0


def command_download_wave(args: argparse.Namespace) -> int:
    repo = args.repo or current_repo()
    specs = parse_run_specs(args.runs)
    if not specs:
        raise SystemExit("download-wave requires RUNS=<run_id>:<arm_id> entries")

    dest = Path(args.dest)
    dest.mkdir(parents=True, exist_ok=True)

    for spec in specs:
        out_dir = dest / f"{spec.arm_id}-{spec.run_id}"
        if out_dir.exists() and any(out_dir.iterdir()):
            if not args.overwrite:
                raise SystemExit(
                    f"{out_dir} already exists and is not empty. "
                    "Set OVERWRITE=1 or pass --overwrite to replace it."
                )
            shutil.rmtree(out_dir)
        out_dir.mkdir(parents=True, exist_ok=True)

        print(f"== {spec.run_id} {spec.arm_id} ==", file=sys.stderr)
        for artifact in list_run_artifacts(repo=repo, run_id=spec.run_id):
            print(
                f"artifact\t{artifact.get('name')}\t{artifact.get('size_in_bytes')}\t"
                f"expired={artifact.get('expired')}",
                file=sys.stderr,
            )

        subprocess.run(
            ["gh", "run", "download", spec.run_id, "--repo", repo, "-D", str(out_dir)],
            cwd=repo_root(),
            check=True,
        )
        print(f"downloaded\t{spec.run_id}\t{spec.arm_id}\t{out_dir}")

    return 0


def parse_result_path(path: Path) -> tuple[str, str, str] | None:
    parts = path.parts
    if "results" not in parts:
        return None
    i = parts.index("results")
    if len(parts) <= i + 3:
        return None
    phase = parts[i + 1]
    storage_mode = parts[i + 2]
    arm_part = parts[i + 3]
    if not arm_part.startswith("arm-"):
        return None
    return phase, storage_mode, arm_part.removeprefix("arm-")


def read_json(path: Path) -> dict[str, Any] | None:
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception:
        return None


def is_top_level_run_result(path: Path, expected_trials: int | None) -> bool:
    if not TIMESTAMP_RE.fullmatch(path.parent.name):
        return False
    data = read_json(path)
    if not isinstance(data, dict):
        return False
    if "stats" not in data or "n_total_trials" not in data:
        return False
    if expected_trials is not None and data.get("n_total_trials") != expected_trials:
        return False
    return True


def candidate_roots(dest: Path, specs: list[RunSpec]) -> Iterable[tuple[str, str, Path]]:
    if specs:
        for spec in specs:
            yield spec.run_id, spec.arm_id, dest / f"{spec.arm_id}-{spec.run_id}"
        return

    for child in sorted(dest.iterdir() if dest.exists() else []):
        if not child.is_dir():
            continue
        match = re.fullmatch(r"(?P<arm>.+)-(?P<run_id>\d+)", child.name)
        if match:
            yield match.group("run_id"), match.group("arm"), child


def discover_run_dir_rows(
    *,
    dest: Path,
    runs: str | None,
    arms: list[str],
    phase: str | None,
    storage_mode: str | None,
    expected_trials: int | None,
    strict: bool,
) -> list[RunDirRow]:
    specs = parse_run_specs(runs)
    allowed_arms = set(arms)
    rows: list[RunDirRow] = []
    failures: list[str] = []

    for run_id, arm_id, root in candidate_roots(dest, specs):
        if allowed_arms and arm_id not in allowed_arms:
            continue
        matches: list[Path] = []
        if root.exists():
            for result_path in sorted(root.rglob("result.json")):
                parsed = parse_result_path(result_path)
                if parsed is None:
                    continue
                result_phase, result_storage_mode, result_arm_id = parsed
                if phase and result_phase != phase:
                    continue
                if result_arm_id != arm_id:
                    continue
                if storage_mode and result_storage_mode != storage_mode:
                    continue
                if is_top_level_run_result(result_path, expected_trials):
                    matches.append(result_path.parent)

        if len(matches) == 1:
            rows.append(RunDirRow(run_id=run_id, arm_id=arm_id, run_dir=matches[0]))
            continue

        message = f"{run_id}\t{arm_id}\tfound {len(matches)} top-level run dirs under {root}"
        if matches:
            message += "\t" + ",".join(str(m) for m in matches)
        failures.append(message)

    if failures and strict:
        raise SystemExit("run-dir discovery failed:\n" + "\n".join(failures))

    return rows


def command_discover_wave(args: argparse.Namespace) -> int:
    context = resolve_context(args)
    rows = discover_run_dir_rows(
        dest=Path(args.dest),
        runs=args.runs,
        arms=parse_arms(args.arms),
        phase=context.phase,
        storage_mode=context.storage_mode,
        expected_trials=context.expected_trials,
        strict=not args.allow_missing,
    )

    out = Path(args.run_dirs_file)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(
        "".join(f"{row.run_id}\t{row.arm_id}\t{row.run_dir.as_posix()}\n" for row in rows),
        encoding="utf-8",
    )
    print(
        f"wrote\t{out}\trows={len(rows)}\tphase={context.phase or ''}\t"
        f"logical_mode={context.logical_mode or ''}\tstorage_mode={context.storage_mode or ''}\t"
        f"expected_trials={context.expected_trials or ''}"
    )
    for row in rows:
        write_tsv_row([row.run_id, row.arm_id, row.run_dir])
    return 0


def read_run_dirs_file(path: Path) -> list[RunDirRow]:
    rows: list[RunDirRow] = []
    for lineno, raw in enumerate(path.read_text(encoding="utf-8").splitlines(), start=1):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        parts = line.split("\t")
        if parts[0] == "run_id":
            continue
        if len(parts) < 3:
            raise SystemExit(f"{path}:{lineno}: expected run_id<TAB>arm_id<TAB>run_dir")
        rows.append(RunDirRow(run_id=parts[0], arm_id=parts[1], run_dir=Path(parts[2])))
    return rows


def safe_manifest_name(row: RunDirRow) -> str:
    return f"{row.arm_id}-{row.run_dir.name}-{row.run_id}.manifest.json"


def manifest_wave(
    *,
    rows: list[RunDirRow],
    manifest_dir: Path,
    r2_prefix: str,
    logical_mode: str | None,
    suite_id: str | None,
    expected_trials: int | None,
    fail_on_incomplete: bool,
) -> list[tuple[RunDirRow, Path, dict[str, Any]]]:
    manifest_dir.mkdir(parents=True, exist_ok=True)
    built: list[tuple[RunDirRow, Path, dict[str, Any]]] = []
    failures: list[str] = []

    for row in rows:
        if not row.run_dir.exists():
            failures.append(f"{row.run_id}\t{row.arm_id}\trun_dir_missing\t{row.run_dir}")
            continue
        ensure_timestamped_run_dir(row.run_dir)
        manifest = build_manifest(
            row.run_dir,
            r2_prefix,
            logical_mode_override=logical_mode,
            suite_id_override=suite_id,
            github_run_id=row.run_id,
        )
        run = manifest.get("run") or {}
        trials = len(manifest.get("trials") or [])
        if run.get("arm_id") != row.arm_id:
            failures.append(f"{row.run_id}\t{row.arm_id}\tarm_mismatch\tmanifest_arm={run.get('arm_id')}")
        if expected_trials is not None and trials != expected_trials:
            failures.append(f"{row.run_id}\t{row.arm_id}\ttrial_count={trials}\texpected={expected_trials}")

        out = manifest_dir / safe_manifest_name(row)
        out.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n", encoding="utf-8")
        built.append((row, out, manifest))

    if failures and fail_on_incomplete:
        raise SystemExit("manifest check failed:\n" + "\n".join(failures))

    return built


def command_manifest_wave(args: argparse.Namespace) -> int:
    context = resolve_context(args)
    rows = read_run_dirs_file(Path(args.run_dirs_file))
    built = manifest_wave(
        rows=rows,
        manifest_dir=Path(args.manifest_dir),
        r2_prefix=context.r2_prefix or "",
        logical_mode=context.logical_mode,
        suite_id=context.suite_id,
        expected_trials=context.expected_trials,
        fail_on_incomplete=not args.allow_incomplete,
    )

    write_tsv_header(
        ["run_id", "arm_id", "run_dir", "manifest", "trials", "artifacts", "cost_usd", "status"],
        enabled=not args.no_header,
    )
    for row, manifest_path, manifest in built:
        run = manifest.get("run") or {}
        write_tsv_row(
            [
                row.run_id,
                row.arm_id,
                row.run_dir,
                manifest_path,
                len(manifest.get("trials") or []),
                len(manifest.get("artifacts") or []),
                run.get("cost_usd"),
                run.get("status"),
            ]
        )
    return 0


def command_ingest_wave(args: argparse.Namespace) -> int:
    context = resolve_context(args)
    rows = read_run_dirs_file(Path(args.run_dirs_file))

    built = manifest_wave(
        rows=rows,
        manifest_dir=Path(args.manifest_dir),
        r2_prefix=context.r2_prefix or "",
        logical_mode=context.logical_mode,
        suite_id=context.suite_id,
        expected_trials=context.expected_trials,
        fail_on_incomplete=not args.allow_incomplete,
    )

    ingest_script = repo_root() / "scripts" / "ingest_phase3_run_metadata.py"
    failures = 0
    for row, manifest_path, _manifest in built:
        cmd = [
            sys.executable,
            str(ingest_script),
            "--run-dir",
            str(row.run_dir),
            "--manifest-out",
            str(manifest_path),
            "--r2-prefix",
            context.r2_prefix or "",
            "--github-run-id",
            row.run_id,
        ]
        if context.logical_mode:
            cmd.extend(["--logical-mode", context.logical_mode])
        if context.suite_id:
            cmd.extend(["--suite-id", context.suite_id])
        if args.upload_r2:
            cmd.append("--upload-r2")
        if args.insert_db:
            cmd.append("--insert-db")
        if args.dry_run:
            cmd.append("--dry-run")

        print(f"ingest\t{row.run_id}\t{row.arm_id}\t{row.run_dir}", file=sys.stderr)
        proc = subprocess.run(cmd, cwd=repo_root())
        if proc.returncode != 0:
            failures += 1
            print(f"failed\t{row.run_id}\t{row.arm_id}\texit={proc.returncode}", file=sys.stderr)

    print(f"ingest_failures\t{failures}")
    return 0 if failures == 0 else 1


def write_tsv_header(values: list[str], *, enabled: bool) -> None:
    if enabled:
        write_tsv_row(values)


def clean_tsv(value: Any) -> str:
    if value is None:
        return ""
    return str(value).replace("\t", " ").replace("\n", " ")


def write_tsv_row(values: Iterable[Any]) -> None:
    print("\t".join(clean_tsv(value) for value in values))


def add_common_wave_args(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--runs", default=os.getenv("RUNS"), help="Whitespace-separated <github_run_id>:<arm_id> entries.")
    parser.add_argument("--dest", default=os.getenv("DEST", "tmp/eval-artifacts/wave"))
    parser.add_argument("--phase", default=os.getenv("PHASE"), help="Override suite phase.")
    parser.add_argument("--suite-id", default=os.getenv("SUITE_ID"))
    parser.add_argument("--artifact-prefix", default=os.getenv("ARTIFACT_PREFIX"))


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    p = sub.add_parser("list-artifacts", help="List GitHub Actions artifacts for completed eval runs.")
    p.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY"))
    p.add_argument("--runs", default=os.getenv("RUNS"))
    p.add_argument("--workflow", default=os.getenv("WORKFLOW", "phase3-arm-dispatch.yml"))
    p.add_argument("--branch", default=os.getenv("BRANCH"))
    p.add_argument("--limit", type=int, default=int(os.getenv("LIMIT", "30")))
    p.add_argument("--suite-id", default=os.getenv("SUITE_ID"))
    p.add_argument("--phase", default=os.getenv("PHASE"))
    p.add_argument("--artifact-prefix", default=os.getenv("ARTIFACT_PREFIX"))
    p.add_argument("--no-header", action="store_true")
    p.set_defaults(func=command_list_artifacts)

    p = sub.add_parser("download-wave", help="Download all artifacts for a wave of run IDs.")
    p.add_argument("--repo", default=os.getenv("GITHUB_REPOSITORY"))
    add_common_wave_args(p)
    p.add_argument("--overwrite", action="store_true", default=os.getenv("OVERWRITE", "").lower() in {"1", "true", "yes"})
    p.set_defaults(func=command_download_wave)

    p = sub.add_parser("discover-wave", help="Discover top-level Harbor run directories in downloaded artifacts.")
    add_common_wave_args(p)
    p.add_argument("--arms", default=os.getenv("ARMS"))
    p.add_argument("--run-dirs-file", default=os.getenv("RUN_DIRS_FILE", "tmp/eval_wave_run_dirs.tsv"))
    p.add_argument("--storage-mode", default=os.getenv("STORAGE_MODE"))
    p.add_argument("--expected-trials", type=int, default=env_int("EXPECTED_TRIALS"))
    p.add_argument("--allow-missing", action="store_true")
    p.set_defaults(func=command_discover_wave)

    p = sub.add_parser("manifest-wave", help="Build and validate local ingestion manifests for a discovered wave.")
    p.add_argument("--run-dirs-file", default=os.getenv("RUN_DIRS_FILE", "tmp/eval_wave_run_dirs.tsv"))
    p.add_argument("--manifest-dir", default=os.getenv("MANIFEST_DIR", "tmp/eval-ingest-manifests"))
    p.add_argument("--suite-id", default=os.getenv("SUITE_ID"))
    p.add_argument("--phase", default=os.getenv("PHASE"))
    p.add_argument("--logical-mode", default=os.getenv("LOGICAL_MODE"))
    p.add_argument("--r2-prefix", default=os.getenv("R2_PREFIX"))
    p.add_argument("--expected-trials", type=int, default=env_int("EXPECTED_TRIALS"))
    p.add_argument("--allow-incomplete", action="store_true")
    p.add_argument("--no-header", action="store_true")
    p.set_defaults(func=command_manifest_wave)

    p = sub.add_parser("ingest-wave", help="Ingest a discovered wave into R2 and/or Supabase.")
    p.add_argument("--run-dirs-file", default=os.getenv("RUN_DIRS_FILE", "tmp/eval_wave_run_dirs.tsv"))
    p.add_argument("--manifest-dir", default=os.getenv("MANIFEST_DIR", "tmp/eval-ingest-manifests"))
    p.add_argument("--suite-id", default=os.getenv("SUITE_ID"))
    p.add_argument("--phase", default=os.getenv("PHASE"))
    p.add_argument("--logical-mode", default=os.getenv("LOGICAL_MODE"))
    p.add_argument("--r2-prefix", default=os.getenv("R2_PREFIX"))
    p.add_argument("--expected-trials", type=int, default=env_int("EXPECTED_TRIALS"))
    p.add_argument("--allow-incomplete", action="store_true")
    p.add_argument("--upload-r2", action="store_true")
    p.add_argument("--insert-db", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    p.set_defaults(func=command_ingest_wave)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
