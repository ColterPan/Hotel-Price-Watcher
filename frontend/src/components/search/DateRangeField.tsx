import { useCallback, useEffect, useRef, useState } from "react";
import { DayPicker, type DateRange } from "react-day-picker";
import "react-day-picker/style.css";

import { useClickOutside } from "../../hooks/useClickOutside";
import { formatStay, nightsBetween, parseDay, plural, toDayString } from "../../lib/format";
import { Icon } from "../Icon";
import styles from "./SearchBar.module.css";

const MAX_NIGHTS = 30;

interface DateRangeFieldProps {
  checkIn: string | null;
  checkOut: string | null;
  onChange: (checkIn: string, checkOut: string) => void;
}

function useWide(): boolean {
  const query = "(min-width: 760px)";
  const [wide, setWide] = useState(() => window.matchMedia?.(query).matches ?? true);
  useEffect(() => {
    const media = window.matchMedia?.(query);
    if (!media) return;
    const onChange = () => setWide(media.matches);
    media.addEventListener("change", onChange);
    return () => media.removeEventListener("change", onChange);
  }, []);
  return wide;
}

export function DateRangeField({ checkIn, checkOut, onChange }: DateRangeFieldProps) {
  const [open, setOpen] = useState(false);
  const [range, setRange] = useState<DateRange | undefined>(
    checkIn && checkOut ? { from: parseDay(checkIn), to: parseDay(checkOut) } : undefined,
  );
  const wrapRef = useRef<HTMLDivElement>(null);
  const wide = useWide();
  const close = useCallback(() => setOpen(false), []);
  useClickOutside(wrapRef, close, open);

  const today = new Date();
  today.setHours(0, 0, 0, 0);

  const onSelect = (next: DateRange | undefined) => {
    setRange(next);
    if (next?.from && next.to && next.to.getTime() !== next.from.getTime()) {
      onChange(toDayString(next.from), toDayString(next.to));
      setOpen(false);
    }
  };

  const label =
    checkIn && checkOut
      ? `${formatStay(checkIn, checkOut)}, ${plural(nightsBetween(checkIn, checkOut), "night")}`
      : "Add dates";

  return (
    <div className={styles.field} ref={wrapRef}>
      <button
        type="button"
        className={styles.fieldButton}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-haspopup="dialog"
      >
        <Icon name="calendar" className={styles.fieldIcon} />
        <span className={checkIn ? undefined : styles.placeholder}>{label}</span>
      </button>
      {open ? (
        <div className={styles.popover} role="dialog" aria-label="Choose check-in and check-out dates">
          <DayPicker
            mode="range"
            selected={range}
            onSelect={onSelect}
            numberOfMonths={wide ? 2 : 1}
            disabled={{ before: today }}
            startMonth={today}
            min={1}
            max={MAX_NIGHTS}
            defaultMonth={range?.from ?? today}
            className={styles.dayPicker}
          />
          <p className={styles.popoverHint}>
            {range?.from && !range.to ? "Now pick your check-out day." : "Pick check-in, then check-out."}
          </p>
        </div>
      ) : null}
    </div>
  );
}
