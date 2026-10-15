import { useCallback, useMemo, useState } from "react";

import { ApiError } from "./api/client";
import { AlertBell } from "./components/AlertBell";
import { HotelDetail } from "./components/detail/HotelDetail";
import { Icon } from "./components/Icon";
import { Intro } from "./components/Intro";
import { MapView } from "./components/map/MapView";
import { ResultsPanel, ResultsSkeleton } from "./components/results/ResultsPanel";
import { SearchBar } from "./components/search/SearchBar";
import styles from "./components/Shell.module.css";
import { WatchesPanel } from "./components/watches/WatchesPanel";
import { useHealth, useLiveRates, useSearch, useWatches } from "./hooks/queries";
import { nightsBetween } from "./lib/format";
import { effectivePrice, isUnavailable, needsLiveRates } from "./lib/hotels";
import { computeValues, DEFAULT_WEIGHT } from "./lib/value";
import { applyFilters, DEFAULT_FILTERS, sortViews, type Filters, type HotelView, type MapBounds, type SortKey } from "./lib/view";
import { CurrencyProvider, useMoney } from "./state/currency";
import { readSearchFromUrl, writeSearchToUrl } from "./state/urlState";
import type { SearchParams } from "./types";

type Panel = "results" | "watches";

export default function App() {
  const health = useHealth();
  return (
    <CurrencyProvider defaultCurrency={health.data?.default_display_currency ?? "SGD"}>
      <Shell checkIntervalHours={health.data?.check_interval_hours ?? null} />
    </CurrencyProvider>
  );
}

function Shell({ checkIntervalHours }: { checkIntervalHours: number | null }) {
  const money = useMoney();
  const [params, setParams] = useState<SearchParams | null>(() => readSearchFromUrl());
  const [refreshToken, setRefreshToken] = useState(0);
  const [panel, setPanel] = useState<Panel>("results");
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [hoveredId, setHoveredId] = useState<string | null>(null);
  const [filters, setFilters] = useState<Filters>(DEFAULT_FILTERS);
  const [sort, setSort] = useState<SortKey>("value");
  const [weight, setWeight] = useState(DEFAULT_WEIGHT);
  const [bounds, setBounds] = useState<MapBounds | null>(null);
  const [sheetFull, setSheetFull] = useState(false);

  const search = useSearch(params, refreshToken);
  const watches = useWatches();
  const hotels = useMemo(() => search.data?.hotels ?? [], [search.data]);
  const live = useLiveRates(hotels, params);

  const allViews: HotelView[] = useMemo(() => {
    const base = hotels.map((hotel) => ({
      hotel,
      price: effectivePrice(hotel, live.ratesById.get(hotel.id)),
      loadingPrice: needsLiveRates(hotel) && live.pendingIds.has(hotel.id),
      unavailable: isUnavailable(live.ratesById.get(hotel.id)),
    }));
    const values = computeValues(
      base.map((v) => ({ id: v.hotel.id, price: v.price?.nightlyUsd ?? null, quality: v.hotel.quality?.score ?? null })),
      weight,
    );
    return base.map((v) => ({ ...v, value: values.get(v.hotel.id) ?? null }));
  }, [hotels, live.ratesById, live.pendingIds, weight]);

  const mapViews = useMemo(
    () => applyFilters(allViews, { ...filters, onlyInView: false }, null, money.toUsd),
    [allViews, filters, money.toUsd],
  );
  const listViews = useMemo(
    () => sortViews(applyFilters(allViews, filters, bounds, money.toUsd), sort),
    [allViews, filters, bounds, money.toUsd, sort],
  );
  const selected = allViews.find((v) => v.hotel.id === selectedId) ?? null;
  const nights = params ? nightsBetween(params.check_in, params.check_out) : 1;
  const maxPriceUsd = filters.maxPrice !== null ? money.toUsd(filters.maxPrice) : null;

  const runSearch = useCallback((next: SearchParams) => {
    setParams(next);
    writeSearchToUrl(next);
    setRefreshToken(0);
    setSelectedId(null);
    setPanel("results");
  }, []);

  const select = useCallback((id: string) => {
    setSelectedId(id);
    setPanel("results");
    setSheetFull(true);
  }, []);

  const existingWatch =
    selected && params
      ? (watches.data ?? []).find(
          (w) =>
            w.hotel_key === selected.hotel.rates_key &&
            w.check_in === params.check_in &&
            w.check_out === params.check_out &&
            w.adults === params.adults,
        ) ?? null
      : null;

  const center: [number, number] | null =
    search.data?.center_latitude != null && search.data.center_longitude != null
      ? [search.data.center_latitude, search.data.center_longitude]
      : null;

  let drawer;
  if (panel === "watches") {
    drawer = <WatchesPanel onClose={() => setPanel("results")} checkIntervalHours={checkIntervalHours} />;
  } else if (!params) {
    drawer = <Intro onSearch={runSearch} />;
  } else if (search.isPending) {
    drawer = <ResultsSkeleton />;
  } else if (search.isError) {
    drawer = (
      <div className={styles.errorBox} role="alert">
        <p>{search.error instanceof ApiError ? search.error.message : "The search failed."}</p>
        <button type="button" className="btn btn-sm" onClick={() => void search.refetch()}>
          Try again
        </button>
      </div>
    );
  } else if (selected) {
    drawer = (
      <HotelDetail
        view={selected}
        params={params}
        nights={nights}
        watch={existingWatch}
        formatPrice={money.format}
        onBack={() => setSelectedId(null)}
        onOpenWatches={() => setPanel("watches")}
      />
    );
  } else {
    drawer = (
      <ResultsPanel
        response={search.data}
        views={listViews}
        totalCount={hotels.length}
        nights={nights}
        ratesProgress={{ pending: live.pendingIds.size, total: live.total }}
        hoveredId={hoveredId}
        sort={sort}
        onSortChange={setSort}
        filters={filters}
        onFiltersChange={setFilters}
        weight={weight}
        onWeightChange={setWeight}
        currency={money.currency}
        formatPrice={money.format}
        onSelect={select}
        onHover={setHoveredId}
        onRefresh={() => setRefreshToken((t) => t + 1)}
        refreshing={search.isFetching}
      />
    );
  }

  const watchCount = watches.data?.length ?? 0;

  return (
    <div className={styles.app}>
      <MapView
        views={mapViews}
        center={center}
        resultsKey={search.data ? `${search.data.generated_at}|${search.data.query.location_key}` : null}
        selectedId={selectedId}
        hoveredId={hoveredId}
        maxPriceUsd={maxPriceUsd}
        formatPrice={money.format}
        onSelect={select}
        onHover={setHoveredId}
        onBoundsChange={setBounds}
      />

      <header className={styles.topbar}>
        <a className={styles.brand} href="/" aria-label="Hotel Price Watcher, start over">
          <img src="/favicon.svg" alt="" width={28} height={28} />
          <span>Hotel Price Watcher</span>
        </a>
        <SearchBar
          key={params ? JSON.stringify(params) : "empty"}
          initial={params}
          onSearch={runSearch}
          busy={search.isFetching}
        />
        <div className={styles.topActions}>
          <label className="visually-hidden" htmlFor="currency">
            Show prices in
          </label>
          <select
            id="currency"
            className={`field ${styles.currency}`}
            value={money.currency}
            onChange={(event) => money.setCurrency(event.target.value)}
            title={money.ratesAsOf ? `Exchange rates as of ${money.ratesAsOf}` : "Exchange rates"}
          >
            {Object.keys(money.supported)
              .sort()
              .map((code) => (
                <option key={code} value={code}>
                  {code}
                </option>
              ))}
          </select>
          <button
            type="button"
            className={`btn ${styles.topButton} ${panel === "watches" ? styles.topButtonActive : ""}`}
            onClick={() => setPanel((p) => (p === "watches" ? "results" : "watches"))}
            aria-pressed={panel === "watches"}
          >
            <Icon name="eye" />
            <span className={styles.hideSmall}>Watching</span>
            {watchCount > 0 ? <span className="num">{watchCount}</span> : null}
          </button>
          <AlertBell onOpenWatches={() => setPanel("watches")} />
        </div>
      </header>

      <aside className={`${styles.drawer} ${sheetFull ? styles.drawerFull : ""}`}>
        <button
          type="button"
          className={styles.handle}
          onClick={() => setSheetFull((full) => !full)}
          aria-label={sheetFull ? "Show more map" : "Show more results"}
        >
          <span />
        </button>
        <div className={styles.drawerBody}>{drawer}</div>
      </aside>

      {money.ratesUnavailable ? (
        <p className={styles.toast} role="status">
          Exchange rates are unavailable, so prices are shown in USD.
        </p>
      ) : null}
    </div>
  );
}
