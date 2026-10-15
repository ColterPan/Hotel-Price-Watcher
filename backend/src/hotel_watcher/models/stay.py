"""Search and stay inputs, validated at the API boundary."""

from __future__ import annotations

import re
from datetime import date, timedelta
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

MAX_NIGHTS = 30
#: Booking sites rarely list rates further out than this.
MAX_DAYS_AHEAD = 500
MAX_ADULTS = 8

#: A TripAdvisor location id, as Xotelo's /list expects it ("g294265").
LOCATION_KEY_PATTERN = r"^g\d{2,10}$"

#: Hotel keys this app can fetch per-hotel rates for:
#:   * Xotelo / TripAdvisor: "g294265-d302294"
#:   * demo provider:        "demo-g294265-07"
HOTEL_KEY_PATTERN = r"^(g\d{2,10}-d\d{2,12}|demo-g\d{2,10}-\d{2})$"
_HOTEL_KEY_RE = re.compile(HOTEL_KEY_PATTERN)


def is_rateable_hotel_key(key: str) -> bool:
    return bool(_HOTEL_KEY_RE.match(key))


def validate_stay_dates(check_in: date, check_out: date, today: date | None = None) -> None:
    """Raise ValueError when the date pair cannot be a real bookable stay."""
    today = today or date.today()
    if check_in < today:
        raise ValueError("check-in date is in the past")
    if check_in > today + timedelta(days=MAX_DAYS_AHEAD):
        raise ValueError(f"check-in must be within {MAX_DAYS_AHEAD} days from today")
    if check_out <= check_in:
        raise ValueError("check-out must be after check-in")
    if (check_out - check_in).days > MAX_NIGHTS:
        raise ValueError(f"stays longer than {MAX_NIGHTS} nights are not supported")


class StayDates(BaseModel):
    model_config = ConfigDict(frozen=True)

    check_in: date
    check_out: date
    adults: int = Field(default=2, ge=1, le=MAX_ADULTS)

    @model_validator(mode="after")
    def _dates_make_sense(self) -> Self:
        validate_stay_dates(self.check_in, self.check_out)
        return self

    @property
    def nights(self) -> int:
        return (self.check_out - self.check_in).days


class SearchQuery(StayDates):
    """Find hotels in one area for one stay."""

    location_key: str = Field(pattern=LOCATION_KEY_PATTERN)
    location_name: str = Field(min_length=1, max_length=120)
    limit: int = Field(default=30, ge=5, le=60)

    @field_validator("location_name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        stripped = value.strip()
        if not stripped:
            raise ValueError("location name is empty")
        return stripped

    def cache_key(self) -> tuple:
        return (self.location_key, self.check_in, self.check_out, self.adults, self.limit)

    @property
    def label(self) -> str:
        return f"{self.location_name} {self.check_in}..{self.check_out} x{self.adults}"


class StayQuery(StayDates):
    """Rates for one hotel and one stay."""

    hotel_key: str = Field(pattern=HOTEL_KEY_PATTERN)

    def cache_key(self) -> tuple:
        return (self.hotel_key, self.check_in, self.check_out, self.adults)
