from decimal import Decimal

import pytest

from hotel_watcher.models.hotel import PriceSummary
from hotel_watcher.providers import serpapi_parse, xotelo_parse
from hotel_watcher.search import matching
from tests.conftest import load_fixture, make_hotel, offer, rating


def test_distance_is_roughly_right():
    # About 111 m per 0.001 degree of latitude.
    assert matching.distance_meters(1.0, 103.0, 1.001, 103.0) == pytest.approx(111, abs=2)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Crowne Plaza Changi Airport By IHG", "Crowne Plaza Changi Airport, an IHG Hotel"),
        ("The Fullerton Hotel Singapore", "Fullerton Hotel Singapore"),
        ("Hotel Mi Rochor", "Mi Rochor"),
        ("Café Royal & Spa", "Cafe Royal and Spa"),
    ],
)
def test_names_that_should_match(a, b):
    assert matching.names_match(a, b)


@pytest.mark.parametrize(
    ("a", "b"),
    [
        ("Village Hotel Bugis", "Village Hotel Albert Court"),
        ("Pan Pacific Singapore", "PARKROYAL Collection Marina Bay"),
        ("Hotel", "The Hotel"),
    ],
)
def test_names_that_should_not_match(a, b):
    assert not matching.names_match(a, b)


def test_same_name_far_apart_is_not_the_same_property():
    a = make_hotel("Ibis Budget", lat=1.30, lng=103.85)
    b = make_hotel("Ibis Budget", lat=1.32, lng=103.85)
    assert not matching.is_same_property(a, b)


def test_merge_combines_ratings_price_and_providers():
    base = make_hotel("Pan Pacific Singapore", ratings=(rating(4.6, 17000),), rates_key="g1-d1", id="g1-d1")
    extra = make_hotel(
        "Pan Pacific Singapore",
        lat=1.2901,
        ratings=(rating(4.5, 9000, source="google"),),
        providers=("serpapi",),
        offers=(offer("301"),),
        price=PriceSummary(nightly=Decimal("301"), total=Decimal("602"), currency="USD", kind="live"),
        hotel_class=5,
        id="gh-x",
    )
    (merged,) = matching.merge_hotels([[base], [extra]])
    assert merged.id == "g1-d1"
    assert merged.rates_key == "g1-d1"
    assert merged.providers == ("xotelo", "serpapi")
    assert {r.source for r in merged.ratings} == {"tripadvisor", "google"}
    assert merged.price is not None and merged.price.nightly == Decimal("301")
    assert merged.hotel_class == 5


def test_same_provider_listings_are_never_merged():
    a = make_hotel("Twin Tower Hotel", id="1")
    b = make_hotel("Twin Tower Hotel", id="2")
    assert len(matching.merge_hotels([[a, b]])) == 2


def test_one_base_absorbs_at_most_one_listing_per_provider():
    base = make_hotel("Harbour Hotel", id="base")
    first = make_hotel("Harbour Hotel", id="g1", providers=("serpapi",))
    second = make_hotel("Harbour Hotel", id="g2", providers=("serpapi",))
    merged = matching.merge_hotels([[base], [first, second]])
    assert [h.id for h in merged] == ["base", "g2"]


def test_real_fixtures_merge_the_overlapping_hotels():
    xotelo = xotelo_parse.parse_list(load_fixture("xotelo_list.json"))
    serp = serpapi_parse.parse_properties(load_fixture("serpapi_google_hotels.json"), "USD", 2)
    merged = matching.merge_hotels([xotelo, serp])

    # 5 Xotelo hotels, 2 of which Google also lists, plus 1 Google-only hotel.
    assert len(merged) == 6
    pan_pacific = next(h for h in merged if h.name == "Pan Pacific Singapore")
    assert set(pan_pacific.providers) == {"xotelo", "serpapi"}
