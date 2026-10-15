import { useMutation, useQueries, useQuery, useQueryClient, type UseQueryResult } from "@tanstack/react-query";
import { useCallback, useMemo } from "react";

import { api, type StayParams } from "../api/client";
import { needsLiveRates } from "../lib/hotels";
import type { Hotel, RatesResponse, SearchParams, WatchCreate } from "../types";

const MINUTE = 60 * 1000;

export function useHealth() {
  return useQuery({ queryKey: ["health"], queryFn: api.health, staleTime: 5 * MINUTE });
}

export function useSearch(params: SearchParams | null, refreshToken: number) {
  return useQuery({
    queryKey: ["search", params, refreshToken],
    // A non-zero refresh token means the user asked to bypass the server cache.
    queryFn: () => api.search(params!, refreshToken > 0),
    enabled: params !== null,
    staleTime: 15 * MINUTE,
    retry: false,
  });
}

export function stayOf(params: SearchParams): StayParams {
  return { check_in: params.check_in, check_out: params.check_out, adults: params.adults };
}

/**
 * Live rates for every hotel that only has a "typical" price, fetched in
 * parallel. The backend caps how many reach Xotelo at once, so this can fire
 * them all and let prices fill in on the map as they arrive.
 */
export interface LiveRates {
  ratesById: Map<string, RatesResponse>;
  pendingIds: Set<string>;
  total: number;
}

export function useLiveRates(hotels: readonly Hotel[], params: SearchParams | null): LiveRates {
  const stay = useMemo(() => (params ? stayOf(params) : null), [params]);
  const targets = useMemo(() => (stay ? hotels.filter(needsLiveRates) : []), [hotels, stay]);
  // A stable `combine` keeps the returned maps referentially stable until a
  // result actually changes, so the map and list don't re-render for nothing.
  const combine = useCallback(
    (results: UseQueryResult<RatesResponse>[]): LiveRates => {
      const ratesById = new Map<string, RatesResponse>();
      const pendingIds = new Set<string>();
      results.forEach((result, index) => {
        const hotel = targets[index];
        if (!hotel) return;
        if (result.data) ratesById.set(hotel.id, result.data);
        if (result.isPending) pendingIds.add(hotel.id);
      });
      return { ratesById, pendingIds, total: targets.length };
    },
    [targets],
  );
  return useQueries({
    queries: targets.map((hotel) => ({
      queryKey: ["rates", hotel.rates_key, stay],
      queryFn: () => api.rates(hotel.rates_key!, stay!),
      staleTime: 30 * MINUTE,
      retry: 1,
    })),
    combine,
  });
}

export function useHotelRates(hotelKey: string | null, params: SearchParams | null) {
  const stay = params ? stayOf(params) : null;
  return useQuery({
    queryKey: ["rates", hotelKey, stay],
    queryFn: () => api.rates(hotelKey!, stay!),
    enabled: hotelKey !== null && stay !== null,
    staleTime: 30 * MINUTE,
  });
}

export function useHeatmap(hotelKey: string | null, checkOut: string | null) {
  return useQuery({
    queryKey: ["heatmap", hotelKey, checkOut],
    queryFn: () => api.heatmap(hotelKey!, checkOut!),
    enabled: hotelKey !== null && checkOut !== null,
    staleTime: 60 * MINUTE,
    retry: false,
  });
}

export function usePriceHistory(hotelKey: string | null, params: SearchParams | null) {
  const stay = params ? stayOf(params) : null;
  return useQuery({
    queryKey: ["history", hotelKey, stay],
    queryFn: () => api.history(hotelKey!, stay!),
    enabled: hotelKey !== null && stay !== null,
  });
}

export function useWatches() {
  return useQuery({ queryKey: ["watches"], queryFn: api.watches, refetchInterval: 5 * MINUTE });
}

export function useAlerts() {
  return useQuery({ queryKey: ["alerts"], queryFn: api.alerts, refetchInterval: MINUTE });
}

export function useWatchMutations() {
  const client = useQueryClient();
  const refresh = () => {
    void client.invalidateQueries({ queryKey: ["watches"] });
    void client.invalidateQueries({ queryKey: ["alerts"] });
    void client.invalidateQueries({ queryKey: ["history"] });
  };
  const create = useMutation({ mutationFn: (data: WatchCreate) => api.createWatch(data), onSuccess: refresh });
  const remove = useMutation({ mutationFn: (id: number) => api.deleteWatch(id), onSuccess: refresh });
  const check = useMutation({ mutationFn: (id: number) => api.checkWatch(id), onSuccess: refresh });
  return { create, remove, check };
}

export function useAlertMutations() {
  const client = useQueryClient();
  const refresh = () => void client.invalidateQueries({ queryKey: ["alerts"] });
  const markRead = useMutation({ mutationFn: (id: number) => api.markAlertRead(id), onSuccess: refresh });
  const markAll = useMutation({ mutationFn: () => api.markAllAlertsRead(), onSuccess: refresh });
  return { markRead, markAll };
}
