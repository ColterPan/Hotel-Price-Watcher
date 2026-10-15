"""Xotelo: free hotel prices from several booking sites, plus TripAdvisor review summaries.

API docs: https://xotelo.com. There is no published rate limit, so this
provider caps concurrent requests (XOTELO_MAX_CONCURRENCY) and the app caches
results. Please keep it that way, the API is free and shared.
"""

from __future__ import annotations

import asyncio
from datetime import date
from typing import Any

import httpx

from hotel_watcher.logging_config import get_logger
from hotel_watcher.models.hotel import Heatmap, ProviderOutcome, RatesOutcome
from hotel_watcher.models.stay import SearchQuery, StayQuery
from hotel_watcher.providers import xotelo_parse
from hotel_watcher.providers.base import HotelProvider
from hotel_watcher.providers.xotelo_parse import PRICE_CURRENCY, XoteloResponseError

logger = get_logger(__name__)


class XoteloProvider(HotelProvider):
    name = "xotelo"
    label = "Xotelo (TripAdvisor prices and reviews)"

    def __init__(
        self,
        client: httpx.AsyncClient,
        base_url: str = "https://data.xotelo.com/api",
        max_concurrency: int = 4,
        list_sort: str = "best_value",
    ) -> None:
        self._client = client
        self._base_url = base_url.rstrip("/")
        self._semaphore = asyncio.Semaphore(max_concurrency)
        self._list_sort = list_sort

    async def _get(self, path: str, params: dict[str, Any]) -> Any:
        async with self._semaphore:
            response = await self._client.get(f"{self._base_url}/{path}", params=params)
        # Xotelo reports bad input as 200 or 4xx with a JSON error body; both
        # are surfaced through xotelo_parse.unwrap, so only parse JSON here.
        if response.status_code >= 500:
            raise XoteloResponseError(f"server error {response.status_code}")
        try:
            return response.json()
        except ValueError as exc:
            raise XoteloResponseError(f"non-JSON response (HTTP {response.status_code})") from exc

    async def search(self, query: SearchQuery) -> ProviderOutcome:
        params = {"location_key": query.location_key, "limit": query.limit, "sort": self._list_sort}
        try:
            hotels = xotelo_parse.parse_list(await self._get("list", params))
        except (httpx.HTTPError, XoteloResponseError) as exc:
            logger.warning("xotelo list failed for %s: %s", query.label, exc)
            return ProviderOutcome(
                provider=self.name, status="error", diagnostic=str(exc) or type(exc).__name__
            )
        if not hotels:
            return ProviderOutcome(provider=self.name, status="no_results")
        return ProviderOutcome(provider=self.name, status="ok", hotels=hotels)

    def handles_rates_for(self, hotel_key: str) -> bool:
        return not hotel_key.startswith("demo-")

    async def rates(self, stay: StayQuery) -> RatesOutcome:
        params = {
            "hotel_key": stay.hotel_key,
            "chk_in": stay.check_in.isoformat(),
            "chk_out": stay.check_out.isoformat(),
            "adults": stay.adults,
            "rooms": 1,
            "currency": PRICE_CURRENCY,
        }
        try:
            offers = xotelo_parse.parse_rates(await self._get("rates", params))
        except (httpx.HTTPError, XoteloResponseError) as exc:
            logger.warning("xotelo rates failed for %s: %s", stay.hotel_key, exc)
            return RatesOutcome(provider=self.name, status="error", diagnostic=str(exc) or type(exc).__name__)
        if not offers:
            return RatesOutcome(provider=self.name, status="no_results")
        return RatesOutcome(provider=self.name, status="ok", offers=offers)

    async def heatmap(self, hotel_key: str, check_out: date) -> Heatmap | None:
        try:
            payload = await self._get("heatmap", {"hotel_key": hotel_key, "chk_out": check_out.isoformat()})
            return xotelo_parse.parse_heatmap(payload)
        except (httpx.HTTPError, XoteloResponseError) as exc:
            logger.warning("xotelo heatmap failed for %s: %s", hotel_key, exc)
            return None
