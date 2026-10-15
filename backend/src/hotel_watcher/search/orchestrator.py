"""Run every enabled provider for one search, merge the results and score them."""

from __future__ import annotations

import asyncio
from collections.abc import Sequence
from datetime import datetime
from decimal import Decimal

from pydantic import BaseModel, ConfigDict

from hotel_watcher.locations import find_by_key
from hotel_watcher.logging_config import get_logger
from hotel_watcher.models.hotel import Hotel, ProviderOutcome, ProviderStatus
from hotel_watcher.models.stay import SearchQuery
from hotel_watcher.providers.base import HotelProvider
from hotel_watcher.scoring.quality import score_hotels
from hotel_watcher.search.matching import merge_hotels

logger = get_logger(__name__)


class SearchResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    query: SearchQuery
    hotels: tuple[Hotel, ...]
    provider_statuses: dict[str, ProviderStatus]
    provider_diagnostics: dict[str, str]
    center_latitude: float | None
    center_longitude: float | None
    generated_at: datetime
    from_cache: bool = False


async def _safe_search(provider: HotelProvider, query: SearchQuery) -> ProviderOutcome:
    """Backstop for the never-raise rule, so one buggy provider cannot sink a search."""
    try:
        return await provider.search(query)
    except Exception as exc:  # noqa: BLE001 - providers must not take the whole search down
        logger.exception("provider %s raised during search", provider.name)
        return ProviderOutcome(provider=provider.name, status="error", diagnostic=type(exc).__name__)


def _center(query: SearchQuery, hotels: Sequence[Hotel]) -> tuple[float | None, float | None]:
    location = find_by_key(query.location_key)
    if location and location.latitude is not None:
        return location.latitude, location.longitude
    if not hotels:
        return None, None
    lats = sorted(hotel.latitude for hotel in hotels)
    lngs = sorted(hotel.longitude for hotel in hotels)
    return lats[len(lats) // 2], lngs[len(lngs) // 2]


def _sort_key(hotel: Hotel) -> tuple:
    quality = hotel.quality.score if hotel.quality else 0.0
    price = hotel.price.nightly if hotel.price else hotel.typical_min or Decimal("1e9")
    return (-quality, price)


async def run_search(providers: Sequence[HotelProvider], query: SearchQuery, now: datetime) -> SearchResponse:
    outcomes = await asyncio.gather(*(_safe_search(provider, query) for provider in providers))
    merged = merge_hotels([outcome.hotels for outcome in outcomes])
    scored = tuple(sorted(score_hotels(merged), key=_sort_key))
    lat, lng = _center(query, scored)
    return SearchResponse(
        query=query,
        hotels=scored,
        provider_statuses={outcome.provider: outcome.status for outcome in outcomes},
        provider_diagnostics={
            outcome.provider: outcome.diagnostic for outcome in outcomes if outcome.diagnostic
        },
        center_latitude=lat,
        center_longitude=lng,
        generated_at=now,
    )
