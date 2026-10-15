"""Hotel, rating, offer and provider-outcome models shared by every provider."""

from __future__ import annotations

from datetime import date
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, ConfigDict, Field

#: What a provider can report about one call. Kept distinct on purpose so the UI
#: never shows "no hotels here" when the truth is "this provider is broken" or
#: "you did not add a key for it".
ProviderStatus = Literal["ok", "no_results", "not_configured", "quota_exhausted", "error"]


class SourceRating(BaseModel):
    """One review source's verdict on a hotel, on that source's own scale."""

    model_config = ConfigDict(frozen=True)

    source: str  # stable id, e.g. "tripadvisor", "google"
    label: str  # shown to people, e.g. "TripAdvisor"
    rating: float = Field(ge=0)
    scale: float = Field(gt=0)  # 5 for TripAdvisor/Google, 10 for Booking-style scores
    review_count: int = Field(ge=0)
    url: str | None = None


class Offer(BaseModel):
    """One booking site's nightly price for a stay."""

    model_config = ConfigDict(frozen=True)

    site: str
    site_code: str | None = None
    nightly: Decimal = Field(gt=0)
    currency: str
    link: str | None = None
    free_cancellation: bool | None = None


class QualityScore(BaseModel):
    model_config = ConfigDict(frozen=True)

    score: float = Field(ge=0, le=10)
    label: str
    review_count: int
    low_confidence: bool


class PriceSummary(BaseModel):
    """The price shown on a hotel's map pin and card."""

    model_config = ConfigDict(frozen=True)

    nightly: Decimal
    total: Decimal
    currency: str
    #: "live" is a dated quote for this stay. "typical" is the provider's usual
    #: range for the hotel (not tied to these dates) and is shown as "from".
    kind: Literal["live", "typical"]
    cheapest_site: str | None = None


class Hotel(BaseModel):
    model_config = ConfigDict(frozen=True)

    id: str
    name: str
    latitude: float
    longitude: float
    image_url: str | None = None
    url: str | None = None
    accommodation_type: str | None = None
    hotel_class: int | None = Field(default=None, ge=1, le=5)
    amenities: tuple[str, ...] = ()
    labels: tuple[str, ...] = ()
    providers: tuple[str, ...] = ()

    #: Key for per-hotel rate lookups (Xotelo or demo). None when only a
    #: provider without per-hotel rates (SerpApi) knows this hotel.
    rates_key: str | None = None

    ratings: tuple[SourceRating, ...] = ()
    offers: tuple[Offer, ...] = ()
    price: PriceSummary | None = None
    typical_min: Decimal | None = None
    typical_max: Decimal | None = None
    typical_currency: str | None = None
    quality: QualityScore | None = None


class ProviderOutcome(BaseModel):
    """What one provider returned for one search. Providers never raise."""

    model_config = ConfigDict(frozen=True)

    provider: str
    status: ProviderStatus
    hotels: tuple[Hotel, ...] = ()
    diagnostic: str | None = None


class RatesOutcome(BaseModel):
    model_config = ConfigDict(frozen=True)

    provider: str
    status: ProviderStatus
    offers: tuple[Offer, ...] = ()
    diagnostic: str | None = None

    @property
    def cheapest(self) -> Offer | None:
        return min(self.offers, key=lambda offer: offer.nightly, default=None)


class Heatmap(BaseModel):
    """Which nearby check-in days look cheap, average or expensive for a hotel."""

    model_config = ConfigDict(frozen=True)

    cheap: tuple[date, ...] = ()
    average: tuple[date, ...] = ()
    high: tuple[date, ...] = ()
