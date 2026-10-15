import { useCallback, useRef, useState } from "react";

import { useAlertMutations, useAlerts } from "../hooks/queries";
import { useClickOutside } from "../hooks/useClickOutside";
import { formatStay, timeAgo } from "../lib/format";
import { useMoney } from "../state/currency";
import type { Alert } from "../types";
import { Icon } from "./Icon";
import styles from "./Shell.module.css";

function AlertText({ alert }: { alert: Alert }) {
  const money = useMoney();
  const price = money.format(Number(alert.price));
  const site = alert.site ? ` on ${alert.site}` : "";
  if (alert.kind === "target_hit") {
    return (
      <>
        <strong>{alert.hotel_name}</strong> is down to <span className="num">{price}</span> a night{site}, under your
        target.
      </>
    );
  }
  return (
    <>
      <strong>{alert.hotel_name}</strong> hit a new low of <span className="num">{price}</span> a night{site}
      {alert.previous_low ? (
        <>
          , was <span className="num">{money.format(Number(alert.previous_low))}</span>
        </>
      ) : null}
      .
    </>
  );
}

export function AlertBell({ onOpenWatches }: { onOpenWatches: () => void }) {
  const [open, setOpen] = useState(false);
  const wrapRef = useRef<HTMLDivElement>(null);
  const alerts = useAlerts();
  const { markRead, markAll } = useAlertMutations();
  const close = useCallback(() => setOpen(false), []);
  useClickOutside(wrapRef, close, open);

  const unread = alerts.data?.unread_count ?? 0;
  const list = alerts.data?.alerts ?? [];

  return (
    <div className={styles.bellWrap} ref={wrapRef}>
      <button
        type="button"
        className={`btn btn-icon ${styles.topButton}`}
        onClick={() => setOpen((o) => !o)}
        aria-expanded={open}
        aria-label={unread > 0 ? `Alerts, ${unread} unread` : "Alerts"}
      >
        <Icon name="bell" />
        {unread > 0 ? <span className={styles.badge}>{unread > 9 ? "9+" : unread}</span> : null}
      </button>
      {open ? (
        <div className={styles.alerts} role="dialog" aria-label="Price alerts">
          <div className={styles.alertsHead}>
            <strong>Price alerts</strong>
            {unread > 0 ? (
              <button type="button" className="btn btn-ghost btn-sm" onClick={() => markAll.mutate()}>
                Mark all read
              </button>
            ) : null}
          </div>
          {list.length === 0 ? (
            <p className={styles.alertsEmpty}>
              No alerts yet. Watch a hotel and you'll hear about drops here.
            </p>
          ) : (
            <ul className={styles.alertList}>
              {list.map((alert) => (
                <li key={alert.id} className={alert.read_at ? styles.alertRead : styles.alertUnread}>
                  <button
                    type="button"
                    className={styles.alertButton}
                    onClick={() => {
                      if (!alert.read_at) markRead.mutate(alert.id);
                      setOpen(false);
                      onOpenWatches();
                    }}
                  >
                    <span className={styles.alertText}>
                      <AlertText alert={alert} />
                    </span>
                    <span className={styles.alertMeta}>
                      {formatStay(alert.check_in, alert.check_out)}, {timeAgo(alert.created_at)}
                    </span>
                  </button>
                </li>
              ))}
            </ul>
          )}
        </div>
      ) : null}
    </div>
  );
}
