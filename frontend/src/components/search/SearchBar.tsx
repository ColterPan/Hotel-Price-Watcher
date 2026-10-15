import { useState, type FormEvent } from "react";

import { formatStay } from "../../lib/format";
import type { SearchParams } from "../../types";
import { Icon } from "../Icon";
import { DateRangeField } from "./DateRangeField";
import { GuestField } from "./GuestField";
import { LocationField } from "./LocationField";
import styles from "./SearchBar.module.css";

interface SearchBarProps {
  initial: SearchParams | null;
  onSearch: (params: SearchParams) => void;
  busy: boolean;
}

export function SearchBar({ initial, onSearch, busy }: SearchBarProps) {
  const [location, setLocation] = useState(
    initial ? { key: initial.location_key, name: initial.location_name } : null,
  );
  const [checkIn, setCheckIn] = useState<string | null>(initial?.check_in ?? null);
  const [checkOut, setCheckOut] = useState<string | null>(initial?.check_out ?? null);
  const [adults, setAdults] = useState(initial?.adults ?? 2);
  const [problem, setProblem] = useState<string | null>(null);
  // On small screens the form hides behind a one-line summary.
  const [expanded, setExpanded] = useState(initial === null);

  const submit = (event: FormEvent) => {
    event.preventDefault();
    if (!location) return setProblem("Pick a city from the list first.");
    if (!checkIn || !checkOut) return setProblem("Add your check-in and check-out dates.");
    setProblem(null);
    setExpanded(false);
    onSearch({ location_key: location.key, location_name: location.name, check_in: checkIn, check_out: checkOut, adults });
  };

  const summary = location && checkIn && checkOut ? `${location.name}, ${formatStay(checkIn, checkOut)}` : "Search hotels";

  return (
    <div className={styles.wrap}>
      <button
        type="button"
        className={`${styles.summary} ${expanded ? styles.summaryHidden : ""}`}
        onClick={() => setExpanded(true)}
      >
        <Icon name="search" />
        <span>{summary}</span>
        <span className={styles.summaryGuests}>{adults} adults</span>
      </button>

      <form className={`${styles.bar} ${expanded ? styles.barOpen : ""}`} onSubmit={submit} role="search">
        <LocationField value={location} onChange={setLocation} />
        <DateRangeField
          checkIn={checkIn}
          checkOut={checkOut}
          onChange={(nextIn, nextOut) => {
            setCheckIn(nextIn);
            setCheckOut(nextOut);
          }}
        />
        <GuestField value={adults} onChange={setAdults} />
        <button type="submit" className={`btn btn-primary ${styles.submit}`} disabled={busy}>
          <Icon name="search" size={16} />
          <span>{busy ? "Searching" : "Search"}</span>
        </button>
        {problem ? (
          <p className={styles.problem} role="alert">
            {problem}
          </p>
        ) : null}
      </form>
    </div>
  );
}
