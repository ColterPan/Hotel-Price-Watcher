import { formatReviews } from "../../lib/format";
import { safeUrl } from "../../lib/safeUrl";
import type { Hotel } from "../../types";
import { ScoreBadge } from "../results/Badges";
import styles from "./Detail.module.css";

export function ScoreBreakdown({ hotel }: { hotel: Hotel }) {
  if (hotel.ratings.length === 0) {
    return <p className={styles.muted}>No review scores were found for this place.</p>;
  }
  return (
    <div className={styles.scoreBlock}>
      <ScoreBadge quality={hotel.quality} size="lg" />
      <ul className={styles.sources}>
        {hotel.ratings.map((rating) => {
          const outOfTen = (rating.rating / rating.scale) * 10;
          const link = safeUrl(rating.url);
          return (
            <li key={rating.source} className={styles.source}>
              <div className={styles.sourceHead}>
                <span>{rating.label}</span>
                <span className="num">
                  {rating.rating.toFixed(1)} / {rating.scale}
                </span>
              </div>
              <div className={styles.bar} aria-hidden="true">
                <div className={styles.barFill} style={{ width: `${Math.min(100, outOfTen * 10)}%` }} />
              </div>
              <span className={styles.sourceMeta}>
                {formatReviews(rating.review_count)}
                {link ? (
                  <>
                    {" "}
                    <a href={link} target="_blank" rel="noopener noreferrer">
                      read them
                    </a>
                  </>
                ) : null}
              </span>
            </li>
          );
        })}
      </ul>
      <p className={styles.footnote}>
        Every source is put on a 0 to 10 scale, then weighted by its number of reviews. A rating from only a handful of
        reviews is pulled toward the area average.
      </p>
    </div>
  );
}
