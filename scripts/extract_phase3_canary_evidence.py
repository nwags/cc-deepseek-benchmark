#!/usr/bin/env python3
from __future__ import annotations

import csv
import json
import re
import subprocess
from pathlib import Path
from statistics import mean

try:
    import yaml
except ImportError as exc:
    raise SystemExit("PyYAML is required. Run inside the project venv with `uv run python ...`.") from exc


ROOT = Path(".")
CANARY_ROOT = ROOT / "results" / "phase3" / "canary"
SUPP_ROOT = ROOT / "results" / "phase3" / "supplemental"
REPORT_ROOT = ROOT / "docs" / "reports" / "phase3"
FIG_ROOT = ROOT / "figures" / "phase3"
ARM_ROOT = ROOT / "configs" / "arms"

SUPP_ROOT.mkdir(parents=True, exist_ok=True)
REPORT_ROOT.mkdir(parents=True, exist_ok=True)
FIG_ROOT.mkdir(parents=True, exist_ok=True)


AUTH_QUOTA_PAT = re.compile(
    r"401|403|429|quota|rate_limit|rate limit|authentication|invalid_api_key|"
    r"insufficient balance|access denied|Model\.AccessDenied|permission|credits|license",
    re.I,
)
CONFIG_PAT = re.compile(
    r"model_not_found|not found|unsupported|schema|BadRequest|bad request|"
    r"invalid_request|pages parameter|stream|tool|api_base|base_url|slug",
    re.I,
)
CONTAM_PAT = re.compile(r"WebSearch|WebFetch|web_search_requests|web_fetch_requests", re.I)


def load_json(path: Path) -> dict:
    try:
        return json.loads(path.read_text())
    except Exception:
        return {}


def load_yaml(path: Path) -> dict:
    if not path.exists():
        return {}
    return yaml.safe_load(path.read_text()) or {}


def latest_run_dir(arm_dir: Path) -> Path | None:
    runs = sorted(p for p in arm_dir.iterdir() if p.is_dir() and p.name.startswith("2026-"))
    return runs[-1] if runs else None


def nested_trial_dirs(run_dir: Path) -> list[Path]:
    return sorted(
        p for p in run_dir.iterdir()
        if p.is_dir() and (p / "result.json").exists()
    )


def collect_text(run_dir: Path, max_chars: int = 120_000) -> str:
    chunks: list[str] = []
    for pat in [
        "result.json",
        "*/result.json",
        "*/exception.txt",
        "*/agent/claude-code.txt",
        "*/agent/trajectory.json",
        "job.log",
        "*/trial.log",
    ]:
        for p in run_dir.glob(pat):
            try:
                chunks.append(p.read_text(errors="replace")[:max_chars])
            except Exception:
                pass
    return "\n".join(chunks)[:max_chars]


def run_contamination_audit(run_dir: Path) -> tuple[str, str]:
    audit_script = ROOT / "scripts" / "audit_tool_usage.py"
    if not audit_script.exists():
        return "unknown", "scripts/audit_tool_usage.py not found"

    proc = subprocess.run(
        [
            "uv",
            "run",
            "python",
            str(audit_script),
            "--strict",
            "--fail-on-available",
            str(run_dir),
        ],
        text=True,
        capture_output=True,
    )
    summary = " | ".join(
        line.strip()
        for line in (proc.stdout + "\n" + proc.stderr).splitlines()
        if line.strip()
    )
    return ("clean" if proc.returncode == 0 else "failed", summary)


def observed_models(run_dir: Path) -> str:
    models: set[str] = set()
    for p in run_dir.glob("*/result.json"):
        data = load_json(p)
        usage = data.get("result", {}).get("modelUsage") or data.get("modelUsage") or {}
        if isinstance(usage, dict):
            models.update(str(k) for k in usage.keys())

    text = collect_text(run_dir)
    for m in re.findall(r'"model"\s*:\s*"([^"]+)"', text):
        if m and m != "<synthetic>":
            models.add(m)

    return ", ".join(sorted(models))


def stats_from_result(result: dict) -> dict:
    stats = result.get("stats", {})
    evals = stats.get("evals", {}) or {}

    reward = None
    exceptions: list[str] = []
    mean_metric = None

    for eval_data in evals.values():
        for metric in eval_data.get("metrics", []) or []:
            if "mean" in metric:
                mean_metric = metric["mean"]

        reward_stats = eval_data.get("reward_stats", {}).get("reward", {})
        if reward_stats:
            try:
                reward = max(float(k) for k in reward_stats.keys())
            except Exception:
                pass

        exception_stats = eval_data.get("exception_stats", {}) or {}
        exceptions.extend(exception_stats.keys())

    return {
        "n_total_trials": result.get("n_total_trials"),
        "n_completed_trials": stats.get("n_completed_trials"),
        "n_errored_trials": stats.get("n_errored_trials"),
        "cost_usd": stats.get("cost_usd", 0) or 0,
        "input_tokens": stats.get("n_input_tokens", 0) or 0,
        "cache_tokens": stats.get("n_cache_tokens", 0) or 0,
        "output_tokens": stats.get("n_output_tokens", 0) or 0,
        "mean": mean_metric,
        "reward": reward,
        "exceptions": ", ".join(sorted(set(exceptions))),
    }


def runtime_seconds(result: dict) -> float | None:
    from datetime import datetime

    started = result.get("started_at")
    finished = result.get("finished_at")
    if not started or not finished:
        return None

    try:
        s = datetime.fromisoformat(started.replace("Z", "+00:00"))
        f = datetime.fromisoformat(finished.replace("Z", "+00:00"))
        return round((f - s).total_seconds(), 3)
    except Exception:
        return None


def classify(row: dict, text: str, contamination: str) -> tuple[str, str]:
    reward = row.get("reward")
    n_errors = row.get("n_errored_trials") or 0
    exceptions = row.get("exceptions") or ""

    if contamination == "failed":
        return "FAIL-CONTAMINATION", "Forbidden web/tool exposure or available-tool contamination detected"

    if n_errors == 0 and reward == 1.0:
        return "PASS", "Canary passed"

    if AUTH_QUOTA_PAT.search(text):
        return "FAIL-AUTH/QUOTA", "Provider auth, access, billing, quota, or model entitlement issue"

    if CONFIG_PAT.search(text + "\n" + exceptions):
        return "FAIL-CONFIG", "Router/provider/model/tool/schema configuration issue"

    if n_errors == 0 and reward == 0.0:
        return "FAIL-BENCH", "Model ran without Harbor exception but failed the task"

    if n_errors:
        return "FAIL-CONFIG", "Harbor/agent exception without clear auth/quota signature"

    return "UNKNOWN", "Needs manual review"


def smoke_readiness(classification: str) -> str:
    if classification == "PASS":
        return "ready-for-funded-smoke"
    if classification == "FAIL-BENCH":
        return "route-good-but-quality-risk"
    if classification == "FAIL-AUTH/QUOTA":
        return "blocked-provider-access"
    if classification == "FAIL-CONTAMINATION":
        return "blocked-contamination"
    if classification == "FAIL-CONFIG":
        return "blocked-config"
    return "manual-review"


def build_ledger() -> list[dict]:
    rows: list[dict] = []

    for arm_dir in sorted(CANARY_ROOT.glob("arm-*")):
        arm_id = arm_dir.name.removeprefix("arm-")
        run_dir = latest_run_dir(arm_dir)
        if run_dir is None:
            continue

        result = load_json(run_dir / "result.json")
        arm_cfg = load_yaml(ARM_ROOT / f"{arm_id}.yaml")
        base_stats = stats_from_result(result)
        text = collect_text(run_dir)
        contamination, audit_summary = run_contamination_audit(run_dir)
        classification, issue = classify(base_stats, text, contamination)

        row = {
            "arm_id": arm_id,
            "provider": arm_cfg.get("provider", ""),
            "backend_model": arm_cfg.get("backend_model", ""),
            "latest_result_path": str(run_dir),
            "classification": classification,
            "reward": base_stats["reward"],
            "mean": base_stats["mean"],
            "exceptions": base_stats["exceptions"],
            "cost_usd": base_stats["cost_usd"],
            "input_tokens": base_stats["input_tokens"],
            "cache_tokens": base_stats["cache_tokens"],
            "output_tokens": base_stats["output_tokens"],
            "runtime_seconds": runtime_seconds(result),
            "contamination_audit": contamination,
            "contamination_audit_summary": audit_summary,
            "observed_model": observed_models(run_dir),
            "issue_category": issue,
            "smoke_readiness": smoke_readiness(classification),
            "notes": "",
        }
        rows.append(row)

    return rows


def write_csv_json(rows: list[dict]) -> None:
    csv_path = SUPP_ROOT / "canary_ledger.csv"
    json_path = SUPP_ROOT / "canary_ledger.json"

    fields = [
        "arm_id",
        "provider",
        "backend_model",
        "latest_result_path",
        "classification",
        "reward",
        "mean",
        "exceptions",
        "cost_usd",
        "input_tokens",
        "cache_tokens",
        "output_tokens",
        "runtime_seconds",
        "contamination_audit",
        "observed_model",
        "issue_category",
        "smoke_readiness",
        "notes",
        "contamination_audit_summary",
    ]

    with csv_path.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for row in rows:
            w.writerow({k: row.get(k, "") for k in fields})

    json_path.write_text(json.dumps(rows, indent=2, sort_keys=True) + "\n")


def cost_forecasts(rows: list[dict]) -> None:
    passed = [r for r in rows if r["classification"] == "PASS" and float(r["cost_usd"] or 0) > 0]
    ready = [r for r in rows if r["smoke_readiness"] == "ready-for-funded-smoke"]

    forecast_rows = []
    for r in ready:
        c = float(r["cost_usd"] or 0)
        forecast_rows.append({
            "arm_id": r["arm_id"],
            "canary_cost_usd": c,
            "smoke_5_tasks_1_attempt_est_usd": c * 5,
            "smoke_5_tasks_1_attempt_reserve_2x_usd": c * 5 * 2,
            "full_20_tasks_3_attempts_est_usd": c * 60,
            "full_20_tasks_3_attempts_reserve_1_5x_usd": c * 60 * 1.5,
            "expanded_25_tasks_3_attempts_est_usd": c * 75,
            "expanded_25_tasks_3_attempts_reserve_1_5x_usd": c * 75 * 1.5,
        })

    out = SUPP_ROOT / "phase3_cost_forecast_canary_scaled.csv"
    fields = [
        "arm_id",
        "canary_cost_usd",
        "smoke_5_tasks_1_attempt_est_usd",
        "smoke_5_tasks_1_attempt_reserve_2x_usd",
        "full_20_tasks_3_attempts_est_usd",
        "full_20_tasks_3_attempts_reserve_1_5x_usd",
        "expanded_25_tasks_3_attempts_est_usd",
        "expanded_25_tasks_3_attempts_reserve_1_5x_usd",
    ]

    with out.open("w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, lineterminator="\n")
        w.writeheader()
        for row in forecast_rows:
            w.writerow(row)

    summary = {
        "method": "canary_cost_scaled_by_trial_count; use only as rough order-of-magnitude until smoke results exist",
        "n_ready_arms": len(ready),
        "n_pass_with_nonzero_cost": len(passed),
        "mean_pass_canary_cost_usd": mean([float(r["cost_usd"]) for r in passed]) if passed else 0,
        "total_smoke_5_tasks_1_attempt_est_usd": sum(r["smoke_5_tasks_1_attempt_est_usd"] for r in forecast_rows),
        "total_smoke_5_tasks_1_attempt_reserve_2x_usd": sum(r["smoke_5_tasks_1_attempt_reserve_2x_usd"] for r in forecast_rows),
        "total_full_20_tasks_3_attempts_est_usd": sum(r["full_20_tasks_3_attempts_est_usd"] for r in forecast_rows),
        "total_full_20_tasks_3_attempts_reserve_1_5x_usd": sum(r["full_20_tasks_3_attempts_reserve_1_5x_usd"] for r in forecast_rows),
        "total_expanded_25_tasks_3_attempts_est_usd": sum(r["expanded_25_tasks_3_attempts_est_usd"] for r in forecast_rows),
        "total_expanded_25_tasks_3_attempts_reserve_1_5x_usd": sum(r["expanded_25_tasks_3_attempts_reserve_1_5x_usd"] for r in forecast_rows),
    }
    (SUPP_ROOT / "phase3_cost_forecast_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True) + "\n"
    )


def write_report(rows: list[dict]) -> None:
    counts: dict[str, int] = {}
    for r in rows:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1

    ready = [r for r in rows if r["smoke_readiness"] == "ready-for-funded-smoke"]
    blocked = [r for r in rows if r["smoke_readiness"] != "ready-for-funded-smoke"]

    def md_table(items: list[dict]) -> str:
        lines = [
            "| Arm | Backend | Class | Reward | Cost | Tokens in/cache/out | Runtime | Audit | Result |",
            "|---|---:|---:|---:|---:|---:|---:|---:|---|",
        ]
        for r in items:
            lines.append(
                f"| `{r['arm_id']}` | `{r['backend_model']}` | `{r['classification']}` | "
                f"{r['reward']} | ${float(r['cost_usd'] or 0):.6f} | "
                f"{r['input_tokens']}/{r['cache_tokens']}/{r['output_tokens']} | "
                f"{r['runtime_seconds']}s | {r['contamination_audit']} | "
                f"`{r['latest_result_path']}` |"
            )
        return "\n".join(lines)

    summary_lines = [
        "# Phase 3 Canary Evidence Ledger",
        "",
        "This report is generated by `scripts/extract_phase3_canary_evidence.py`.",
        "",
        "## Executive summary",
        "",
        "- Phase 3 is now a router-mediated, multi-provider Claude Code benchmark harness.",
        "- Canary results are separated from smoke/full-sweep results under `results/phase3/canary`.",
        "- The canary layer is used to classify routing/config/auth/contamination readiness before paid smoke runs.",
        "- Cost estimates below are canary-scaled rough-order estimates, not final budget numbers.",
        "",
        "## Classification counts",
        "",
    ]

    for key in sorted(counts):
        summary_lines.append(f"- `{key}`: {counts[key]}")

    summary_lines.extend([
        "",
        "## Ready for funded smoke",
        "",
        md_table(ready) if ready else "_No arms currently classified ready._",
        "",
        "## Blocked or manual-review canaries",
        "",
        md_table(blocked) if blocked else "_No blocked arms in latest canary selection._",
        "",
        "## Notes for sponsor briefing",
        "",
        "- The first slide should lead with impact: multi-provider routing is operational, but full-sweep cost should not be approved until staged smoke runs establish provider-specific cost behavior.",
        "- Benchmark-contamination controls should remain visible in the material: `WebSearch`, `WebFetch`, `EnterPlanMode`, `ExitPlanMode`, and `AskUserQuestion` are denied on router arms where applicable.",
        "- Provider-specific issues should be framed as infrastructure learnings, not model-quality failures, unless the model actually ran and failed the task.",
        "",
        "## Generated support files",
        "",
        "- `results/phase3/supplemental/canary_ledger.csv`",
        "- `results/phase3/supplemental/canary_ledger.json`",
        "- `results/phase3/supplemental/phase3_cost_forecast_canary_scaled.csv`",
        "- `results/phase3/supplemental/phase3_cost_forecast_summary.json`",
        "- `figures/phase3/canary_cost_by_arm.png`",
        "- `figures/phase3/canary_status_counts.png`",
        "",
    ])

    (REPORT_ROOT / "PHASE3_CANARY_EVIDENCE.md").write_text("\n".join(summary_lines))


def write_figures(rows: list[dict]) -> None:
    try:
        import matplotlib.pyplot as plt
    except Exception:
        print("matplotlib unavailable; skipping figures")
        return

    cost_rows = [r for r in rows if float(r["cost_usd"] or 0) > 0]
    cost_rows = sorted(cost_rows, key=lambda r: float(r["cost_usd"] or 0), reverse=True)

    if cost_rows:
        labels = [r["arm_id"].replace("router-", "") for r in cost_rows]
        values = [float(r["cost_usd"] or 0) for r in cost_rows]

        plt.figure(figsize=(12, max(4, len(labels) * 0.35)))
        plt.barh(labels, values)
        plt.xlabel("Canary cost, USD")
        plt.title("Phase 3 Canary Cost by Arm")
        plt.gca().invert_yaxis()
        plt.tight_layout()
        plt.savefig(FIG_ROOT / "canary_cost_by_arm.png", dpi=180)
        plt.close()

    counts: dict[str, int] = {}
    for r in rows:
        counts[r["classification"]] = counts.get(r["classification"], 0) + 1

    if counts:
        labels = list(sorted(counts))
        values = [counts[k] for k in labels]

        plt.figure(figsize=(8, 4))
        plt.bar(labels, values)
        plt.ylabel("Arm count")
        plt.title("Phase 3 Canary Classification Counts")
        plt.xticks(rotation=30, ha="right")
        plt.tight_layout()
        plt.savefig(FIG_ROOT / "canary_status_counts.png", dpi=180)
        plt.close()


def main() -> None:
    if not CANARY_ROOT.exists():
        raise SystemExit(f"Missing canary root: {CANARY_ROOT}")

    rows = build_ledger()
    write_csv_json(rows)
    cost_forecasts(rows)
    write_report(rows)
    write_figures(rows)

    print(f"wrote {SUPP_ROOT / 'canary_ledger.csv'}")
    print(f"wrote {SUPP_ROOT / 'canary_ledger.json'}")
    print(f"wrote {REPORT_ROOT / 'PHASE3_CANARY_EVIDENCE.md'}")
    print(f"wrote figures under {FIG_ROOT}")


if __name__ == "__main__":
    main()
