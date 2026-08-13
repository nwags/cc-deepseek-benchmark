export type LinearDomain = readonly [number, number];
export type LinearRange = readonly [number, number];

export type PaddedDomainOptions = Readonly<{
  paddingRatio?: number;
  minimumPadding?: number;
  clampMinimum?: number;
  clampMaximum?: number;
}>;

function finiteValues(values: readonly number[]): readonly number[] {
  if (values.some((value) => !Number.isFinite(value))) {
    throw new Error("Chart domain values must be finite");
  }
  return values;
}

/**
 * Build a compact padded domain without treating zero as a datum when every
 * reviewed value is positive. Empty inputs use a harmless fallback domain;
 * callers do not plot against it.
 */
export function paddedLinearDomain(
  values: readonly number[],
  options: PaddedDomainOptions = {},
): LinearDomain {
  finiteValues(values);
  if (values.length === 0) return Object.freeze([0, 1]);

  const paddingRatio = options.paddingRatio ?? 0.08;
  const minimumPadding = options.minimumPadding ?? 1e-9;
  if (!Number.isFinite(paddingRatio) || paddingRatio < 0) {
    throw new Error("Chart padding ratio must be a nonnegative finite number");
  }
  if (!Number.isFinite(minimumPadding) || minimumPadding <= 0) {
    throw new Error("Chart minimum padding must be a positive finite number");
  }

  const minimum = Math.min(...values);
  const maximum = Math.max(...values);
  const span = maximum - minimum;
  const referenceMagnitude = Math.max(Math.abs(minimum), Math.abs(maximum), minimumPadding);
  const padding = Math.max(
    span > 0 ? span * paddingRatio : referenceMagnitude * paddingRatio,
    minimumPadding,
  );
  let lower = minimum - padding;
  let upper = maximum + padding;

  if (minimum > 0 && lower <= 0) lower = minimum / 2;
  if (options.clampMinimum !== undefined) lower = Math.max(lower, options.clampMinimum);
  if (options.clampMaximum !== undefined) upper = Math.min(upper, options.clampMaximum);

  if (lower === upper) {
    if (options.clampMinimum !== undefined && lower === options.clampMinimum) {
      upper = lower + minimumPadding;
    } else {
      lower -= minimumPadding;
    }
  }
  if (!Number.isFinite(lower) || !Number.isFinite(upper) || lower >= upper) {
    throw new Error("Chart domain must have finite increasing bounds");
  }
  return Object.freeze([lower, upper]);
}

export function linearScale(
  domain: LinearDomain,
  range: LinearRange,
): (value: number) => number {
  const [domainStart, domainEnd] = domain;
  const [rangeStart, rangeEnd] = range;
  if (![domainStart, domainEnd, rangeStart, rangeEnd].every(Number.isFinite)) {
    throw new Error("Chart scale bounds must be finite");
  }
  if (domainStart >= domainEnd) throw new Error("Chart scale domain must increase");
  return (value: number): number => {
    if (!Number.isFinite(value)) throw new Error("Chart scale value must be finite");
    return rangeStart + ((value - domainStart) / (domainEnd - domainStart)) * (rangeEnd - rangeStart);
  };
}

export function linearTicks(domain: LinearDomain, count = 5): readonly number[] {
  if (!Number.isInteger(count) || count < 2) {
    throw new Error("Chart tick count must be an integer of at least two");
  }
  const [start, end] = domain;
  if (!Number.isFinite(start) || !Number.isFinite(end) || start >= end) {
    throw new Error("Chart tick domain must have finite increasing bounds");
  }
  const interval = (end - start) / (count - 1);
  return Object.freeze(Array.from({ length: count }, (_, index) => start + interval * index));
}
