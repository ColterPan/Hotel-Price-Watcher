// Mirrors the backend's response models. Money arrives as decimal strings and
// is always in the provider currency (USD); the UI converts only for display.

export type ProviderStatus = "ok" | "no_results" | "not_configured" | "quota_exhausted" | "error";

export interface Location {
  name: string;
  country: string;
  location_key: string;
  latitude: number | null;
  longitude: number | null;
}

export interface SourceRating {
  source: string;
  label: string;
  rating: number;
  scale: number;
  review_count: number;
  url: string | null;
}

export interface Offer {
  site: string;
  site_code: string | null;
  nightly: string;
  currency: string;
  link: string | null;
  free_cancellation: boolean | null;
}

export interface QualityScore {
  score: number;
  label: string;
  review_count: number;
  low_confidence: boolean;
}

export interface PriceSummary {
  nightly: string;
  total: string;
  currency: string;
  kind: "live" | "typical";
  cheapest_site: string | null;
}

export interface Hotel {
  id: string;
  name: string;
  latitude: number;
  longitude: number;
  image_url: string | null;
  url: string | null;
  accommodation_type: string | null;
  hotel_class: number | null;
  amenities: string[];
  labels: string[];
  providers: string[];
  rates_key: string | null;
  ratings: SourceRating[];
  offers: Offer[];
  price: PriceSummary | null;
  typical_min: string | null;
  typical_max: string | null;
  typical_currency: string | null;
  quality: QualityScore | null;
}

export interface SearchParams {
  location_key: string;
  location_name: string;
  check_in: string; // YYYY-MM-DD
  check_out: string;
  adults: number;
}

export interface SearchResponse {
  query: SearchParams & { limit: number };
  hotels: Hotel[];
  provider_statuses: Record<string, ProviderStatus>;
  provider_diagnostics: Record<string, string>;
  center_latitude: number | null;
  center_longitude: number | null;
  generated_at: string;
  from_cache: boolean;
}

export interface RatesResponse {
  hotel_key: string;
  check_in: string;
  check_out: string;
  adults: number;
  nights: number;
  provider: string;
  status: ProviderStatus;
  offers: Offer[];
  cheapest: Offer | null;
  total: string | null;
  diagnostic: string | null;
  from_cache: boolean;
}

export interface Heatmap {
  cheap: string[];
  average: string[];
  high: string[];
}

export interface PricePoint {
  observed_at: string;
  nightly: string;
  currency: string;
  site: string | null;
}

export interface Watch {
  id: number;
  hotel_key: string;
  hotel_name: string;
  location_name: string | null;
  latitude: number | null;
  longitude: number | null;
  image_url: string | null;
  hotel_url: string | null;
  check_in: string;
  check_out: string;
  adults: number;
  target_price: string | null;
  currency: string;
  active: boolean;
  created_at: string;
  last_checked_at: string | null;
  last_status: string | null;
  last_price: string | null;
  last_site: string | null;
  lowest_price: string | null;
  history: PricePoint[];
}

export interface WatchCreate {
  hotel_key: string;
  hotel_name: string;
  location_name: string | null;
  latitude: number | null;
  longitude: number | null;
  image_url: string | null;
  hotel_url: string | null;
  check_in: string;
  check_out: string;
  adults: number;
  target_price: string | null;
}

export interface CheckResult {
  watch_id: number;
  status: string;
  price: string | null;
  site: string | null;
  alert_kind: "new_low" | "target_hit" | null;
  alert_id: number | null;
}

export interface CheckResponse {
  result: CheckResult;
  watch: Watch;
}

export interface Alert {
  id: number;
  watch_id: number;
  hotel_name: string;
  hotel_key: string;
  check_in: string;
  check_out: string;
  kind: "new_low" | "target_hit";
  price: string;
  previous_low: string | null;
  currency: string;
  site: string | null;
  message: string;
  created_at: string;
  read_at: string | null;
}

export interface AlertsResponse {
  alerts: Alert[];
  unread_count: number;
}

export interface Health {
  status: string;
  version: string;
  providers: { name: string; label: string }[];
  serpapi: { configured: boolean; used_this_month: number; monthly_budget: number } | null;
  default_display_currency: string;
  check_interval_hours: number;
}

export interface ExchangeRates {
  base: string;
  as_of: string;
  stale: boolean;
  rates: Record<string, string>;
  supported_currencies: Record<string, string>;
}
