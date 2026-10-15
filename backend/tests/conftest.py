"""Shared test helpers. Every test here runs offline."""

from __future__ import annotations

import json
import sqlite3
from collections.abc import Iterator
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path
from typing import Any

import pytest

from hotel_watcher.db.database import connect
from hotel_watcher.models.hotel import Hotel, Offer, SourceRating
from hotel_watcher.models.stay import SearchQuery, StayQuery

FIXTURES = Path(__file__).parent / "fixtures"


def load_fixture(name: str) -> Any:
    return json.loads((FIXTURES / name).read_text(encoding="utf-8"))


def future_date(days_ahead: int = 40) -> date:
    """A date that stays valid as real time passes, unlike a hardcoded one."""
    return date.today() + timedelta(days=days_ahead)


def make_search(location_key: str = "g294265", nights: int = 2, **overrides: Any) -> SearchQuery:
    check_in = overrides.pop("check_in", future_date())
    return SearchQuery(
        location_key=location_key,
        location_name=overrides.pop("location_name", "Singapore"),
        check_in=check_in,
        check_out=overrides.pop("check_out", check_in + timedelta(days=nights)),
        **overrides,
    )


def make_stay(hotel_key: str = "g294265-d302294", nights: int = 2, adults: int = 2) -> StayQuery:
    check_in = future_date()
    return StayQuery(
        hotel_key=hotel_key, check_in=check_in, check_out=check_in + timedelta(days=nights), adults=adults
    )


def make_hotel(
    name: str = "Test Hotel",
    lat: float = 1.29,
    lng: float = 103.85,
    ratings: tuple[SourceRating, ...] = (),
    **overrides: Any,
) -> Hotel:
    return Hotel(
        id=overrides.pop("id", f"id-{name}"),
        name=name,
        latitude=lat,
        longitude=lng,
        ratings=ratings,
        providers=overrides.pop("providers", ("xotelo",)),
        **overrides,
    )


def rating(value: float, count: int, scale: float = 5.0, source: str = "tripadvisor") -> SourceRating:
    return SourceRating(source=source, label=source.title(), rating=value, scale=scale, review_count=count)


def offer(nightly: str, site: str = "Booking.com") -> Offer:
    return Offer(site=site, nightly=Decimal(nightly), currency="USD")


@pytest.fixture
def conn() -> Iterator[sqlite3.Connection]:
    connection = connect(":memory:")
    try:
        yield connection
    finally:
        connection.close()
