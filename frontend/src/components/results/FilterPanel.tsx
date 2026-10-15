import { useId } from "react";

import type { Filters } from "../../lib/view";
import styles from "./Results.module.css";

interface FilterPanelProps {
  filters: Filters;
  onChange: (filters: Filters) => void;
  weight: number;
  onWeightChange: (weight: number) => void;
  currency: string;
}

const SCORE_OPTIONS = [0, 7, 8, 8.5, 9];
const STAR_OPTIONS = [0, 3, 4, 5];

export function FilterPanel({ filters, onChange, weight, onWeightChange, currency }: FilterPanelProps) {
  const id = useId();
  const set = <K extends keyof Filters>(key: K, value: Filters[K]) => onChange({ ...filters, [key]: value });

  return (
    <div className={styles.filters}>
      <div className={styles.filterRow}>
        <label htmlFor={`${id}-weight`} className={styles.filterLabel}>
          What matters more
        </label>
        <div className={styles.slider}>
          <span>Price</span>
          <input
            id={`${id}-weight`}
            type="range"
            min={0}
            max={1}
            step={0.05}
            value={weight}
            onChange={(event) => onWeightChange(Number(event.target.value))}
            aria-valuetext={`${Math.round((1 - weight) * 100)}% price, ${Math.round(weight * 100)}% quality`}
          />
          <span>Quality</span>
        </div>
      </div>

      <div className={styles.filterGrid}>
        <label className={styles.filterField}>
          <span className={styles.filterLabel}>Max per night ({currency})</span>
          <input
            className="field num"
            type="number"
            inputMode="numeric"
            min={0}
            placeholder="Any"
            value={filters.maxPrice ?? ""}
            onChange={(event) => set("maxPrice", event.target.value === "" ? null : Math.max(0, Number(event.target.value)))}
          />
        </label>

        <label className={styles.filterField}>
          <span className={styles.filterLabel}>Min score</span>
          <select className="field" value={filters.minScore} onChange={(event) => set("minScore", Number(event.target.value))}>
            {SCORE_OPTIONS.map((score) => (
              <option key={score} value={score}>
                {score === 0 ? "Any" : `${score}+`}
              </option>
            ))}
          </select>
        </label>

        <label className={styles.filterField}>
          <span className={styles.filterLabel}>Stars</span>
          <select className="field" value={filters.minStars} onChange={(event) => set("minStars", Number(event.target.value))}>
            {STAR_OPTIONS.map((stars) => (
              <option key={stars} value={stars}>
                {stars === 0 ? "Any" : `${stars}+`}
              </option>
            ))}
          </select>
        </label>
      </div>

      <label className={styles.toggle}>
        <input type="checkbox" checked={filters.onlyInView} onChange={(event) => set("onlyInView", event.target.checked)} />
        <span>Only show hotels in the map view</span>
      </label>
    </div>
  );
}
