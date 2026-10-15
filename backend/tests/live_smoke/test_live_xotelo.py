"""Hits the real Xotelo API. Not part of the default test run or CI.

Run by hand when you suspect Xotelo changed something:

    pytest tests/live_smoke -v
"""

from collections.abc import AsyncIterator
from datetime import timedelta

import httpx
import pytest

from hotel_watcher.models.stay import StayQuery
from hotel_watcher.providers.xotelo import XoteloProvider
from tests.conftest import future_date, make_search


@pytest.fixture
async def provider() -> AsyncIterator[XoteloProvider]:
    async with httpx.AsyncClient(timeout=30) as client:
        yield XoteloProvider(client)


async def test_live_list_and_rates(provider):
    outcome = await provider.search(make_search(limit=5))
    assert outcome.status == "ok", outcome.diagnostic
    assert outcome.hotels

    hotel = outcome.hotels[0]
    check_in = future_date(35)
    stay = StayQuery(hotel_key=hotel.rates_key, check_in=check_in, check_out=check_in + timedelta(days=2))
    rates = await provider.rates(stay)
    assert rates.status in ("ok", "no_results"), rates.diagnostic
