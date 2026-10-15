from datetime import UTC, datetime
from decimal import Decimal

from hotel_watcher.models.hotel import Offer, ProviderOutcome, RatesOutcome
from hotel_watcher.providers.base import HotelProvider
from hotel_watcher.search.cache import TtlCache
from hotel_watcher.search.orchestrator import run_search
from hotel_watcher.search.rates import RatesService
from tests.conftest import make_hotel, make_search, make_stay, rating

NOW = datetime(2026, 10, 15, tzinfo=UTC)


class StubProvider(HotelProvider):
    def __init__(
        self, name: str, outcome: ProviderOutcome | Exception, rates_outcome=None, prefix: str = "g"
    ):
        self.name = name
        self.label = name
        self._outcome = outcome
        self._rates = rates_outcome
        self._prefix = prefix
        self.rate_calls = 0

    async def search(self, query):
        if isinstance(self._outcome, Exception):
            raise self._outcome
        return self._outcome

    def handles_rates_for(self, hotel_key):
        return hotel_key.startswith(self._prefix)

    async def rates(self, stay):
        self.rate_calls += 1
        if isinstance(self._rates, Exception):
            raise self._rates
        return self._rates


async def test_search_merges_scores_and_reports_every_provider():
    good = StubProvider(
        "xotelo",
        ProviderOutcome(
            provider="xotelo",
            status="ok",
            hotels=(
                make_hotel("Low", ratings=(rating(3.5, 500),)),
                make_hotel("High", lat=1.35, ratings=(rating(4.8, 500),)),
            ),
        ),
    )
    broken = StubProvider("serpapi", RuntimeError("bug"))

    response = await run_search([good, broken], make_search(), NOW)

    assert [h.name for h in response.hotels] == ["High", "Low"]
    assert all(h.quality is not None for h in response.hotels)
    assert response.provider_statuses == {"xotelo": "ok", "serpapi": "error"}
    assert response.provider_diagnostics == {"serpapi": "RuntimeError"}
    # Singapore is a bundled city, so the map centres on it.
    assert response.center_latitude == 1.2912


async def test_search_with_unknown_area_centres_on_results():
    provider = StubProvider(
        "xotelo",
        ProviderOutcome(provider="xotelo", status="ok", hotels=(make_hotel("A", lat=10.0, lng=20.0),)),
    )
    response = await run_search([provider], make_search(location_key="g1234567"), NOW)
    assert (response.center_latitude, response.center_longitude) == (10.0, 20.0)


async def test_search_with_nothing_found():
    provider = StubProvider("xotelo", ProviderOutcome(provider="xotelo", status="no_results"))
    response = await run_search([provider], make_search(location_key="g1234567"), NOW)
    assert response.hotels == ()
    assert response.center_latitude is None


def _ok_rates():
    return RatesOutcome(
        provider="xotelo",
        status="ok",
        offers=(Offer(site="A", nightly=Decimal("100"), currency="USD"),),
    )


async def test_rates_are_cached_unless_bypassed():
    provider = StubProvider("xotelo", ProviderOutcome(provider="xotelo", status="ok"), _ok_rates())
    service = RatesService([provider], TtlCache(ttl_seconds=60))
    stay = make_stay()

    first, first_cached = await service.rates(stay)
    second, second_cached = await service.rates(stay)
    await service.rates(stay, use_cache=False)

    assert (first_cached, second_cached) == (False, True)
    assert first == second
    assert provider.rate_calls == 2


async def test_rate_errors_are_not_cached():
    provider = StubProvider(
        "xotelo",
        ProviderOutcome(provider="xotelo", status="ok"),
        RatesOutcome(provider="xotelo", status="error"),
    )
    service = RatesService([provider], TtlCache(ttl_seconds=60))
    await service.rates(make_stay())
    await service.rates(make_stay())
    assert provider.rate_calls == 2


async def test_rates_route_to_the_provider_that_owns_the_key():
    xotelo = StubProvider("xotelo", ProviderOutcome(provider="xotelo", status="ok"), _ok_rates(), prefix="g")
    service = RatesService([xotelo], TtlCache(ttl_seconds=0))
    outcome, _ = await service.rates(make_stay("demo-g294265-01"))
    assert outcome.status == "not_configured"
    assert xotelo.rate_calls == 0


async def test_raising_provider_becomes_error_outcome():
    provider = StubProvider("xotelo", ProviderOutcome(provider="xotelo", status="ok"), RuntimeError("boom"))
    service = RatesService([provider], TtlCache(ttl_seconds=60))
    outcome, _ = await service.rates(make_stay())
    assert outcome.status == "error"


async def test_heatmap_without_owner_is_none():
    service = RatesService([], TtlCache(ttl_seconds=0))
    stay = make_stay()
    assert await service.heatmap(stay.hotel_key, stay.check_out) is None
