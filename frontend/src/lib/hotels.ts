import type { Hotel, ProviderStatus, RatesResponse } from "../types";

/** The best nightly USD price we know for a hotel right now, and how sure we are of it. */
export interface EffectivePrice {
  nightlyUsd: number;
  kind: "live" | "typical";
  site: string | null;
}

/** The live check finished and no booking site lists the hotel for these dates. */
export function isUnavailable(rates: RatesResponse | undefined): boolean {
  return rates?.status === "no_results";
}

export function effectivePrice(hotel: Hotel, rates: RatesResponse | undefined): EffectivePrice | null {
  // Its usual starting price would be misleading here: it can't be booked.
  if (isUnavailable(rates)) return null;
  if (rates?.cheapest) {
    return { nightlyUsd: Number(rates.cheapest.nightly), kind: "live", site: rates.cheapest.site };
  }
  if (hotel.price) {
    return { nightlyUsd: Number(hotel.price.nightly), kind: hotel.price.kind, site: hotel.price.cheapest_site };
  }
  if (hotel.typical_min) {
    return { nightlyUsd: Number(hotel.typical_min), kind: "typical", site: null };
  }
  return null;
}

export function needsLiveRates(hotel: Hotel): boolean {
  return hotel.rates_key !== null && hotel.price?.kind !== "live";
}

/** Plain-language names for the people using the app, not provider ids. */
export const PROVIDER_NAMES: Record<string, string> = {
  xotelo: "TripAdvisor prices",
  serpapi: "Google Hotels",
  demo: "Sample data",
};

export const STATUS_TEXT: Record<ProviderStatus, string> = {
  ok: "live",
  no_results: "nothing found",
  not_configured: "needs an API key",
  quota_exhausted: "monthly limit reached",
  error: "unavailable",
};

export function starsLabel(hotelClass: number | null): string | null {
  return hotelClass ? `${hotelClass}-star` : null;
}
