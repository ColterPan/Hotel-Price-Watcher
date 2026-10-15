"""SerpApi Google Hotels: Google ratings, per-site prices and amenities for an area.

Optional. Needs SERPAPI_KEY. Every call spends one search from the user's
SerpApi plan, so calls go through a monthly budget (SERPAPI_MONTHLY_BUDGET)
and this provider is never used by the background watcher.
"""

from __future__ import annotations

from typing import Protocol

import httpx

from hotel_watcher.logging_config import get_logger
from hotel_watcher.models.hotel import ProviderOutcome
from hotel_watcher.models.stay import SearchQuery
from hotel_watcher.providers import serpapi_parse
from hotel_watcher.providers.base import HotelProvider
from hotel_watcher.providers.serpapi_parse import SerpApiResponseError

logger = get_logger(__name__)

SERPAPI_URL = "https://serpapi.com/search.json"
PRICE_CURRENCY = "USD"


class UsageBudget(Protocol):
    def try_consume(self, provider: str) -> bool:
        """Count one call and return True, or return False if the budget is spent."""
        ...


class SerpApiHotelsProvider(HotelProvider):
    name = "serpapi"
    label = "Google Hotels (via SerpApi)"

    def __init__(self, client: httpx.AsyncClient, api_key: str, budget: UsageBudget) -> None:
        self._client = client
        self._api_key = api_key
        self._budget = budget

    async def search(self, query: SearchQuery) -> ProviderOutcome:
        if not self._api_key:
            return ProviderOutcome(
                provider=self.name, status="not_configured", diagnostic="SERPAPI_KEY is not set"
            )
        if not self._budget.try_consume(self.name):
            return ProviderOutcome(
                provider=self.name,
                status="quota_exhausted",
                diagnostic="monthly SerpApi budget reached (SERPAPI_MONTHLY_BUDGET)",
            )

        params = {
            "engine": "google_hotels",
            "q": f"hotels in {query.location_name}",
            "check_in_date": query.check_in.isoformat(),
            "check_out_date": query.check_out.isoformat(),
            "adults": query.adults,
            "currency": PRICE_CURRENCY,
            "hl": "en",
            "api_key": self._api_key,
        }
        try:
            response = await self._client.get(SERPAPI_URL, params=params)
            payload = response.json()
            hotels = serpapi_parse.parse_properties(payload, PRICE_CURRENCY, query.nights)
        except SerpApiResponseError as exc:
            if serpapi_parse.is_no_results_error(str(exc)):
                return ProviderOutcome(provider=self.name, status="no_results")
            logger.warning("serpapi search failed for %s: %s", query.label, exc)
            return ProviderOutcome(provider=self.name, status="error", diagnostic=str(exc))
        except (httpx.HTTPError, ValueError) as exc:
            # Never include the request URL here: it carries the API key.
            logger.warning("serpapi request failed for %s: %s", query.label, type(exc).__name__)
            return ProviderOutcome(provider=self.name, status="error", diagnostic=type(exc).__name__)

        if not hotels:
            return ProviderOutcome(provider=self.name, status="no_results")
        return ProviderOutcome(provider=self.name, status="ok", hotels=hotels)
