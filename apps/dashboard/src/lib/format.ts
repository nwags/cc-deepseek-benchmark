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
