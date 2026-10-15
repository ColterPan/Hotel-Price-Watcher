import { memo } from "react";

import { formatReviews } from "../../lib/format";
import { starsLabel } from "../../lib/hotels";
import { safeUrl } from "../../lib/safeUrl";
import type { HotelView } from "../../lib/view";
import { GradeBadge, ScoreBadge } from "./Badges";
import styles from "./Results.module.css";

interface HotelCardProps {
  view: HotelView;
  nights: number;
  highlighted: boolean;
  formatPrice: (usd: number) => string;
  onSelect: (id: string) => void;
  onHover: (id: string | null) => void;
}

function HotelCardImpl({ view, nights, highlighted, formatPrice, onSelect, onHover }: HotelCardProps) {
  const { hotel, price, value, loadingPrice } = view;
  const image = safeUrl(hotel.image_url);
  const meta = [starsLabel(hotel.hotel_class), hotel.accommodation_type].filter(Boolean).join(", ");

  return (
    <li>
      <button
        type="button"
        className={`${styles.card} ${highlighted ? styles.cardHighlighted : ""}`}
        onClick={() => onSelect(hotel.id)}
        onMouseEnter={() => onHover(hotel.id)}
        onMouseLeave={() => onHover(null)}
        onFocus={() => onHover(hotel.id)}
        onBlur={() => onHover(null)}
      >
        <div className={styles.thumb}>
          {image ? (
            <img src={image} alt="" loading="lazy" referrerPolicy="no-referrer" />
          ) : (
            <span className={styles.thumbEmpty} aria-hidden="true">
              {hotel.name.slice(0, 1)}
            </span>
          )}
        </div>

        <div className={styles.cardBody}>
          <div className={styles.cardTitleRow}>
            <h3 className={styles.cardTitle}>{hotel.name}</h3>
            <GradeBadge grade={value?.grade ?? null} />
          </div>
          {meta ? <p className={styles.cardMeta}>{meta}</p> : null}
          <div className={styles.cardScoreRow}>
            <ScoreBadge quality={hotel.quality} />
            {hotel.quality ? (
              <span className={styles.reviews}>{formatReviews(hotel.quality.review_count)}</span>
            ) : null}
          </div>

          <div className={styles.cardPriceRow}>
            {price ? (
              <>
                <span className={styles.priceBlock}>
                  {price.kind === "typical" ? <span className={styles.priceFrom}>usually from</span> : null}
                  <span className={`num ${styles.price}`}>{formatPrice(price.nightlyUsd)}</span>
                  <span className={styles.perNight}>/ night</span>
                </span>
                {price.kind === "live" ? (
                  <span className={styles.priceTotal}>
                    <span className="num">{formatPrice(price.nightlyUsd * nights)}</span> total
                    {price.site ? <> on {price.site}</> : null}
                  </span>
                ) : loadingPrice ? (
                  <span className={styles.priceTotal}>checking your dates</span>
                ) : (
                  <span className={styles.priceTotal}>no dated price</span>
                )}
              </>
            ) : (
              <span className={styles.priceTotal}>
                {loadingPrice
                  ? "checking your dates"
                  : view.unavailable
                    ? "No rooms listed for these dates"
                    : "No price found"}
              </span>
            )}
          </div>
        </div>
      </button>
    </li>
  );
}

export const HotelCard = memo(HotelCardImpl);
