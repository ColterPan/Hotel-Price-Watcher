import { useState } from "react";

import { formatStay, plural } from "../../lib/format";
import { DEFAULT_FILTERS, type Filters, type HotelView, type SortKey } from "../../lib/view";
import type { SearchResponse } from "../../types";
import { Icon } from "../Icon";
import { FilterPanel } from "./FilterPanel";
import { HotelCard } from "./HotelCard";
import { ProviderStrip } from "./ProviderStrip";
import styles from "./Results.module.css";

interface ResultsPanelProps {
  response: SearchResponse;
  views: HotelView[];
  totalCount: number;
  nights: number;
  ratesProgress: { pending: number; total: number };
  hoveredId: string | null;
  sort: SortKey;
  onSortChange: (sort: SortKey) => void;
  filters: Filters;
  onFiltersChange: (filters: Filters) => void;
  weight: number;
  onWeightChange: (weight: number) => void;
  currency: string;
  formatPrice: (usd: number) => string;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
  onRefresh: () => void;
  refreshing: boolean;
}

const SORTS: { key: SortKey; label: string }[] = [
  { key: "value", label: "Best value" },
  { key: "price", label: "Cheapest" },
  { key: "score", label: "Top rated" },
];

function activeFilterCount(filters: Filters): number {
  return (
    (filters.maxPrice !== null ? 1 : 0) +
    (filters.minScore > 0 ? 1 : 0) +
    (filters.minStars > 0 ? 1 : 0) +
    (filters.onlyInView ? 1 : 0)
  );
}

export function ResultsPanel(props: ResultsPanelProps) {
  const { response, views, totalCount, nights, ratesProgress, filters } = props;
  const [showFilters, setShowFilters] = useState(false);
  const activeFilters = activeFilterCount(filters);
  const { query } = response;
  const checked = ratesProgress.total - ratesProgress.pending;

  return (
    <section className={styles.panel} aria-label="Search results">
      <header className={styles.header}>
        <div className={styles.headerTop}>
          <div>
            <h2 className={styles.title}>
              {plural(totalCount, "place")} in {query.location_name}
            </h2>
            <p className={styles.subtitle}>
              {formatStay(query.check_in, query.check_out)}, {plural(nights, "night")}, {plural(query.adults, "adult")}
            </p>
          </div>
          <button
            type="button"
            className="btn btn-ghost btn-icon"
            onClick={props.onRefresh}
            disabled={props.refreshing}
            title="Search again for fresh prices"
            aria-label="Search again for fresh prices"
          >
            <Icon name="refresh" />
          </button>
        </div>
        <ProviderStrip statuses={response.provider_statuses} diagnostics={response.provider_diagnostics} />
        {ratesProgress.total > 0 && ratesProgress.pending > 0 ? (
          <div className={styles.progress} role="status">
            <div className={styles.progressBar} style={{ width: `${(checked / ratesProgress.total) * 100}%` }} />
            <span>
              Checking prices for your dates: {checked} of {ratesProgress.total}
            </span>
          </div>
        ) : null}

        <div className={styles.controls}>
          <div className={styles.segmented} role="radiogroup" aria-label="Sort by">
            {SORTS.map((option) => (
              <button
                key={option.key}
                type="button"
                role="radio"
                aria-checked={props.sort === option.key}
                className={props.sort === option.key ? styles.segmentActive : styles.segment}
                onClick={() => props.onSortChange(option.key)}
              >
                {option.label}
              </button>
            ))}
          </div>
          <button
            type="button"
            className={`btn btn-sm ${showFilters ? styles.filtersOn : ""}`}
            onClick={() => setShowFilters((s) => !s)}
            aria-expanded={showFilters}
          >
            <Icon name="sliders" size={15} />
            Filters{activeFilters > 0 ? ` (${activeFilters})` : ""}
          </button>
        </div>
        {showFilters ? (
          <FilterPanel
            filters={filters}
            onChange={props.onFiltersChange}
            weight={props.weight}
            onWeightChange={props.onWeightChange}
            currency={props.currency}
          />
        ) : null}
      </header>

      {views.length === 0 ? (
        <div className={styles.empty}>
          {totalCount === 0 ? (
            <p>
              No hotels came back for this area. If a source above says unavailable, try again in a minute.
            </p>
          ) : (
            <>
              <p>Nothing matches these filters.</p>
              <button type="button" className="btn btn-sm" onClick={() => props.onFiltersChange(DEFAULT_FILTERS)}>
                Clear filters
              </button>
            </>
          )}
        </div>
      ) : (
        <ul className={styles.list}>
          {views.map((view) => (
            <HotelCard
              key={view.hotel.id}
              view={view}
              nights={nights}
              highlighted={view.hotel.id === props.hoveredId}
              formatPrice={props.formatPrice}
              onSelect={props.onSelect}
              onHover={props.onHover}
            />
          ))}
        </ul>
      )}
    </section>
  );
}

export function ResultsSkeleton() {
  return (
    <section className={styles.panel} aria-busy="true" aria-label="Loading results">
      <header className={styles.header}>
        <div className="skeleton" style={{ height: 22, width: "60%" }} />
        <div className="skeleton" style={{ height: 14, width: "40%", marginTop: 8 }} />
      </header>
      <ul className={styles.list}>
        {Array.from({ length: 5 }, (_, i) => (
          <li key={i} className={styles.skeletonCard}>
            <div className="skeleton" style={{ width: 88, height: 88 }} />
            <div style={{ flex: 1 }}>
              <div className="skeleton" style={{ height: 16, width: "70%" }} />
              <div className="skeleton" style={{ height: 12, width: "40%", marginTop: 10 }} />
              <div className="skeleton" style={{ height: 18, width: "50%", marginTop: 14 }} />
            </div>
          </li>
        ))}
      </ul>
    </section>
  );
}
