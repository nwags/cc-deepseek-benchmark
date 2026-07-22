from __future__ import annotations

import csv
import statistics
from collections import defaultdict
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
DATE = "20260716"

CROSS_PHASE = ROOT / "results/phase3/reporting/cross_phase_adjusted_comparison_20260714.tsv"
PHASE3_SPONSOR = ROOT / "results/phase3/reporting/phase3_sponsor_summary_table_20260713.tsv"
PHASE3_COST = ROOT / "results/phase3/reporting/phase3_arm_cost_coverage_20260712.tsv"
PHASE3_TRIALS = ROOT / "results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv"
PHASE3_QUAL = ROOT / "results/phase3/reporting/phase3_arm_qualitative_summary_20260712.tsv"
PHASE3_TOKEN = ROOT / "results/phase3/reporting/phase3_token_outcome_breakdown_20260713.tsv"
PHASE3_TASK_QUAL = ROOT / "results/phase3/reporting/phase3_task_qualitative_summary_20260712.tsv"
PHASE3_ARM_TASK = ROOT / "results/phase3/reporting/phase3_arm_task_qualitative_matrix_20260712.tsv"

TAXONOMY_OUT = ROOT / "configs/tasks/phase3_task_taxonomy.tsv"
ROUTER_TSV = ROOT / f"results/phase3/reporting/router_effect_comparison_{DATE}.tsv"
ROUTER_MD = ROOT / f"docs/reports/phase3/PHASE3_ROUTER_EFFECT_COMPARISON_{DATE}.md"
TASK_FAMILY_MATRIX = ROOT / f"results/phase3/reporting/phase3_task_family_arm_matrix_{DATE}.tsv"
ARM_BEHAVIOR = ROOT / f"results/phase3/reporting/phase3_arm_behavior_profile_{DATE}.tsv"
COMPREHENSIVE_MD = ROOT / f"docs/reports/phase3/PHASE3_COMPREHENSIVE_ANALYSIS_{DATE}.md"


def read_table(path: Path) -> list[dict[str, str]]:
    delimiter = "\t" if path.suffix == ".tsv" else ","
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_tsv(path: Path, rows: list[dict[str, Any]], fieldnames: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({key: row.get(key, "") for key in fieldnames})


def f(row: dict[str, Any], key: str, default: float = 0.0) -> float:
    value = row.get(key, "")
    if value in ("", None):
        return default
    try:
        return float(value)
    except ValueError:
        return default


def i(row: dict[str, Any], key: str, default: int = 0) -> int:
    return int(round(f(row, key, float(default))))


def fmt_pct(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"{100.0 * value:.1f}%"


def fmt_money(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"${value:,.2f}"


def fmt_float(value: float | None, places: int = 2) -> str:
    if value is None:
        return "n/a"
    return f"{value:.{places}f}"


def task_slug(task_id: str) -> str:
    return task_id.split(":", 1)[-1]


def classify_task(slug: str) -> tuple[str, str, str]:
    s = slug.lower()

    if "cython" in s or "modernize" in s:
        return ("build-packaging", "Build, packaging, and dependency modernization", "build or dependency stack work")
    if "async" in s or "cancel" in s:
        return ("concurrency-async", "Concurrency and async control flow", "async cancellation/control-flow task")
    if "nginx" in s or "webserver" in s or "web" in s or ("request" in s and "logging" in s):
        return ("web-networking", "Web, networking, and service configuration", "web/service logging or configuration task")
    if "memory" in s or "heap" in s or "rust" in s or "polyglot" in s:
        return ("systems-low-level", "Systems, low-level, and polyglot implementation", "low-level systems or interop task")
    if "vulnerability" in s or "leak" in s or "openssl" in s or "password" in s or "cert" in s:
        return ("security-crypto", "Security, cryptography, and recovery", "security/crypto/recovery task")
    if "sqlite" in s or "db" in s or "database" in s or ("query" in s and "optimiz" in s):
        return ("database-storage", "Database and storage operations", "database/query optimization or storage task")

    if "portfolio" in s:
        return ("optimization-finance", "Optimization and quantitative planning", "portfolio/numerical optimization task")
    if "data" in s or "merger" in s:
        return ("data-processing", "Data processing and integration", "multi-source data processing task")
    if "scheme" in s or "eval" in s and "relu" not in s:
        return ("language-implementation", "Language implementation and interpreters", "interpreter/language task")
    if "torch" in s or "mteb" in s or "inference" in s or "model-extraction" in s or "relu" in s or "llm" in s:
        return ("ml-scientific", "ML, scientific computing, and retrieval", "ML/scientific/retrieval task")

    return ("uncategorized-review", "Uncategorized, needs review", "heuristic did not classify task")


def visible_tokens(row: dict[str, Any]) -> float:
    return f(row, "input_tokens") + f(row, "cache_tokens") + f(row, "output_tokens")


def median(values: list[float]) -> float:
    clean = [value for value in values if value is not None]
    if not clean:
        return 0.0
    return float(statistics.median(clean))


def ratio(num: float, den: float) -> float | None:
    if num <= 0 or den <= 0:
        return None
    return num / den


def is_success(row: dict[str, Any]) -> bool:
    return str(row.get("reward", "")).strip() in {"1", "1.0", "True", "true"}


def behavior_tags(row: dict[str, Any], qual: dict[str, str], global_success_token_median: float) -> str:
    tags: list[str] = []
    pass_rate = f(row, "pass_rate")
    adjusted = f(row, "adjusted_cost_usd")
    cost_per_clean = f(row, "cost_per_clean_success_usd")
    unclean_share = f(row, "unclean_spend_share")
    exceptions = i(qual, "exception_count")
    suspect_noop = i(qual, "suspect_noop_count")

    med_success_tokens = f(row, "median_success_visible_tokens")

    if pass_rate >= 0.70:
        tags.append("high-pass-rate")
    elif pass_rate >= 0.60:
        tags.append("mid-pass-rate")
    else:
        tags.append("lower-pass-rate")

    if cost_per_clean and cost_per_clean <= 1.50:
        tags.append("cost-efficient-clean-success")
    elif cost_per_clean >= 4.00:
        tags.append("expensive-clean-success")

    if adjusted >= 100:
        tags.append("high-total-cost")

    if exceptions >= 10:
        tags.append("exception-heavy")

    if unclean_share >= 0.50:
        tags.append("high-unclean-spend")

    if suspect_noop > 0:
        tags.append("suspect-noop-present")

    if global_success_token_median > 0 and med_success_tokens > 0:
        if med_success_tokens <= 0.60 * global_success_token_median:
            tags.append("lower-token-success-pattern")
        elif med_success_tokens >= 1.60 * global_success_token_median:
            tags.append("higher-token-success-pattern")
        else:
            tags.append("middle-token-success-pattern")

    return ";".join(tags)


def interpretation(direct: dict[str, str], router: dict[str, str]) -> str:
    dp = f(direct, "pass_rate")
    rp = f(router, "pass_rate")
    dc = f(direct, "adjusted_cost_usd")
    rc = f(router, "adjusted_cost_usd")
    du = f(direct, "unclean_spend_share")
    ru = f(router, "unclean_spend_share")

    bits: list[str] = []
    delta_pp = (rp - dp) * 100.0
    if delta_pp >= 5:
        bits.append("router-associated pass rate higher")
    elif delta_pp <= -5:
        bits.append("router-associated pass rate lower")
    else:
        bits.append("pass rate broadly similar")

    if dc and rc:
        cr = rc / dc
        if cr >= 1.5:
            bits.append("router run materially more expensive")
        elif cr <= 0.75:
            bits.append("router run materially cheaper")
        else:
            bits.append("adjusted cost broadly similar")
    else:
        bits.append("cost ratio unavailable")

    if ru - du >= 0.10:
        bits.append("router run had higher unclean spend share")
    elif du - ru >= 0.10:
        bits.append("router run had lower unclean spend share")

    return "; ".join(bits)


def main() -> None:
    cross = read_table(CROSS_PHASE)
    sponsor = read_table(PHASE3_SPONSOR)
    cost = read_table(PHASE3_COST)
    trials = read_table(PHASE3_TRIALS)
    qual = read_table(PHASE3_QUAL)
    token = read_table(PHASE3_TOKEN)
    task_qual = read_table(PHASE3_TASK_QUAL)
    arm_task = read_table(PHASE3_ARM_TASK)

    cross_by = {(row["phase"], row["arm_id"]): row for row in cross}
    sponsor_by = {row["arm_id"]: row for row in sponsor}
    cost_by = {row["arm_id"]: row for row in cost}
    qual_by = {row["arm_id"]: row for row in qual}
    token_by = {row["arm_id"]: row for row in token}

    phase3_runtime_values_by_arm: dict[str, list[float]] = defaultdict(list)
    for trial in trials:
        runtime = f(trial, "runtime_seconds")
        if runtime > 0:
            phase3_runtime_values_by_arm[trial["arm_id"]].append(runtime)
    phase3_median_runtime_by_arm = {
        arm_id: median(values)
        for arm_id, values in phase3_runtime_values_by_arm.items()
    }

    unique_tasks = sorted({row["task_id"] for row in trials})
    taxonomy_rows: list[dict[str, Any]] = []
    taxonomy_by_task: dict[str, dict[str, str]] = {}
    for task_id in unique_tasks:
        slug = task_slug(task_id)
        family, label, rationale = classify_task(slug)
        tax = {
            "task_id": task_id,
            "task_slug": slug,
            "task_family": family,
            "task_family_label": label,
            "rationale": rationale,
            "taxonomy_status": "heuristic_review"
        }
        taxonomy_rows.append(tax)
        taxonomy_by_task[task_id] = tax

    write_tsv(
        TAXONOMY_OUT,
        taxonomy_rows,
        ["task_id", "task_slug", "task_family", "task_family_label", "rationale", "taxonomy_status"],
    )

    router_pairs = [
        ("Anthropic Sonnet", "phase1", "arm-a-anthropic", "phase3", "router-anthropic-sonnet", "Phase 1 direct baseline vs Phase 3 LiteLLM router."),
        ("Anthropic Sonnet", "phase2", "arm-anthropic-sonnet", "phase3", "router-anthropic-sonnet", "Phase 2 direct Sonnet vs Phase 3 LiteLLM router."),
        ("DeepSeek Pro", "phase1", "arm-b-deepseek-pro", "phase3", "router-deepseek-pro", "Phase 1 direct DeepSeek endpoint vs Phase 3 LiteLLM router."),
        ("DeepSeek Pro", "phase2", "arm-deepseek-pro", "phase3", "router-deepseek-pro", "Phase 2 direct DeepSeek endpoint vs Phase 3 LiteLLM router."),
        ("DeepSeek Flash", "phase1", "arm-c-deepseek-flash", "phase3", "router-deepseek-flash", "Phase 1 direct DeepSeek endpoint vs Phase 3 LiteLLM router."),
        ("DeepSeek Flash", "phase2", "arm-deepseek-flash", "phase3", "router-deepseek-flash", "Phase 2 direct DeepSeek endpoint vs Phase 3 LiteLLM router."),
        ("Anthropic Opus", "phase2", "arm-anthropic-opus", "phase3", "router-anthropic-opus", "Phase 2 direct Opus vs Phase 3 LiteLLM router."),
        ("Anthropic Haiku", "phase2", "arm-anthropic-haiku", "phase3", "router-anthropic-haiku-sanitized", "Phase 2 direct Haiku vs Phase 3 router plus sanitizer path."),
    ]

    router_rows: list[dict[str, Any]] = []
    for family, direct_phase, direct_arm, router_phase, router_arm, notes in router_pairs:
        direct = cross_by.get((direct_phase, direct_arm))
        router = cross_by.get((router_phase, router_arm))
        q = qual_by.get(router_arm, {})
        if not direct or not router:
            router_rows.append({
                "model_family": family,
                "direct_phase": direct_phase,
                "direct_arm_id": direct_arm,
                "router_phase": router_phase,
                "router_arm_id": router_arm,
                "comparison_status": "missing_input_row",
                "notes": notes,
            })
            continue

        direct_cost = f(direct, "adjusted_cost_usd")
        router_cost = f(router, "adjusted_cost_usd")
        direct_pass = f(direct, "pass_rate")
        router_pass = f(router, "pass_rate")
        direct_clean_cost = f(direct, "cost_per_clean_success_usd")
        router_clean_cost = f(router, "cost_per_clean_success_usd")
        direct_clock = f(direct, "median_wall_clock_seconds")
        router_clock = f(router, "median_wall_clock_seconds")
        if router_phase == "phase3" and router_clock <= 0:
            router_clock = phase3_median_runtime_by_arm.get(router_arm, 0.0)

        router_rows.append({
            "model_family": family,
            "direct_phase": direct_phase,
            "direct_arm_id": direct_arm,
            "direct_backend_model": direct.get("backend_model", ""),
            "direct_routing_path": direct.get("routing_path", ""),
            "router_phase": router_phase,
            "router_arm_id": router_arm,
            "router_backend_model": router.get("backend_model", ""),
            "router_routing_path": router.get("routing_path", ""),
            "direct_success_count": i(direct, "success_count"),
            "router_success_count": i(router, "success_count"),
            "delta_success_count": i(router, "success_count") - i(direct, "success_count"),
            "direct_pass_rate": direct_pass,
            "router_pass_rate": router_pass,
            "delta_pass_rate_pct_points": (router_pass - direct_pass) * 100.0,
            "direct_adjusted_cost_usd": direct_cost,
            "router_adjusted_cost_usd": router_cost,
            "router_vs_direct_cost_ratio": ratio(router_cost, direct_cost),
            "direct_cost_per_clean_success_usd": direct_clean_cost,
            "router_cost_per_clean_success_usd": router_clean_cost,
            "router_vs_direct_cost_per_clean_success_ratio": ratio(router_clean_cost, direct_clean_cost),
            "direct_median_wall_clock_seconds": direct_clock,
            "router_median_wall_clock_seconds": router_clock,
            "router_vs_direct_wall_clock_ratio": ratio(router_clock, direct_clock),
            "direct_unclean_spend_share": f(direct, "unclean_spend_share"),
            "router_unclean_spend_share": f(router, "unclean_spend_share"),
            "router_exception_count": i(q, "exception_count"),
            "router_normal_failure_count": i(q, "normal_failure_count"),
            "router_suspect_noop_count": i(q, "suspect_noop_count"),
            "direct_cost_confidence": direct.get("cost_confidence", ""),
            "router_cost_confidence": router.get("cost_confidence", ""),
            "comparison_status": "ok",
            "interpretation": interpretation(direct, router),
            "notes": notes,
        })

    router_fields = [
        "model_family", "direct_phase", "direct_arm_id", "direct_backend_model", "direct_routing_path",
        "router_phase", "router_arm_id", "router_backend_model", "router_routing_path",
        "direct_success_count", "router_success_count", "delta_success_count",
        "direct_pass_rate", "router_pass_rate", "delta_pass_rate_pct_points",
        "direct_adjusted_cost_usd", "router_adjusted_cost_usd", "router_vs_direct_cost_ratio",
        "direct_cost_per_clean_success_usd", "router_cost_per_clean_success_usd",
        "router_vs_direct_cost_per_clean_success_ratio",
        "direct_median_wall_clock_seconds", "router_median_wall_clock_seconds",
        "router_vs_direct_wall_clock_ratio",
        "direct_unclean_spend_share", "router_unclean_spend_share",
        "router_exception_count", "router_normal_failure_count", "router_suspect_noop_count",
        "direct_cost_confidence", "router_cost_confidence",
        "comparison_status", "interpretation", "notes",
    ]
    write_tsv(ROUTER_TSV, router_rows, router_fields)

    trial_groups: dict[tuple[str, str], list[dict[str, str]]] = defaultdict(list)
    for row in trials:
        tax = taxonomy_by_task.get(row["task_id"])
        family = tax["task_family"] if tax else "uncategorized-review"
        trial_groups[(row["arm_id"], family)].append(row)

    matrix_rows: list[dict[str, Any]] = []
    for (arm_id, family), rows in sorted(trial_groups.items()):
        successes = sum(1 for row in rows if is_success(row))
        adjusted_cost = sum(f(row, "adjusted_cost_usd") for row in rows)
        unclean_cost = sum(f(row, "adjusted_cost_usd") for row in rows if row.get("outcome_bucket") != "clean_success")
        token_values = [visible_tokens(row) for row in rows]
        success_token_values = [visible_tokens(row) for row in rows if is_success(row)]
        failure_token_values = [visible_tokens(row) for row in rows if not is_success(row)]
        runtimes = [f(row, "runtime_seconds") for row in rows if f(row, "runtime_seconds") > 0]
        exceptions = sum(1 for row in rows if row.get("exception_type"))
        missing = sum(1 for row in rows if row.get("cost_source") != "recorded_artifact")
        unresolved = sum(1 for row in rows if row.get("cost_confidence") == "unresolved")

        label = next((tax["task_family_label"] for tax in taxonomy_rows if tax["task_family"] == family), family)

        matrix_rows.append({
            "arm_id": arm_id,
            "provider": sponsor_by.get(arm_id, {}).get("provider", ""),
            "backend_model": sponsor_by.get(arm_id, {}).get("backend_model", ""),
            "task_family": family,
            "task_family_label": label,
            "trial_count": len(rows),
            "success_count": successes,
            "pass_rate": successes / len(rows) if rows else 0,
            "exception_count": exceptions,
            "missing_or_reconstructed_cost_count": missing,
            "unresolved_cost_count": unresolved,
            "adjusted_cost_usd": adjusted_cost,
            "unclean_adjusted_cost_usd": unclean_cost,
            "unclean_adjusted_cost_share": unclean_cost / adjusted_cost if adjusted_cost else 0,
            "cost_per_success_usd": adjusted_cost / successes if successes else "",
            "visible_token_sum": sum(token_values),
            "median_visible_tokens": median(token_values),
            "median_success_visible_tokens": median(success_token_values),
            "median_failure_visible_tokens": median(failure_token_values),
            "median_runtime_seconds": median(runtimes),
        })

    matrix_fields = [
        "arm_id", "provider", "backend_model", "task_family", "task_family_label",
        "trial_count", "success_count", "pass_rate", "exception_count",
        "missing_or_reconstructed_cost_count", "unresolved_cost_count",
        "adjusted_cost_usd", "unclean_adjusted_cost_usd", "unclean_adjusted_cost_share",
        "cost_per_success_usd", "visible_token_sum", "median_visible_tokens",
        "median_success_visible_tokens", "median_failure_visible_tokens", "median_runtime_seconds",
    ]
    write_tsv(TASK_FAMILY_MATRIX, matrix_rows, matrix_fields)

    all_success_visible = [visible_tokens(row) for row in trials if is_success(row) and visible_tokens(row) > 0]
    global_success_token_median = median(all_success_visible)

    trials_by_arm: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in trials:
        trials_by_arm[row["arm_id"]].append(row)

    behavior_rows: list[dict[str, Any]] = []
    for arm_id, row in sorted(sponsor_by.items()):
        q = qual_by.get(arm_id, {})
        c = cost_by.get(arm_id, {})
        t = token_by.get(arm_id, {})
        arm_trials = trials_by_arm.get(arm_id, [])
        success_tokens = [visible_tokens(trial) for trial in arm_trials if is_success(trial)]
        failure_tokens = [visible_tokens(trial) for trial in arm_trials if not is_success(trial)]
        all_tokens = [visible_tokens(trial) for trial in arm_trials]
        enriched = dict(row)
        enriched["median_success_visible_tokens"] = median(success_tokens)

        behavior_rows.append({
            "arm_id": arm_id,
            "provider": row.get("provider", ""),
            "backend_model": row.get("backend_model", ""),
            "success_count": i(row, "success_count"),
            "trial_count": i(row, "trial_count"),
            "pass_rate": f(row, "pass_rate"),
            "adjusted_cost_usd": f(row, "adjusted_cost_usd"),
            "cost_per_clean_success_usd": f(row, "cost_per_clean_success_usd"),
            "failure_incomplete_spend_share": f(row, "failure_incomplete_spend_share"),
            "unclean_spend_share": f(row, "unclean_spend_share"),
            "failure_incomplete_token_share": f(row, "failure_incomplete_token_share"),
            "unclean_token_share": f(row, "unclean_token_share"),
            "exception_count": i(q, "exception_count"),
            "normal_failure_count": i(q, "normal_failure_count"),
            "suspect_noop_count": i(q, "suspect_noop_count"),
            "missing_cost_count": i(q, "missing_cost_count"),
            "unresolved_cost_count": i(row, "unresolved_cost_count"),
            "total_visible_tokens_from_trials": sum(all_tokens),
            "median_visible_tokens_per_attempt": median(all_tokens),
            "median_success_visible_tokens": median(success_tokens),
            "median_failure_visible_tokens": median(failure_tokens),
            "existing_total_tokens_metric": f(t, "total_tokens"),
            "cost_confidence": row.get("cost_confidence", ""),
            "behavior_tags": behavior_tags(enriched, q, global_success_token_median),
        })

    behavior_fields = [
        "arm_id", "provider", "backend_model", "success_count", "trial_count", "pass_rate",
        "adjusted_cost_usd", "cost_per_clean_success_usd",
        "failure_incomplete_spend_share", "unclean_spend_share",
        "failure_incomplete_token_share", "unclean_token_share",
        "exception_count", "normal_failure_count", "suspect_noop_count",
        "missing_cost_count", "unresolved_cost_count",
        "total_visible_tokens_from_trials", "median_visible_tokens_per_attempt",
        "median_success_visible_tokens", "median_failure_visible_tokens",
        "existing_total_tokens_metric", "cost_confidence", "behavior_tags",
    ]
    write_tsv(ARM_BEHAVIOR, behavior_rows, behavior_fields)

    ok_router = [row for row in router_rows if row.get("comparison_status") == "ok"]
    phase3_sorted = sorted(sponsor, key=lambda row: f(row, "pass_rate"), reverse=True)
    efficient_sorted = sorted(sponsor, key=lambda row: f(row, "cost_per_clean_success_usd") or 999999)
    wastage_sorted = sorted(sponsor, key=lambda row: f(row, "unclean_spend_share"), reverse=True)

    family_summary: dict[str, dict[str, Any]] = {}
    for row in matrix_rows:
        fam = row["task_family"]
        bucket = family_summary.setdefault(fam, {
            "trial_count": 0,
            "success_count": 0,
            "adjusted_cost_usd": 0.0,
            "unclean_adjusted_cost_usd": 0.0,
            "task_family_label": row["task_family_label"],
        })
        bucket["trial_count"] += int(row["trial_count"])
        bucket["success_count"] += int(row["success_count"])
        bucket["adjusted_cost_usd"] += float(row["adjusted_cost_usd"])
        bucket["unclean_adjusted_cost_usd"] += float(row["unclean_adjusted_cost_usd"])

    family_summary_rows = []
    for fam, row in family_summary.items():
        trials_count = row["trial_count"]
        successes = row["success_count"]
        adjusted = row["adjusted_cost_usd"]
        unclean = row["unclean_adjusted_cost_usd"]
        family_summary_rows.append({
            "task_family": fam,
            "label": row["task_family_label"],
            "trial_count": trials_count,
            "success_count": successes,
            "pass_rate": successes / trials_count if trials_count else 0,
            "adjusted_cost_usd": adjusted,
            "unclean_share": unclean / adjusted if adjusted else 0,
        })
    family_summary_rows.sort(key=lambda row: row["pass_rate"], reverse=True)

    router_lines = [
        f"# Phase 3 router-associated comparison ({DATE})",
        "",
        "## Scope",
        "",
        "This report compares matched model families that have direct Claude Code runs in Phase 1 and/or Phase 2 and LiteLLM-router runs in Phase 3.",
        "",
        "This is an observational comparison, not causal proof. Routing path changed along with date, provider-side model revisions, runner setup, invalid-run handling, cost accounting, and in one case an Anthropic sanitizer path.",
        "",
        "## Matched comparisons",
        "",
        "| Model family | Direct baseline | Router arm | Pass delta | Cost ratio | Clean-success cost ratio | Runtime ratio | Interpretation |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]

    for row in ok_router:
        router_lines.append(
            "| {family} | {direct} {ds}/{dt} | {router} {rs}/{rt} | {dpp} pp | {cr} | {ccr} | {wr} | {interp} |".format(
                family=row["model_family"],
                direct=row["direct_phase"],
                ds=row["direct_success_count"],
                dt=60,
                router=row["router_arm_id"],
                rs=row["router_success_count"],
                rt=60,
                dpp=fmt_float(row["delta_pass_rate_pct_points"], 1),
                cr=fmt_float(row["router_vs_direct_cost_ratio"], 2),
                ccr=fmt_float(row["router_vs_direct_cost_per_clean_success_ratio"], 2),
                wr=fmt_float(row["router_vs_direct_wall_clock_ratio"], 2),
                interp=row["interpretation"],
            )
        )

    router_lines.extend([
        "",
        "## Notes",
        "",
        "- Cost ratios use adjusted known cost where available.",
        "- Runtime ratios use median wall-clock seconds when both sides are available.",
        "- For Phase 3 router arms, median runtime is computed from trial-level runtime fields because the cross-phase adjusted summary does not carry router median wall-clock values.",
        "- The Haiku comparison is especially confounded because the Phase 3 arm is the sanitized router path.",
        f"- Source table: results/phase3/reporting/router_effect_comparison_{DATE}.tsv",
        "",
    ])
    ROUTER_MD.parent.mkdir(parents=True, exist_ok=True)
    ROUTER_MD.write_text("\n".join(line.rstrip() for line in router_lines).rstrip() + "\n")

    total_trials = sum(i(row, "trial_count") for row in sponsor)
    total_success = sum(i(row, "success_count") for row in sponsor)
    total_adjusted = sum(f(row, "adjusted_cost_usd") for row in sponsor)
    total_unclean = sum(f(row, "unclean_spend_usd") for row in sponsor)

    comp_lines = [
        f"# Phase 3 comprehensive benchmark analysis ({DATE})",
        "",
        "## Scope",
        "",
        "This report extends the Phase 3 benchmark analysis with router-associated comparisons, task-family analysis, cost efficiency, wastage, and behavioral profiling.",
        "",
        "Primary generated artifacts:",
        "",
        f"- results/phase3/reporting/router_effect_comparison_{DATE}.tsv",
        f"- docs/reports/phase3/PHASE3_ROUTER_EFFECT_COMPARISON_{DATE}.md",
        f"- configs/tasks/phase3_task_taxonomy.tsv",
        f"- results/phase3/reporting/phase3_task_family_arm_matrix_{DATE}.tsv",
        f"- results/phase3/reporting/phase3_arm_behavior_profile_{DATE}.tsv",
        "",
        "Existing inputs incorporated:",
        "",
        "- docs/reports/phase3/PHASE3_BENCHMARK_ANALYSIS_20260713.md",
        "- docs/reports/phase3/PHASE3_COST_COVERAGE_20260712.md",
        "- docs/reports/phase3/PHASE3_CROSS_PHASE_COMPARISON_20260714.md",
        "- docs/reports/phase3/PHASE3_CROSS_PHASE_TASK_AUDIT_20260714.md",
        "- results/phase3/reporting/phase3_sponsor_summary_table_20260713.tsv",
        "- results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv",
        "- results/phase3/reporting/phase3_arm_qualitative_summary_20260712.tsv",
        "",
        "## Executive summary",
        "",
        f"- Phase 3 valid full-suite layer covers {len(sponsor)} arms, {total_trials} trials, and {total_success} raw successes.",
        f"- Aggregate Phase 3 raw pass rate across arms is {fmt_pct(total_success / total_trials if total_trials else 0)}.",
        f"- Aggregate adjusted known cost across Phase 3 valid arms is {fmt_money(total_adjusted)}.",
        f"- Aggregate unclean spend is {fmt_money(total_unclean)}, or {fmt_pct(total_unclean / total_adjusted if total_adjusted else 0)} of adjusted known cost.",
        "",
        "## Highest raw pass-rate arms",
        "",
        "| Arm | Successes | Pass rate | Adjusted cost | Cost per clean success | Unclean spend share |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for row in phase3_sorted[:7]:
        comp_lines.append(
            f"| {row['arm_id']} | {i(row, 'success_count')}/{i(row, 'trial_count')} | {fmt_pct(f(row, 'pass_rate'))} | {fmt_money(f(row, 'adjusted_cost_usd'))} | {fmt_money(f(row, 'cost_per_clean_success_usd'))} | {fmt_pct(f(row, 'unclean_spend_share'))} |"
        )

    comp_lines.extend([
        "",
        "## Lowest adjusted cost per clean success",
        "",
        "| Arm | Successes | Pass rate | Adjusted cost | Cost per clean success | Behavior tags |",
        "|---|---:|---:|---:|---:|---|",
    ])

    behavior_by_arm = {row["arm_id"]: row for row in behavior_rows}
    for row in efficient_sorted[:7]:
        beh = behavior_by_arm.get(row["arm_id"], {})
        comp_lines.append(
            f"| {row['arm_id']} | {i(row, 'success_count')}/{i(row, 'trial_count')} | {fmt_pct(f(row, 'pass_rate'))} | {fmt_money(f(row, 'adjusted_cost_usd'))} | {fmt_money(f(row, 'cost_per_clean_success_usd'))} | {beh.get('behavior_tags', '')} |"
        )

    comp_lines.extend([
        "",
        "## Highest unclean spend share",
        "",
        "| Arm | Pass rate | Adjusted cost | Unclean spend share | Failure/incomplete token share | Qualitative flags |",
        "|---|---:|---:|---:|---:|---|",
    ])

    for row in wastage_sorted[:7]:
        beh = behavior_by_arm.get(row["arm_id"], {})
        comp_lines.append(
            f"| {row['arm_id']} | {fmt_pct(f(row, 'pass_rate'))} | {fmt_money(f(row, 'adjusted_cost_usd'))} | {fmt_pct(f(row, 'unclean_spend_share'))} | {fmt_pct(f(row, 'failure_incomplete_token_share'))} | {beh.get('behavior_tags', '')} |"
        )

    comp_lines.extend([
        "",
        "## Task-family performance",
        "",
        "Task families are generated as a reviewable heuristic taxonomy in configs/tasks/phase3_task_taxonomy.tsv. The taxonomy should be treated as an analysis aid, not as a benchmark ground truth.",
        "",
        "| Task family | Trials | Successes | Pass rate | Adjusted cost | Unclean cost share |",
        "|---|---:|---:|---:|---:|---:|",
    ])

    for row in family_summary_rows:
        comp_lines.append(
            f"| {row['task_family']} | {row['trial_count']} | {row['success_count']} | {fmt_pct(row['pass_rate'])} | {fmt_money(row['adjusted_cost_usd'])} | {fmt_pct(row['unclean_share'])} |"
        )

    comp_lines.extend([
        "",
        "## Router-associated findings",
        "",
        "The focused router comparison is emitted separately and summarized here. It compares matched direct Phase 1/2 arms to Phase 3 LiteLLM-router arms where a model-family counterpart exists.",
        "",
        "| Model family | Direct phase | Router arm | Pass delta | Cost ratio | Runtime ratio | Interpretation |",
        "|---|---|---|---:|---:|---:|---|",
    ])

    for row in ok_router:
        comp_lines.append(
            f"| {row['model_family']} | {row['direct_phase']} | {row['router_arm_id']} | {fmt_float(row['delta_pass_rate_pct_points'], 1)} pp | {fmt_float(row['router_vs_direct_cost_ratio'], 2)} | {fmt_float(row['router_vs_direct_wall_clock_ratio'], 2)} | {row['interpretation']} |"
        )

    comp_lines.extend([
        "",
        "## Behavioral interpretation layer",
        "",
        "The behavior profile table groups arms by observed cost, token, exception, and wastage signatures. It is intended to guide follow-up qualitative review rather than replace manual artifact inspection.",
        "",
        "Examples of generated behavior tags:",
        "",
        "- high-pass-rate: raw pass rate at or above 70%.",
        "- cost-efficient-clean-success: adjusted cost per clean success at or below $1.50.",
        "- exception-heavy: at least 10 exception-classified trials.",
        "- high-unclean-spend: at least half of adjusted spend went to failures, incomplete outcomes, or exception-with-success-signal rows.",
        "- lower-token-success-pattern / higher-token-success-pattern: median successful-attempt visible tokens are materially below or above the suite median.",
        "",
        "## Caveats",
        "",
        "- Router-associated differences are not causal proof of LiteLLM effects.",
        "- Cross-phase comparisons are confounded by time, provider-side model revisions, runner configuration, routing path, invalid-run policy, and accounting changes.",
        "- The Phase 3 Haiku sanitized arm includes an Anthropic sanitizer path and should not be treated as a pure router-only comparison.",
        "- Task-family taxonomy is heuristic and reviewable.",
        "- Visible token sums are derived from imported token fields and are best used for relative behavioral profiling, not provider billing reconciliation.",
        "",
    ])

    COMPREHENSIVE_MD.parent.mkdir(parents=True, exist_ok=True)
    COMPREHENSIVE_MD.write_text("\n".join(line.rstrip() for line in comp_lines).rstrip() + "\n")

    print("wrote")
    for path in [TAXONOMY_OUT, ROUTER_TSV, ROUTER_MD, TASK_FAMILY_MATRIX, ARM_BEHAVIOR, COMPREHENSIVE_MD]:
        print(path.relative_to(ROOT))


if __name__ == "__main__":
    main()
