import { describe, expect, it } from "vitest";

import { computeValues, gradeFor, percentileRanks } from "./value";

describe("percentileRanks", () => {
  it("spreads distinct values from 0 to 1", () => {
    expect(percentileRanks([30, 10, 20])).toEqual([1, 0, 0.5]);
  });

  it("gives ties their average rank", () => {
    expect(percentileRanks([10, 10, 20])).toEqual([0.25, 0.25, 1]);
  });

  it("handles empty and single inputs", () => {
    expect(percentileRanks([])).toEqual([]);
    expect(percentileRanks([42])).toEqual([0.5]);
  });
});

describe("computeValues", () => {
  const hotels = [
    { id: "cheap-ok", price: 80, quality: 7.5 },
    { id: "mid-great", price: 150, quality: 9.2 },
    { id: "pricey-good", price: 400, quality: 8.4 },
  ];

  it("at balanced weight, favours the hotel that is both cheap-ish and great", () => {
    const values = computeValues(hotels, 0.5);
    expect(values.get("mid-great")!.value).toBeGreaterThan(values.get("pricey-good")!.value);
    // 0.5 * quality 0.5 + 0.5 * (1 - price 1) = 0.25
    expect(values.get("pricey-good")!.value).toBe(0.25);
    expect(values.get("pricey-good")!.grade).toBe("D");
  });

  it("weight 0 ranks purely by price", () => {
    const values = computeValues(hotels, 0);
    expect(values.get("cheap-ok")!.value).toBe(1);
    expect(values.get("pricey-good")!.value).toBe(0);
  });

  it("weight 1 ranks purely by quality", () => {
    const values = computeValues(hotels, 1);
    expect(values.get("mid-great")!.value).toBe(1);
    expect(values.get("cheap-ok")!.value).toBe(0);
  });

  it("clamps out-of-range weights", () => {
    expect(computeValues(hotels, 5).get("mid-great")!.value).toBe(1);
  });

  it("skips hotels without a price or score", () => {
    const values = computeValues(
      [...hotels, { id: "no-price", price: null, quality: 9 }, { id: "no-score", price: 50, quality: null }],
      0.5,
    );
    expect(values.has("no-price")).toBe(false);
    expect(values.has("no-score")).toBe(false);
    expect(values.size).toBe(3);
  });
});

describe("gradeFor", () => {
  it.each([
    [0.95, "A"],
    [0.8, "A"],
    [0.65, "B"],
    [0.4, "C"],
    [0.2, "D"],
    [0.05, "E"],
  ])("%s -> %s", (value, grade) => {
    expect(gradeFor(value)).toBe(grade);
  });
});
