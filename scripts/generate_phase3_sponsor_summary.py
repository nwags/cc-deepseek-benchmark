from __future__ import annotations

import argparse
import csv
import html
import math
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATE = "20260713"
DEFAULT_ARM_TSV = ROOT / "results/phase3/reporting/phase3_arm_cost_coverage_20260712.tsv"
DEFAULT_TRIAL_TSV = ROOT / "results/phase3/reporting/phase3_trial_cost_coverage_20260712.tsv"
DEFAULT_OUT_DIR = ROOT / "results/phase3/reporting"
DEFAULT_REPORT_DIR = ROOT / "docs/reports/phase3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate Phase 3 sponsor summary chart and report.")
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--arm-tsv", type=Path, default=DEFAULT_ARM_TSV)
    parser.add_argument("--trial-tsv", type=Path, default=DEFAULT_TRIAL_TSV)
    parser.add_argument("--out-dir", type=Path, default=DEFAULT_OUT_DIR)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    return parser.parse_args()


def f(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    return float(text)


def i(value: Any) -> int:
    return int(round(f(value)))


def money(value: float) -> str:
    return f"${value:,.2f}"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def short_arm(arm_id: str) -> str:
    return (
        arm_id.removeprefix("router-")
        .replace("anthropic-", "")
        .replace("sanitized", "")
        .replace("-build-0.1", " build")
        .replace("-", " ")
        .strip()
        .title()
        .replace("Gpt", "GPT")
        .replace("Glm", "GLM")
        .replace("Qwen", "Qwen")
        .replace("Kimi", "Kimi")
    )


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def outcome_token_breakdown(trials: list[dict[str, str]]) -> dict[str, dict[str, float]]:
    by_arm: dict[str, dict[str, float]] = defaultdict(lambda: defaultdict(float))
    for row in trials:
        arm = row["arm_id"]
        outcome = row["outcome_bucket"]
        total_tokens = f(row["input_tokens"]) + f(row["output_tokens"])
        adjusted_cost = f(row["adjusted_cost_usd"])

        by_arm[arm]["total_tokens"] += total_tokens
        by_arm[arm]["total_adjusted_cost_usd"] += adjusted_cost

        if outcome == "clean_success":
            by_arm[arm]["clean_tokens"] += total_tokens
            by_arm[arm]["clean_adjusted_cost_usd"] += adjusted_cost
        elif outcome == "exception_with_success_signal":
            by_arm[arm]["exception_success_tokens"] += total_tokens
            by_arm[arm]["exception_success_adjusted_cost_usd"] += adjusted_cost
        else:
            by_arm[arm]["failure_incomplete_tokens"] += total_tokens
            by_arm[arm]["failure_incomplete_adjusted_cost_usd"] += adjusted_cost

        if outcome != "clean_success":
            by_arm[arm]["unclean_tokens"] += total_tokens
            by_arm[arm]["unclean_adjusted_cost_usd"] += adjusted_cost

    return by_arm


def enrich_arm_rows(arms: list[dict[str, str]], token_breakdown: dict[str, dict[str, float]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in arms:
        arm = row["arm_id"]
        tb = token_breakdown[arm]
        trial_count = i(row["trial_count"])
        success_count = i(row["success_count"])
        clean_success_count = i(row["clean_success_count"])
        adjusted = f(row["adjusted_cost_usd"])
        recorded = f(row["recorded_cost_usd"])
        pass_rate = success_count / trial_count if trial_count else 0.0
        mean_adjusted_per_attempt = adjusted / trial_count if trial_count else 0.0
        mean_recorded_per_attempt = recorded / trial_count if trial_count else 0.0
        total_tokens = tb["total_tokens"]
        failure_tokens = tb["failure_incomplete_tokens"]
        unclean_tokens = tb["unclean_tokens"]
        failure_cost = f(row["adjusted_failure_or_incomplete_cost_usd"])
        clean_cost = f(row["adjusted_clean_success_cost_usd"])
        exception_success_cost = f(row["adjusted_exception_success_signal_cost_usd"])
        unclean_cost = adjusted - clean_cost

        out.append(
            {
                "arm_id": arm,
                "label": short_arm(arm),
                "backend_model": row["backend_model"],
                "provider": row["provider"],
                "trial_count": trial_count,
                "success_count": success_count,
                "clean_success_count": clean_success_count,
                "pass_rate": pass_rate,
                "recorded_cost_usd": recorded,
                "adjusted_cost_usd": adjusted,
                "known_accounting_gap_usd": adjusted - recorded,
                "mean_recorded_cost_per_attempt_usd": mean_recorded_per_attempt,
                "mean_adjusted_cost_per_attempt_usd": mean_adjusted_per_attempt,
                "mean_adjusted_cost_per_3_attempt_task_usd": mean_adjusted_per_attempt * 3,
                "cost_per_clean_success_usd": f(row["adjusted_cost_per_clean_success"]),
                "cost_per_any_success_usd": f(row["adjusted_cost_per_any_success"]),
                "failure_incomplete_spend_usd": failure_cost,
                "exception_success_signal_spend_usd": exception_success_cost,
                "unclean_spend_usd": unclean_cost,
                "failure_incomplete_spend_share": failure_cost / adjusted if adjusted else 0.0,
                "unclean_spend_share": unclean_cost / adjusted if adjusted else 0.0,
                "total_tokens": total_tokens,
                "failure_incomplete_tokens": failure_tokens,
                "unclean_tokens": unclean_tokens,
                "failure_incomplete_token_share": failure_tokens / total_tokens if total_tokens else 0.0,
                "unclean_token_share": unclean_tokens / total_tokens if total_tokens else 0.0,
                "unresolved_cost_count": i(row["unresolved_missing_cost_count"]),
                "cost_confidence": row["cost_confidence"],
                "notes": row["notes"],
            }
        )
    return out


def pareto_frontier(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frontier: list[dict[str, Any]] = []
    best_rate = -1.0
    for row in sorted(rows, key=lambda r: (r["mean_adjusted_cost_per_attempt_usd"], -r["pass_rate"])):
        if row["pass_rate"] > best_rate + 1e-12:
            frontier.append(row)
            best_rate = row["pass_rate"]
    return frontier


def write_summary_table(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "arm_id",
        "backend_model",
        "provider",
        "success_count",
        "trial_count",
        "pass_rate",
        "recorded_cost_usd",
        "adjusted_cost_usd",
        "known_accounting_gap_usd",
        "mean_adjusted_cost_per_attempt_usd",
        "mean_adjusted_cost_per_3_attempt_task_usd",
        "cost_per_clean_success_usd",
        "failure_incomplete_spend_usd",
        "unclean_spend_usd",
        "failure_incomplete_spend_share",
        "unclean_spend_share",
        "failure_incomplete_tokens",
        "unclean_tokens",
        "failure_incomplete_token_share",
        "unclean_token_share",
        "unresolved_cost_count",
        "cost_confidence",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in sorted(rows, key=lambda r: (-r["pass_rate"], r["mean_adjusted_cost_per_attempt_usd"])):
            writer.writerow({k: row[k] for k in fieldnames})


def write_token_breakdown(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = [
        "arm_id",
        "total_tokens",
        "failure_incomplete_tokens",
        "unclean_tokens",
        "failure_incomplete_token_share",
        "unclean_token_share",
        "failure_incomplete_spend_usd",
        "unclean_spend_usd",
        "failure_incomplete_spend_share",
        "unclean_spend_share",
    ]
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, delimiter="\t")
        writer.writeheader()
        for row in sorted(rows, key=lambda r: r["unclean_spend_share"], reverse=True):
            writer.writerow({k: row[k] for k in fieldnames})


def svg_text(x: float, y: float, text: str, *, size: int = 12, weight: str = "400", fill: str = "#1f2937") -> str:
    return f'<text x="{x:.1f}" y="{y:.1f}" font-size="{size}" font-weight="{weight}" fill="{fill}">{html.escape(text)}</text>'


def write_frontier_svg(path: Path, rows: list[dict[str, Any]], frontier: list[dict[str, Any]]) -> None:
    width, height = 1200, 820
    ml, mr, mt, mb = 110, 70, 80, 110
    plot_w = width - ml - mr
    plot_h = height - mt - mb

    x_vals = [r["mean_adjusted_cost_per_attempt_usd"] for r in rows]
    y_vals = [r["pass_rate"] for r in rows]
    x_min = 0.0
    x_max = max(x_vals) * 1.08
    y_min = max(0.0, min(y_vals) - 0.08)
    y_max = min(1.0, max(y_vals) + 0.08)

    def sx(x: float) -> float:
        return ml + (x - x_min) / (x_max - x_min) * plot_w

    def sy(y: float) -> float:
        return mt + (y_max - y) / (y_max - y_min) * plot_h

    frontier_ids = {r["arm_id"] for r in frontier}

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">',
        '<rect width="100%" height="100%" rx="28" fill="#ffffff"/>',
        svg_text(ml, 42, "Phase 3 adjusted cost/performance frontier", size=26, weight="700"),
        svg_text(ml, 68, "Valid full-suite arms; x-axis uses mean adjusted cost per benchmark attempt.", size=14, fill="#6b7280"),
    ]

    # Grid and axes.
    for tick in [0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        if tick <= x_max:
            x = sx(tick)
            parts.append(f'<line x1="{x:.1f}" y1="{mt}" x2="{x:.1f}" y2="{height-mb}" stroke="#e5e7eb" stroke-width="1"/>')
            parts.append(svg_text(x - 16, height - mb + 36, f"${tick:.1f}", size=13, fill="#6b7280"))

    y_ticks = [0.20, 0.30, 0.40, 0.50, 0.60, 0.70, 0.80]
    for tick in y_ticks:
        if y_min <= tick <= y_max:
            y = sy(tick)
            parts.append(f'<line x1="{ml}" y1="{y:.1f}" x2="{width-mr}" y2="{y:.1f}" stroke="#e5e7eb" stroke-width="1"/>')
            parts.append(svg_text(38, y + 4, f"{tick*100:.0f}%", size=13, fill="#6b7280"))

    parts.append(f'<line x1="{ml}" y1="{height-mb}" x2="{width-mr}" y2="{height-mb}" stroke="#9ca3af" stroke-width="1.2"/>')
    parts.append(f'<line x1="{ml}" y1="{mt}" x2="{ml}" y2="{height-mb}" stroke="#9ca3af" stroke-width="1.2"/>')
    parts.append(svg_text(width / 2 - 165, height - 28, "Mean adjusted cost per benchmark attempt ($)", size=16, weight="700", fill="#111827"))
    parts.append(f'<text x="26" y="{height/2+120:.1f}" font-size="16" font-weight="700" fill="#111827" transform="rotate(-90 26,{height/2+120:.1f})">Overall pass rate</text>')

    # Frontier shaded area and line.
    frontier_points = [(sx(r["mean_adjusted_cost_per_attempt_usd"]), sy(r["pass_rate"])) for r in frontier]
    if frontier_points:
        polygon = [(ml, height - mb)] + frontier_points + [(width - mr, frontier_points[-1][1]), (width - mr, height - mb)]
        points = " ".join(f"{x:.1f},{y:.1f}" for x, y in polygon)
        parts.append(f'<polygon points="{points}" fill="#fee2e2" opacity="0.55"/>')
        line_points = " ".join(f"{x:.1f},{y:.1f}" for x, y in frontier_points)
        parts.append(f'<polyline points="{line_points}" fill="none" stroke="#ef4444" stroke-width="4" stroke-dasharray="10 9"/>')

    # Points and labels.
    for row in sorted(rows, key=lambda r: r["pass_rate"]):
        x = sx(row["mean_adjusted_cost_per_attempt_usd"])
        y = sy(row["pass_rate"])
        is_frontier = row["arm_id"] in frontier_ids
        fill = "#ef4444" if is_frontier else "#475569"
        stroke = "#ffffff"
        radius = 10 if is_frontier else 8
        parts.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{radius}" fill="{fill}" stroke="{stroke}" stroke-width="3"/>')

    label_offsets = {
        "router-glm-5.1": (12, -22),
        "router-glm-5.2": (12, -18),
        "router-anthropic-fable-5": (12, -18),
        "router-deepseek-flash": (12, -18),
        "router-gpt-5.5": (-180, -18),
        "router-gpt-5.4": (-178, 26),
        "router-anthropic-haiku-sanitized": (12, 26),
        "router-gemini-flash": (12, 26),
        "router-anthropic-opus": (12, 26),
    }

    for row in rows:
        x = sx(row["mean_adjusted_cost_per_attempt_usd"])
        y = sy(row["pass_rate"])
        dx, dy = label_offsets.get(row["arm_id"], (12, -12))
        label = f'{row["label"]} · {pct(row["pass_rate"])} · {money(row["mean_adjusted_cost_per_attempt_usd"])}/attempt'
        fill = "#111827" if row["arm_id"] in frontier_ids else "#6b7280"
        parts.append(svg_text(x + dx, y + dy, label, size=12, weight="700" if row["arm_id"] in frontier_ids else "400", fill=fill))

    parts.append("</svg>")
    path.write_text("\n".join(parts) + "\n")


def markdown_table(rows: list[dict[str, Any]], *, limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    lines = [
        "| Arm | Pass rate | Adjusted cost | Cost / clean success | Failure/incomplete spend | Unclean spend | Unclean token share | Confidence |",
        "|---|---:|---:|---:|---:|---:|---:|---|",
    ]
    for r in selected:
        lines.append(
            "| {arm} | {pass_rate} | {adjusted} | {clean_cost} | {failure_spend} | {unclean_spend} | {unclean_tokens} | {confidence} |".format(
                arm=r["arm_id"],
                pass_rate=pct(r["pass_rate"]),
                adjusted=money(r["adjusted_cost_usd"]),
                clean_cost=money(r["cost_per_clean_success_usd"]),
                failure_spend=f'{money(r["failure_incomplete_spend_usd"])} ({pct(r["failure_incomplete_spend_share"])})',
                unclean_spend=f'{money(r["unclean_spend_usd"])} ({pct(r["unclean_spend_share"])})',
                unclean_tokens=pct(r["unclean_token_share"]),
                confidence=r["cost_confidence"],
            )
        )
    return "\n".join(lines)


def write_report(path: Path, rows: list[dict[str, Any]], frontier: list[dict[str, Any]], *, date: str, chart_rel: str, summary_rel: str, token_rel: str) -> None:
    total_trials = sum(r["trial_count"] for r in rows)
    total_success = sum(r["success_count"] for r in rows)
    recorded = sum(r["recorded_cost_usd"] for r in rows)
    adjusted = sum(r["adjusted_cost_usd"] for r in rows)
    gap = adjusted - recorded
    clean_spend = sum(f(r["adjusted_clean_success_cost_usd"]) if "adjusted_clean_success_cost_usd" in r else 0 for r in rows)
    failure_spend = sum(r["failure_incomplete_spend_usd"] for r in rows)
    unclean_spend = sum(r["unclean_spend_usd"] for r in rows)
    total_tokens = sum(r["total_tokens"] for r in rows)
    failure_tokens = sum(r["failure_incomplete_tokens"] for r in rows)
    unclean_tokens = sum(r["unclean_tokens"] for r in rows)
    unresolved = sum(r["unresolved_cost_count"] for r in rows)

    best_pass = max(rows, key=lambda r: (r["pass_rate"], -r["mean_adjusted_cost_per_attempt_usd"]))
    best_clean_cost = min([r for r in rows if r["clean_success_count"] > 0], key=lambda r: r["cost_per_clean_success_usd"])
    low_cost_frontier = frontier[0]
    frontier_names = ", ".join(r["arm_id"] for r in frontier)

    rows_by_pass = sorted(rows, key=lambda r: (-r["pass_rate"], r["mean_adjusted_cost_per_attempt_usd"]))
    rows_by_value = sorted([r for r in rows if r["pass_rate"] >= 0.60], key=lambda r: r["cost_per_clean_success_usd"])

    lines = [
        f"# Phase 3 sponsor summary: adjusted cost frontier ({date})",
        "",
        "## Executive summary",
        "",
        f"- Scope: {len(rows)} valid full-suite arms, {total_trials} benchmark attempts, and {total_success} raw successes.",
        f"- Best raw pass rate: **{best_pass['arm_id']}** at **{pct(best_pass['pass_rate'])}**, with adjusted known cost of **{money(best_pass['adjusted_cost_usd'])}**.",
        f"- Lowest cost per clean success among arms at or above 60% pass rate: **{best_clean_cost['arm_id']}** at **{money(best_clean_cost['cost_per_clean_success_usd'])}** per clean success.",
        f"- Recorded cost was **{money(recorded)}**; adjusted known cost is **{money(adjusted)}**, revealing a known accounting gap of **{money(gap)}**.",
        f"- Failure/incomplete spend was **{money(failure_spend)}** ({pct(failure_spend / adjusted if adjusted else 0)} of adjusted known cost). Unclean spend was **{money(unclean_spend)}** ({pct(unclean_spend / adjusted if adjusted else 0)}).",
        f"- Failure/incomplete attempts consumed **{failure_tokens:,.0f}** input+output tokens ({pct(failure_tokens / total_tokens if total_tokens else 0)}). Non-clean outcomes consumed **{unclean_tokens:,.0f}** input+output tokens ({pct(unclean_tokens / total_tokens if total_tokens else 0)}).",
        f"- Remaining unresolved cost rows: **{unresolved}**, all rows without usable cost or token metadata in the adjusted-cost layer.",
        "",
        "## Cost/performance frontier",
        "",
        f"![Adjusted cost frontier]({chart_rel})",
        "",
        f"The Pareto frontier by pass rate versus mean adjusted cost per benchmark attempt is: **{frontier_names}**.",
        "Because the full Terminal-Bench suite uses three attempts per task, the chart uses cost per benchmark attempt. Multiply by three for a rough three-attempt-per-task budget.",
        "",
        "## Sponsor summary table",
        "",
        markdown_table(rows_by_pass),
        "",
        "## Value-oriented shortlist",
        "",
        markdown_table(rows_by_value, limit=8),
        "",
        "## Cost accounting and nonproductive spend",
        "",
        f"- The original recorded-cost view understated known spend by **{money(gap)}**, or **{pct(gap / recorded if recorded else 0)}** over recorded cost.",
        "- The gap is concentrated in errored or operationally unclean paths, which is why adjusted cost is more appropriate for sponsor-facing cost comparisons.",
        f"- Failure/incomplete spend directly measures money spent on attempts that did not pass: **{money(failure_spend)}**.",
        f"- Unclean spend includes failures, incomplete outcomes, and exception-with-success-signal rows: **{money(unclean_spend)}**.",
        f"- Token-volume waste is directionally similar: failure/incomplete attempts consumed **{failure_tokens:,.0f}** tokens; all non-clean outcomes consumed **{unclean_tokens:,.0f}** tokens.",
        "",
        "## Method note",
        "",
        "- Recorded cost remains preserved as imported artifact truth.",
        "- Adjusted known cost adds reconstructed missing-cost rows using configured pricing snapshots or same-arm empirical estimates.",
        "- Invalid/quarantined runs are excluded from this valid-only comparison.",
        "- Token-volume analysis uses input + output tokens. Cache tokens affect cost but are not added to the token-volume numerator to avoid double-counting cached input.",
        "- Provider invoices/dashboards remain separate evidence; this report is a benchmark-level adjusted-cost view.",
        "",
        "## Generated artifacts",
        "",
        f"- Frontier chart: `{chart_rel}`",
        f"- Sponsor summary table: `{summary_rel}`",
        f"- Token/outcome breakdown: `{token_rel}`",
        "",
    ]

    path.write_text("\n".join(lines))


def main() -> None:
    args = parse_args()
    args.out_dir.mkdir(parents=True, exist_ok=True)
    args.report_dir.mkdir(parents=True, exist_ok=True)

    arms = read_tsv(args.arm_tsv)
    trials = read_tsv(args.trial_tsv)

    token_breakdown = outcome_token_breakdown(trials)
    rows = enrich_arm_rows(arms, token_breakdown)
    frontier = pareto_frontier(rows)

    summary_tsv = args.out_dir / f"phase3_sponsor_summary_table_{args.date}.tsv"
    token_tsv = args.out_dir / f"phase3_token_outcome_breakdown_{args.date}.tsv"
    chart_svg = args.out_dir / f"phase3_adjusted_cost_frontier_{args.date}.svg"
    report_md = args.report_dir / f"PHASE3_SPONSOR_SUMMARY_{args.date}.md"

    write_summary_table(summary_tsv, rows)
    write_token_breakdown(token_tsv, rows)
    write_frontier_svg(chart_svg, rows, frontier)
    write_report(
        report_md,
        rows,
        frontier,
        date=args.date,
        chart_rel=f"../../../results/phase3/reporting/{chart_svg.name}",
        summary_rel=f"results/phase3/reporting/{summary_tsv.name}",
        token_rel=f"results/phase3/reporting/{token_tsv.name}",
    )

    print(chart_svg)
    print(summary_tsv)
    print(token_tsv)
    print(report_md)


if __name__ == "__main__":
    main()
