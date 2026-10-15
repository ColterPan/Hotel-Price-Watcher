import { useQuery } from "@tanstack/react-query";
import { useId, useRef, useState, type KeyboardEvent } from "react";

import { api } from "../../api/client";
import { useDebounced } from "../../hooks/useDebounced";
import { useClickOutside } from "../../hooks/useClickOutside";
import type { Location } from "../../types";
import { Icon } from "../Icon";
import styles from "./SearchBar.module.css";

interface LocationFieldProps {
  value: { key: string; name: string } | null;
  onChange: (location: { key: string; name: string }) => void;
}

export function LocationField({ value, onChange }: LocationFieldProps) {
  const [text, setText] = useState(value?.name ?? "");
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const listId = useId();
  const wrapRef = useRef<HTMLDivElement>(null);
  const debounced = useDebounced(text, 150);

  useClickOutside(wrapRef, () => setOpen(false), open);

  const suggestions = useQuery({
    queryKey: ["locations", debounced],
    queryFn: () => api.locations(debounced),
    enabled: open,
    staleTime: Infinity,
  });
  const items: Location[] = suggestions.data ?? [];

  const choose = (location: Location) => {
    onChange({ key: location.location_key, name: location.name });
    setText(location.name);
    setOpen(false);
  };

  const onKeyDown = (event: KeyboardEvent<HTMLInputElement>) => {
    if (event.key === "ArrowDown") {
      event.preventDefault();
      setOpen(true);
      setActive((i) => Math.min(i + 1, Math.max(items.length - 1, 0)));
    } else if (event.key === "ArrowUp") {
      event.preventDefault();
      setActive((i) => Math.max(i - 1, 0));
    } else if (event.key === "Enter" && open && items[active]) {
      event.preventDefault();
      choose(items[active]);
    } else if (event.key === "Escape") {
      setOpen(false);
    }
  };

  return (
    <div className={`${styles.field} ${styles.locationField}`} ref={wrapRef}>
      <Icon name="pin" className={styles.fieldIcon} />
      <label className="visually-hidden" htmlFor={`${listId}-input`}>
        City or TripAdvisor link
      </label>
      <input
        id={`${listId}-input`}
        className={styles.input}
        placeholder="Where to? City or TripAdvisor link"
        value={text}
        autoComplete="off"
        role="combobox"
        aria-expanded={open}
        aria-controls={listId}
        aria-autocomplete="list"
        aria-activedescendant={open && items[active] ? `${listId}-${active}` : undefined}
        onFocus={(event) => {
          event.currentTarget.select();
          setOpen(true);
        }}
        onChange={(event) => {
          setText(event.target.value);
          setActive(0);
          setOpen(true);
        }}
        onKeyDown={onKeyDown}
      />
      {open ? (
        <ul className={styles.suggestions} id={listId} role="listbox">
          {items.map((location, index) => (
            <li
              key={location.location_key}
              id={`${listId}-${index}`}
              role="option"
              aria-selected={index === active}
              className={index === active ? styles.suggestionActive : styles.suggestion}
              onMouseEnter={() => setActive(index)}
              onMouseDown={(event) => {
                event.preventDefault();
                choose(location);
              }}
            >
              <span>{location.name}</span>
              <span className={styles.suggestionMeta}>{location.country || location.location_key}</span>
            </li>
          ))}
          {suggestions.isSuccess && items.length === 0 ? (
            <li className={styles.suggestionEmpty}>
              Not in the built-in list. Paste a TripAdvisor hotels link for that area instead.
            </li>
          ) : null}
        </ul>
      ) : null}
    </div>
  );
}
