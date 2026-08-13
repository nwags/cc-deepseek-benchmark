"use client";

import Link from "next/link";
import { useRouter } from "next/navigation";
import { useMemo, useState, type KeyboardEvent } from "react";
import {
  CHART_X_AXIS_OPTIONS,
  DEFAULT_CHART_X_AXIS_METRIC,
  clearChartArmIds,
  clearProviderFamilies,
  deriveCostPerformanceChartView,
  metricValueForArm,
  selectAllChartArmIds,
  selectAllProviderFamilies,
  type ChartArmDatum,
  type ChartMetricValue,
  type ChartPlotPoint,
  type ChartProviderFilterOption,
  type ChartScope,
  type ChartXAxisMetric,
} from "../lib/cost-performance-chart-view";
import {
  linearScale,
  linearTicks,
  paddedLinearDomain,
} from "../lib/cost-performance-chart-geometry";
import { CostPerformanceChartTable } from "./CostPerformanceChartTable";

export const PROVIDER_FAMILY_COLORS: Readonly<Record<string, string>> = Object.freeze({
  anthropic: "#ff9f7a",
  "dashscope-qwen": "#47d7c7",
  deepseek: "#a78bfa",
  "google-gemini": "#f4d35e",
  "moonshot-kimi": "#62d98b",
  openai: "#e5edf8",
  xai: "#fb7185",
  "zai-glm": "#60a5fa",
});

const SVG_WIDTH = 1_000;
const SVG_HEIGHT = 520;
const PLOT_LEFT = 82;
const PLOT_RIGHT = 34;
const PLOT_TOP = 34;
const PLOT_BOTTOM = 76;
const PLOT_WIDTH = SVG_WIDTH - PLOT_LEFT - PLOT_RIGHT;
const PLOT_HEIGHT = SVG_HEIGHT - PLOT_TOP - PLOT_BOTTOM;

export type CostPerformanceChartProps = Readonly<{
  arms: readonly ChartArmDatum[];
  providerOptions: readonly ChartProviderFilterOption[];
  scopeId: ChartScope;
  scopeWarningMessage?: string | null;
}>;

function metricLabel(metric: ChartXAxisMetric): string {
  return CHART_X_AXIS_OPTIONS.find((option) => option.metric === metric)?.label ?? metric;
}

function providerColor(providerFamily: string): string {
  return PROVIDER_FAMILY_COLORS[providerFamily] ?? "#b8c5d8";
}

function formatUsdTick(value: number): string {
  const absolute = Math.abs(value);
  const maximumFractionDigits = absolute < 0.01 ? 4 : absolute < 1 ? 3 : 2;
  return `$${value.toLocaleString("en-US", {
    minimumFractionDigits: 0,
    maximumFractionDigits,
  })}`;
}

function formatPercent(value: number): string {
  return `${(value * 100).toFixed(1)}%`;
}

function statusLabel(value: string | null): string {
  return value?.replaceAll("_", " ") ?? "not separately qualified in G1";
}

function metricValueText(value: ChartMetricValue): string {
  if (value.status === "unavailable") return `Unavailable — ${value.reason}`;
  return `$${value.decimalUsd}${value.qualification ? ` — ${value.qualification}` : ""}`;
}

function failureSpendText(arm: ChartArmDatum): string {
  const spend = arm.failureIncompleteSpend;
  return spend.status === "available"
    ? `$${spend.decimalUsd}`
    : `Unavailable — ${spend.reason}`;
}

function hasMaterialQualification(arm: ChartArmDatum): boolean {
  return arm.costConfidence.toLowerCase() !== "high"
    || Number(arm.accountingGapUsd) !== 0
    || arm.pricingProvenanceStatus !== "historical_reviewed_layer"
    || arm.armRunAllocationConfidence !== "reviewed_core_layer"
    || arm.trialAllocationStatus !== "available_for_reviewed_layer"
    || arm.providerLogExclusivityStatus !== null
    || arm.qualificationText !== null;
}

function pointAriaLabel(point: ChartPlotPoint, metric: ChartXAxisMetric): string {
  const qualification = hasMaterialQualification(point.arm)
    ? " Reviewed cost evidence has a confidence or accounting qualification."
    : "";
  return `${point.arm.displayName}, ${point.arm.providerFamilyLabel}. ${metricLabel(metric)} $${point.xDecimalUsd}. Pass rate ${formatPercent(point.passRate)}, ${point.arm.successCount} of ${point.arm.trialCount} successes.${qualification}`;
}

export function CostPerformanceChart({
  arms,
  providerOptions,
  scopeId,
  scopeWarningMessage = null,
}: CostPerformanceChartProps) {
  const router = useRouter();
  const [xMetric, setXMetric] = useState<ChartXAxisMetric>(DEFAULT_CHART_X_AXIS_METRIC);
  const [selectedProviderFamilies, setSelectedProviderFamilies] = useState<readonly string[]>(
    () => selectAllProviderFamilies(providerOptions),
  );
  const [selectedArmIds, setSelectedArmIds] = useState<readonly string[]>(
    () => selectAllChartArmIds(arms),
  );
  const [activeArmId, setActiveArmId] = useState<string | null>(null);

  const view = useMemo(() => deriveCostPerformanceChartView({
    arms,
    selectedProviderFamilies,
    selectedArmIds,
    metric: xMetric,
  }), [arms, selectedProviderFamilies, selectedArmIds, xMetric]);

  const xDomain = useMemo(
    () => paddedLinearDomain(view.plotPoints.map((point) => point.xValue), { minimumPadding: 1e-6 }),
    [view.plotPoints],
  );
  const yDomain = useMemo(
    () => paddedLinearDomain(view.plotPoints.map((point) => point.passRate), {
      minimumPadding: 0.01,
      clampMinimum: 0,
      clampMaximum: 1,
    }),
    [view.plotPoints],
  );
  const xPosition = useMemo(
    () => linearScale(xDomain, [PLOT_LEFT, PLOT_LEFT + PLOT_WIDTH]),
    [xDomain],
  );
  const yPosition = useMemo(
    () => linearScale(yDomain, [PLOT_TOP + PLOT_HEIGHT, PLOT_TOP]),
    [yDomain],
  );
  const xTicks = useMemo(() => linearTicks(xDomain, 6), [xDomain]);
  const yTicks = useMemo(() => linearTicks(yDomain, 5), [yDomain]);
  const activePoint = view.plotPoints.find((point) => point.armId === activeArmId)
    ?? view.plotPoints[0]
    ?? null;
  const selectedProviderSet = new Set(selectedProviderFamilies);
  const selectedArmSet = new Set(selectedArmIds);
  const selectedMetricLabel = metricLabel(xMetric);

  function replaceScope(nextScope: ChartScope): void {
    const parameters = new URLSearchParams(window.location.search);
    parameters.set("chart_scope", nextScope);
    router.push(`${window.location.pathname}?${parameters.toString()}`, { scroll: false });
  }

  function toggleProvider(providerFamily: string): void {
    setSelectedProviderFamilies((current) => current.includes(providerFamily)
      ? current.filter((value) => value !== providerFamily)
      : Object.freeze([...current, providerFamily].sort()));
  }

  function toggleArm(armId: string): void {
    setSelectedArmIds((current) => current.includes(armId)
      ? current.filter((value) => value !== armId)
      : Object.freeze([...current, armId].sort()));
  }

  function activatePoint(armId: string): void {
    setActiveArmId(armId);
  }

  function handlePointKeyDown(event: KeyboardEvent<SVGGElement>, armId: string): void {
    if (event.key === "Enter" || event.key === " ") {
      event.preventDefault();
      activatePoint(armId);
    }
  }

  let emptyMessage: string | null = null;
  if (selectedProviderFamilies.length === 0) {
    emptyMessage = "No provider families are enabled.";
  } else if (selectedArmIds.length === 0) {
    emptyMessage = "No arms are selected.";
  } else if (view.plotPoints.length === 0) {
    emptyMessage = `${view.unavailableMetricArms.length} selected arms have no reviewed value for ${selectedMetricLabel} and are excluded from the plot.`;
  } else if (view.plotPoints.length === 1) {
    emptyMessage = "One eligible point is visible; no frontier segment is drawn.";
  } else if (view.frontier.length < 2) {
    emptyMessage = "The visible population has no multi-point frontier segment.";
  }

  const frontierPoints = view.frontier.map((point) => (
    `${xPosition(point.xValue)},${yPosition(point.passRate)}`
  )).join(" ");

  return (
    <section className="panel cost-performance-chart" aria-labelledby="cost-performance-chart-title">
      <div className="cost-performance-chart-intro">
        <div>
          <p className="cost-performance-chart-kicker">Reviewed comparison · F1 facts / G1 run identity</p>
          <h2 id="cost-performance-chart-title">Reviewed Phase 3 cost/performance frontier</h2>
          <p>
            Lower cost and higher pass rate are better. Quantitative values come only from the checked-in reviewed
            F1 snapshot; arm and run links use the frozen G1 selection. Point size is fixed, while reviewed
            failure/incomplete spend remains available in details and the evidence table where supported.
          </p>
        </div>
        <a className="cost-performance-table-jump" href="#cost-performance-chart-table">
          Skip to non-hover evidence table ↓
        </a>
      </div>

      {scopeWarningMessage ? <p className="chart-control-warning" role="alert">{scopeWarningMessage}</p> : null}

      <div className="cost-performance-controls">
        <fieldset className="chart-control-group chart-control-scope">
          <legend>Reviewed chart scope</legend>
          <label>
            <input
              type="radio"
              name="cost-performance-scope"
              value="phase3-extended"
              checked={scopeId === "phase3-extended"}
              onChange={() => replaceScope("phase3-extended")}
            />
            <span>Phase 3 extended <small>16 arms</small></span>
          </label>
          <label>
            <input
              type="radio"
              name="cost-performance-scope"
              value="phase3-core"
              checked={scopeId === "phase3-core"}
              onChange={() => replaceScope("phase3-core")}
            />
            <span>Phase 3 core <small>15 arms</small></span>
          </label>
        </fieldset>

        <fieldset className="chart-control-group chart-control-metric">
          <legend>X-axis metric</legend>
          {CHART_X_AXIS_OPTIONS.map((option) => (
            <label key={option.metric}>
              <input
                type="radio"
                name="cost-performance-x-metric"
                value={option.metric}
                checked={xMetric === option.metric}
                onChange={() => setXMetric(option.metric)}
              />
              <span>{option.label}</span>
            </label>
          ))}
        </fieldset>

        <fieldset className="chart-control-group chart-control-providers">
          <legend>Provider families</legend>
          <div className="chart-control-actions">
            <button type="button" onClick={() => setSelectedProviderFamilies(selectAllProviderFamilies(providerOptions))}>
              Select all
            </button>
            <button type="button" onClick={() => setSelectedProviderFamilies(clearProviderFamilies())}>
              Clear
            </button>
          </div>
          <div className="chart-provider-options">
            {providerOptions.map((option) => (
              <label key={option.providerFamily}>
                <input
                  type="checkbox"
                  checked={selectedProviderSet.has(option.providerFamily)}
                  onChange={() => toggleProvider(option.providerFamily)}
                />
                <span
                  className="chart-provider-swatch"
                  style={{ backgroundColor: providerColor(option.providerFamily) }}
                  aria-hidden="true"
                />
                <span>{option.label} <small>{option.armCount}</small></span>
              </label>
            ))}
          </div>
        </fieldset>
      </div>

      <details className="chart-arm-selector">
        <summary>Arm visibility · {selectedArmIds.length} of {arms.length} selected</summary>
        <div className="chart-arm-selector-body">
          <div className="chart-control-actions">
            <button type="button" onClick={() => setSelectedArmIds(selectAllChartArmIds(arms))}>Select all arms</button>
            <button type="button" onClick={() => setSelectedArmIds(clearChartArmIds())}>Clear arms</button>
          </div>
          <fieldset>
            <legend className="sr-only">Individual arm selection</legend>
            <div className="chart-arm-options">
              {arms.map((arm) => (
                <label key={arm.armId}>
                  <input
                    type="checkbox"
                    checked={selectedArmSet.has(arm.armId)}
                    onChange={() => toggleArm(arm.armId)}
                  />
                  <span>{arm.displayName}<small className="mono">{arm.armId}</small></span>
                </label>
              ))}
            </div>
          </fieldset>
        </div>
      </details>

      <div className="cost-performance-legend" aria-label="Provider color and qualification legend">
        {providerOptions.map((option) => (
          <span key={option.providerFamily}>
            <i style={{ backgroundColor: providerColor(option.providerFamily) }} aria-hidden="true" />
            {option.label}
          </span>
        ))}
        <span><i className="chart-qualification-key" aria-hidden="true" />Qualified / accounting gap</span>
        <span><i className="chart-frontier-key" aria-hidden="true" />Pareto frontier</span>
      </div>

      <div className="cost-performance-visual-grid">
        <div className="cost-performance-svg-wrap">
          <svg
            className="cost-performance-svg"
            viewBox={`0 0 ${SVG_WIDTH} ${SVG_HEIGHT}`}
            role="group"
            aria-labelledby="cost-performance-svg-title cost-performance-svg-description"
            preserveAspectRatio="xMidYMid meet"
          >
            <title id="cost-performance-svg-title">{`${selectedMetricLabel} against reviewed pass rate`}</title>
            <desc id="cost-performance-svg-description">
              Interactive scatter plot of selected reviewed Phase 3 arms. Lower horizontal values and higher
              vertical values are better. Focus a point to show its complete evidence details beside the plot.
            </desc>

            {yTicks.map((tick) => {
              const y = yPosition(tick);
              return (
                <g key={`y-${tick}`} aria-hidden="true">
                  <line className="chart-grid-line" x1={PLOT_LEFT} x2={PLOT_LEFT + PLOT_WIDTH} y1={y} y2={y} />
                  <text className="chart-tick-label" x={PLOT_LEFT - 14} y={y + 5} textAnchor="end">
                    {formatPercent(tick)}
                  </text>
                </g>
              );
            })}
            {xTicks.map((tick) => {
              const x = xPosition(tick);
              return (
                <g key={`x-${tick}`} aria-hidden="true">
                  <line className="chart-grid-line" x1={x} x2={x} y1={PLOT_TOP} y2={PLOT_TOP + PLOT_HEIGHT} />
                  <text className="chart-tick-label" x={x} y={PLOT_TOP + PLOT_HEIGHT + 28} textAnchor="middle">
                    {formatUsdTick(tick)}
                  </text>
                </g>
              );
            })}

            <line className="chart-axis-line" x1={PLOT_LEFT} x2={PLOT_LEFT + PLOT_WIDTH} y1={PLOT_TOP + PLOT_HEIGHT} y2={PLOT_TOP + PLOT_HEIGHT} />
            <line className="chart-axis-line" x1={PLOT_LEFT} x2={PLOT_LEFT} y1={PLOT_TOP} y2={PLOT_TOP + PLOT_HEIGHT} />
            <text className="chart-axis-label" x={PLOT_LEFT + PLOT_WIDTH / 2} y={SVG_HEIGHT - 18} textAnchor="middle">
              {selectedMetricLabel} (USD) · lower is better →
            </text>
            <text
              className="chart-axis-label"
              x={22}
              y={PLOT_TOP + PLOT_HEIGHT / 2}
              textAnchor="middle"
              transform={`rotate(-90 22 ${PLOT_TOP + PLOT_HEIGHT / 2})`}
            >
              Pass rate · higher is better →
            </text>

            {view.frontier.length >= 2 ? (
              <polyline
                className="chart-frontier-line"
                points={frontierPoints}
                data-frontier-arm-ids={view.frontier.map((point) => point.armId).join(",")}
                aria-label={`Pareto frontier: ${view.frontier.map((point) => point.arm.displayName).join(", ")}`}
              />
            ) : null}

            {view.plotPoints.map((point) => {
              const x = xPosition(point.xValue);
              const y = yPosition(point.passRate);
              const qualified = hasMaterialQualification(point.arm);
              const active = activePoint?.armId === point.armId;
              return (
                <g
                  className="cost-performance-point"
                  key={point.armId}
                  role="button"
                  tabIndex={0}
                  focusable="true"
                  aria-label={pointAriaLabel(point, xMetric)}
                  aria-pressed={active}
                  onFocus={() => activatePoint(point.armId)}
                  onMouseEnter={() => activatePoint(point.armId)}
                  onClick={() => activatePoint(point.armId)}
                  onKeyDown={(event) => handlePointKeyDown(event, point.armId)}
                >
                  <circle className="cost-performance-point-hit" cx={x} cy={y} r={18} />
                  <circle className="cost-performance-point-focus" cx={x} cy={y} r={16} />
                  {qualified ? <circle className="cost-performance-point-qualified" cx={x} cy={y} r={13} /> : null}
                  {active ? <circle className="cost-performance-point-active" cx={x} cy={y} r={11} /> : null}
                  <circle
                    className="cost-performance-point-dot"
                    cx={x}
                    cy={y}
                    r={8}
                    fill={providerColor(point.arm.providerFamily)}
                  />
                </g>
              );
            })}
          </svg>

          {emptyMessage ? <p className="chart-empty-state" role="status">{emptyMessage}</p> : null}
          {view.unavailableMetricArms.length > 0 ? (
            <div className="chart-unavailable" role="status">
              <strong>Selected but unavailable for {selectedMetricLabel}</strong>
              <ul>
                {view.unavailableMetricArms.map((arm) => {
                  const metricValue = metricValueForArm(arm, xMetric);
                  return (
                    <li key={arm.armId}>
                      {arm.displayName} <span className="mono">{arm.armId}</span>: {metricValue.status === "unavailable"
                        ? metricValue.reason
                        : "Reviewed metric is available."}
                    </li>
                  );
                })}
              </ul>
            </div>
          ) : null}
        </div>

        <aside className="cost-performance-detail" aria-live="polite" aria-label="Selected chart point details">
          {activePoint ? (() => {
            const arm = activePoint.arm;
            const metricValue = metricValueForArm(arm, xMetric);
            return (
              <>
                <p className="cost-performance-detail-label">Selected reviewed arm</p>
                <h3>{arm.displayName}</h3>
                <p className="mono">{arm.armId}</p>
                <dl>
                  <div><dt>Provider family</dt><dd>{arm.providerFamilyLabel}</dd></div>
                  {arm.reviewedProvider !== arm.providerFamily ? (
                    <div><dt>Reviewed provider value</dt><dd className="mono">{arm.reviewedProvider}</dd></div>
                  ) : null}
                  <div><dt>{selectedMetricLabel}</dt><dd>{metricValueText(metricValue)}</dd></div>
                  <div><dt>Reviewed pass rate</dt><dd>{formatPercent(arm.passRate)} · {arm.successCount} / {arm.trialCount} successes</dd></div>
                  <div><dt>Cost basis</dt><dd>{arm.costBasisLabel} <span className="mono">{arm.costBasis}</span></dd></div>
                  <div><dt>Cost sources / confidence</dt><dd>{arm.costSources.join(", ")} · {arm.costConfidence}</dd></div>
                  <div><dt>Accounting gap</dt><dd>${arm.accountingGapUsd}</dd></div>
                  <div><dt>Pricing provenance</dt><dd>{statusLabel(arm.pricingProvenanceStatus)}</dd></div>
                  <div><dt>Arm/run allocation</dt><dd>{statusLabel(arm.armRunAllocationConfidence)}</dd></div>
                  <div><dt>Trial allocation</dt><dd>{statusLabel(arm.trialAllocationStatus)}</dd></div>
                  <div><dt>Billing reconciliation</dt><dd>{statusLabel(arm.billingReconciliationStatus)}</dd></div>
                  <div><dt>Provider-log exclusivity</dt><dd>{statusLabel(arm.providerLogExclusivityStatus)}</dd></div>
                  <div><dt>Failure / incomplete spend</dt><dd>{failureSpendText(arm)}</dd></div>
                  <div><dt>Frozen selected run</dt><dd className="mono">{arm.selectedRunLabel}</dd></div>
                </dl>
                {arm.costBasis === "qualified_retained_rate_estimate" ? (
                  <div className="chart-qualified-callout" role="note">
                    <strong>Qualified retained-rate estimate — not adjusted-known, invoice, or provider-billed cost.</strong>
                    <span>Pricing provenance is incomplete; allocation confidence is low; trial allocation is unresolved; provider-log exclusivity is not proven.</span>
                  </div>
                ) : null}
                <p className="cost-performance-qualification">
                  {arm.qualificationText ?? "No additional qualification beyond the reviewed evidence statuses above."}
                </p>
                <div className="cost-performance-detail-links">
                  <Link href={arm.armHref}>Arm evidence →</Link>
                  <Link href={arm.selectedRunHref}>Frozen selected-run evidence →</Link>
                </div>
              </>
            );
          })() : (
            <div className="chart-detail-empty">
              <p className="cost-performance-detail-label">Selected reviewed arm</p>
              <h3>No eligible point</h3>
              <p>Adjust provider, arm, or metric controls to place a reviewed point on the chart.</p>
            </div>
          )}
        </aside>
      </div>

      <div className="cost-performance-chart-table" id="cost-performance-chart-table">
        <h3>Reviewed chart evidence — non-hover equivalent</h3>
        <p>
          Includes arms that are selected and provider-visible. An unavailable metric remains explicit instead of
          silently removing the arm from this evidence view.
        </p>
        <CostPerformanceChartTable
          arms={view.selectedVisibleArms}
          xMetric={xMetric}
          caption={`${scopeId === "phase3-core" ? "Phase 3 core" : "Phase 3 extended"} reviewed chart evidence. Current x-axis: ${selectedMetricLabel}.`}
        />
      </div>
    </section>
  );
}
