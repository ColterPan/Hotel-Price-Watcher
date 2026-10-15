import { useState, type FormEvent } from "react";

import { ApiError } from "../../api/client";
import { useWatchMutations } from "../../hooks/queries";
import { timeAgo } from "../../lib/format";
import { safeUrl } from "../../lib/safeUrl";
import { useMoney } from "../../state/currency";
import type { Hotel, SearchParams, Watch } from "../../types";
import { Icon } from "../Icon";
import styles from "./Detail.module.css";

interface WatchBoxProps {
  hotel: Hotel;
  params: SearchParams;
  existing: Watch | null;
  onOpenWatches: () => void;
}

export function WatchBox({ hotel, params, existing, onOpenWatches }: WatchBoxProps) {
  const money = useMoney();
  const { create } = useWatchMutations();
  const [target, setTarget] = useState("");

  if (!hotel.rates_key) {
    return (
      <p className={styles.muted}>
        This listing only comes from Google Hotels, which can't be re-checked for free. Watching works for hotels with
        TripAdvisor prices.
      </p>
    );
  }

  if (existing) {
    return (
      <div className={styles.watching}>
        <Icon name="eye" />
        <div>
          <strong>You're watching this stay.</strong>
          <p className={styles.muted}>
            {existing.lowest_price ? `Lowest seen ${money.format(Number(existing.lowest_price))}. ` : ""}
            {existing.last_checked_at ? `Checked ${timeAgo(existing.last_checked_at)}.` : ""}
          </p>
        </div>
        <button type="button" className="btn btn-sm" onClick={onOpenWatches}>
          Open
        </button>
      </div>
    );
  }

  const submit = (event: FormEvent) => {
    event.preventDefault();
    const amount = target.trim() === "" ? null : Number(target);
    if (amount !== null && (!Number.isFinite(amount) || amount <= 0)) return;
    create.mutate({
      hotel_key: hotel.rates_key!,
      hotel_name: hotel.name,
      location_name: params.location_name,
      latitude: hotel.latitude,
      longitude: hotel.longitude,
      image_url: safeUrl(hotel.image_url),
      hotel_url: safeUrl(hotel.url),
      check_in: params.check_in,
      check_out: params.check_out,
      adults: params.adults,
      target_price: amount === null ? null : money.toUsd(amount).toFixed(2),
    });
  };

  return (
    <form className={styles.watchForm} onSubmit={submit}>
      <label className={styles.watchLabel}>
        <span>Alert me below ({money.currency}, optional)</span>
        <input
          className="field num"
          type="number"
          inputMode="decimal"
          min={1}
          placeholder="Any new low"
          value={target}
          onChange={(event) => setTarget(event.target.value)}
        />
      </label>
      <button type="submit" className="btn btn-primary" disabled={create.isPending}>
        <Icon name="eye" size={16} />
        {create.isPending ? "Saving" : "Watch this price"}
      </button>
      {create.isError ? (
        <p className={styles.error} role="alert">
          {create.error instanceof ApiError ? create.error.message : "Couldn't save the watch."}
        </p>
      ) : null}
      <p className={styles.footnote}>
        Checked in the background every few hours. You'll get an alert here when it hits a new low
        {target ? " under your target" : ""}.
      </p>
    </form>
  );
}
