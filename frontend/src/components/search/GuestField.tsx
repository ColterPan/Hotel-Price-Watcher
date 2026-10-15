import { Icon } from "../Icon";
import styles from "./SearchBar.module.css";

const MIN_GUESTS = 1;
const MAX_GUESTS = 8;

interface GuestFieldProps {
  value: number;
  onChange: (adults: number) => void;
}

export function GuestField({ value, onChange }: GuestFieldProps) {
  return (
    <div className={`${styles.field} ${styles.guests}`} role="group" aria-label="Adults">
      <Icon name="user" className={styles.fieldIcon} />
      <button
        type="button"
        className={styles.stepper}
        onClick={() => onChange(Math.max(MIN_GUESTS, value - 1))}
        disabled={value <= MIN_GUESTS}
        aria-label="One fewer adult"
      >
        <Icon name="minus" size={14} />
      </button>
      <span className="num" aria-live="polite">
        {value}
      </span>
      <button
        type="button"
        className={styles.stepper}
        onClick={() => onChange(Math.min(MAX_GUESTS, value + 1))}
        disabled={value >= MAX_GUESTS}
        aria-label="One more adult"
      >
        <Icon name="plus" size={14} />
      </button>
    </div>
  );
}
