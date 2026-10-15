import type { SearchParams } from "../types";

// The current search lives in the URL so a refresh or a shared link restores it.

const LOCATION_KEY = /^g\d{2,10}$/;
const DAY = /^\d{4}-\d{2}-\d{2}$/;

export function readSearchFromUrl(search: string = window.location.search): SearchParams | null {
  const params = new URLSearchParams(search);
  const location_key = params.get("loc") ?? "";
  const location_name = params.get("name") ?? "";
  const check_in = params.get("in") ?? "";
  const check_out = params.get("out") ?? "";
  const adults = Number(params.get("adults") ?? "2");
  if (!LOCATION_KEY.test(location_key) || !location_name || !DAY.test(check_in) || !DAY.test(check_out)) {
    return null;
  }
  if (!Number.isInteger(adults) || adults < 1 || adults > 8) return null;
  return { location_key, location_name, check_in, check_out, adults };
}

export function writeSearchToUrl(params: SearchParams): void {
  const query = new URLSearchParams({
    loc: params.location_key,
    name: params.location_name,
    in: params.check_in,
    out: params.check_out,
    adults: String(params.adults),
  });
  window.history.replaceState(null, "", `?${query.toString()}`);
}
