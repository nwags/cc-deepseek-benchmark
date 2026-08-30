from __future__ import annotations

import argparse
import csv
import os
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import yaml

from scripts.lib.costs import (
    RATES,
    estimate_cost_usd,
    harbor_aggregate_reconstruction_safe,
)


ROOT = Path(__file__).resolve().parents[1]


@dataclass
class TrialCostRow:
    suite_id: str
    arm_id: str
    backend_model: str
    provider: str
    run_label: str
    task_id: str
    attempt_index: int | None
    trial_id: str
    reward: str
    exception_type: str
    runtime_seconds: str
    input_tokens: int
    cache_tokens: int
    output_tokens: int
    recorded_cost_usd: float | None
    token_reconstructed_cost_usd: float | None
    empirical_reconstructed_cost_usd: float | None
    adjusted_cost_usd: float | None
    cost_source: str
    cost_confidence: str
    cost_gap_reason: str
    outcome_bucket: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Phase 3 adjusted cost coverage reports.")
    parser.add_argument("--suite-id", default="phase3-full-20")
    parser.add_argument("--date", required=True, help="Report date suffix, e.g. 20260712")
    parser.add_argument("--db-url", default=os.environ.get("SUPABASE_DB_URL"))
    parser.add_argument("--out-dir", type=Path, default=ROOT / "results/phase3/reporting")
    return parser.parse_args()


def intish(value: Any) -> int:
    if value in (None, ""):
        return 0
    return int(float(value))


def floatish(value: Any) -> float | None:
    if value in (None, ""):
        return None
    return float(value)


def fmt_money(value: float | None) -> str:
    if value is None:
        return ""
    return f"{value:.12f}".rstrip("0").rstrip(".")


def load_arm_metadata() -> dict[str, dict[str, str]]:
    out: dict[str, dict[str, str]] = {}
    for path in sorted((ROOT / "configs/arms").glob("router-*.yaml")):
        data = yaml.safe_load(path.read_text()) or {}
        arm_id = data.get("id") or path.stem
        out[arm_id] = {
            "provider": str(data.get("provider") or ""),
            "backend_model": str(
                data.get("backend_model")
                or data.get("model")
                or arm_id
            ),
            "router": str(data.get("router") or ""),
        }
    return out


def fetch_valid_trials(db_url: str, suite_id: str) -> list[dict[str, Any]]:
    try:
        import psycopg
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "psycopg is required for DB-backed Phase 3 cost generation"
        ) from exc

    sql = """
    select
      ar.suite_id,
      ar.arm_id,
      r.run_label,
      t.task_id,
      t.attempt_index,
      t.id::text as trial_id,
      t.reward,
      t.exception_type,
      t.runtime_seconds,
      t.input_tokens,
      t.cache_tokens,
      t.output_tokens,
      t.cost_usd
    from benchmark.benchmark_trials t
    join benchmark.benchmark_arm_runs ar on ar.id = t.arm_run_id
    join benchmark.benchmark_runs r on r.id = ar.run_id
    where ar.suite_id = %s
      and not exists (
        select 1
        from benchmark.benchmark_invalid_arm_runs bad
        where bad.suite_id = ar.suite_id
          and bad.arm_id = ar.arm_id
          and bad.run_label = r.run_label
      )
    order by ar.arm_id, r.run_label, t.attempt_index, t.id
    """
    with psycopg.connect(db_url) as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (suite_id,))
            cols = [d.name for d in cur.description]
            return [dict(zip(cols, row, strict=True)) for row in cur.fetchall()]


def build_empirical_rates(
    raw_rows: list[dict[str, Any]],
    *,
    excluded_arm_ids: set[str] | None = None,
    min_recorded_rows: int = 10,
) -> dict[str, float]:
    """Build legacy same-arm empirical rates for eligible non-router arms.

    Router-mediated Claude Code cost is not an authoritative provider charge,
    so routed arms must never seed this empirical fallback.
    """
    excluded = excluded_arm_ids or set()
    sums: dict[str, dict[str, float]] = defaultdict(
        lambda: {"rows": 0, "tokens": 0, "cost": 0.0}
    )
    for row in raw_rows:
        arm_id = str(row["arm_id"])
        if arm_id in excluded:
            continue

        cost = floatish(row.get("cost_usd"))
        total_tokens = (
            intish(row.get("input_tokens"))
            + intish(row.get("output_tokens"))
        )
        if cost is None or total_tokens <= 0:
            continue

        sums[arm_id]["rows"] += 1
        sums[arm_id]["tokens"] += total_tokens
        sums[arm_id]["cost"] += cost

    rates: dict[str, float] = {}
    for arm_id, values in sums.items():
        if (
            values["rows"] >= min_recorded_rows
            and values["tokens"] > 0
        ):
            rates[arm_id] = (
                values["cost"]
                / values["tokens"]
                * 1_000_000
            )
    return rates


def classify_outcome(reward: str, exception_type: str) -> str:
    success = reward == "1"
    has_exception = bool(exception_type)

    if success and not has_exception:
        return "clean_success"
    if success and has_exception:
        return "exception_with_success_signal"
    if has_exception:
        return "exception_failure"
    if reward in {"0", "0.0"}:
        return "normal_failure"
    return "unknown_or_incomplete"


def classify_cost(
    *,
    arm_id: str,
    backend_model: str,
    routed: bool,
    recorded_cost: float | None,
    input_tokens: int,
    cache_tokens: int,
    output_tokens: int,
    empirical_rates: dict[str, float],
) -> tuple[
    float | None,
    float | None,
    float | None,
    str,
    str,
    str,
]:
    has_tokens = any(
        [input_tokens, cache_tokens, output_tokens]
    )

    if routed:
        # The current Claude Code path emits total_cost_usd as a
        # harness/client estimate for the router alias. The policy here is
        # harness-agnostic: preserve routed/custom-model harness cost as
        # recorded evidence, but do not select it as provider-authoritative
        # adjusted cost without independent qualification.
        if not has_tokens:
            return (
                None,
                None,
                None,
                "unresolved_routed_harness_cost_not_authoritative_no_token_metadata",
                "unknown",
                "routed_harness_cost_preserved_but_not_selected;"
                "no_token_usage_metadata_for_provider_reconstruction",
            )

        if harbor_aggregate_reconstruction_safe(backend_model):
            reconstructed = estimate_cost_usd(
                backend_model,
                n_input_tokens=input_tokens,
                n_cache_tokens=cache_tokens,
                n_output_tokens=output_tokens,
            )
            return (
                reconstructed,
                reconstructed
                if recorded_cost is None
                else None,
                None,
                "provider_rate_reconstructed_routed_harness_untrusted",
                "medium",
                "routed_harness_cost_preserved_but_not_selected;"
                "provider_rate_reconstruction_from_harbor_aggregate_tokens",
            )

        return (
            None,
            None,
            None,
            "unresolved_routed_harness_cost_not_authoritative_pricing",
            "unknown",
            "routed_harness_cost_preserved_but_not_selected;"
            "provider_pricing_not_safe_from_harbor_aggregate_tokens:"
            f"{backend_model}",
        )

    # Historical/direct behavior remains unchanged.
    if recorded_cost is not None:
        return (
            recorded_cost,
            None,
            None,
            "recorded_artifact",
            "high",
            "",
        )

    if not has_tokens:
        return (
            None,
            None,
            None,
            "unresolved_no_token_metadata",
            "unknown",
            "cost_missing_and_no_token_usage_metadata",
        )

    if backend_model in RATES:
        reconstructed = estimate_cost_usd(
            backend_model,
            n_input_tokens=input_tokens,
            n_cache_tokens=cache_tokens,
            n_output_tokens=output_tokens,
        )
        return (
            reconstructed,
            reconstructed,
            None,
            "token_reconstructed_from_configured_price_snapshot",
            "medium",
            "cost_missing_but_token_usage_and_configured_pricing_available",
        )

    empirical_rate = empirical_rates.get(arm_id)
    if empirical_rate is not None:
        empirical = (
            (input_tokens + output_tokens)
            / 1_000_000
            * empirical_rate
        )
        return (
            empirical,
            None,
            empirical,
            "empirical_reconstructed_from_same_arm_recorded_rows",
            "low",
            "missing_configured_pricing_used_same_arm_empirical_rate_"
            f"usd_per_1m_total_tokens:{empirical_rate:.6f}",
        )

    return (
        None,
        None,
        None,
        "unresolved_missing_pricing",
        "unknown",
        f"missing_price_rate_for_backend_model:{backend_model}",
    )


def build_trial_rows(raw_rows: list[dict[str, Any]], arm_meta: dict[str, dict[str, str]]) -> list[TrialCostRow]:
    out: list[TrialCostRow] = []
    routed_arm_ids = {
        arm_id
        for arm_id, meta in arm_meta.items()
        if meta.get("router")
    }
    empirical_rates = build_empirical_rates(
        raw_rows,
        excluded_arm_ids=routed_arm_ids,
    )

    for r in raw_rows:
        arm_id = str(r["arm_id"])
        meta = arm_meta.get(arm_id, {})
        backend_model = meta.get("backend_model", arm_id)
        provider = meta.get("provider", "")
        routed = bool(meta.get("router"))

        input_tokens = intish(r.get("input_tokens"))
        cache_tokens = intish(r.get("cache_tokens"))
        output_tokens = intish(r.get("output_tokens"))
        recorded_cost = floatish(r.get("cost_usd"))

        reward = "" if r.get("reward") is None else str(r.get("reward"))
        exception_type = "" if r.get("exception_type") is None else str(r.get("exception_type"))

        adjusted, reconstructed, empirical, source, confidence, reason = classify_cost(
            arm_id=arm_id,
            backend_model=backend_model,
            routed=routed,
            recorded_cost=recorded_cost,
            input_tokens=input_tokens,
            cache_tokens=cache_tokens,
            output_tokens=output_tokens,
            empirical_rates=empirical_rates,
        )

        out.append(
            TrialCostRow(
                suite_id=str(r["suite_id"]),
                arm_id=arm_id,
                backend_model=backend_model,
                provider=provider,
                run_label=str(r["run_label"]),
                task_id=str(r["task_id"]),
                attempt_index=r.get("attempt_index"),
                trial_id=str(r["trial_id"]),
                reward=reward,
                exception_type=exception_type,
                runtime_seconds="" if r.get("runtime_seconds") is None else str(r.get("runtime_seconds")),
                input_tokens=input_tokens,
                cache_tokens=cache_tokens,
                output_tokens=output_tokens,
                recorded_cost_usd=recorded_cost,
                token_reconstructed_cost_usd=reconstructed,
                empirical_reconstructed_cost_usd=empirical,
                adjusted_cost_usd=adjusted,
                cost_source=source,
                cost_confidence=confidence,
                cost_gap_reason=reason,
                outcome_bucket=classify_outcome(reward, exception_type),
            )
        )
    return out


def write_trial_tsv(path: Path, rows: list[TrialCostRow]) -> None:
    fieldnames = list(TrialCostRow.__dataclass_fields__.keys())
    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in rows:
            d = row.__dict__.copy()
            for k in (
                "recorded_cost_usd",
                "token_reconstructed_cost_usd",
                "empirical_reconstructed_cost_usd",
                "adjusted_cost_usd",
            ):
                d[k] = fmt_money(d[k])
            writer.writerow(d)


def arm_confidence(source_counts: Counter[str]) -> str:
    has_unresolved = any(
        source.startswith("unresolved_") and count
        for source, count in source_counts.items()
    )
    has_medium_reconstruction = bool(
        source_counts.get(
            "token_reconstructed_from_configured_price_snapshot"
        )
        or source_counts.get(
            "provider_rate_reconstructed_routed_harness_untrusted"
        )
    )
    has_low_reconstruction = bool(
        source_counts.get(
            "empirical_reconstructed_from_same_arm_recorded_rows"
        )
    )

    if has_unresolved:
        if has_medium_reconstruction or has_low_reconstruction:
            return "mixed"
        return "low"

    if has_low_reconstruction:
        return "low"

    if has_medium_reconstruction:
        return "medium"

    return "high"


def write_arm_tsv(path: Path, rows: list[TrialCostRow]) -> None:
    grouped: dict[str, list[TrialCostRow]] = defaultdict(list)
    for row in rows:
        grouped[row.arm_id].append(row)

    fieldnames = [
        "arm_id",
        "backend_model",
        "provider",
        "trial_count",
        "success_count",
        "clean_success_count",
        "exception_success_signal_count",
        "failure_or_incomplete_count",
        "recorded_cost_usd",
        "missing_cost_count",
        "missing_cost_with_visible_tokens_count",
        "token_reconstructed_missing_cost_usd",
        "empirical_reconstructed_missing_cost_usd",
        "unresolved_missing_cost_count",
        "adjusted_cost_usd",
        "adjusted_clean_success_cost_usd",
        "adjusted_exception_success_signal_cost_usd",
        "adjusted_failure_or_incomplete_cost_usd",
        "nonproductive_or_unclean_spend_share",
        "mean_recorded_cost_per_attempt",
        "mean_adjusted_cost_per_attempt",
        "adjusted_cost_per_clean_success",
        "adjusted_cost_per_any_success",
        "cost_confidence",
        "cost_source_counts",
        "outcome_cost_counts",
        "notes",
    ]

    with path.open("w", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()

        for arm_id in sorted(grouped):
            arm_rows = grouped[arm_id]
            source_counts = Counter(r.cost_source for r in arm_rows)
            outcome_counts = Counter(r.outcome_bucket for r in arm_rows)

            trial_count = len(arm_rows)
            success_count = sum(1 for r in arm_rows if r.reward == "1")
            clean_success_count = outcome_counts["clean_success"]
            exception_success_count = outcome_counts["exception_with_success_signal"]
            failure_or_incomplete_count = trial_count - clean_success_count - exception_success_count

            recorded = sum(r.recorded_cost_usd or 0 for r in arm_rows)
            missing = sum(1 for r in arm_rows if r.recorded_cost_usd is None)
            missing_with_tokens = sum(
                1 for r in arm_rows if r.recorded_cost_usd is None and any([r.input_tokens, r.cache_tokens, r.output_tokens])
            )
            token_reconstructed = sum(r.token_reconstructed_cost_usd or 0 for r in arm_rows)
            empirical_reconstructed = sum(r.empirical_reconstructed_cost_usd or 0 for r in arm_rows)
            adjusted = sum(r.adjusted_cost_usd or 0 for r in arm_rows)
            unresolved = sum(
                1
                for r in arm_rows
                if r.cost_source.startswith("unresolved_")
            )

            clean_success_cost = sum(r.adjusted_cost_usd or 0 for r in arm_rows if r.outcome_bucket == "clean_success")
            exception_success_cost = sum(
                r.adjusted_cost_usd or 0 for r in arm_rows if r.outcome_bucket == "exception_with_success_signal"
            )
            failure_cost = sum(
                r.adjusted_cost_usd or 0
                for r in arm_rows
                if r.outcome_bucket not in {"clean_success", "exception_with_success_signal"}
            )
            unclean_cost = adjusted - clean_success_cost
            unclean_share = unclean_cost / adjusted if adjusted else None

            notes = []
            if source_counts.get("unresolved_missing_pricing"):
                notes.append("pricing_snapshot_needed")
            if source_counts.get("unresolved_no_token_metadata"):
                notes.append("no_token_metadata_for_some_missing_cost_rows")
            if source_counts.get("token_reconstructed_from_configured_price_snapshot"):
                notes.append("adjusted_cost_includes_configured_price_reconstruction")
            if source_counts.get("empirical_reconstructed_from_same_arm_recorded_rows"):
                notes.append("adjusted_cost_includes_same_arm_empirical_reconstruction")
            if source_counts.get(
                "provider_rate_reconstructed_routed_harness_untrusted"
            ):
                notes.append(
                    "adjusted_cost_uses_provider_rate_reconstruction_"
                    "not_routed_harness_cost"
                )
            if any(
                source.startswith(
                    "unresolved_routed_harness_cost_not_authoritative"
                )
                and count
                for source, count in source_counts.items()
            ):
                notes.append(
                    "routed_harness_cost_preserved_but_not_authoritative"
                )

            writer.writerow(
                {
                    "arm_id": arm_id,
                    "backend_model": arm_rows[0].backend_model,
                    "provider": arm_rows[0].provider,
                    "trial_count": trial_count,
                    "success_count": success_count,
                    "clean_success_count": clean_success_count,
                    "exception_success_signal_count": exception_success_count,
                    "failure_or_incomplete_count": failure_or_incomplete_count,
                    "recorded_cost_usd": fmt_money(recorded),
                    "missing_cost_count": missing,
                    "missing_cost_with_visible_tokens_count": missing_with_tokens,
                    "token_reconstructed_missing_cost_usd": fmt_money(token_reconstructed),
                    "empirical_reconstructed_missing_cost_usd": fmt_money(empirical_reconstructed),
                    "unresolved_missing_cost_count": unresolved,
                    "adjusted_cost_usd": fmt_money(adjusted),
                    "adjusted_clean_success_cost_usd": fmt_money(clean_success_cost),
                    "adjusted_exception_success_signal_cost_usd": fmt_money(exception_success_cost),
                    "adjusted_failure_or_incomplete_cost_usd": fmt_money(failure_cost),
                    "nonproductive_or_unclean_spend_share": fmt_money(unclean_share),
                    "mean_recorded_cost_per_attempt": fmt_money(recorded / trial_count if trial_count else None),
                    "mean_adjusted_cost_per_attempt": fmt_money(adjusted / trial_count if trial_count else None),
                    "adjusted_cost_per_clean_success": fmt_money(adjusted / clean_success_count if clean_success_count else None),
                    "adjusted_cost_per_any_success": fmt_money(adjusted / success_count if success_count else None),
                    "cost_confidence": arm_confidence(source_counts),
                    "cost_source_counts": ",".join(f"{k}:{source_counts[k]}" for k in sorted(source_counts)),
                    "outcome_cost_counts": ",".join(f"{k}:{outcome_counts[k]}" for k in sorted(outcome_counts)),
                    "notes": ";".join(notes),
                }
            )


def write_report(
    path: Path,
    date: str,
    rows: list[TrialCostRow],
) -> None:
    source_counts = Counter(r.cost_source for r in rows)
    outcome_counts = Counter(r.outcome_bucket for r in rows)

    recorded = sum(r.recorded_cost_usd or 0 for r in rows)
    token_reconstructed = sum(
        r.token_reconstructed_cost_usd or 0
        for r in rows
    )
    empirical_reconstructed = sum(
        r.empirical_reconstructed_cost_usd or 0
        for r in rows
    )
    adjusted = sum(r.adjusted_cost_usd or 0 for r in rows)

    recorded_row_count = sum(
        1
        for r in rows
        if r.recorded_cost_usd is not None
    )
    missing = sum(
        1
        for r in rows
        if r.recorded_cost_usd is None
    )
    missing_with_tokens = sum(
        1
        for r in rows
        if r.recorded_cost_usd is None
        and any(
            [
                r.input_tokens,
                r.cache_tokens,
                r.output_tokens,
            ]
        )
    )
    unresolved = sum(
        count
        for source, count in source_counts.items()
        if source.startswith("unresolved_")
    )

    routed_reconstructed_count = source_counts[
        "provider_rate_reconstructed_routed_harness_untrusted"
    ]
    routed_reconstructed_cost = sum(
        r.adjusted_cost_usd or 0
        for r in rows
        if r.cost_source
        == "provider_rate_reconstructed_routed_harness_untrusted"
    )
    routed_unresolved = sum(
        count
        for source, count in source_counts.items()
        if source.startswith(
            "unresolved_routed_harness_cost_not_authoritative"
        )
    )

    clean_success_cost = sum(
        r.adjusted_cost_usd or 0
        for r in rows
        if r.outcome_bucket == "clean_success"
    )
    exception_success_cost = sum(
        r.adjusted_cost_usd or 0
        for r in rows
        if r.outcome_bucket == "exception_with_success_signal"
    )
    failure_cost = sum(
        r.adjusted_cost_usd or 0
        for r in rows
        if r.outcome_bucket
        not in {
            "clean_success",
            "exception_with_success_signal",
        }
    )

    lines = [
        f"# Phase 3 Cost Coverage ({date})",
        "",
        (
            "This report distinguishes immutable harness-recorded cost "
            "from selected adjusted cost, provider-rate reconstruction, "
            "and unresolved cost authority."
        ),
        "",
        "## Summary",
        "",
        f"- Trial rows: {len(rows)}",
        (
            "- Rows with a recorded harness cost value: "
            f"{recorded_row_count}"
        ),
        (
            "- Selected direct/non-router recorded-artifact rows: "
            f"{source_counts['recorded_artifact']}"
        ),
        (
            "- Routed provider-rate reconstructed rows: "
            f"{routed_reconstructed_count}"
        ),
        (
            "- Routed rows with unresolved cost authority: "
            f"{routed_unresolved}"
        ),
        f"- Missing recorded-cost rows: {missing}",
        (
            "- Missing-cost rows with visible tokens: "
            f"{missing_with_tokens}"
        ),
        (
            "- Configured-price reconstructed missing-cost rows: "
            f"{source_counts['token_reconstructed_from_configured_price_snapshot']}"
        ),
        (
            "- Same-arm empirical reconstructed missing-cost rows: "
            f"{source_counts['empirical_reconstructed_from_same_arm_recorded_rows']}"
        ),
        f"- Unresolved adjusted-cost rows: {unresolved}",
        f"- Recorded harness cost USD: ${recorded:.6f}",
        (
            "- Routed provider-rate reconstructed selected cost USD: "
            f"${routed_reconstructed_cost:.6f}"
        ),
        (
            "- Configured-price reconstructed missing cost USD: "
            f"${token_reconstructed:.6f}"
        ),
        (
            "- Same-arm empirical reconstructed missing cost USD: "
            f"${empirical_reconstructed:.6f}"
        ),
        f"- Adjusted known cost USD: ${adjusted:.6f}",
        "",
        "## Outcome-cost breakdown",
        "",
        (
            "- Clean-success trials: "
            f"{outcome_counts['clean_success']}"
        ),
        (
            "- Exception-with-success-signal trials: "
            f"{outcome_counts['exception_with_success_signal']}"
        ),
        (
            "- Exception-failure trials: "
            f"{outcome_counts['exception_failure']}"
        ),
        (
            "- Normal-failure trials: "
            f"{outcome_counts['normal_failure']}"
        ),
        (
            "- Unknown/incomplete trials: "
            f"{outcome_counts['unknown_or_incomplete']}"
        ),
        (
            "- Adjusted clean-success cost USD: "
            f"${clean_success_cost:.6f}"
        ),
        (
            "- Adjusted exception-with-success-signal cost USD: "
            f"${exception_success_cost:.6f}"
        ),
        (
            "- Adjusted failure/incomplete cost USD: "
            f"${failure_cost:.6f}"
        ),
        "",
        "## Cost source taxonomy",
        "",
        (
            "- `recorded_artifact`: `cost_usd` was present in imported "
            "benchmark metadata for a non-router/direct arm and remains "
            "the selected historical adjusted-cost evidence."
        ),
        (
            "- `provider_rate_reconstructed_routed_harness_untrusted`: "
            "a routed/custom-model harness cost was preserved as recorded "
            "evidence but not treated as provider-authoritative; adjusted "
            "cost was reconstructed from an approved backend pricing "
            "snapshot using Harbor aggregate tokens."
        ),
        (
            "- `unresolved_routed_harness_cost_not_authoritative_"
            "no_token_metadata`: routed harness cost may exist, but "
            "provider-aware reconstruction is impossible because usable "
            "token telemetry is absent."
        ),
        (
            "- `unresolved_routed_harness_cost_not_authoritative_pricing`: "
            "routed harness cost may exist, but the backend cannot be "
            "safely priced from Harbor's collapsed aggregate token "
            "classes."
        ),
        (
            "- `token_reconstructed_from_configured_price_snapshot`: "
            "`cost_usd` was missing, but DB token usage and a configured "
            "pricing snapshot were available."
        ),
        (
            "- `empirical_reconstructed_from_same_arm_recorded_rows`: "
            "`cost_usd` was missing and no configured pricing snapshot "
            "was available, but enough same-arm rows had both token usage "
            "and recorded cost to estimate an empirical effective "
            "USD-per-token rate."
        ),
        (
            "- `unresolved_missing_pricing`: token usage exists, but no "
            "configured pricing snapshot or empirical estimate was "
            "available."
        ),
        (
            "- `unresolved_no_token_metadata`: neither cost nor token "
            "usage was recorded."
        ),
        "",
        (
            "Provider-reconciled billing is intentionally not claimed by "
            "this report. Harness-recorded cost remains immutable evidence; "
            "provider-aware adjusted cost is selected separately."
        ),
        "",
    ]

    path.write_text("\n".join(lines) + "\n")


def main() -> None:
    args = parse_args()
    if not args.db_url:
        raise SystemExit("SUPABASE_DB_URL is required via --db-url or environment.")

    args.out_dir.mkdir(parents=True, exist_ok=True)

    arm_meta = load_arm_metadata()
    raw_rows = fetch_valid_trials(args.db_url, args.suite_id)
    rows = build_trial_rows(raw_rows, arm_meta)

    trial_path = args.out_dir / f"phase3_trial_cost_coverage_{args.date}.tsv"
    arm_path = args.out_dir / f"phase3_arm_cost_coverage_{args.date}.tsv"
    report_path = ROOT / "docs/reports/phase3" / f"PHASE3_COST_COVERAGE_{args.date}.md"

    write_trial_tsv(trial_path, rows)
    write_arm_tsv(arm_path, rows)
    write_report(report_path, args.date, rows)

    print(trial_path)
    print(arm_path)
    print(report_path)


if __name__ == "__main__":
    main()
