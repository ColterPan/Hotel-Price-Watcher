import { useHeatmap, useHotelRates, usePriceHistory } from "../../hooks/queries";
import { formatStay, plural } from "../../lib/format";
import { PROVIDER_NAMES, starsLabel } from "../../lib/hotels";
import { safeUrl } from "../../lib/safeUrl";
import type { HotelView } from "../../lib/view";
import type { SearchParams, Watch } from "../../types";
import { Icon } from "../Icon";
import { GradeBadge } from "../results/Badges";
import { CheapDates } from "./CheapDates";
import styles from "./Detail.module.css";
import { PriceTable } from "./PriceTable";
import { ScoreBreakdown } from "./ScoreBreakdown";
import { Sparkline } from "./Sparkline";
import { WatchBox } from "./WatchBox";

interface HotelDetailProps {
  view: HotelView;
  params: SearchParams;
  nights: number;
  watch: Watch | null;
  formatPrice: (usd: number) => string;
  onBack: () => void;
  onOpenWatches: () => void;
}

export function HotelDetail({ view, params, nights, watch, formatPrice, onBack, onOpenWatches }: HotelDetailProps) {
  const { hotel, price, value } = view;
  const rates = useHotelRates(hotel.rates_key, params);
  const heatmap = useHeatmap(hotel.rates_key, params.check_out);
  const history = usePriceHistory(hotel.rates_key, params);

  const offers = rates.data?.offers ?? hotel.offers;
  const image = safeUrl(hotel.image_url);
  const listing = safeUrl(hotel.url);
  const meta = [starsLabel(hotel.hotel_class), hotel.accommodation_type].filter(Boolean).join(", ");
  const historyValues = (history.data ?? []).map((point) => Number(point.nightly));

  return (
    <article className={styles.detail} aria-label={hotel.name}>
      <div className={styles.topRow}>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onBack}>
          <Icon name="back" size={16} />
          All results
        </button>
      </div>

      <div className={styles.scroll}>
        {image ? (
          <div className={styles.hero}>
            <img src={image} alt="" referrerPolicy="no-referrer" />
          </div>
        ) : null}

        <header className={styles.head}>
          <div className={styles.titleRow}>
            <h2 className={styles.name}>{hotel.name}</h2>
            <GradeBadge grade={value?.grade ?? null} />
          </div>
          {meta ? <p className={styles.meta}>{meta}</p> : null}
          {hotel.labels.length > 0 ? (
            <div className={styles.chips}>
              {hotel.labels.map((label) => (
                <span key={label} className="chip">
                  {label}
                </span>
              ))}
            </div>
          ) : null}
          {price ? (
            <p className={styles.headPrice}>
              <span className={`num ${styles.bigPrice}`}>{formatPrice(price.nightlyUsd)}</span>
              <span className={styles.muted}>
                {price.kind === "live"
                  ? ` a night, ${formatPrice(price.nightlyUsd * nights)} for ${plural(nights, "night")}`
                  : " a night, usual starting price"}
              </span>
            </p>
          ) : null}
        </header>

        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>Prices for {formatStay(params.check_in, params.check_out)}</h3>
          <PriceTable
            offers={offers}
            nights={nights}
            formatPrice={formatPrice}
            loading={hotel.rates_key !== null && rates.isPending}
            failed={rates.isError}
          />
          <p className={styles.footnote}>
            Per room, per night, as listed by each site. Taxes and fees may be extra. Book on the site itself.
            {listing ? (
              <>
                {" "}
                <a href={listing} target="_blank" rel="noopener noreferrer">
                  Open the listing <Icon name="external" size={12} />
                </a>
              </>
            ) : null}
          </p>
        </section>

        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>How good is it</h3>
          <ScoreBreakdown hotel={hotel} />
        </section>

        {heatmap.data ? (
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Cheaper days nearby</h3>
            <CheapDates heatmap={heatmap.data} checkIn={params.check_in} />
          </section>
        ) : null}

        {historyValues.length >= 2 ? (
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Price history for these dates</h3>
            <Sparkline values={historyValues} label={`Cheapest nightly price over ${historyValues.length} checks`} />
            <p className={styles.footnote}>
              Lowest {formatPrice(Math.min(...historyValues))}, highest {formatPrice(Math.max(...historyValues))}, over{" "}
              {plural(historyValues.length, "check")}.
            </p>
          </section>
        ) : null}

        <section className={styles.section}>
          <h3 className={styles.sectionTitle}>Watch for a drop</h3>
          <WatchBox hotel={hotel} params={params} existing={watch} onOpenWatches={onOpenWatches} />
        </section>

        {hotel.amenities.length > 0 ? (
          <section className={styles.section}>
            <h3 className={styles.sectionTitle}>Amenities</h3>
            <div className={styles.chips}>
              {hotel.amenities.map((amenity) => (
                <span key={amenity} className="chip">
                  {amenity}
                </span>
              ))}
            </div>
          </section>
        ) : null}

        <p className={styles.sourcesLine}>
          Data from {hotel.providers.map((p) => PROVIDER_NAMES[p] ?? p).join(" and ")}.
        </p>
      </div>
    </article>
  );
}
