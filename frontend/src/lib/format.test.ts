import { describe, expect, it } from "vitest";

import { formatMoney, formatReviews, formatStay, nightsBetween, plural, timeAgo, toDayString } from "./format";

describe("formatMoney", () => {
  it("rounds to whole units and never shows a bare, ambiguous dollar sign", () => {
    expect(formatMoney(1284.4, "SGD")).toBe("S$1,284");
    expect(formatMoney(98, "USD")).toBe("US$98");
    expect(formatMoney(14200, "JPY")).toBe("¥14,200");
    expect(formatMoney(310, "MYR")).toBe("RM310");
  });

  it("falls back for unknown currency codes", () => {
    expect(formatMoney(10, "ZZZ1")).toBe("ZZZ1 10");
  });
});

describe("dates", () => {
  it("counts nights across a month boundary", () => {
    expect(nightsBetween("2026-10-30", "2026-11-02")).toBe(3);
  });

  it("formats a stay with plain words, no dashes", () => {
    expect(formatStay("2026-11-20", "2026-11-22")).toBe("Nov 20 to Nov 22");
  });

  it("round-trips a local day string", () => {
    expect(toDayString(new Date(2026, 0, 5))).toBe("2026-01-05");
  });
});

describe("text helpers", () => {
  it("pluralizes", () => {
    expect(plural(1, "night")).toBe("1 night");
    expect(plural(3, "night")).toBe("3 nights");
  });

  it("shortens review counts", () => {
    expect(formatReviews(1)).toBe("1 review");
    expect(formatReviews(845)).toBe("845 reviews");
    expect(formatReviews(1000)).toBe("1k reviews");
    expect(formatReviews(1650)).toBe("1.6k reviews");
    expect(formatReviews(17055)).toBe("17k reviews");
  });

  it("describes elapsed time", () => {
    const now = new Date("2026-10-15T12:00:00Z");
    expect(timeAgo("2026-10-15T11:59:30Z", now)).toBe("just now");
    expect(timeAgo("2026-10-15T11:15:00Z", now)).toBe("45 min ago");
    expect(timeAgo("2026-10-15T07:00:00Z", now)).toBe("5 h ago");
    expect(timeAgo("2026-10-13T12:00:00Z", now)).toBe("2 days ago");
  });
});
