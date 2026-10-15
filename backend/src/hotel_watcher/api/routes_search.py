"""Area search and per-hotel details (rates, heatmap, price history)."""

from __future__ import annotations

import sqlite3
from datetime import date
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Path, Query
from pydantic import BaseModel, ConfigDict

from hotel_watcher.api.deps import (
    get_db,
    get_providers,
    get_rates_service,
    get_search_cache,
    stay_query,
)
from hotel_watcher.db import repository
from hotel_watcher.models.hotel import Heatmap, Offer, ProviderStatus
from hotel_watcher.models.stay import HOTEL_KEY_PATTERN, SearchQuery, StayQuery
from hotel_watcher.models.watch import PricePoint
from hotel_watcher.providers.base import HotelProvider
from hotel_watcher.search.cache import TtlCache
from hotel_watcher.search.orchestrator import SearchResponse, run_search
from hotel_watcher.search.rates import RatesService

router = APIRouter(prefix="/api")


class RatesResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    hotel_key: str
    check_in: date
    check_out: date
    adults: int
    nights: int
    provider: str
    status: ProviderStatus
    offers: tuple[Offer, ...]
    cheapest: Offer | None
    total: Decimal | None
    diagnostic: str | None
    from_cache: bool


@router.post("/search")
async def search(
    query: SearchQuery,
    refresh: bool = Query(default=False),
    providers: list[HotelProvider] = Depends(get_providers),
    cache: TtlCache[SearchResponse] = Depends(get_search_cache),
) -> SearchResponse:
    if not refresh:
        cached = await cache.get(query.cache_key())
        if cached is not None:
            return cached.model_copy(update={"from_cache": True})
    response = await run_search(providers, query, repository.utc_now())
    if any(status in ("ok", "no_results") for status in response.provider_statuses.values()):
        await cache.put(query.cache_key(), response)
    return response


@router.get("/hotels/{hotel_key}/rates")
async def hotel_rates(
    stay: StayQuery = Depends(stay_query),
    refresh: bool = Query(default=False),
    rates: RatesService = Depends(get_rates_service),
    conn: sqlite3.Connection = Depends(get_db),
) -> RatesResponse:
    outcome, from_cache = await rates.rates(stay, use_cache=not refresh)
    cheapest = outcome.cheapest
    if cheapest is not None and not from_cache:
        # Every fresh quote feeds the price history, watched or not.
        repository.record_observation(conn, stay, cheapest)
    return RatesResponse(
        hotel_key=stay.hotel_key,
        check_in=stay.check_in,
        check_out=stay.check_out,
        adults=stay.adults,
        nights=stay.nights,
        provider=outcome.provider,
        status=outcome.status,
        offers=outcome.offers,
        cheapest=cheapest,
        total=cheapest.nightly * stay.nights if cheapest else None,
        diagnostic=outcome.diagnostic,
        from_cache=from_cache,
    )


@router.get("/hotels/{hotel_key}/heatmap")
async def hotel_heatmap(
    hotel_key: str = Path(pattern=HOTEL_KEY_PATTERN),
    check_out: date = Query(),
    rates: RatesService = Depends(get_rates_service),
) -> Heatmap:
    heatmap = await rates.heatmap(hotel_key, check_out)
    if heatmap is None:
        raise HTTPException(status_code=404, detail="no price calendar for this hotel")
    return heatmap


@router.get("/hotels/{hotel_key}/history")
def hotel_history(
    stay: StayQuery = Depends(stay_query),
    conn: sqlite3.Connection = Depends(get_db),
) -> list[PricePoint]:
    return repository.get_history(conn, stay)
