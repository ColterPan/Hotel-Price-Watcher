"""Watches (a hotel + stay being tracked), price history points and in-app alerts."""

from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

from hotel_watcher.models.stay import HOTEL_KEY_PATTERN, StayDates, StayQuery

AlertKind = Literal["new_low", "target_hit"]


class WatchCreate(StayDates):
    """What the UI sends to start watching a hotel for one stay."""

    hotel_key: str = Field(pattern=HOTEL_KEY_PATTERN)
    hotel_name: str = Field(min_length=1, max_length=200)
    location_name: str | None = Field(default=None, max_length=120)
    latitude: float | None = Field(default=None, ge=-90, le=90)
    longitude: float | None = Field(default=None, ge=-180, le=180)
    image_url: str | None = Field(default=None, max_length=1000)
    hotel_url: str | None = Field(default=None, max_length=1000)
    #: In `currency` (USD, the provider currency). The UI converts before sending.
    target_price: Decimal | None = Field(default=None, gt=0, le=1_000_000)
    currency: Literal["USD"] = "USD"

    @field_validator("image_url", "hotel_url")
    @classmethod
    def _http_only(cls, value: str | None) -> str | None:
        # These are rendered as links/images in the UI, so refuse anything
        # that is not plain http(s), e.g. "javascript:" URLs.
        if value is not None and not value.startswith(("https://", "http://")):
            raise ValueError("must be an http(s) URL")
        return value


class Watch(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    hotel_key: str
    hotel_name: str
    location_name: str | None
    latitude: float | None
    longitude: float | None
    image_url: str | None
    hotel_url: str | None
    check_in: date
    check_out: date
    adults: int
    target_price: Decimal | None
    currency: str
    active: bool
    created_at: datetime
    last_checked_at: datetime | None
    last_status: str | None
    last_price: Decimal | None
    last_site: str | None

    def to_stay(self) -> StayQuery:
        """The rate query for this watch. Skips date validation: an old watch's
        stay may be in the past, and the caller decides what to do with that."""
        return StayQuery.model_construct(
            hotel_key=self.hotel_key, check_in=self.check_in, check_out=self.check_out, adults=self.adults
        )


class PricePoint(BaseModel):
    model_config = ConfigDict(frozen=True)

    observed_at: datetime
    nightly: Decimal
    currency: str
    site: str | None


class Alert(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: int
    watch_id: int
    hotel_name: str
    hotel_key: str
    check_in: date
    check_out: date
    kind: AlertKind
    price: Decimal
    previous_low: Decimal | None
    currency: str
    site: str | None
    message: str
    created_at: datetime
    read_at: datetime | None
