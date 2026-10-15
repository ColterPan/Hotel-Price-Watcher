"""Shared FastAPI dependencies. Long-lived objects are created once in the app lifespan."""

from __future__ import annotations

import sqlite3
from collections.abc import Generator
from datetime import date

from fastapi import HTTPException, Path, Query, Request
from pydantic import ValidationError

from hotel_watcher.config import Settings
from hotel_watcher.currency import ExchangeRateCache
from hotel_watcher.db.database import connect
from hotel_watcher.models.stay import HOTEL_KEY_PATTERN, StayQuery
from hotel_watcher.providers.base import HotelProvider
from hotel_watcher.search.cache import TtlCache
from hotel_watcher.search.orchestrator import SearchResponse
from hotel_watcher.search.rates import RatesService


def get_settings_dep(request: Request) -> Settings:
    return request.app.state.settings


def get_db(request: Request) -> Generator[sqlite3.Connection, None, None]:
    conn = connect(request.app.state.settings.database_path)
    try:
        yield conn
    finally:
        conn.close()


def get_providers(request: Request) -> list[HotelProvider]:
    return request.app.state.providers


def get_search_cache(request: Request) -> TtlCache[SearchResponse]:
    return request.app.state.search_cache


def get_rates_service(request: Request) -> RatesService:
    return request.app.state.rates_service


def get_exchange_rate_cache(request: Request) -> ExchangeRateCache:
    return request.app.state.exchange_rate_cache


def friendly_validation_message(exc: ValidationError) -> str:
    """The first validation problem, phrased for a person rather than a parser."""
    error = exc.errors()[0]
    message = str(error.get("msg", "invalid input"))
    return message.removeprefix("Value error, ")


def stay_query(
    hotel_key: str = Path(pattern=HOTEL_KEY_PATTERN),
    check_in: date = Query(),
    check_out: date = Query(),
    adults: int = Query(default=2),
) -> StayQuery:
    try:
        return StayQuery(hotel_key=hotel_key, check_in=check_in, check_out=check_out, adults=adults)
    except ValidationError as exc:
        raise HTTPException(status_code=422, detail=friendly_validation_message(exc)) from exc
