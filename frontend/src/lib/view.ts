import type { Hotel } from "../types";
import type { EffectivePrice } from "./hotels";
import type { ValueResult } from "./value";

/** A hotel plus everything the UI derives for it in the current search. */
export interface HotelView {
  hotel: Hotel;
  price: EffectivePrice | null;
  value: ValueResult | null;
  /** Live rates for this hotel are still loading. */
  loadingPrice: boolean;
}

export interface MapBounds {
  south: number;
  west: number;
  north: number;
  east: number;
}

export function inBounds(hotel: Hotel, bounds: MapBounds | null): boolean {
  if (!bounds) return true;
  return (
    hotel.latitude >= bounds.south &&
    hotel.latitude <= bounds.north &&
    hotel.longitude >= bounds.west &&
    hotel.longitude <= bounds.east
  );
}

export type SortKey = "value" | "price" | "score";

export interface Filters {
  /** In the display currency. Null means no limit. */
  maxPrice: number | null;
  minScore: number;
  minStars: number;
  onlyInView: boolean;
}

export const DEFAULT_FILTERS: Filters = { maxPrice: null, minScore: 0, minStars: 0, onlyInView: false };

export function sortViews(views: readonly HotelView[], key: SortKey): HotelView[] {
  const score = (v: HotelView) => v.hotel.quality?.score ?? -1;
  const price = (v: HotelView) => v.price?.nightlyUsd ?? Number.POSITIVE_INFINITY;
  const value = (v: HotelView) => v.value?.value ?? -1;
  const compare: Record<SortKey, (a: HotelView, b: HotelView) => number> = {
    value: (a, b) => value(b) - value(a) || score(b) - score(a),
    price: (a, b) => price(a) - price(b) || score(b) - score(a),
    score: (a, b) => score(b) - score(a) || price(a) - price(b),
  };
  return [...views].sort(compare[key]);
}

export function applyFilters(
  views: readonly HotelView[],
  filters: Filters,
  bounds: MapBounds | null,
  toUsd: (amount: number) => number,
): HotelView[] {
  const maxUsd = filters.maxPrice !== null ? toUsd(filters.maxPrice) : null;
  return views.filter((view) => {
    if (maxUsd !== null && view.price && view.price.nightlyUsd > maxUsd) return false;
    if (filters.minScore > 0 && (view.hotel.quality?.score ?? 0) < filters.minScore) return false;
    if (filters.minStars > 0 && (view.hotel.hotel_class ?? 0) < filters.minStars) return false;
    if (filters.onlyInView && !inBounds(view.hotel, bounds)) return false;
    return true;
  });
}
