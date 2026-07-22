from __future__ import annotations

import argparse
import csv
import html
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_INPUT = ROOT / "results/phase3/reporting/phase3_sponsor_summary_table_20260713.tsv"
DEFAULT_OUTPUT = ROOT / "results/phase3/reporting/phase3_adjusted_cost_frontier_interactive_20260713.html"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate a standalone interactive HTML/SVG cost frontier chart.")
    parser.add_argument("--input-tsv", type=Path, default=DEFAULT_INPUT)
    parser.add_argument("--output-html", type=Path, default=DEFAULT_OUTPUT)
    return parser.parse_args()


def read_tsv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="") as handle:
        return list(csv.DictReader(handle, delimiter="\t"))


def f(value: str | None) -> float:
    text = str(value or "").strip()
    return float(text) if text else 0.0


def money(value: float) -> str:
    return f"${value:,.2f}"


def pct(value: float) -> str:
    return f"{value * 100:.1f}%"


def pareto_frontier(rows: list[dict]) -> list[dict]:
    frontier: list[dict] = []
    best_rate = -1.0
    for row in sorted(rows, key=lambda r: (r["cost_per_attempt"], -r["pass_rate"])):
        if row["pass_rate"] > best_rate + 1e-12:
            frontier.append(row)
            best_rate = row["pass_rate"]
    return frontier


def tooltip(row: dict) -> str:
    return (
        f"<strong>{html.escape(row['arm_id'])}</strong><br>"
        f"Model: {html.escape(row['backend_model'])}<br>"
        f"Provider: {html.escape(row['provider'])}<br>"
        f"Pass rate: {pct(row['pass_rate'])} ({row['success_count']}/{row['trial_count']})<br>"
        f"Cost / attempt: {money(row['cost_per_attempt'])}<br>"
        f"Adjusted total cost: {money(row['adjusted_cost'])}<br>"
        f"Cost / clean success: {money(row['cost_per_clean_success'])}<br>"
        f"Failure/incomplete spend: {money(row['failure_spend'])} ({pct(row['failure_share'])})<br>"
        f"Unclean spend: {money(row['unclean_spend'])} ({pct(row['unclean_share'])})<br>"
        f"Known accounting gap: {money(row['known_gap'])}<br>"
        f"Unresolved cost rows: {row['unresolved_count']}<br>"
        f"Cost confidence: {html.escape(row['confidence'])}"
    )


def main() -> None:
    args = parse_args()

    rows: list[dict] = []
    for row in read_tsv(args.input_tsv):
        rows.append(
            {
                "arm_id": row["arm_id"],
                "backend_model": row.get("backend_model", ""),
                "provider": row.get("provider", ""),
                "success_count": int(round(f(row.get("success_count")))),
                "trial_count": int(round(f(row.get("trial_count")))),
                "pass_rate": f(row.get("pass_rate")),
                "cost_per_attempt": f(row.get("mean_adjusted_cost_per_attempt_usd")),
                "adjusted_cost": f(row.get("adjusted_cost_usd")),
                "cost_per_clean_success": f(row.get("cost_per_clean_success_usd")),
                "failure_spend": f(row.get("failure_incomplete_spend_usd")),
                "unclean_spend": f(row.get("unclean_spend_usd")),
                "failure_share": f(row.get("failure_incomplete_spend_share")),
                "unclean_share": f(row.get("unclean_spend_share")),
                "known_gap": f(row.get("known_accounting_gap_usd")),
                "unresolved_count": int(round(f(row.get("unresolved_cost_count")))),
                "confidence": row.get("cost_confidence", ""),
            }
        )

    frontier = pareto_frontier(rows)
    frontier_ids = {row["arm_id"] for row in frontier}

    width = 1120
    height = 650
    left = 82
    right = 34
    top = 48
    bottom = 78
    plot_w = width - left - right
    plot_h = height - top - bottom

    x_min = 0.25
    x_max = max(row["cost_per_attempt"] for row in rows) * 1.08
    y_min = 0.18
    y_max = 0.77

    def sx(x: float) -> float:
        return left + ((x - x_min) / (x_max - x_min)) * plot_w

    def sy(y: float) -> float:
        return top + ((y_max - y) / (y_max - y_min)) * plot_h

    svg_parts: list[str] = [
        f'<svg class="chart" viewBox="0 0 {width} {height}" role="img" aria-label="Cost versus pass rate frontier">',
        '<rect x="0" y="0" width="1120" height="650" rx="14" fill="#ffffff"/>',
    ]

    for x_tick in [0.5, 1.0, 1.5, 2.0, 2.5, 3.0]:
        if x_min <= x_tick <= x_max:
            x = sx(x_tick)
            svg_parts.append(f'<line class="grid" x1="{x:.1f}" y1="{top}" x2="{x:.1f}" y2="{height-bottom}"/>')
            svg_parts.append(f'<text class="tick" x="{x:.1f}" y="{height-bottom+34}" text-anchor="middle">${x_tick:.1f}</text>')

    for y_tick in [0.2, 0.3, 0.4, 0.5, 0.6, 0.7]:
        y = sy(y_tick)
        svg_parts.append(f'<line class="grid" x1="{left}" y1="{y:.1f}" x2="{width-right}" y2="{y:.1f}"/>')
        svg_parts.append(f'<text class="tick" x="{left-18}" y="{y+4:.1f}" text-anchor="end">{int(y_tick * 100)}%</text>')

    svg_parts.extend(
        [
            f'<line class="axis" x1="{left}" y1="{height-bottom}" x2="{width-right}" y2="{height-bottom}"/>',
            f'<line class="axis" x1="{left}" y1="{top}" x2="{left}" y2="{height-bottom}"/>',
            f'<text class="axis-label" x="{width/2}" y="{height-26}" text-anchor="middle">Cost per benchmark attempt (USD)</text>',
            f'<text class="axis-label" x="24" y="{height/2}" text-anchor="middle" transform="rotate(-90 24 {height/2})">Pass rate</text>',
        ]
    )

    frontier_points = " ".join(f"{sx(row['cost_per_attempt']):.1f},{sy(row['pass_rate']):.1f}" for row in frontier)
    svg_parts.append(f'<polyline class="frontier-line" points="{frontier_points}"/>')

    for row in rows:
        x = sx(row["cost_per_attempt"])
        y = sy(row["pass_rate"])
        css_class = "point frontier-point" if row["arm_id"] in frontier_ids else "point other-point"
        radius = 8 if row["arm_id"] in frontier_ids else 7
        tip = html.escape(tooltip(row), quote=True)
        svg_parts.append(
            f'<circle class="{css_class}" cx="{x:.1f}" cy="{y:.1f}" r="{radius}" tabindex="0" data-tooltip="{tip}">'
            f'<title>{html.escape(row["arm_id"])}</title></circle>'
        )

    svg_parts.append("</svg>")
    svg = "\n".join(svg_parts)

    page = f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>Cost vs. pass rate frontier</title>
  <style>
    :root {{
      --text: #172033;
      --muted: #5f6b7a;
      --border: #e5e7eb;
      --bg: #f8fafc;
      --card: #ffffff;
      --grid: #e8edf4;
      --axis: #9aa7b5;
      --other: #64748b;
      --frontier: #ef4444;
    }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: Inter, system-ui, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
    }}
    .page {{
      max-width: 1220px;
      margin: 0 auto;
      padding: 34px 30px 44px;
    }}
    .header {{
      max-width: 980px;
      margin-bottom: 20px;
    }}
    h1 {{
      margin: 0 0 10px;
      font-size: 32px;
      line-height: 1.1;
      letter-spacing: -0.025em;
    }}
    .subtitle, .note, .footer {{
      color: var(--muted);
      line-height: 1.5;
    }}
    .subtitle {{
      margin: 0;
      font-size: 15px;
    }}
    .note {{
      margin: 10px 0 0;
      font-size: 13px;
    }}
    .chart-card {{
      position: relative;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 18px;
      box-shadow: 0 18px 45px rgba(15, 23, 42, 0.08);
      padding: 18px;
    }}
    .legend {{
      display: flex;
      gap: 20px;
      align-items: center;
      margin: 0 0 8px 8px;
      color: var(--muted);
      font-size: 13px;
    }}
    .legend-item {{
      display: inline-flex;
      align-items: center;
      gap: 8px;
    }}
    .swatch {{
      width: 12px;
      height: 12px;
      border-radius: 999px;
      display: inline-block;
      background: var(--other);
    }}
    .swatch.frontier {{
      border-radius: 2px;
      transform: rotate(45deg);
      background: var(--frontier);
    }}
    .chart {{
      width: 100%;
      height: auto;
      display: block;
    }}
    .grid {{
      stroke: var(--grid);
      stroke-width: 1;
    }}
    .axis {{
      stroke: var(--axis);
      stroke-width: 1.2;
    }}
    .tick {{
      fill: var(--muted);
      font-size: 13px;
    }}
    .axis-label {{
      fill: var(--text);
      font-size: 15px;
      font-weight: 650;
    }}
    .frontier-line {{
      fill: none;
      stroke: var(--frontier);
      stroke-width: 3;
      stroke-linecap: round;
      stroke-linejoin: round;
    }}
    .point {{
      cursor: pointer;
      stroke: #ffffff;
      stroke-width: 2.5;
      transition: r 120ms ease, opacity 120ms ease;
    }}
    .point:hover, .point:focus {{
      r: 10;
      opacity: 1;
      outline: none;
    }}
    .other-point {{
      fill: var(--other);
      opacity: 0.78;
    }}
    .frontier-point {{
      fill: var(--frontier);
      opacity: 0.95;
    }}
    .tooltip {{
      position: fixed;
      z-index: 20;
      max-width: 360px;
      pointer-events: none;
      background: #111827;
      color: white;
      border-radius: 12px;
      padding: 12px 14px;
      box-shadow: 0 18px 42px rgba(15, 23, 42, 0.28);
      font-size: 13px;
      line-height: 1.45;
      opacity: 0;
      transform: translate(12px, 12px);
      transition: opacity 90ms ease;
    }}
    .tooltip.visible {{
      opacity: 1;
    }}
    .footer {{
      margin: 14px 0 0;
      font-size: 12px;
    }}
  </style>
</head>
<body>
  <main class="page">
    <header class="header">
      <h1>Cost vs. pass rate frontier</h1>
      <p class="subtitle">
        Each point is one model/backend arm. The Y-axis is overall pass rate. The X-axis is cost per benchmark attempt.
      </p>
      <p class="note">
        Cost uses adjusted known cost: recorded cost plus reconstructed missing-cost rows where usage/pricing evidence exists.
        This avoids undercounting failed or errored attempts that consumed tokens.
      </p>
    </header>

    <section class="chart-card">
      <div class="legend">
        <span class="legend-item"><span class="swatch"></span>Other arms</span>
        <span class="legend-item"><span class="swatch frontier"></span>Pareto frontier</span>
      </div>
      {svg}
    </section>

    <p class="footer">
      Hover over a point for model, provider, pass rate, adjusted total cost, cost per clean success, unclean spend, and cost-confidence details.
    </p>
  </main>

  <div class="tooltip" id="tooltip"></div>
  <script>
    const tooltip = document.getElementById("tooltip");
    const points = document.querySelectorAll("[data-tooltip]");

    function showTooltip(event) {{
      tooltip.innerHTML = event.currentTarget.dataset.tooltip;
      tooltip.classList.add("visible");
      moveTooltip(event);
    }}

    function moveTooltip(event) {{
      const pad = 18;
      let x = event.clientX + 16;
      let y = event.clientY + 16;
      const box = tooltip.getBoundingClientRect();

      if (x + box.width + pad > window.innerWidth) {{
        x = event.clientX - box.width - 16;
      }}
      if (y + box.height + pad > window.innerHeight) {{
        y = event.clientY - box.height - 16;
      }}

      tooltip.style.left = `${{Math.max(pad, x)}}px`;
      tooltip.style.top = `${{Math.max(pad, y)}}px`;
    }}

    function hideTooltip() {{
      tooltip.classList.remove("visible");
    }}

    points.forEach((point) => {{
      point.addEventListener("mouseenter", showTooltip);
      point.addEventListener("mousemove", moveTooltip);
      point.addEventListener("mouseleave", hideTooltip);
      point.addEventListener("focus", showTooltip);
      point.addEventListener("blur", hideTooltip);
    }});
  </script>
</body>
</html>
"""

    args.output_html.parent.mkdir(parents=True, exist_ok=True)
    args.output_html.write_text(page)
    print(args.output_html)


if __name__ == "__main__":
    main()
