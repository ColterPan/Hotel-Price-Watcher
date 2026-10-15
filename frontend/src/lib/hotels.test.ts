import { describe, expect, it } from "vitest";

import type { Hotel, RatesResponse } from "../types";
import { effectivePrice, isUnavailable, needsLiveRates } from "./hotels";

function hotel(overrides: Partial<Hotel> = {}): Hotel {
  return {
    id: "g1-d11",
    name: "Test",
    latitude: 1,
    longitude: 2,
    image_url: null,
    url: null,
    accommodation_type: null,
    hotel_class: null,
    amenities: [],
    labels: [],
    providers: ["xotelo"],
    rates_key: "g1-d11",
    ratings: [],
    offers: [],
    price: null,
    typical_min: "72",
    typical_max: "200",
    typical_currency: "USD",
    quality: null,
    ...overrides,
  };
}

const liveRates = {
  cheapest: { site: "Agoda.com", nightly: "65", currency: "USD", site_code: null, link: null, free_cancellation: null },
} as RatesResponse;

describe("effectivePrice", () => {
  it("prefers a live quote over the typical range", () => {
    expect(effectivePrice(hotel(), liveRates)).toEqual({ nightlyUsd: 65, kind: "live", site: "Agoda.com" });
  });

  it("falls back to the typical minimum", () => {
    expect(effectivePrice(hotel(), undefined)).toEqual({ nightlyUsd: 72, kind: "typical", site: null });
  });

  it("drops the typical price once the live check finds no rooms", () => {
    const soldOut = { status: "no_results", cheapest: null } as RatesResponse;
    expect(isUnavailable(soldOut)).toBe(true);
    expect(effectivePrice(hotel(), soldOut)).toBeNull();
  });

  it("keeps the typical price when the live check failed, since availability is unknown", () => {
    const failed = { status: "error", cheapest: null } as RatesResponse;
    expect(isUnavailable(failed)).toBe(false);
    expect(effectivePrice(hotel(), failed)?.kind).toBe("typical");
  });

  it("is null when nothing is known", () => {
    expect(effectivePrice(hotel({ typical_min: null }), undefined)).toBeNull();
  });
});

describe("needsLiveRates", () => {
  it("is true for a rateable hotel without a dated price", () => {
    expect(needsLiveRates(hotel())).toBe(true);
  });

  it("is false when the search already returned a live price or no key exists", () => {
    const live = hotel({ price: { nightly: "1", total: "2", currency: "USD", kind: "live", cheapest_site: null } });
    expect(needsLiveRates(live)).toBe(false);
    expect(needsLiveRates(hotel({ rates_key: null }))).toBe(false);
  });
});
