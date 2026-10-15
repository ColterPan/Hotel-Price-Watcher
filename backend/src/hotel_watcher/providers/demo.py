"""Made-up hotels for trying the app offline, for tests and for screenshots.

Everything here is fictional: hotel names, review sources and booking sites.
Real brand names are deliberately avoided so sample prices can never be
mistaken for a real quote. Prices drift every couple of minutes so the
watcher and its alerts can be seen working without waiting hours.
"""

from __future__ import annotations

import hashlib
import math
import time
from collections.abc import Callable
from datetime import date, timedelta
from decimal import Decimal

from hotel_watcher.locations import find_by_key
from hotel_watcher.models.hotel import Heatmap, Hotel, Offer, ProviderOutcome, RatesOutcome, SourceRating
from hotel_watcher.models.stay import SearchQuery, StayQuery
from hotel_watcher.providers.base import HotelProvider

CURRENCY = "USD"
DEFAULT_CENTER = (1.2912, 103.8476)  # Singapore, used when the location is unknown

_NAME_PARTS = (
    ("Harbourlight", "Hotel"),
    ("Juniper Lane", "Inn"),
    ("The Lantern", "House"),
    ("Saltwater", "Suites"),
    ("Orchid Row", "Hotel"),
    ("Copperleaf", "Residences"),
    ("Riverbend", "Lodge"),
    ("Kampong Breeze", "Guesthouse"),
    ("Northlight", "Hotel"),
    ("Tidewater", "Boutique Hotel"),
    ("Old Mill", "Hostel"),
    ("Marigold", "Suites"),
    ("Cloudline", "Tower Hotel"),
    ("Palm Court", "Inn"),
    ("Granite Bay", "Hotel"),
    ("Little Fig", "Capsule Hotel"),
    ("Seastone", "Resort"),
    ("Willow & Brick", "Hotel"),
    ("Lighthouse Quay", "Hotel"),
    ("Hillside", "Garden Inn"),
)
_SITES = ("Demo Travel", "Sample Stays", "Example Booking", "Placeholder Trips")
_AMENITIES = (
    "Free Wi-Fi",
    "Pool",
    "Breakfast",
    "Gym",
    "Air conditioning",
    "Airport shuttle",
    "Spa",
    "Kitchen",
)

#: Prices move every this many seconds.
DRIFT_PERIOD_SECONDS = 120


def _unit(seed: str) -> float:
    """A stable pseudo-random number in [0, 1) derived from `seed`."""
    digest = hashlib.sha256(seed.encode("utf-8")).digest()
    return int.from_bytes(digest[:8], "big") / 2**64


def _hotel_index(hotel_key: str) -> int | None:
    try:
        return int(hotel_key.rsplit("-", 1)[1])
    except (IndexError, ValueError):
        return None


class DemoProvider(HotelProvider):
    name = "demo"
    label = "Sample data (not real prices)"

    def __init__(self, clock: Callable[[], float] = time.time) -> None:
        self._clock = clock

    def _base_price(self, location_key: str, index: int) -> Decimal:
        return Decimal(round(60 + _unit(f"{location_key}:{index}:price") * 340))

    def _hotel(self, location_key: str, index: int, center: tuple[float, float]) -> Hotel:
        seed = f"{location_key}:{index}"
        first, last = _NAME_PARTS[index % len(_NAME_PARTS)]
        angle = _unit(seed + ":angle") * 2 * math.pi
        radius = 0.004 + _unit(seed + ":radius") * 0.045
        base = self._base_price(location_key, index)
        quality = _unit(seed + ":quality")
        amenity_count = 2 + int(_unit(seed + ":amenities") * 5)
        key = f"demo-{location_key}-{index:02d}"
        return Hotel(
            id=key,
            name=f"{first} {last}",
            latitude=round(center[0] + radius * math.sin(angle), 6),
            longitude=round(center[1] + radius * math.cos(angle), 6),
            accommodation_type="Hotel",
            hotel_class=1 + int(_unit(seed + ":stars") * 5),
            amenities=_AMENITIES[:amenity_count],
            providers=(self.name,),
            rates_key=key,
            ratings=(
                SourceRating(
                    source="demo_a",
                    label="Sample reviews A",
                    rating=round(3.2 + quality * 1.8, 1),
                    scale=5.0,
                    review_count=int(5 + _unit(seed + ":count_a") * 4000),
                ),
                SourceRating(
                    source="demo_b",
                    label="Sample reviews B",
                    rating=round(6.0 + quality * 3.8 + (_unit(seed + ":jitter") - 0.5), 1),
                    scale=10.0,
                    review_count=int(_unit(seed + ":count_b") * 2500),
                ),
            ),
            typical_min=(base * Decimal("0.8")).quantize(Decimal("1")),
            typical_max=(base * Decimal("1.9")).quantize(Decimal("1")),
            typical_currency=CURRENCY,
        )

    async def search(self, query: SearchQuery) -> ProviderOutcome:
        location = find_by_key(query.location_key)
        center = (location.latitude, location.longitude) if location else DEFAULT_CENTER
        count = min(query.limit, len(_NAME_PARTS))
        hotels = tuple(self._hotel(query.location_key, index, center) for index in range(count))
        return ProviderOutcome(provider=self.name, status="ok", hotels=hotels)

    def handles_rates_for(self, hotel_key: str) -> bool:
        return hotel_key.startswith("demo-")

    async def rates(self, stay: StayQuery) -> RatesOutcome:
        index = _hotel_index(stay.hotel_key)
        location_key = stay.hotel_key.split("-")[1] if stay.hotel_key.count("-") >= 2 else ""
        if index is None or not location_key:
            return RatesOutcome(provider=self.name, status="no_results")

        base = self._base_price(location_key, index)
        tick = int(self._clock() // DRIFT_PERIOD_SECONDS)
        stay_seed = f"{stay.hotel_key}:{stay.check_in}:{stay.check_out}:{stay.adults}"
        offers = []
        for site_index, site in enumerate(_SITES):
            if _unit(f"{stay_seed}:{site}:listed") < 0.25:
                continue
            drift = 0.85 + 0.3 * _unit(f"{stay_seed}:{site}:{tick}")
            nightly = (base * Decimal(str(round(drift, 3)))).quantize(Decimal("1"))
            offers.append(Offer(site=site, site_code=f"demo{site_index}", nightly=nightly, currency=CURRENCY))
        offers.sort(key=lambda offer: offer.nightly)
        if not offers:
            return RatesOutcome(provider=self.name, status="no_results")
        return RatesOutcome(provider=self.name, status="ok", offers=tuple(offers))

    async def heatmap(self, hotel_key: str, check_out: date) -> Heatmap | None:
        days = [check_out - timedelta(days=offset) for offset in range(1, 36)]
        buckets: dict[str, list[date]] = {"cheap": [], "average": [], "high": []}
        for day in days:
            roll = _unit(f"{hotel_key}:{day}")
            buckets["cheap" if roll < 0.25 else "high" if roll > 0.8 else "average"].append(day)
        return Heatmap(
            cheap=tuple(sorted(buckets["cheap"])),
            average=tuple(sorted(buckets["average"])),
            high=tuple(sorted(buckets["high"])),
        )
