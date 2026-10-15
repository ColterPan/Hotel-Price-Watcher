"""Pure parsing of SerpApi Google Hotels responses. No network here.

Field names follow SerpApi's documentation for `engine=google_hotels`
(https://serpapi.com/google-hotels-api). The test fixture was written from
that documentation, not captured live, because capturing needs a key. Run
scripts/capture_fixtures.py with SERPAPI_KEY set to replace it with a real
response. The parser is defensive about every optional field for that reason.
"""

from __future__ import annotations

import hashlib
from decimal import Decimal, InvalidOperation
from typing import Any

from hotel_watcher.models.hotel import Hotel, Offer, PriceSummary, SourceRating

PROVIDER_NAME = "serpapi"

#: SerpApi's wording when a query simply has no hotels, as opposed to a real error.
_NO_RESULTS_MARKERS = ("hasn't returned any results", "no results")


class SerpApiResponseError(Exception):
    pass


def is_no_results_error(message: str) -> bool:
    lowered = message.lower()
    return any(marker in lowered for marker in _NO_RESULTS_MARKERS)


def _decimal(value: Any) -> Decimal | None:
    if value is None or isinstance(value, bool):
        return None
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return None
    return number if number > 0 else None


def _hotel_class(prop: dict[str, Any]) -> int | None:
    value = prop.get("extracted_hotel_class")
    if isinstance(value, int) and 1 <= value <= 5:
        return value
    text = prop.get("hotel_class")
    if isinstance(text, str) and text[:1].isdigit():
        digit = int(text[0])
        return digit if 1 <= digit <= 5 else None
    return None


def stable_id(property_token: str) -> str:
    """A short id safe for URLs. Property tokens are long and opaque."""
    return "gh-" + hashlib.sha1(property_token.encode("utf-8")).hexdigest()[:12]


def _offers(prop: dict[str, Any], currency: str) -> tuple[Offer, ...]:
    offers = []
    for price in prop.get("prices") or ():
        if not isinstance(price, dict):
            continue
        nightly = _decimal((price.get("rate_per_night") or {}).get("extracted_lowest"))
        if nightly is None or not price.get("source"):
            continue
        offers.append(
            Offer(
                site=price["source"],
                nightly=nightly,
                currency=currency,
                link=price.get("link"),
                free_cancellation=price.get("free_cancellation"),
            )
        )
    return tuple(sorted(offers, key=lambda offer: offer.nightly))


def parse_property(prop: dict[str, Any], currency: str, nights: int) -> Hotel | None:
    name = prop.get("name")
    token = prop.get("property_token")
    gps = prop.get("gps_coordinates") or {}
    lat, lng = gps.get("latitude"), gps.get("longitude")
    if not name or not token or lat is None or lng is None:
        return None

    ratings: tuple[SourceRating, ...] = ()
    if prop.get("overall_rating") is not None and prop.get("reviews") is not None:
        ratings = (
            SourceRating(
                source="google",
                label="Google",
                rating=float(prop["overall_rating"]),
                scale=5.0,
                review_count=int(prop["reviews"]),
                url=prop.get("link"),
            ),
        )

    offers = _offers(prop, currency)
    nightly = _decimal((prop.get("rate_per_night") or {}).get("extracted_lowest"))
    total = _decimal((prop.get("total_rate") or {}).get("extracted_lowest"))
    price = None
    if nightly is not None:
        price = PriceSummary(
            nightly=nightly,
            total=total if total is not None else nightly * nights,
            currency=currency,
            kind="live",
            cheapest_site=offers[0].site if offers else None,
        )

    images = prop.get("images") or []
    image_url = None
    if images and isinstance(images[0], dict):
        image_url = images[0].get("thumbnail") or images[0].get("original_image")

    return Hotel(
        id=stable_id(token),
        name=name,
        latitude=float(lat),
        longitude=float(lng),
        image_url=image_url,
        url=prop.get("link"),
        accommodation_type=prop.get("type"),
        hotel_class=_hotel_class(prop),
        amenities=tuple(a for a in prop.get("amenities") or () if isinstance(a, str)),
        providers=(PROVIDER_NAME,),
        ratings=ratings,
        offers=offers,
        price=price,
    )


def parse_properties(payload: Any, currency: str, nights: int) -> tuple[Hotel, ...]:
    if not isinstance(payload, dict):
        raise SerpApiResponseError("response is not a JSON object")
    if payload.get("error"):
        raise SerpApiResponseError(str(payload["error"]))
    hotels = []
    for prop in payload.get("properties") or ():
        hotel = parse_property(prop, currency, nights) if isinstance(prop, dict) else None
        if hotel is not None:
            hotels.append(hotel)
    return tuple(hotels)
