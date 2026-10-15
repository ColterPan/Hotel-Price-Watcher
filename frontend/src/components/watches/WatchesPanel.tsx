import { ApiError } from "../../api/client";
import { useWatchMutations, useWatches } from "../../hooks/queries";
import { formatStay, plural, timeAgo } from "../../lib/format";
import { safeUrl } from "../../lib/safeUrl";
import { useMoney } from "../../state/currency";
import type { Watch } from "../../types";
import { Sparkline } from "../detail/Sparkline";
import { Icon } from "../Icon";
import styles from "./Watches.module.css";

const STATUS_TEXT: Record<string, string> = {
  ok: "price found",
  no_results: "no price for these dates",
  error: "last check failed",
  not_configured: "provider not enabled",
  stay_passed: "stay has passed",
};

interface WatchesPanelProps {
  onClose: () => void;
  checkIntervalHours: number | null;
}

export function WatchesPanel({ onClose, checkIntervalHours }: WatchesPanelProps) {
  const watches = useWatches();
  const list = watches.data ?? [];

  return (
    <section className={styles.panel} aria-label="Watched hotels">
      <header className={styles.header}>
        <button type="button" className="btn btn-ghost btn-sm" onClick={onClose}>
          <Icon name="back" size={16} />
          Back
        </button>
        <h2 className={styles.title}>Watching {list.length > 0 ? `(${list.length})` : ""}</h2>
      </header>
      <p className={styles.intro}>
        {checkIntervalHours
          ? `Each stay is re-checked every ${plural(checkIntervalHours, "hour")} while the app is running.`
          : "Each stay is re-checked in the background while the app is running."}{" "}
        Alerts show up under the bell.
      </p>

      {watches.isPending ? (
        <div className={styles.list}>
          <div className="skeleton" style={{ height: 120 }} />
        </div>
      ) : watches.isError ? (
        <p className={styles.empty}>Couldn't load your watches. Is the backend running?</p>
      ) : list.length === 0 ? (
        <p className={styles.empty}>
          Nothing watched yet. Open any hotel from a search and press "Watch this price".
        </p>
      ) : (
        <ul className={styles.list}>
          {list.map((watch) => (
            <WatchCard key={watch.id} watch={watch} />
          ))}
        </ul>
      )}
    </section>
  );
}

function WatchCard({ watch }: { watch: Watch }) {
  const money = useMoney();
  const { check, remove } = useWatchMutations();
  const image = safeUrl(watch.image_url);
  const listing = safeUrl(watch.hotel_url);
  const history = watch.history.map((point) => Number(point.nightly));
  const last = watch.last_price ? Number(watch.last_price) : null;
  const lowest = watch.lowest_price ? Number(watch.lowest_price) : null;
  const target = watch.target_price ? Number(watch.target_price) : null;
  const checkingThis = check.isPending && check.variables === watch.id;
  const atLowest = last !== null && lowest !== null && last <= lowest;

  return (
    <li className={styles.card}>
      <div className={styles.cardTop}>
        <div className={styles.thumb}>{image ? <img src={image} alt="" referrerPolicy="no-referrer" /> : null}</div>
        <div className={styles.cardInfo}>
          <h3 className={styles.name}>
            {listing ? (
              <a href={listing} target="_blank" rel="noopener noreferrer">
                {watch.hotel_name}
              </a>
            ) : (
              watch.hotel_name
            )}
          </h3>
          <p className={styles.meta}>
            {formatStay(watch.check_in, watch.check_out)}, {plural(watch.adults, "adult")}
            {watch.location_name ? `, ${watch.location_name}` : ""}
          </p>
        </div>
      </div>

      <dl className={styles.stats}>
        <div>
          <dt>Now</dt>
          <dd className={`num ${atLowest ? styles.good : ""}`}>{last !== null ? money.format(last) : "n/a"}</dd>
        </div>
        <div>
          <dt>Lowest seen</dt>
          <dd className="num">{lowest !== null ? money.format(lowest) : "n/a"}</dd>
        </div>
        <div>
          <dt>Target</dt>
          <dd className="num">{target !== null ? money.format(target) : "any drop"}</dd>
        </div>
      </dl>

      {history.length >= 2 ? (
        <Sparkline values={history} height={36} label={`Price over the last ${history.length} checks`} />
      ) : null}

      <div className={styles.footer}>
        <span className={styles.status} data-status={watch.last_status ?? "none"}>
          {watch.last_checked_at
            ? `${STATUS_TEXT[watch.last_status ?? ""] ?? watch.last_status}, ${timeAgo(watch.last_checked_at)}`
            : "not checked yet"}
          {watch.last_site ? ` on ${watch.last_site}` : ""}
        </span>
        <div className={styles.actions}>
          <button type="button" className="btn btn-sm" onClick={() => check.mutate(watch.id)} disabled={checkingThis}>
            <Icon name="refresh" size={14} />
            {checkingThis ? "Checking" : "Check now"}
          </button>
          <button
            type="button"
            className="btn btn-sm btn-ghost btn-icon"
            onClick={() => remove.mutate(watch.id)}
            aria-label={`Stop watching ${watch.hotel_name}`}
            title="Stop watching"
          >
            <Icon name="trash" size={15} />
          </button>
        </div>
      </div>
      {check.isError && check.variables === watch.id ? (
        <p className={styles.error} role="alert">
          {check.error instanceof ApiError ? check.error.message : "Check failed."}
        </p>
      ) : null}
    </li>
  );
}
