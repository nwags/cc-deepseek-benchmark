from __future__ import annotations

import argparse
import csv
import statistics
from collections import Counter, defaultdict
from pathlib import Path


def n(value, default=None):
    if value is None:
        return default
    text = str(value).strip()
    if text == "":
        return default
    try:
        return float(text)
    except ValueError:
        return default


def yes(value) -> bool:
    return str(value).strip().lower() in {"true", "1", "yes"}


def div(a, b):
    return a / b if b else 0.0


def read_csv(path: Path, delimiter=","):
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter=delimiter))


def write_tsv(path: Path, rows: list[dict], cols: list[str]):
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=cols, delimiter="\t", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({col: row.get(col, "") for col in cols})


def total_tokens(row: dict) -> float:
    return (
        (n(row.get("n_input_tokens"), 0.0) or 0.0)
        + (n(row.get("n_cache_tokens"), 0.0) or 0.0)
        + (n(row.get("n_output_tokens"), 0.0) or 0.0)
    )


def token_price_cost(row: dict) -> float | None:
    input_tokens = n(row.get("n_input_tokens"), 0.0) or 0.0
    cache_tokens = n(row.get("n_cache_tokens"), 0.0) or 0.0
    output_tokens = n(row.get("n_output_tokens"), 0.0) or 0.0
    miss_price = n(row.get("input_cache_miss_usd_per_million"))
    hit_price = n(row.get("input_cache_hit_usd_per_million"))
    output_price = n(row.get("output_usd_per_million"))

    if miss_price is None or output_price is None:
        return None

    miss_tokens = max(input_tokens - cache_tokens, 0.0)
    cost = miss_tokens * miss_price / 1_000_000.0
    if cache_tokens:
        if hit_price is None:
            return None
        cost += cache_tokens * hit_price / 1_000_000.0
    cost += output_tokens * output_price / 1_000_000.0
    return cost


def outcome(row: dict) -> str:
    success = yes(row.get("success"))
    exception = bool(str(row.get("exception_type") or row.get("exception_message") or "").strip())
    if success and exception:
        return "exception_with_success_signal"
    if success:
        return "clean_success"
    if exception:
        return "exception_failure"
    return "normal_failure"


def empirical_rates(rows: list[dict]) -> dict[str, float]:
    by_arm = defaultdict(list)
    for row in rows:
        by_arm[row["arm_dir"]].append(row)

    rates = {}
    for arm, arm_rows in by_arm.items():
        cost_sum = 0.0
        token_sum = 0.0
        for row in arm_rows:
            cost = n(row.get("effective_cost_usd"))
            tokens = total_tokens(row)
            if cost is not None and cost > 0 and tokens > 0:
                cost_sum += cost
                token_sum += tokens
        rates[arm] = div(cost_sum, token_sum)
    return rates


def adjusted_cost(row: dict, rate: float) -> tuple[float, float, str, str]:
    effective = n(row.get("effective_cost_usd"))
    if effective is not None:
        return effective, effective, "recorded_effective_cost", "high"

    provider = n(row.get("provider_reported_cost_usd"))
    if provider is not None:
        return 0.0, provider, "provider_reported_fallback", "medium"

    computed = n(row.get("computed_cache_aware_cost_usd"))
    if computed is not None:
        return 0.0, computed, "computed_cache_aware_fallback", "medium"

    priced = token_price_cost(row)
    if priced is not None:
        return 0.0, priced, "token_price_reconstructed", "medium"

    tokens = total_tokens(row)
    if tokens > 0 and rate > 0:
        return 0.0, tokens * rate, "empirical_reconstructed", "medium"

    return 0.0, 0.0, "unresolved_no_token_metadata", "low"


def enrich_phase(phase: str, rows: list[dict]) -> list[dict]:
    rates = empirical_rates(rows)
    out = []

    for index, row in enumerate(rows):
        recorded, adjusted, source, confidence = adjusted_cost(row, rates.get(row["arm_dir"], 0.0))
        bucket = outcome(row)
        out.append({
            "phase": phase,
            "row_index": index,
            "arm_id": row["arm_dir"],
            "backend": row.get("backend", ""),
            "backend_model": row.get("model_backend", ""),
            "task_name": row.get("task_name", ""),
            "trial_name": row.get("trial_name", ""),
            "success": yes(row.get("success")),
            "outcome_bucket": bucket,
            "exception_present": bucket in {"exception_failure", "exception_with_success_signal"},
            "wall_clock_seconds": n(row.get("wall_clock_seconds"), 0.0) or 0.0,
            "recorded_cost_usd": recorded,
            "adjusted_cost_usd": adjusted,
            "known_accounting_gap_usd": adjusted - recorded,
            "cost_source": source,
            "cost_confidence": confidence,
            "input_tokens": n(row.get("n_input_tokens"), 0.0) or 0.0,
            "cache_tokens": n(row.get("n_cache_tokens"), 0.0) or 0.0,
            "output_tokens": n(row.get("n_output_tokens"), 0.0) or 0.0,
            "total_tokens": total_tokens(row),
        })
    return out


def aggregate(enriched: list[dict], routing_path: str) -> list[dict]:
    by_arm = defaultdict(list)
    for row in enriched:
        by_arm[(row["phase"], row["arm_id"])].append(row)

    out = []
    for (phase, arm), rows in sorted(by_arm.items()):
        count = len(rows)
        success = sum(1 for row in rows if row["success"])
        clean = sum(1 for row in rows if row["outcome_bucket"] == "clean_success")
        recorded = sum(row["recorded_cost_usd"] for row in rows)
        adjusted = sum(row["adjusted_cost_usd"] for row in rows)
        gap = sum(row["known_accounting_gap_usd"] for row in rows)
        failure_spend = sum(row["adjusted_cost_usd"] for row in rows if row["outcome_bucket"] in {"normal_failure", "exception_failure"})
        unclean_spend = sum(row["adjusted_cost_usd"] for row in rows if row["outcome_bucket"] != "clean_success")
        total_tok = sum(row["total_tokens"] for row in rows)
        failure_tok = sum(row["total_tokens"] for row in rows if row["outcome_bucket"] in {"normal_failure", "exception_failure"})
        unclean_tok = sum(row["total_tokens"] for row in rows if row["outcome_bucket"] != "clean_success")
        runtimes = [row["wall_clock_seconds"] for row in rows if row["wall_clock_seconds"]]
        sources = Counter(row["cost_source"] for row in rows)
        confidence = "mixed" if sources["unresolved_no_token_metadata"] else ("medium" if len(sources) > 1 or "recorded_effective_cost" not in sources else "high")
        sample = rows[0]

        out.append({
            "phase": phase,
            "arm_id": arm,
            "backend_model": sample["backend_model"],
            "provider": sample["backend"],
            "routing_path": routing_path,
            "success_count": success,
            "clean_success_count": clean,
            "trial_count": count,
            "pass_rate": div(success, count),
            "recorded_cost_usd": recorded,
            "adjusted_cost_usd": adjusted,
            "known_accounting_gap_usd": gap,
            "mean_adjusted_cost_per_attempt_usd": div(adjusted, count),
            "mean_adjusted_cost_per_3_attempt_task_usd": div(adjusted, count) * 3.0,
            "cost_per_clean_success_usd": div(adjusted, clean),
            "failure_incomplete_spend_usd": failure_spend,
            "unclean_spend_usd": unclean_spend,
            "failure_incomplete_spend_share": div(failure_spend, adjusted),
            "unclean_spend_share": div(unclean_spend, adjusted),
            "failure_incomplete_tokens": failure_tok,
            "unclean_tokens": unclean_tok,
            "failure_incomplete_token_share": div(failure_tok, total_tok),
            "unclean_token_share": div(unclean_tok, total_tok),
            "median_wall_clock_seconds": statistics.median(runtimes) if runtimes else "",
            "recorded_artifact_count": sources["recorded_effective_cost"],
            "fallback_or_reconstructed_count": count - sources["recorded_effective_cost"] - sources["unresolved_no_token_metadata"],
            "unresolved_cost_count": sources["unresolved_no_token_metadata"],
            "cost_confidence": confidence,
        })
    return out


def load_phase3(path: Path) -> list[dict]:
    out = []
    for row in read_csv(path, "\t"):
        adjusted = n(row["adjusted_cost_usd"], 0.0) or 0.0
        cps = n(row["cost_per_clean_success_usd"], 0.0) or 0.0
        clean = round(div(adjusted, cps)) if cps else int(n(row["success_count"], 0) or 0)
        out.append({
            "phase": "phase3",
            "arm_id": row["arm_id"],
            "backend_model": row["backend_model"],
            "provider": row["provider"],
            "routing_path": "litellm_router",
            "success_count": int(n(row["success_count"], 0) or 0),
            "clean_success_count": clean,
            "trial_count": int(n(row["trial_count"], 0) or 0),
            "pass_rate": n(row["pass_rate"], 0.0) or 0.0,
            "recorded_cost_usd": n(row["recorded_cost_usd"], 0.0) or 0.0,
            "adjusted_cost_usd": adjusted,
            "known_accounting_gap_usd": n(row["known_accounting_gap_usd"], 0.0) or 0.0,
            "mean_adjusted_cost_per_attempt_usd": n(row["mean_adjusted_cost_per_attempt_usd"], 0.0) or 0.0,
            "mean_adjusted_cost_per_3_attempt_task_usd": n(row["mean_adjusted_cost_per_3_attempt_task_usd"], 0.0) or 0.0,
            "cost_per_clean_success_usd": cps,
            "failure_incomplete_spend_usd": n(row["failure_incomplete_spend_usd"], 0.0) or 0.0,
            "unclean_spend_usd": n(row["unclean_spend_usd"], 0.0) or 0.0,
            "failure_incomplete_spend_share": n(row["failure_incomplete_spend_share"], 0.0) or 0.0,
            "unclean_spend_share": n(row["unclean_spend_share"], 0.0) or 0.0,
            "failure_incomplete_tokens": n(row["failure_incomplete_tokens"], 0.0) or 0.0,
            "unclean_tokens": n(row["unclean_tokens"], 0.0) or 0.0,
            "failure_incomplete_token_share": n(row["failure_incomplete_token_share"], 0.0) or 0.0,
            "unclean_token_share": n(row["unclean_token_share"], 0.0) or 0.0,
            "median_wall_clock_seconds": "",
            "recorded_artifact_count": "",
            "fallback_or_reconstructed_count": "",
            "unresolved_cost_count": int(n(row["unresolved_cost_count"], 0) or 0),
            "cost_confidence": row["cost_confidence"],
        })
    return out


TRIAL_COLS = [
    "phase", "row_index", "arm_id", "backend", "backend_model", "task_name", "trial_name",
    "success", "outcome_bucket", "exception_present", "wall_clock_seconds",
    "recorded_cost_usd", "adjusted_cost_usd", "known_accounting_gap_usd",
    "cost_source", "cost_confidence", "input_tokens", "cache_tokens", "output_tokens", "total_tokens",
]

ARM_COLS = [
    "phase", "arm_id", "backend_model", "provider", "routing_path",
    "success_count", "clean_success_count", "trial_count", "pass_rate",
    "recorded_cost_usd", "adjusted_cost_usd", "known_accounting_gap_usd",
    "mean_adjusted_cost_per_attempt_usd", "mean_adjusted_cost_per_3_attempt_task_usd",
    "cost_per_clean_success_usd", "failure_incomplete_spend_usd", "unclean_spend_usd",
    "failure_incomplete_spend_share", "unclean_spend_share",
    "failure_incomplete_tokens", "unclean_tokens",
    "failure_incomplete_token_share", "unclean_token_share",
    "median_wall_clock_seconds", "recorded_artifact_count",
    "fallback_or_reconstructed_count", "unresolved_cost_count", "cost_confidence",
]


def write_report(path: Path, rows: list[dict]):
    totals = defaultdict(lambda: {"arms": 0, "trials": 0, "success": 0, "recorded": 0.0, "adjusted": 0.0})
    for row in rows:
        t = totals[row["phase"]]
        t["arms"] += 1
        t["trials"] += int(row["trial_count"])
        t["success"] += int(row["success_count"])
        t["recorded"] += float(row["recorded_cost_usd"])
        t["adjusted"] += float(row["adjusted_cost_usd"])

    lines = [
        "# Cross-phase adjusted cost comparison",
        "",
        "Phase 1, Phase 2, and Phase 3 are compared using an adjusted-cost layer for all phases.",
        "",
        "Phase 1 and Phase 2 source aggregates remain frozen. Their adjusted-cost coverage tables are derived reporting artifacts. Phase 3 uses the existing valid-only sponsor summary with adjusted known cost.",
        "",
        "The comparison is apples-to-apples at the benchmark-unit level: 20 tasks × 3 attempts per arm. The routing path remains explicit because Phase 3 used LiteLLM/router infrastructure.",
        "",
        "## Phase totals",
        "",
        "| Phase | Arms | Trials | Successes | Pass rate | Recorded cost | Adjusted known cost |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]

    for phase in sorted(totals):
        t = totals[phase]
        lines.append(f"| {phase} | {t['arms']} | {t['trials']} | {t['success']} | {div(t['success'], t['trials']):.1%} | ${t['recorded']:.2f} | ${t['adjusted']:.2f} |")

    lines += [
        "",
        "## Arm table",
        "",
        "| Phase | Arm | Routing path | Pass rate | Adjusted cost | Cost / clean success | Confidence |",
        "|---|---|---|---:|---:|---:|---|",
    ]

    for row in sorted(rows, key=lambda r: (r["phase"], -float(r["pass_rate"]), float(r["adjusted_cost_usd"]))):
        lines.append(f"| {row['phase']} | `{row['arm_id']}` | {row['routing_path']} | {float(row['pass_rate']):.1%} | ${float(row['adjusted_cost_usd']):.2f} | ${float(row['cost_per_clean_success_usd']):.2f} | {row['cost_confidence']} |")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines) + "\n")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", default="20260714")
    args = parser.parse_args()

    out_dir = Path("results/phase3/reporting")
    phase1_trials = enrich_phase("phase1", read_csv(Path("results/phase1/combined.csv")))
    phase2_trials = enrich_phase("phase2", read_csv(Path("results/phase2/combined.csv")))
    phase1_arms = aggregate(phase1_trials, "phase1_direct")
    phase2_arms = aggregate(phase2_trials, "phase2_direct")
    phase3_arms = load_phase3(Path("results/phase3/reporting/phase3_sponsor_summary_table_20260713.tsv"))

    write_tsv(out_dir / f"phase1_trial_cost_coverage_{args.date}.tsv", phase1_trials, TRIAL_COLS)
    write_tsv(out_dir / f"phase2_trial_cost_coverage_{args.date}.tsv", phase2_trials, TRIAL_COLS)
    write_tsv(out_dir / f"phase1_arm_cost_coverage_{args.date}.tsv", phase1_arms, ARM_COLS)
    write_tsv(out_dir / f"phase2_arm_cost_coverage_{args.date}.tsv", phase2_arms, ARM_COLS)

    cross = phase1_arms + phase2_arms + phase3_arms
    write_tsv(out_dir / f"cross_phase_adjusted_comparison_{args.date}.tsv", cross, ARM_COLS)
    write_report(Path(f"docs/reports/phase3/PHASE3_CROSS_PHASE_COMPARISON_{args.date}.md"), cross)
    print("wrote cross-phase adjusted comparison artifacts")


if __name__ == "__main__":
    main()
