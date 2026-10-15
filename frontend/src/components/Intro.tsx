import { addDays, toDayString } from "../lib/format";
import type { SearchParams } from "../types";
import styles from "./Shell.module.css";

const QUICK_PICKS: { name: string; key: string }[] = [
  { name: "Singapore", key: "g294265" },
  { name: "Bangkok", key: "g293916" },
  { name: "Kuala Lumpur", key: "g298570" },
  { name: "Tokyo", key: "g298184" },
  { name: "Bali", key: "g294226" },
  { name: "Seoul", key: "g294197" },
];

/** First screen: what this does, in three lines, plus one-tap example searches. */
export function Intro({ onSearch }: { onSearch: (params: SearchParams) => void }) {
  const checkIn = addDays(new Date(), 30);
  const pick = (name: string, key: string) =>
    onSearch({
      location_key: key,
      location_name: name,
      check_in: toDayString(checkIn),
      check_out: toDayString(addDays(checkIn, 2)),
      adults: 2,
    });

  return (
    <section className={styles.intro}>
      <h1 className={styles.introTitle}>Every hotel in the area, on one map.</h1>
      <ul className={styles.introPoints}>
        <li>
          <strong>Prices from several booking sites</strong> for your exact dates, side by side.
        </li>
        <li>
          <strong>One quality score</strong> built from thousands of reviews, adjusted so a handful of five-star reviews
          can't game it.
        </li>
        <li>
          <strong>A value grade</strong> that tells you what's worth the money here, and a watcher that tells you when
          the price drops.
        </li>
      </ul>
      <p className={styles.introHint}>Try a city, two nights a month from now:</p>
      <div className={styles.quickPicks}>
        {QUICK_PICKS.map((city) => (
          <button key={city.key} type="button" className="btn btn-sm" onClick={() => pick(city.name, city.key)}>
            {city.name}
          </button>
        ))}
      </div>
    </section>
  );
}
