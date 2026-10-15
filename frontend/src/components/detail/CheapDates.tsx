import { parseDay } from "../../lib/format";
import type { Heatmap } from "../../types";
import styles from "./Detail.module.css";

type Level = "cheap" | "average" | "high";

const DAY_LABEL = new Intl.DateTimeFormat("en", { weekday: "short", day: "numeric", month: "short" });

/** Which nearby check-in days tend to be cheap, from the provider's price calendar. */
export function CheapDates({ heatmap, checkIn }: { heatmap: Heatmap; checkIn: string }) {
  const days: { day: string; level: Level }[] = [
    ...heatmap.cheap.map((day) => ({ day, level: "cheap" as const })),
    ...heatmap.average.map((day) => ({ day, level: "average" as const })),
    ...heatmap.high.map((day) => ({ day, level: "high" as const })),
  ].sort((a, b) => a.day.localeCompare(b.day));

  if (days.length === 0) return null;
  const cheapCount = heatmap.cheap.length;

  return (
    <div>
      <div className={styles.heatmap} role="list" aria-label="Typical price by check-in day">
        {days.map(({ day, level }) => (
          <span
            key={day}
            role="listitem"
            className={styles.heatDay}
            data-level={level}
            data-current={day === checkIn || undefined}
            title={`${DAY_LABEL.format(parseDay(day))}: ${level} price`}
          />
        ))}
      </div>
      <div className={styles.legend}>
        <span data-level="cheap">cheap</span>
        <span data-level="average">average</span>
        <span data-level="high">expensive</span>
        <span className={styles.legendCurrent}>your check-in</span>
      </div>
      <p className={styles.footnote}>
        {cheapCount > 0
          ? `${cheapCount} of the ${days.length} days shown usually price low. Hover a day to see its date.`
          : "No unusually cheap days around these dates."}
      </p>
    </div>
  );
}
