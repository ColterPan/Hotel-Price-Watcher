"""The contract every hotel data provider implements.

Rules every provider follows (same as the flight watcher this grew out of):

1. Never let an exception escape `search` or `rates`. Catch it and return an
   outcome with status "error" and a short diagnostic.
2. Keep "no results", "not configured", "quota exhausted" and "error" apart.
   Mixing them up would let the app say "no hotels here" when the truth is
   "this source is down".
3. Keep parsing in plain functions over JSON (`*_parse.py`) so it can be
   tested against captured fixtures with no network.
"""

from __future__ import annotations

import abc
from datetime import date

from hotel_watcher.models.hotel import Heatmap, ProviderOutcome, RatesOutcome
from hotel_watcher.models.stay import SearchQuery, StayQuery


class HotelProvider(abc.ABC):
    name: str
    label: str

    @abc.abstractmethod
    async def search(self, query: SearchQuery) -> ProviderOutcome:
        """Hotels in `query`'s area. Returns an outcome, never raises."""
        raise NotImplementedError

    def handles_rates_for(self, hotel_key: str) -> bool:
        """Whether this provider can quote per-hotel rates for `hotel_key`."""
        return False

    async def rates(self, stay: StayQuery) -> RatesOutcome:
        """Nightly rates per booking site for one hotel. Returns an outcome, never raises."""
        return RatesOutcome(provider=self.name, status="not_configured", diagnostic="rates not supported")

    async def heatmap(self, hotel_key: str, check_out: date) -> Heatmap | None:
        """Cheap/average/high check-in days around a stay, if the provider knows them."""
        return None
