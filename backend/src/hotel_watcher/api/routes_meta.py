"""Health, locations and exchange rates: the small endpoints the UI needs on load."""

from __future__ import annotations

import sqlite3

from fastapi import APIRouter, Depends, HTTPException, Query

from hotel_watcher import __version__
from hotel_watcher.api.deps import get_db, get_exchange_rate_cache, get_providers, get_settings_dep
from hotel_watcher.config import Settings
from hotel_watcher.currency import SUPPORTED_CURRENCIES, ExchangeRateCache, ExchangeRateError
from hotel_watcher.db import repository
from hotel_watcher.locations import Location, search_locations
from hotel_watcher.logging_config import get_logger
from hotel_watcher.providers.base import HotelProvider

logger = get_logger(__name__)

router = APIRouter(prefix="/api")


@router.get("/health")
def health(
    settings: Settings = Depends(get_settings_dep),
    providers: list[HotelProvider] = Depends(get_providers),
    conn: sqlite3.Connection = Depends(get_db),
) -> dict:
    serpapi = None
    if "serpapi" in settings.enabled_provider_list:
        serpapi = {
            "configured": bool(settings.serpapi_key),
            "used_this_month": repository.get_usage(conn, "serpapi"),
            "monthly_budget": settings.serpapi_monthly_budget,
        }
    return {
        "status": "ok",
        "version": __version__,
        "providers": [{"name": p.name, "label": p.label} for p in providers],
        "serpapi": serpapi,
        "default_display_currency": settings.default_display_currency,
        "check_interval_hours": settings.check_interval_hours,
    }


@router.get("/locations")
def locations(q: str = Query(default="", max_length=300)) -> list[Location]:
    return list(search_locations(q))


@router.get("/currency/rates")
async def exchange_rates(
    base: str = Query(default="USD", min_length=3, max_length=3),
    cache: ExchangeRateCache = Depends(get_exchange_rate_cache),
) -> dict:
    base = base.strip().upper()
    if base not in SUPPORTED_CURRENCIES:
        raise HTTPException(status_code=422, detail=f"unsupported currency code: {base}")
    try:
        snapshot = await cache.get_rates(base)
    except ExchangeRateError as exc:
        logger.warning("exchange rates unavailable for %s: %s", base, exc)
        raise HTTPException(
            status_code=503,
            detail="Exchange rates are unavailable right now. Prices are shown in USD.",
        ) from exc
    return {
        "base": snapshot.base,
        "as_of": snapshot.as_of,
        "stale": snapshot.stale,
        "rates": {code: str(rate) for code, rate in snapshot.rates.items()},
        "supported_currencies": SUPPORTED_CURRENCIES,
    }
