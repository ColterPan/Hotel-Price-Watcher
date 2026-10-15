"""When a checked price deserves an alert. Pure logic, no I/O.

Rules:
* A watch's first check: alert only if a target is set and the price is
  already at or below it. Otherwise that price is the baseline, not a "drop".
  Prices seen while browsing before the watch existed don't count here,
  otherwise a target that is already met would never be announced.
* Later checks: alert only on a new all-time low for that exact stay. With a
  target set, the new low must also be at or below the target.
* A price that is not a new low never alerts, even under the target, so the
  same deal is not announced again on every check.
"""

from __future__ import annotations

from decimal import Decimal

from hotel_watcher.models.watch import AlertKind


def evaluate(
    price: Decimal,
    target: Decimal | None,
    historical_min: Decimal | None,
    first_check: bool = False,
) -> AlertKind | None:
    if first_check or historical_min is None:
        return "target_hit" if target is not None and price <= target else None
    if price >= historical_min:
        return None
    if target is None:
        return "new_low"
    return "target_hit" if price <= target else None


def describe(
    hotel_name: str,
    kind: AlertKind,
    price: Decimal,
    previous_low: Decimal | None,
    currency: str,
    site: str | None,
) -> str:
    where = f" on {site}" if site else ""
    amount = f"{currency} {price:,.0f}"
    if kind == "target_hit":
        return f"{hotel_name} is down to {amount} a night{where}, at or under your target."
    was = f" (lowest before: {currency} {previous_low:,.0f})" if previous_low is not None else ""
    return f"{hotel_name} hit a new low of {amount} a night{where}{was}."
