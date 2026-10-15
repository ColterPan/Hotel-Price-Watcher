"""Per-hotel rate lookups, shared by the API and the background watcher."""

from __future__ import annotations

from collections.abc import Sequence
from datetime import date

from hotel_watcher.logging_config import get_logger
from hotel_watcher.models.hotel import Heatmap, RatesOutcome
from hotel_watcher.models.stay import StayQuery
from hotel_watcher.providers.base import HotelProvider
from hotel_watcher.search.cache import TtlCache

logger = get_logger(__name__)


class RatesService:
    def __init__(self, providers: Sequence[HotelProvider], cache: TtlCache[RatesOutcome]) -> None:
        self._providers = tuple(providers)
        self._cache = cache

    def _provider_for(self, hotel_key: str) -> HotelProvider | None:
        return next((p for p in self._providers if p.handles_rates_for(hotel_key)), None)

    async def rates(self, stay: StayQuery, use_cache: bool = True) -> tuple[RatesOutcome, bool]:
        """Rates for one stay, and whether they came from the cache."""
        provider = self._provider_for(stay.hotel_key)
        if provider is None:
            outcome = RatesOutcome(
                provider="none", status="not_configured", diagnostic="no enabled provider quotes this hotel"
            )
            return outcome, False

        if use_cache:
            cached = await self._cache.get(stay.cache_key())
            if cached is not None:
                return cached, True

        try:
            outcome = await provider.rates(stay)
        except Exception as exc:  # noqa: BLE001 - same never-raise backstop as searches
            logger.exception("provider %s raised during rates", provider.name)
            outcome = RatesOutcome(provider=provider.name, status="error", diagnostic=type(exc).__name__)

        # Only cache answers worth repeating. An error should be retried.
        if outcome.status in ("ok", "no_results"):
            await self._cache.put(stay.cache_key(), outcome)
        return outcome, False

    async def heatmap(self, hotel_key: str, check_out: date) -> Heatmap | None:
        provider = self._provider_for(hotel_key)
        if provider is None:
            return None
        try:
            return await provider.heatmap(hotel_key, check_out)
        except Exception:  # noqa: BLE001 - a missing heatmap is cosmetic
            logger.exception("provider %s raised during heatmap", provider.name)
            return None
