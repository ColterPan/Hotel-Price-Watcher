import type {
  AlertsResponse,
  CheckResponse,
  ExchangeRates,
  Health,
  Heatmap,
  Location,
  PricePoint,
  RatesResponse,
  SearchParams,
  SearchResponse,
  Watch,
  WatchCreate,
} from "../types";

export class ApiError extends Error {
  readonly status: number;

  constructor(status: number, message: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
  }
}

async function readDetail(response: Response): Promise<string> {
  try {
    const body: unknown = await response.json();
    if (body && typeof body === "object" && "detail" in body) {
      const detail = (body as { detail: unknown }).detail;
      if (typeof detail === "string") return detail;
    }
  } catch {
    // Not JSON (a proxy error page, for example). Fall through to the status text.
  }
  return response.status >= 500
    ? "The server had a problem. Try again in a moment."
    : `Request failed (${response.status})`;
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response;
  try {
    response = await fetch(path, {
      ...init,
      headers: { "Content-Type": "application/json", ...init?.headers },
    });
  } catch {
    throw new ApiError(0, "Can't reach the server. Is the backend running?");
  }
  if (!response.ok) {
    throw new ApiError(response.status, await readDetail(response));
  }
  if (response.status === 204) return undefined as T;
  return (await response.json()) as T;
}

function query(params: Record<string, string | number | boolean>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) search.set(key, String(value));
  return search.toString();
}

export interface StayParams {
  check_in: string;
  check_out: string;
  adults: number;
}

export const api = {
  health: () => request<Health>("/api/health"),

  locations: (q: string) => request<Location[]>(`/api/locations?${query({ q })}`),

  search: (params: SearchParams, refresh = false) =>
    request<SearchResponse>(`/api/search?${query({ refresh })}`, {
      method: "POST",
      body: JSON.stringify({ ...params, limit: 30 }),
    }),

  rates: (hotelKey: string, stay: StayParams) =>
    request<RatesResponse>(`/api/hotels/${encodeURIComponent(hotelKey)}/rates?${query({ ...stay })}`),

  heatmap: (hotelKey: string, checkOut: string) =>
    request<Heatmap>(`/api/hotels/${encodeURIComponent(hotelKey)}/heatmap?${query({ check_out: checkOut })}`),

  history: (hotelKey: string, stay: StayParams) =>
    request<PricePoint[]>(`/api/hotels/${encodeURIComponent(hotelKey)}/history?${query({ ...stay })}`),

  watches: () => request<Watch[]>("/api/watches"),

  createWatch: (data: WatchCreate) =>
    request<CheckResponse>("/api/watches", { method: "POST", body: JSON.stringify(data) }),

  deleteWatch: (id: number) => request<void>(`/api/watches/${id}`, { method: "DELETE" }),

  checkWatch: (id: number) => request<CheckResponse>(`/api/watches/${id}/check`, { method: "POST" }),

  alerts: () => request<AlertsResponse>("/api/alerts?limit=30"),

  markAlertRead: (id: number) => request<void>(`/api/alerts/${id}/read`, { method: "POST" }),

  markAllAlertsRead: () => request<void>("/api/alerts/read-all", { method: "POST" }),

  exchangeRates: () => request<ExchangeRates>("/api/currency/rates?base=USD"),
};
