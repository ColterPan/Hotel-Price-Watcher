// Value = how much hotel you get for the money, relative to the other hotels
// in the same search. Mirrors docs/scoring.md.
//
//   value = w * qualityPercentile + (1 - w) * (1 - pricePercentile)
//
// w comes from the slider (0 = only price matters, 1 = only quality matters).
// Percentiles are ranks within the comparable set, so the grade always means
// "compared to what else is available here", never an absolute verdict.

export type Grade = "A" | "B" | "C" | "D" | "E";

export interface ValueInput {
  id: string;
  price: number | null;
  quality: number | null;
}

export interface ValueResult {
  qualityPct: number;
  pricePct: number;
  value: number;
  grade: Grade;
}

export const DEFAULT_WEIGHT = 0.5;

/** Percentile rank (0 to 1) of each value, ties sharing their average rank. */
export function percentileRanks(values: readonly number[]): number[] {
  const n = values.length;
  if (n === 0) return [];
  if (n === 1) return [0.5];
  const order = values.map((value, index) => ({ value, index })).sort((a, b) => a.value - b.value);
  const ranks = new Array<number>(n).fill(0);
  let start = 0;
  while (start < n) {
    let end = start;
    while (end + 1 < n && order[end + 1]!.value === order[start]!.value) end += 1;
    const averageRank = (start + end) / 2;
    for (let i = start; i <= end; i += 1) ranks[order[i]!.index] = averageRank / (n - 1);
    start = end + 1;
  }
  return ranks;
}

export function gradeFor(value: number): Grade {
  if (value >= 0.8) return "A";
  if (value >= 0.6) return "B";
  if (value >= 0.4) return "C";
  if (value >= 0.2) return "D";
  return "E";
}

/** Value results keyed by id. Hotels missing a price or a score get no entry. */
export function computeValues(items: readonly ValueInput[], weight: number): Map<string, ValueResult> {
  const w = Math.min(1, Math.max(0, weight));
  const comparable = items.filter(
    (item): item is { id: string; price: number; quality: number } =>
      item.price !== null && item.quality !== null && Number.isFinite(item.price) && item.price > 0,
  );
  const qualityPcts = percentileRanks(comparable.map((item) => item.quality));
  const pricePcts = percentileRanks(comparable.map((item) => item.price));

  const results = new Map<string, ValueResult>();
  comparable.forEach((item, index) => {
    const qualityPct = qualityPcts[index]!;
    const pricePct = pricePcts[index]!;
    const value = w * qualityPct + (1 - w) * (1 - pricePct);
    results.set(item.id, { qualityPct, pricePct, value, grade: gradeFor(value) });
  });
  return results;
}
