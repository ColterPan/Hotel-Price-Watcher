"""Xotelo and SerpApi providers against mocked HTTP (respx). No real network."""

from collections.abc import AsyncIterator

import httpx
import pytest
import respx

from hotel_watcher.providers.serpapi_hotels import SERPAPI_URL, SerpApiHotelsProvider
from hotel_watcher.providers.xotelo import XoteloProvider
from tests.conftest import load_fixture, make_search, make_stay

XOTELO = "https://xotelo.test/api"


class Budget:
    def __init__(self, allowed: bool = True) -> None:
        self.allowed = allowed
        self.calls = 0

    def try_consume(self, provider: str) -> bool:
        self.calls += 1
        return self.allowed


@pytest.fixture
async def client() -> AsyncIterator[httpx.AsyncClient]:
    async with httpx.AsyncClient() as http:
        yield http


# --- Xotelo ---------------------------------------------------------------------


@respx.mock
async def test_xotelo_search_ok(client):
    route = respx.get(f"{XOTELO}/list").respond(json=load_fixture("xotelo_list.json"))
    outcome = await XoteloProvider(client, base_url=XOTELO, list_sort="popularity").search(
        make_search(limit=20)
    )

    assert outcome.status == "ok"
    assert len(outcome.hotels) == 5
    params = route.calls.last.request.url.params
    assert (params["location_key"], params["limit"], params["sort"]) == ("g294265", "20", "popularity")


@respx.mock
async def test_xotelo_search_api_error_is_reported_not_raised(client):
    respx.get(f"{XOTELO}/list").respond(
        status_code=400,
        json={"error": {"status_code": 400, "message": "Invalid location_key"}, "result": None},
    )
    outcome = await XoteloProvider(client, base_url=XOTELO).search(make_search())
    assert outcome.status == "error"
    assert outcome.diagnostic == "Invalid location_key"


@respx.mock
async def test_xotelo_search_timeout_is_error(client):
    respx.get(f"{XOTELO}/list").mock(side_effect=httpx.ReadTimeout("slow"))
    outcome = await XoteloProvider(client, base_url=XOTELO).search(make_search())
    assert outcome.status == "error"


@respx.mock
async def test_xotelo_search_server_error_and_html(client):
    respx.get(f"{XOTELO}/list").respond(status_code=502, text="<html>bad gateway</html>")
    outcome = await XoteloProvider(client, base_url=XOTELO).search(make_search())
    assert outcome.status == "error"
    assert "502" in (outcome.diagnostic or "")


@respx.mock
async def test_xotelo_search_non_json_200(client):
    respx.get(f"{XOTELO}/list").respond(status_code=200, text="maintenance")
    outcome = await XoteloProvider(client, base_url=XOTELO).search(make_search())
    assert outcome.status == "error"


@respx.mock
async def test_xotelo_search_empty_list_is_no_results(client):
    respx.get(f"{XOTELO}/list").respond(json={"error": None, "result": {"list": []}})
    outcome = await XoteloProvider(client, base_url=XOTELO).search(make_search())
    assert outcome.status == "no_results"


@respx.mock
async def test_xotelo_rates_ok_requests_usd(client):
    route = respx.get(f"{XOTELO}/rates").respond(json=load_fixture("xotelo_rates.json"))
    stay = make_stay()
    outcome = await XoteloProvider(client, base_url=XOTELO).rates(stay)

    assert outcome.status == "ok"
    assert outcome.cheapest is not None and outcome.cheapest.site == "Trip.com"
    params = route.calls.last.request.url.params
    assert params["currency"] == "USD"
    assert params["chk_in"] == stay.check_in.isoformat()
    assert params["adults"] == "2"


@respx.mock
async def test_xotelo_rates_empty_is_no_results(client):
    respx.get(f"{XOTELO}/rates").respond(json={"error": None, "result": {"rates": []}})
    outcome = await XoteloProvider(client, base_url=XOTELO).rates(make_stay())
    assert outcome.status == "no_results"


@respx.mock
async def test_xotelo_rates_network_error(client):
    respx.get(f"{XOTELO}/rates").mock(side_effect=httpx.ConnectError("down"))
    outcome = await XoteloProvider(client, base_url=XOTELO).rates(make_stay())
    assert outcome.status == "error"


@respx.mock
async def test_xotelo_heatmap_ok_and_failure(client):
    respx.get(f"{XOTELO}/heatmap").respond(json=load_fixture("xotelo_heatmap.json"))
    provider = XoteloProvider(client, base_url=XOTELO)
    stay = make_stay()
    assert (await provider.heatmap(stay.hotel_key, stay.check_out)) is not None

    respx.get(f"{XOTELO}/heatmap").mock(side_effect=httpx.ConnectError("down"))
    assert (await provider.heatmap(stay.hotel_key, stay.check_out)) is None


def test_xotelo_handles_tripadvisor_keys_only(client):
    provider = XoteloProvider(client, base_url=XOTELO)
    assert provider.handles_rates_for("g294265-d302294")
    assert not provider.handles_rates_for("demo-g294265-01")


# --- SerpApi --------------------------------------------------------------------


async def test_serpapi_without_key_is_not_configured(client):
    budget = Budget()
    outcome = await SerpApiHotelsProvider(client, "", budget).search(make_search())
    assert outcome.status == "not_configured"
    assert budget.calls == 0


async def test_serpapi_budget_exhausted(client):
    outcome = await SerpApiHotelsProvider(client, "key", Budget(allowed=False)).search(make_search())
    assert outcome.status == "quota_exhausted"


@respx.mock
async def test_serpapi_search_ok(client):
    route = respx.get(SERPAPI_URL).respond(json=load_fixture("serpapi_google_hotels.json"))
    outcome = await SerpApiHotelsProvider(client, "secret", Budget()).search(make_search())

    assert outcome.status == "ok"
    assert len(outcome.hotels) == 3
    params = route.calls.last.request.url.params
    assert params["engine"] == "google_hotels"
    assert params["q"] == "hotels in Singapore"
    assert params["currency"] == "USD"


@respx.mock
async def test_serpapi_no_results_message(client):
    respx.get(SERPAPI_URL).respond(
        json={"error": "Google Hotels hasn't returned any results for this query."}
    )
    outcome = await SerpApiHotelsProvider(client, "secret", Budget()).search(make_search())
    assert outcome.status == "no_results"


@respx.mock
async def test_serpapi_error_never_leaks_the_key(client):
    respx.get(SERPAPI_URL).mock(
        side_effect=httpx.ConnectError("boom for https://serpapi.com/?api_key=secret")
    )
    outcome = await SerpApiHotelsProvider(client, "secret", Budget()).search(make_search())
    assert outcome.status == "error"
    assert "secret" not in (outcome.diagnostic or "")


@respx.mock
async def test_serpapi_invalid_key_is_error(client):
    respx.get(SERPAPI_URL).respond(status_code=401, json={"error": "Invalid API key."})
    outcome = await SerpApiHotelsProvider(client, "bad", Budget()).search(make_search())
    assert outcome.status == "error"
    assert outcome.diagnostic == "Invalid API key."
