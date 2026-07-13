from __future__ import annotations

import argparse
import csv
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DATE = "20260713"
DEFAULT_SUMMARY_TSV = ROOT / "results/phase3/reporting/phase3_sponsor_summary_table_20260713.tsv"
DEFAULT_TOKEN_TSV = ROOT / "results/phase3/reporting/phase3_token_outcome_breakdown_20260713.tsv"
DEFAULT_REPORT_DIR = ROOT / "docs/reports/phase3"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a Databricks-style Phase 3 benchmark analysis report.")
    parser.add_argument("--date", default=DEFAULT_DATE)
    parser.add_argument("--summary-tsv", type=Path, default=DEFAULT_SUMMARY_TSV)
    parser.add_argument("--token-tsv", type=Path, default=DEFAULT_TOKEN_TSV)
    parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    return parser.parse_args()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def f(value: Any) -> float:
    if value is None:
        return 0.0
    text = str(value).strip()
    if not text:
        return 0.0
    return float(text)


def money(value: float) -> str:
    return f"${value:,.2f}"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def intfmt(value: float) -> str:
    return f"{value:,.0f}"


def arm(rows: list[dict[str, Any]], arm_id: str) -> dict[str, Any]:
    for row in rows:
        if row["arm_id"] == arm_id:
            return row
    raise KeyError(arm_id)


def enrich(rows: list[dict[str, str]]) -> list[dict[str, Any]]:
    out: list[dict[str, Any]] = []
    for row in rows:
        enriched = dict(row)
        for key in [
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
        ]:
            enriched[key] = f(row.get(key))
        for key in ["success_count", "trial_count", "unresolved_cost_count"]:
            enriched[key] = int(round(f(row.get(key))))
        out.append(enriched)
    return out


def pareto_frontier(rows: list[dict[str, Any]]) -> list[dict[str, Any]]:
    frontier: list[dict[str, Any]] = []
    best_rate = -1.0
    for row in sorted(rows, key=lambda r: (r["mean_adjusted_cost_per_attempt_usd"], -r["pass_rate"])):
        if row["pass_rate"] > best_rate + 1e-12:
            frontier.append(row)
            best_rate = row["pass_rate"]
    return frontier


def md_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]], *, limit: int | None = None) -> str:
    selected = rows[:limit] if limit else rows
    header = "| " + " | ".join(label for label, _ in columns) + " |"
    sep = "| " + " | ".join("---" if idx == 0 else "---:" for idx, _ in enumerate(columns)) + " |"
    lines = [header, sep]
    for row in selected:
        cells = []
        for _, key in columns:
            value = row[key]
            if key.endswith("_usd") or key in {
                "adjusted_cost_usd",
                "recorded_cost_usd",
                "cost_per_clean_success_usd",
                "failure_incomplete_spend_usd",
                "unclean_spend_usd",
            }:
                cells.append(money(float(value)))
            elif key.endswith("_share") or key == "pass_rate":
                cells.append(pct(float(value)))
            elif key.endswith("_tokens"):
                cells.append(intfmt(float(value)))
            else:
                cells.append(str(value))
        lines.append("| " + " | ".join(cells) + " |")
    return "\n".join(lines)


def main() -> None:
    args = parse_args()
    args.report_dir.mkdir(parents=True, exist_ok=True)

    rows = enrich(read_tsv(args.summary_tsv))
    frontier = pareto_frontier(rows)

    rows_by_pass = sorted(rows, key=lambda r: (-r["pass_rate"], r["mean_adjusted_cost_per_attempt_usd"]))
    rows_by_clean_cost = sorted([r for r in rows if r["pass_rate"] >= 0.60], key=lambda r: r["cost_per_clean_success_usd"])
    rows_by_unclean_spend = sorted(rows, key=lambda r: r["unclean_spend_usd"], reverse=True)
    rows_by_unclean_share = sorted(rows, key=lambda r: r["unclean_spend_share"], reverse=True)

    total_trials = sum(r["trial_count"] for r in rows)
    total_success = sum(r["success_count"] for r in rows)
    recorded = sum(r["recorded_cost_usd"] for r in rows)
    adjusted = sum(r["adjusted_cost_usd"] for r in rows)
    gap = adjusted - recorded
    failure_spend = sum(r["failure_incomplete_spend_usd"] for r in rows)
    unclean_spend = sum(r["unclean_spend_usd"] for r in rows)
    failure_tokens = sum(r["failure_incomplete_tokens"] for r in rows)
    unclean_tokens = sum(r["unclean_tokens"] for r in rows)
    total_tokens = sum(f(r["failure_incomplete_tokens"]) / f(r["failure_incomplete_token_share"]) if f(r["failure_incomplete_token_share"]) else 0 for r in rows)
    unresolved = sum(r["unresolved_cost_count"] for r in rows)

    gpt55 = arm(rows, "router-gpt-5.5")
    glm51 = arm(rows, "router-glm-5.1")
    glm52 = arm(rows, "router-glm-5.2")
    fable = arm(rows, "router-anthropic-fable-5")
    ds_flash = arm(rows, "router-deepseek-flash")
    haiku = arm(rows, "router-anthropic-haiku-sanitized")
    sonnet = arm(rows, "router-anthropic-sonnet")
    gem_flash = arm(rows, "router-gemini-flash")
    opus = arm(rows, "router-anthropic-opus")

    frontier_names = ", ".join(r["arm_id"] for r in frontier)

    path = args.report_dir / f"PHASE3_BENCHMARK_ANALYSIS_{args.date}.md"

    lines = [
        f"# Benchmarking coding-agent backends on Terminal-Bench/Harbor ({args.date})",
        "",
        "## Overview",
        "",
        "We built Phase 3 to answer a practical question: which Claude Code backend routes deliver the best end-to-end coding-agent performance for the money, and where does spend get consumed when attempts fail?",
        "",
        f"The valid full-suite comparison covers **{len(rows)} model/backend arms**, **{total_trials} benchmark attempts**, and **{total_success} successes** on a fixed Terminal-Bench 2.0 task suite. Claude Code remained the agent harness while the backend route varied across Anthropic, DeepSeek, OpenAI, Google Gemini, GLM/Z.AI, Grok/xAI, Kimi/Moonshot, and Qwen/DashScope.",
        "",
        "Like the Databricks coding-agent benchmark, this analysis emphasizes task-level cost/performance rather than headline token price. The important difference is that our Phase 3 accounting layer also quantifies spend and token volume consumed by failed, errored, or operationally unclean attempts.",
        "",
        "## Main conclusions",
        "",
        f"1. **No single route dominates the frontier.** The adjusted cost/performance Pareto frontier is **{frontier_names}**.",
        f"2. **The highest pass rate came from GPT-5.5**, with **{gpt55['success_count']}/{gpt55['trial_count']} successes ({pct(gpt55['pass_rate'])})**, but it was one of the most expensive arms at **{money(gpt55['adjusted_cost_usd'])}** adjusted known cost.",
        f"3. **Several lower-cost arms were economically compelling.** GLM 5.1 reached **{pct(glm51['pass_rate'])}** at **{money(glm51['adjusted_cost_usd'])}** adjusted cost, GLM 5.2 reached **{pct(glm52['pass_rate'])}** at **{money(glm52['adjusted_cost_usd'])}**, and Fable reached **{pct(fable['pass_rate'])}** at **{money(fable['adjusted_cost_usd'])}**.",
        f"4. **Recorded cost materially understated spend.** Recorded cost was **{money(recorded)}**, while adjusted known cost was **{money(adjusted)}**, a known accounting gap of **{money(gap)}** ({pct(gap / recorded if recorded else 0)} over recorded cost).",
        f"5. **Failures have a direct economic footprint.** Failure/incomplete spend was **{money(failure_spend)}** ({pct(failure_spend / adjusted if adjusted else 0)} of adjusted known cost). Broader unclean spend was **{money(unclean_spend)}** ({pct(unclean_spend / adjusted if adjusted else 0)}).",
        f"6. **Token-volume waste is large enough to operationalize.** Failure/incomplete attempts consumed **{intfmt(failure_tokens)}** input+output tokens; all non-clean outcomes consumed **{intfmt(unclean_tokens)}** tokens.",
        "",
        "## Figure 1: adjusted cost vs. benchmark performance",
        "",
        "![Phase 3 adjusted cost frontier](../../../results/phase3/reporting/phase3_adjusted_cost_frontier_20260713.svg)",
        "",
        "The chart plots raw pass rate against mean adjusted cost per benchmark attempt. Because each full-suite task has three attempts, the per-attempt number can be multiplied by three for a rough three-attempt-per-task budget.",
        "",
        "The frontier shows three practical zones:",
        "",
        f"- **Low-cost frontier:** {glm51['arm_id']} and {glm52['arm_id']} delivered meaningful pass rates at the lowest adjusted costs.",
        f"- **Middle frontier:** {fable['arm_id']} and {ds_flash['arm_id']} offered stronger pass rates without moving into premium-cost territory.",
        f"- **Premium frontier:** {gpt55['arm_id']} delivered the best raw pass rate, but at substantially higher adjusted cost.",
        "",
        "## Models cluster into capability and efficiency tiers",
        "",
        "A pass-rate-only view hides important economic differences. The table below groups arms by performance first, then exposes adjusted cost, clean-success cost, and nonproductive spend.",
        "",
        md_table(
            rows_by_pass,
            [
                ("Arm", "arm_id"),
                ("Pass rate", "pass_rate"),
                ("Adjusted cost", "adjusted_cost_usd"),
                ("Cost / clean success", "cost_per_clean_success_usd"),
                ("Failure/incomplete spend", "failure_incomplete_spend_usd"),
                ("Unclean spend", "unclean_spend_usd"),
                ("Confidence", "cost_confidence"),
            ],
        ),
        "",
        "The strongest absolute result was GPT-5.5, but the economical frontier was more diverse. GLM 5.1 and GLM 5.2 were much cheaper, while Fable and DeepSeek Flash occupied a useful middle tier. Opus matched Fable's raw pass rate, but its adjusted cost and failure spend were much higher.",
        "",
        "## Price-per-token is not the same as price-per-task",
        "",
        "A recurring theme in the Databricks report is that developers should not infer end-to-end coding-agent cost from listed token prices alone. Our data shows the same pattern. The benchmark should be priced by completed task attempts, not just model token rates.",
        "",
        f"Haiku is the clearest example in our run: despite being positioned as a cheaper model class, {haiku['arm_id']} produced only **{pct(haiku['pass_rate'])}** pass rate while costing **{money(haiku['adjusted_cost_usd'])}** adjusted known cost, with **{money(haiku['failure_incomplete_spend_usd'])}** spent on failed/incomplete attempts.",
        "",
        f"DeepSeek Flash shows the opposite nuance: it consumed a large number of tokens on non-clean outcomes (**{pct(ds_flash['unclean_token_share'])}** unclean token share), but cache-aware pricing kept the direct unclean spend to **{money(ds_flash['unclean_spend_usd'])}**.",
        "",
        "## Failure and unclean spend are first-class benchmark outputs",
        "",
        "Traditional benchmark summaries treat failures as quality outcomes. Phase 3 adds a cost lens: failed or operationally unclean attempts also consume money, tokens, and wall-clock time.",
        "",
        f"- Failure/incomplete spend: **{money(failure_spend)}**.",
        f"- Unclean spend, including exception-with-success-signal rows: **{money(unclean_spend)}**.",
        f"- Failure/incomplete token volume: **{intfmt(failure_tokens)}** input+output tokens.",
        f"- Non-clean token volume: **{intfmt(unclean_tokens)}** input+output tokens.",
        f"- Remaining unresolved cost rows: **{unresolved}**, all without usable cost or token metadata.",
        "",
        md_table(
            rows_by_unclean_spend,
            [
                ("Arm", "arm_id"),
                ("Unclean spend", "unclean_spend_usd"),
                ("Unclean spend share", "unclean_spend_share"),
                ("Unclean tokens", "unclean_tokens"),
                ("Unclean token share", "unclean_token_share"),
                ("Pass rate", "pass_rate"),
            ],
            limit=8,
        ),
        "",
        "This view changes how some arms should be interpreted. Kimi, Grok, Qwen, Gemini Flash, and Haiku had comparatively high unclean-spend shares. GPT-5.5 had high absolute unclean spend because its total cost was high, but its share was lower than many mid-tier arms.",
        "",
        "## Qualitative findings from trajectory and artifact review",
        "",
        "The qualitative review helps explain why pure pass-rate and cost summaries are insufficient:",
        "",
        f"- **Exception-heavy paths can distort both quality and cost.** Sonnet's Phase 3 route produced only **{pct(sonnet['pass_rate'])}** pass rate and had many no-token unresolved rows. This should not be read as a general statement that Sonnet is intrinsically weak; it is evidence that the router/harness path had operational issues in this sweep.",
        f"- **Reward 1 with exception markers needs its own bucket.** Fable had clean successes plus exception-with-success-signal rows, which is why its failure/incomplete spend is low but broader unclean spend is higher (**{money(fable['unclean_spend_usd'])}**).",
        f"- **Some failed attempts are expensive because the model keeps working.** Opus reached **{pct(opus['pass_rate'])}**, but failed/incomplete spend was **{money(opus['failure_incomplete_spend_usd'])}**, much higher than Fable at the same raw pass rate.",
        f"- **Some failures are cheap in dollars but expensive in tokens.** DeepSeek Flash had **{pct(ds_flash['unclean_token_share'])}** unclean token share but only **{money(ds_flash['unclean_spend_usd'])}** unclean spend.",
        f"- **Low pass-rate routes can still burn meaningful budget.** Gemini Flash had **{pct(gem_flash['pass_rate'])}** pass rate, **{money(gem_flash['adjusted_cost_usd'])}** adjusted cost, and **{pct(gem_flash['unclean_spend_share'])}** unclean spend share.",
        "",
        "The qualitative pattern is that models do not simply fail or succeed. They fail in different operational modes: clean wrong answers, exception failures after real token usage, no-token/no-op signatures, and success signals paired with exception markers. Those modes matter because they have different cost and remediation implications.",
        "",
        "## What this suggests operationally",
        "",
        "The benchmark supports a routing strategy rather than a single default model:",
        "",
        f"- Use **{gpt55['arm_id']}** when maximum raw success probability matters and premium cost is acceptable.",
        f"- Consider **{fable['arm_id']}**, **{ds_flash['arm_id']}**, and **{glm52['arm_id']}** for strong value-oriented routing.",
        f"- Consider **{glm51['arm_id']}** where cost per clean success is the main constraint.",
        "- Treat high unclean-spend arms as candidates for harness, timeout, context-management, or route debugging before broad deployment.",
        "- Track cost and token waste as first-class outcomes; otherwise, failed attempts can look cheaper than they really are.",
        "",
        "## Methodology",
        "",
        "- Benchmark: Terminal-Bench 2.0 full suite.",
        "- Scope: 20 tasks × 3 attempts × 15 valid arms = 900 attempts.",
        "- Harness: Claude Code fixed as the agent harness.",
        "- Comparison: valid-only full-suite arms; invalid/quarantined runs excluded.",
        "- Cost metric: adjusted known cost, preserving recorded cost while adding reconstructed missing-cost rows.",
        "- Token-waste metric: input + output tokens by outcome bucket; cache tokens affect cost but are not double-counted in token volume.",
        "- Correctness: verifier/test outcomes, not LLM-as-judge scoring.",
        "",
        "## Caveats",
        "",
        "- Adjusted known cost is benchmark-level accounting, not a substitute for provider invoices.",
        "- Same-arm empirical reconstruction is lower confidence than configured-price reconstruction.",
        "- Some cost rows remain unresolved when neither cost nor token metadata exists.",
        "- Terminal-Bench tasks are not the same as internal production PRs, so this report should guide backend selection experiments rather than claim universal model rankings.",
        "",
    ]

    path.write_text("\n".join(lines) + "\n")
    print(path)


if __name__ == "__main__":
    main()
