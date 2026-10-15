"""Every SQL statement the app runs. Money is stored as Decimal text, never float."""

from __future__ import annotations

import sqlite3
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from hotel_watcher.models.hotel import Offer
from hotel_watcher.models.stay import StayQuery
from hotel_watcher.models.watch import Alert, AlertKind, PricePoint, Watch, WatchCreate

#: An identical price for the same stay within this window is not stored
#: again, so refreshing the UI does not flood the history with duplicates.
OBSERVATION_DEDUP_WINDOW = timedelta(minutes=30)


def utc_now() -> datetime:
    return datetime.now(UTC)


def _dec(value: str | None) -> Decimal | None:
    return Decimal(value) if value is not None else None


def _dt(value: str | None) -> datetime | None:
    return datetime.fromisoformat(value) if value is not None else None


# --- price observations -------------------------------------------------------


def record_observation(
    conn: sqlite3.Connection,
    stay: StayQuery,
    cheapest: Offer,
    watch_id: int | None = None,
    now: datetime | None = None,
) -> int | None:
    """Store the cheapest price seen for a stay. Returns the row id, or None if deduplicated."""
    now = now or utc_now()
    if watch_id is None:
        recent = conn.execute(
            """
            SELECT nightly FROM price_observations
            WHERE hotel_key = ? AND check_in = ? AND check_out = ? AND adults = ? AND observed_at >= ?
            ORDER BY observed_at DESC LIMIT 1
            """,
            (*_stay_params(stay), (now - OBSERVATION_DEDUP_WINDOW).isoformat()),
        ).fetchone()
        if recent is not None and Decimal(recent["nightly"]) == cheapest.nightly:
            return None
    cursor = conn.execute(
        """
        INSERT INTO price_observations
            (hotel_key, check_in, check_out, adults, nightly, currency, site, watch_id, observed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            *_stay_params(stay),
            str(cheapest.nightly),
            cheapest.currency,
            cheapest.site,
            watch_id,
            now.isoformat(),
        ),
    )
    conn.commit()
    return cursor.lastrowid


def _stay_params(stay: StayQuery) -> tuple:
    return (stay.hotel_key, stay.check_in.isoformat(), stay.check_out.isoformat(), stay.adults)


def get_historical_min(conn: sqlite3.Connection, stay: StayQuery) -> Decimal | None:
    """Lowest nightly price ever recorded for this exact stay (hotel, dates, guests)."""
    row = conn.execute(
        """
        SELECT nightly FROM price_observations
        WHERE hotel_key = ? AND check_in = ? AND check_out = ? AND adults = ?
        ORDER BY CAST(nightly AS REAL) ASC LIMIT 1
        """,
        _stay_params(stay),
    ).fetchone()
    return Decimal(row["nightly"]) if row else None


def get_history(conn: sqlite3.Connection, stay: StayQuery, limit: int = 200) -> list[PricePoint]:
    rows = conn.execute(
        """
        SELECT observed_at, nightly, currency, site FROM (
            SELECT * FROM price_observations
            WHERE hotel_key = ? AND check_in = ? AND check_out = ? AND adults = ?
            ORDER BY observed_at DESC LIMIT ?
        ) ORDER BY observed_at ASC
        """,
        (*_stay_params(stay), limit),
    ).fetchall()
    return [
        PricePoint(
            observed_at=datetime.fromisoformat(row["observed_at"]),
            nightly=Decimal(row["nightly"]),
            currency=row["currency"],
            site=row["site"],
        )
        for row in rows
    ]


# --- watches -------------------------------------------------------------------


def _row_to_watch(row: sqlite3.Row) -> Watch:
    return Watch(
        id=row["id"],
        hotel_key=row["hotel_key"],
        hotel_name=row["hotel_name"],
        location_name=row["location_name"],
        latitude=row["latitude"],
        longitude=row["longitude"],
        image_url=row["image_url"],
        hotel_url=row["hotel_url"],
        check_in=row["check_in"],
        check_out=row["check_out"],
        adults=row["adults"],
        target_price=_dec(row["target_price"]),
        currency=row["currency"],
        active=bool(row["active"]),
        created_at=datetime.fromisoformat(row["created_at"]),
        needs_baseline=bool(row["needs_baseline"]),
        last_checked_at=_dt(row["last_checked_at"]),
        last_status=row["last_status"],
        last_price=_dec(row["last_price"]),
        last_site=row["last_site"],
    )


def create_watch(conn: sqlite3.Connection, data: WatchCreate, now: datetime | None = None) -> Watch:
    """Create a watch, or reactivate and update the existing one for the same stay.

    Either way the watch starts a fresh baseline (`needs_baseline`), so a target
    that is already met is announced again after a re-add or a target change.
    """
    now = now or utc_now()
    target = str(data.target_price) if data.target_price is not None else None
    conn.execute(
        """
        INSERT INTO watches
            (hotel_key, hotel_name, location_name, latitude, longitude, image_url, hotel_url,
             check_in, check_out, adults, target_price, currency, active, created_at, needs_baseline)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, 1)
        ON CONFLICT (hotel_key, check_in, check_out, adults) DO UPDATE SET
            active = 1,
            needs_baseline = 1,
            target_price = excluded.target_price,
            hotel_name = excluded.hotel_name,
            image_url = COALESCE(excluded.image_url, watches.image_url),
            hotel_url = COALESCE(excluded.hotel_url, watches.hotel_url)
        """,
        (
            data.hotel_key,
            data.hotel_name,
            data.location_name,
            data.latitude,
            data.longitude,
            data.image_url,
            data.hotel_url,
            data.check_in.isoformat(),
            data.check_out.isoformat(),
            data.adults,
            target,
            data.currency,
            now.isoformat(),
        ),
    )
    conn.commit()
    row = conn.execute(
        "SELECT * FROM watches WHERE hotel_key = ? AND check_in = ? AND check_out = ? AND adults = ?",
        (data.hotel_key, data.check_in.isoformat(), data.check_out.isoformat(), data.adults),
    ).fetchone()
    return _row_to_watch(row)


def get_watch(conn: sqlite3.Connection, watch_id: int) -> Watch | None:
    row = conn.execute("SELECT * FROM watches WHERE id = ?", (watch_id,)).fetchone()
    return _row_to_watch(row) if row else None


def list_active_watches(conn: sqlite3.Connection) -> list[Watch]:
    rows = conn.execute("SELECT * FROM watches WHERE active = 1 ORDER BY check_in, hotel_name").fetchall()
    return [_row_to_watch(row) for row in rows]


def deactivate_watch(conn: sqlite3.Connection, watch_id: int) -> bool:
    """Soft delete, so price history and alerts keep their watch row."""
    cursor = conn.execute("UPDATE watches SET active = 0 WHERE id = ? AND active = 1", (watch_id,))
    conn.commit()
    return cursor.rowcount > 0


def update_watch_check_result(
    conn: sqlite3.Connection,
    watch_id: int,
    status: str,
    price: Decimal | None,
    site: str | None,
    now: datetime | None = None,
) -> None:
    """Record the latest check. A failed check keeps the last known price."""
    now = now or utc_now()
    conn.execute(
        """
        UPDATE watches SET
            last_checked_at = ?,
            last_status = ?,
            last_price = COALESCE(?, last_price),
            last_site = COALESCE(?, last_site),
            -- A recorded price is the baseline; a failed check keeps waiting for one.
            needs_baseline = CASE WHEN ? IS NULL THEN needs_baseline ELSE 0 END
        WHERE id = ?
        """,
        (
            now.isoformat(),
            status,
            str(price) if price is not None else None,
            site,
            str(price) if price is not None else None,
            watch_id,
        ),
    )
    conn.commit()


# --- alerts --------------------------------------------------------------------


def create_alert(
    conn: sqlite3.Connection,
    watch_id: int,
    kind: AlertKind,
    price: Decimal,
    previous_low: Decimal | None,
    currency: str,
    site: str | None,
    message: str,
    now: datetime | None = None,
) -> int:
    now = now or utc_now()
    cursor = conn.execute(
        """
        INSERT INTO alerts (watch_id, kind, price, previous_low, currency, site, message, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            watch_id,
            kind,
            str(price),
            str(previous_low) if previous_low is not None else None,
            currency,
            site,
            message,
            now.isoformat(),
        ),
    )
    conn.commit()
    return int(cursor.lastrowid)


def list_alerts(conn: sqlite3.Connection, unread_only: bool = False, limit: int = 50) -> list[Alert]:
    where = "WHERE a.read_at IS NULL" if unread_only else ""
    rows = conn.execute(
        f"""
        SELECT a.*, w.hotel_name, w.hotel_key, w.check_in, w.check_out
        FROM alerts a JOIN watches w ON w.id = a.watch_id
        {where}
        ORDER BY a.created_at DESC, a.id DESC
        LIMIT ?
        """,  # noqa: S608 - `where` is one of two fixed strings, never user input
        (limit,),
    ).fetchall()
    return [
        Alert(
            id=row["id"],
            watch_id=row["watch_id"],
            hotel_name=row["hotel_name"],
            hotel_key=row["hotel_key"],
            check_in=row["check_in"],
            check_out=row["check_out"],
            kind=row["kind"],
            price=Decimal(row["price"]),
            previous_low=_dec(row["previous_low"]),
            currency=row["currency"],
            site=row["site"],
            message=row["message"],
            created_at=datetime.fromisoformat(row["created_at"]),
            read_at=_dt(row["read_at"]),
        )
        for row in rows
    ]


def count_unread_alerts(conn: sqlite3.Connection) -> int:
    return int(conn.execute("SELECT COUNT(*) FROM alerts WHERE read_at IS NULL").fetchone()[0])


def mark_alert_read(conn: sqlite3.Connection, alert_id: int, now: datetime | None = None) -> bool:
    now = now or utc_now()
    cursor = conn.execute(
        "UPDATE alerts SET read_at = ? WHERE id = ? AND read_at IS NULL", (now.isoformat(), alert_id)
    )
    conn.commit()
    return cursor.rowcount > 0


def mark_all_alerts_read(conn: sqlite3.Connection, now: datetime | None = None) -> int:
    now = now or utc_now()
    cursor = conn.execute("UPDATE alerts SET read_at = ? WHERE read_at IS NULL", (now.isoformat(),))
    conn.commit()
    return cursor.rowcount


# --- provider usage (SerpApi budget) ---------------------------------------------


def _month(now: datetime) -> str:
    return now.strftime("%Y-%m")


def get_usage(conn: sqlite3.Connection, provider: str, now: datetime | None = None) -> int:
    row = conn.execute(
        "SELECT calls FROM provider_usage WHERE provider = ? AND month = ?",
        (provider, _month(now or utc_now())),
    ).fetchone()
    return int(row["calls"]) if row else 0


def try_consume_usage(
    conn: sqlite3.Connection, provider: str, limit: int, now: datetime | None = None
) -> bool:
    """Atomically count one call if this month's total is still under `limit`."""
    month = _month(now or utc_now())
    conn.execute(
        "INSERT INTO provider_usage (provider, month, calls) VALUES (?, ?, 0) ON CONFLICT DO NOTHING",
        (provider, month),
    )
    cursor = conn.execute(
        "UPDATE provider_usage SET calls = calls + 1 WHERE provider = ? AND month = ? AND calls < ?",
        (provider, month, limit),
    )
    conn.commit()
    return cursor.rowcount > 0
