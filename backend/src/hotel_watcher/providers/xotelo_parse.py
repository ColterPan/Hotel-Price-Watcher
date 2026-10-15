"""Pure parsing of Xotelo API responses. No network here.

Response shapes were captured from the live API on 2026-10-15 and are kept in
tests/fixtures/xotelo_*.json. Re-capture with scripts/capture_fixtures.py if
the API changes.

Notes from that capture:
* /rates `rate` is the price per room per night. `tax` was always null.
* /rates only accepts USD, GBP, EUR, CAD, CHF, AUD, JPY, CNY, INR, THB, BRL,
  HKD, RUB, BZD. SGD is not one of them, which is why everything is fetched
  in USD and converted for display.
* /search is no longer free (RapidAPI only), so locations come from the
  bundled city list instead. /list, /rates and /heatmap are free.
* An unknown hotel key returns `rates: []`, not an error.
"""

from __future__ import annotations

from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from hotel_watcher.logging_config import get_logger
from hotel_watcher.models.hotel import Heatmap, Hotel, Offer, SourceRating

logger = get_logger(__name__)

PROVIDER_NAME = "xotelo"
PRICE_CURRENCY = "USD"


class XoteloResponseError(Exception):
    """The API answered, but with an error or a shape we do not understand."""


def unwrap(payload: Any) -> dict[str, Any]:
    """Return `result`, or raise with the API's own error message."""
    if not isinstance(payload, dict):
        raise XoteloResponseError("response is not a JSON object")
    error = payload.get("error")
    if error:
        message = error.get("message") if isinstance(error, dict) else str(error)
        raise XoteloResponseError(message or "unknown error")
    result = payload.get("result")
    if not isinstance(result, dict):
        raise XoteloResponseError("response has no result object")
    return result


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number > 0 else None


def parse_list_item(item: dict[str, Any]) -> Hotel | None:
    """One hotel from /list, or None if it lacks a name, key or coordinates."""
    key = item.get("key")
    name = item.get("name")
    geo = item.get("geo") or {}
    lat, lng = geo.get("latitude"), geo.get("longitude")
    if not key or not name or lat is None or lng is None:
        return None

    ratings: tuple[SourceRating, ...] = ()
    summary = item.get("review_summary") or {}
    if summary.get("rating") is not None and summary.get("count") is not None:
        ratings = (
            SourceRating(
                source="tripadvisor",
                label="TripAdvisor",
                rating=float(summary["rating"]),
                scale=5.0,
                review_count=int(summary["count"]),
                url=item.get("url"),
            ),
        )

    price_ranges = item.get("price_ranges") or {}
    return Hotel(
        id=key,
        name=name,
        latitude=float(lat),
        longitude=float(lng),
        image_url=item.get("image"),
        url=item.get("url"),
        accommodation_type=item.get("accommodation_type"),
        labels=tuple(item.get("merchandising_labels") or ()),
        providers=(PROVIDER_NAME,),
        rates_key=key,
        ratings=ratings,
        typical_min=_decimal(price_ranges.get("minimum")),
        typical_max=_decimal(price_ranges.get("maximum")),
        typical_currency=PRICE_CURRENCY,
    )


def parse_list(payload: Any) -> tuple[Hotel, ...]:
    result = unwrap(payload)
    items = result.get("list")
    if not isinstance(items, list):
        raise XoteloResponseError("list response has no hotel list")
    hotels = []
    for item in items:
        hotel = parse_list_item(item) if isinstance(item, dict) else None
        if hotel is None:
            logger.debug("xotelo: skipping unparseable list item %r", item)
            continue
        hotels.append(hotel)
    return tuple(hotels)


def parse_rates(payload: Any) -> tuple[Offer, ...]:
    result = unwrap(payload)
    currency = result.get("currency") or PRICE_CURRENCY
    offers = []
    for rate in result.get("rates") or ():
        nightly = _decimal(rate.get("rate")) if isinstance(rate, dict) else None
        if nightly is None:
            continue
        offers.append(
            Offer(
                site=rate.get("name") or rate.get("code") or "Unknown site",
                site_code=rate.get("code"),
                nightly=nightly,
                currency=currency,
            )
        )
    return tuple(sorted(offers, key=lambda offer: offer.nightly))


def _dates(values: Any) -> tuple[date, ...]:
    parsed = []
    for value in values or ():
        try:
            parsed.append(date.fromisoformat(value))
        except (TypeError, ValueError):
            continue
    return tuple(sorted(parsed))


def parse_heatmap(payload: Any) -> Heatmap:
    heatmap = unwrap(payload).get("heatmap") or {}
    return Heatmap(
        cheap=_dates(heatmap.get("cheap_price_days")),
        average=_dates(heatmap.get("average_price_days")),
        high=_dates(heatmap.get("high_price_days")),
    )
