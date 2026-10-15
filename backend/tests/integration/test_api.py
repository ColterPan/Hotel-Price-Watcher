"""End-to-end API tests through FastAPI's TestClient. Demo provider, so no network."""

from collections.abc import Iterator
from datetime import timedelta

import httpx
import pytest
import respx
from fastapi.testclient import TestClient

from hotel_watcher.api.app import create_app
from hotel_watcher.config import Settings
from tests.conftest import future_date, load_fixture


def _settings(tmp_path, **overrides) -> Settings:
    return Settings(
        _env_file=None,
        database_path=str(tmp_path / "test.db"),
        enabled_providers=overrides.pop("enabled_providers", "demo"),
        scheduler_enabled=False,
        **overrides,
    )


@pytest.fixture
def client(tmp_path) -> Iterator[TestClient]:
    with TestClient(create_app(_settings(tmp_path))) as test_client:
        yield test_client


def _stay_params(nights: int = 2) -> dict:
    check_in = future_date()
    return {"check_in": check_in.isoformat(), "check_out": (check_in + timedelta(days=nights)).isoformat()}


def _search_body(**overrides) -> dict:
    return {
        "location_key": "g294265",
        "location_name": "Singapore",
        "adults": 2,
        "limit": 12,
        **_stay_params(),
        **overrides,
    }


def test_health_lists_providers(client):
    body = client.get("/api/health").json()
    assert body["status"] == "ok"
    assert [p["name"] for p in body["providers"]] == ["demo"]
    assert body["default_display_currency"] == "SGD"
    assert body["serpapi"] is None


def test_locations_search(client):
    names = [loc["name"] for loc in client.get("/api/locations", params={"q": "kual"}).json()]
    assert names == ["Kuala Lumpur"]


def test_search_returns_scored_hotels_and_caches(client):
    first = client.post("/api/search", json=_search_body())
    assert first.status_code == 200
    body = first.json()
    assert len(body["hotels"]) == 12
    assert body["provider_statuses"] == {"demo": "ok"}
    assert body["from_cache"] is False
    assert all(h["quality"] is not None for h in body["hotels"])
    assert body["center_latitude"] == pytest.approx(1.2912)

    again = client.post("/api/search", json=_search_body()).json()
    assert again["from_cache"] is True
    refreshed = client.post("/api/search", params={"refresh": "true"}, json=_search_body()).json()
    assert refreshed["from_cache"] is False


@pytest.mark.parametrize(
    ("override", "fragment"),
    [
        ({"check_in": "2020-01-01", "check_out": "2020-01-03"}, "past"),
        ({"location_key": "singapore"}, "location_key"),
        ({"adults": 20}, "adults"),
    ],
)
def test_search_validation_is_one_readable_message(client, override, fragment):
    response = client.post("/api/search", json=_search_body(**override))
    assert response.status_code == 422
    assert isinstance(response.json()["detail"], str)
    assert fragment in response.json()["detail"]


def test_rates_record_history(client):
    hotel = client.post("/api/search", json=_search_body()).json()["hotels"][0]
    params = {**_stay_params(), "adults": 2}

    rates = client.get(f"/api/hotels/{hotel['rates_key']}/rates", params=params).json()
    assert rates["status"] == "ok"
    assert rates["cheapest"]["nightly"]
    assert float(rates["total"]) == pytest.approx(float(rates["cheapest"]["nightly"]) * 2)

    history = client.get(f"/api/hotels/{hotel['rates_key']}/history", params=params).json()
    assert len(history) == 1

    cached = client.get(f"/api/hotels/{hotel['rates_key']}/rates", params=params).json()
    assert cached["from_cache"] is True


def test_rates_reject_bad_keys_and_dates(client):
    assert client.get("/api/hotels/not-a-key/rates", params=_stay_params()).status_code == 422
    bad_dates = {"check_in": "2020-01-01", "check_out": "2020-01-02"}
    response = client.get("/api/hotels/demo-g294265-01/rates", params=bad_dates)
    assert response.status_code == 422
    assert "past" in response.json()["detail"]


def test_heatmap(client):
    response = client.get(
        "/api/hotels/demo-g294265-01/heatmap", params={"check_out": _stay_params()["check_out"]}
    )
    assert response.status_code == 200
    assert set(response.json()) == {"cheap", "average", "high"}


def test_watch_lifecycle_and_alerts(client):
    params = _stay_params()
    payload = {
        "hotel_key": "demo-g294265-02",
        "hotel_name": "Juniper Lane Inn",
        "location_name": "Singapore",
        "adults": 2,
        "target_price": "100000",
        **params,
    }

    created = client.post("/api/watches", json=payload)
    assert created.status_code == 201
    body = created.json()
    watch_id = body["watch"]["id"]
    # A huge target means the very first price already qualifies.
    assert body["result"]["alert_kind"] == "target_hit"
    assert body["watch"]["last_price"] is not None
    assert len(body["watch"]["history"]) == 1

    assert [w["id"] for w in client.get("/api/watches").json()] == [watch_id]

    checked = client.post(f"/api/watches/{watch_id}/check").json()
    assert checked["result"]["status"] == "ok"

    inbox = client.get("/api/alerts").json()
    assert inbox["unread_count"] == 1
    alert_id = inbox["alerts"][0]["id"]
    assert inbox["alerts"][0]["hotel_name"] == "Juniper Lane Inn"
    assert client.post(f"/api/alerts/{alert_id}/read").status_code == 204
    assert client.get("/api/alerts", params={"unread_only": "true"}).json()["alerts"] == []
    assert client.post("/api/alerts/read-all").status_code == 204

    assert client.delete(f"/api/watches/{watch_id}").status_code == 204
    assert client.delete(f"/api/watches/{watch_id}").status_code == 404
    assert client.post(f"/api/watches/{watch_id}/check").status_code == 404
    assert client.get("/api/watches").json() == []


def test_watch_rejects_javascript_urls(client):
    payload = {
        "hotel_key": "demo-g294265-02",
        "hotel_name": "X",
        "hotel_url": "javascript:alert(1)",
        **_stay_params(),
    }
    response = client.post("/api/watches", json=payload)
    assert response.status_code == 422
    assert "http" in response.json()["detail"]


def test_currency_rejects_unknown_code(client):
    assert client.get("/api/currency/rates", params={"base": "XYZ"}).status_code == 422


@respx.mock
def test_currency_rates_proxy(client):
    respx.get("https://api.frankfurter.dev/v1/latest").respond(
        json={"base": "USD", "date": "2026-10-14", "rates": {"SGD": 1.29, "EUR": 0.86}}
    )
    body = client.get("/api/currency/rates", params={"base": "usd"}).json()
    assert body["rates"]["SGD"] == "1.29"
    assert body["as_of"] == "2026-10-14"


@respx.mock
def test_currency_rates_unavailable_is_503(client):
    respx.get("https://api.frankfurter.dev/v1/latest").mock(side_effect=httpx.ConnectError("down"))
    assert client.get("/api/currency/rates").status_code == 503


@respx.mock
def test_search_with_xotelo_provider(tmp_path):
    respx.get("https://data.xotelo.com/api/list").respond(json=load_fixture("xotelo_list.json"))
    respx.get("https://data.xotelo.com/api/rates").respond(json=load_fixture("xotelo_rates.json"))
    with TestClient(create_app(_settings(tmp_path, enabled_providers="xotelo"))) as client:
        body = client.post("/api/search", json=_search_body()).json()
        assert body["provider_statuses"] == {"xotelo": "ok"}
        names = {h["name"] for h in body["hotels"]}
        assert "Pan Pacific Singapore" in names
        pan_pacific = next(h for h in body["hotels"] if h["name"] == "Pan Pacific Singapore")
        assert pan_pacific["typical_min"] == "341"

        rates = client.get(f"/api/hotels/{pan_pacific['rates_key']}/rates", params=_stay_params()).json()
        assert rates["cheapest"]["site"] == "Trip.com"


def test_serpapi_enabled_without_key_reports_not_configured(tmp_path):
    settings = _settings(tmp_path, enabled_providers="demo,serpapi")
    with TestClient(create_app(settings)) as client:
        body = client.post("/api/search", json=_search_body()).json()
        assert body["provider_statuses"] == {"demo": "ok", "serpapi": "not_configured"}
        health = client.get("/api/health").json()
        assert health["serpapi"] == {"configured": False, "used_this_month": 0, "monthly_budget": 200}


def test_unknown_provider_fails_fast(tmp_path):
    with (
        pytest.raises(ValueError, match="Unknown provider"),
        TestClient(create_app(_settings(tmp_path, enabled_providers="booking"))),
    ):
        pass
