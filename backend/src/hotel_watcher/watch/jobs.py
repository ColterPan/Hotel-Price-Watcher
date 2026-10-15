"""Background check of every active watch, plus the single-watch check behind "Check now"."""

from __future__ import annotations

import sqlite3
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from hotel_watcher.db import repository
from hotel_watcher.db.database import connect
from hotel_watcher.logging_config import get_logger
from hotel_watcher.models.watch import AlertKind, Watch
from hotel_watcher.search.rates import RatesService
from hotel_watcher.watch import threshold

logger = get_logger(__name__)


class CheckResult(BaseModel):
    model_config = ConfigDict(frozen=True)

    watch_id: int
    status: str
    price: Decimal | None = None
    site: str | None = None
    alert_kind: AlertKind | None = None
    alert_id: int | None = None


async def check_watch(
    conn: sqlite3.Connection, watch: Watch, rates: RatesService, now: datetime | None = None
) -> CheckResult:
    """Fetch a fresh price for one watch, store it, and raise an alert if it qualifies."""
    now = now or repository.utc_now()
    if watch.check_in < now.date():
        repository.update_watch_check_result(conn, watch.id, "stay_passed", None, None, now)
        return CheckResult(watch_id=watch.id, status="stay_passed")

    stay = watch.to_stay()
    historical_min = repository.get_historical_min(conn, stay)
    # Read before this check records its own price. A failed earlier check
    # recorded nothing, so the next successful one still counts as the first.
    first_check = not repository.watch_has_prices(conn, watch.id)
    outcome, _ = await rates.rates(stay, use_cache=False)
    cheapest = outcome.cheapest
    if outcome.status != "ok" or cheapest is None:
        repository.update_watch_check_result(conn, watch.id, outcome.status, None, None, now)
        return CheckResult(watch_id=watch.id, status=outcome.status)

    repository.record_observation(conn, stay, cheapest, watch_id=watch.id, now=now)
    repository.update_watch_check_result(conn, watch.id, "ok", cheapest.nightly, cheapest.site, now)

    kind = threshold.evaluate(cheapest.nightly, watch.target_price, historical_min, first_check=first_check)
    if kind is None:
        return CheckResult(watch_id=watch.id, status="ok", price=cheapest.nightly, site=cheapest.site)

    message = threshold.describe(
        watch.hotel_name, kind, cheapest.nightly, historical_min, cheapest.currency, cheapest.site
    )
    alert_id = repository.create_alert(
        conn, watch.id, kind, cheapest.nightly, historical_min, cheapest.currency, cheapest.site, message, now
    )
    logger.info("watch %s: %s", watch.id, message)
    return CheckResult(
        watch_id=watch.id,
        status="ok",
        price=cheapest.nightly,
        site=cheapest.site,
        alert_kind=kind,
        alert_id=alert_id,
    )


async def run_watch_check_job(database_path: str, rates: RatesService) -> list[CheckResult]:
    conn = connect(database_path)
    results: list[CheckResult] = []
    try:
        watches = repository.list_active_watches(conn)
        logger.info("watch check: %s active watch(es)", len(watches))
        for watch in watches:
            try:
                results.append(await check_watch(conn, watch, rates))
            except Exception:  # noqa: BLE001 - one broken watch must not stop the others
                logger.exception("watch %s: check failed", watch.id)
                try:
                    repository.update_watch_check_result(conn, watch.id, "error", None, None)
                except sqlite3.Error:
                    logger.exception("watch %s: could not record the failure", watch.id)
                results.append(CheckResult(watch_id=watch.id, status="error"))
    finally:
        conn.close()
    return results
