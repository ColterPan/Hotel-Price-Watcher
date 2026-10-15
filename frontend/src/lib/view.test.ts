import { describe, expect, it } from "vitest";

import type { Hotel } from "../types";
import { DEFAULT_FILTERS, applyFilters, inBounds, sortViews, type HotelView } from "./view";

function view(id: string, price: number | null, score: number | null, value: number | null, stars = 3): HotelView {
  const hotel = {
    id,
    name: id,
    latitude: 1.3,
    longitude: 103.8,
    hotel_class: stars,
    quality: score === null ? null : { score, label: "", review_count: 100, low_confidence: false },
  } as Hotel;
  return {
    hotel,
    price: price === null ? null : { nightlyUsd: price, kind: "live", site: null },
    value: value === null ? null : { value, grade: "C", qualityPct: 0, pricePct: 0 },
    loadingPrice: false,
  };
}

const views = [view("a", 100, 8, 0.4), view("b", 60, 7, 0.9, 2), view("c", 300, 9.5, 0.2, 5), view("d", null, 9, null)];

describe("sortViews", () => {
  it("sorts by value, unknowns last", () => {
    expect(sortViews(views, "value").map((v) => v.hotel.id)).toEqual(["b", "a", "c", "d"]);
  });

  it("sorts by price, unknown prices last", () => {
    expect(sortViews(views, "price").map((v) => v.hotel.id)).toEqual(["b", "a", "c", "d"]);
  });

  it("sorts by score", () => {
    expect(sortViews(views, "score").map((v) => v.hotel.id)).toEqual(["c", "d", "a", "b"]);
  });

  it("does not mutate the input", () => {
    const before = views.map((v) => v.hotel.id);
    sortViews(views, "price");
    expect(views.map((v) => v.hotel.id)).toEqual(before);
  });
});

describe("applyFilters", () => {
  const identity = (n: number) => n;

  it("keeps everything with default filters", () => {
    expect(applyFilters(views, DEFAULT_FILTERS, null, identity)).toHaveLength(4);
  });

  it("filters by max price in display currency, converting to USD", () => {
    const sgdToUsd = (n: number) => n / 1.3;
    const result = applyFilters(views, { ...DEFAULT_FILTERS, maxPrice: 130 }, null, sgdToUsd);
    // 130 SGD is 100 USD: a (100) and b (60) pass, c fails, d has no price yet so stays.
    expect(result.map((v) => v.hotel.id)).toEqual(["a", "b", "d"]);
  });

  it("filters by score and stars", () => {
    expect(applyFilters(views, { ...DEFAULT_FILTERS, minScore: 8.5 }, null, identity).map((v) => v.hotel.id)).toEqual([
      "c",
      "d",
    ]);
    expect(applyFilters(views, { ...DEFAULT_FILTERS, minStars: 4 }, null, identity).map((v) => v.hotel.id)).toEqual(["c"]);
  });

  it("filters to the visible map area", () => {
    const bounds = { south: 0, north: 1, west: 0, east: 1 };
    expect(applyFilters(views, { ...DEFAULT_FILTERS, onlyInView: true }, bounds, identity)).toEqual([]);
    expect(inBounds(views[0]!.hotel, null)).toBe(true);
  });
});
