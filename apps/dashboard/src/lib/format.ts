export const DASHBOARD_MAX_FRACTION_DIGITS = 4;

function checkedFractionDigits(value: number): number {
  if (
    !Number.isInteger(value)
    || value < 0
    || value > DASHBOARD_MAX_FRACTION_DIGITS
  ) {
    throw new RangeError(
      `fraction digits must be an integer from 0 through ${DASHBOARD_MAX_FRACTION_DIGITS}`,
    );
  }
  return value;
}

/**
 * Presentation-only truncation toward zero.
 *
 * This does not modify stored benchmark values, reviewed snapshots,
 * calculations, database precision, or provider evidence.
 */
export function truncateDecimalPlaces(
  value: number | string,
  fractionDigits: number = DASHBOARD_MAX_FRACTION_DIGITS,
): number {
  const digits = checkedFractionDigits(fractionDigits);
  const numeric = Number(value);

  if (!Number.isFinite(numeric)) {
    return numeric;
  }

  const factor = 10 ** digits;
  const scaled = numeric * factor;

  if (!Number.isFinite(scaled)) {
    return numeric;
  }

  const truncated = Math.trunc(scaled) / factor;
  return Object.is(truncated, -0) ? 0 : truncated;
}

export function formatTruncatedNumber(
  value: number | string,
  maximumFractionDigits: number = DASHBOARD_MAX_FRACTION_DIGITS,
  minimumFractionDigits: number = 0,
): string {
  const maximum = checkedFractionDigits(maximumFractionDigits);
  const minimum = checkedFractionDigits(minimumFractionDigits);

  if (minimum > maximum) {
    throw new RangeError(
      "minimumFractionDigits cannot exceed maximumFractionDigits",
    );
  }

  const truncated = truncateDecimalPlaces(value, maximum);

  return new Intl.NumberFormat("en-US", {
    minimumFractionDigits: minimum,
    maximumFractionDigits: maximum,
  }).format(truncated);
}

export function formatTruncatedCurrency(
  value: number | string,
  maximumFractionDigits: number = DASHBOARD_MAX_FRACTION_DIGITS,
  minimumFractionDigits: number = 2,
): string {
  const maximum = checkedFractionDigits(maximumFractionDigits);
  const minimum = checkedFractionDigits(
    Math.min(minimumFractionDigits, maximum),
  );
  const truncated = truncateDecimalPlaces(value, maximum);

  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    minimumFractionDigits: minimum,
    maximumFractionDigits: maximum,
  }).format(truncated);
}

/**
 * Recursively applies the dashboard decimal ceiling to structured
 * presentation data such as normalized provider pricing rules.
 *
 * Pure decimal strings are changed only when they contain more than
 * four fractional digits. Non-numeric strings, identifiers, integers,
 * source objects, and stored evidence remain unchanged.
 */
export function truncateStructuredDecimalsForDisplay(
  value: unknown,
): unknown {
  if (typeof value === "number") {
    if (!Number.isFinite(value) || Number.isInteger(value)) {
      return value;
    }

    return truncateDecimalPlaces(value);
  }

  if (typeof value === "string") {
    const trimmed = value.trim();
    const match = /^[+-]?\d+\.(\d+)$/.exec(trimmed);

    if (
      match === null
      || match[1].length <= DASHBOARD_MAX_FRACTION_DIGITS
    ) {
      return value;
    }

    return String(truncateDecimalPlaces(trimmed));
  }

  if (Array.isArray(value)) {
    return value.map((item) =>
      truncateStructuredDecimalsForDisplay(item)
    );
  }

  if (!value || typeof value !== "object") {
    return value;
  }

  const output: Record<string, unknown> = {};

  for (const [key, item] of Object.entries(
    value as Record<string, unknown>,
  )) {
    output[key] = truncateStructuredDecimalsForDisplay(item);
  }

  return output;
}

export function formatNumber(value: number | string | null | undefined): string {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat("en-US").format(n);
}

export function formatCurrency(value: number | string | null | undefined): string {
  const n = Number(value ?? 0);
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 2
  }).format(n);
}

export function formatPercent(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${(Number(value) * 100).toFixed(1)}%`;
}

export function formatSeconds(value: number | string | null | undefined): string {
  if (value === null || value === undefined) return "—";
  return `${Number(value).toFixed(1)}s`;
}


export function formatBytes(value: number | null | undefined): string {
  if (value === null || typeof value === "undefined") {
    return "—";
  }

  if (value < 1024) {
    return `${value} B`;
  }

  const units = ["KB", "MB", "GB", "TB"];
  let size = value / 1024;
  let unitIndex = 0;

  while (size >= 1024 && unitIndex < units.length - 1) {
    size /= 1024;
    unitIndex += 1;
  }

  return `${size.toFixed(size >= 10 ? 1 : 2)} ${units[unitIndex]}`;
}


export function formatRecordedCost(
  value: number | null | undefined,
  costRowCount: number | null | undefined,
  missingCostCount: number | null | undefined
): string {
  const recordedRows = costRowCount ?? 0;
  const missingRows = missingCostCount ?? 0;

  if (recordedRows === 0) {
    return "not recorded";
  }

  const recordedCost = formatCurrency(value ?? 0);

  if (missingRows > 0) {
    return `${recordedCost} recorded; ${missingRows} missing`;
  }

  return recordedCost;
}
