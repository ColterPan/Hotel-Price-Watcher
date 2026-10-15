from datetime import date
from decimal import Decimal

import pytest

from hotel_watcher.providers import xotelo_parse
from hotel_watcher.providers.xotelo_parse import XoteloResponseError
from tests.conftest import load_fixture


def test_parse_list_reads_real_capture():
    hotels = xotelo_parse.parse_list(load_fixture("xotelo_list.json"))

    assert len(hotels) == 5
    pan_pacific = next(h for h in hotels if h.name == "Pan Pacific Singapore")
    assert pan_pacific.id == "g294265-d302294"
    assert pan_pacific.rates_key == "g294265-d302294"
    assert pan_pacific.latitude == pytest.approx(1.292475)
    assert pan_pacific.typical_min == Decimal("341")
    assert pan_pacific.typical_max == Decimal("2502")
    assert pan_pacific.typical_currency == "USD"
    assert pan_pacific.providers == ("xotelo",)
    (rating,) = pan_pacific.ratings
    assert (rating.source, rating.rating, rating.scale, rating.review_count) == (
        "tripadvisor",
        4.6,
        5.0,
        17055,
    )


def test_parse_list_keeps_merchandising_labels():
    hotels = xotelo_parse.parse_list(load_fixture("xotelo_list.json"))
    mi_rochor = next(h for h in hotels if h.name == "Hotel Mi Rochor")
    assert mi_rochor.labels == ("Breakfast included",)


def test_parse_list_skips_items_without_coordinates():
    payload = {
        "error": None,
        "result": {
            "list": [
                {"name": "No Geo", "key": "g1-d1"},
                {"name": "Ok", "key": "g1-d2", "geo": {"latitude": 1.0, "longitude": 2.0}},
                "not a dict",
            ]
        },
    }
    hotels = xotelo_parse.parse_list(payload)
    assert [h.name for h in hotels] == ["Ok"]
    assert hotels[0].ratings == ()


def test_parse_rates_sorts_cheapest_first():
    offers = xotelo_parse.parse_rates(load_fixture("xotelo_rates.json"))

    assert [o.site for o in offers][0] == "Trip.com"
    assert offers[0].nightly == Decimal("306")
    assert all(o.currency == "USD" for o in offers)
    assert len(offers) == 5


def test_parse_rates_empty_for_unknown_hotel():
    payload = {"error": None, "result": {"currency": "USD", "rates": []}}
    assert xotelo_parse.parse_rates(payload) == ()


def test_parse_rates_ignores_zero_and_missing_rates():
    payload = {
        "error": None,
        "result": {"rates": [{"name": "A", "rate": 0}, {"name": "B"}, {"name": "C", "rate": 50}]},
    }
    assert [o.site for o in xotelo_parse.parse_rates(payload)] == ["C"]


def test_api_error_message_is_raised():
    payload = {"error": {"status_code": 400, "message": "Invalid location_key"}, "result": None}
    with pytest.raises(XoteloResponseError, match="Invalid location_key"):
        xotelo_parse.parse_list(payload)


@pytest.mark.parametrize("payload", [None, [], {"error": None}, {"error": None, "result": "x"}])
def test_malformed_payloads_raise(payload):
    with pytest.raises(XoteloResponseError):
        xotelo_parse.unwrap(payload)


def test_parse_heatmap():
    heatmap = xotelo_parse.parse_heatmap(load_fixture("xotelo_heatmap.json"))
    assert date(2026, 11, 20) in heatmap.cheap
    assert date(2026, 11, 16) in heatmap.high
    assert list(heatmap.average) == sorted(heatmap.average)


def test_parse_heatmap_skips_bad_dates():
    payload = {"error": None, "result": {"heatmap": {"cheap_price_days": ["2026-01-02", "nope", None]}}}
    assert xotelo_parse.parse_heatmap(payload).cheap == (date(2026, 1, 2),)
