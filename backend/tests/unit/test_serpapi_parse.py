from decimal import Decimal

import pytest

from hotel_watcher.providers import serpapi_parse
from hotel_watcher.providers.serpapi_parse import SerpApiResponseError
from tests.conftest import load_fixture


def _hotels():
    return serpapi_parse.parse_properties(load_fixture("serpapi_google_hotels.json"), "USD", nights=2)


def test_parses_properties_and_skips_ones_without_coordinates():
    names = [h.name for h in _hotels()]
    assert names == ["Pan Pacific Singapore", "Hotel Mi Rochor", "Example Bay Hotel"]


def test_property_fields():
    pan_pacific = _hotels()[0]
    assert pan_pacific.id.startswith("gh-")
    assert pan_pacific.rates_key is None
    assert pan_pacific.hotel_class == 5
    assert pan_pacific.image_url == "https://example.invalid/pp-thumb.jpg"
    assert "Pool" in pan_pacific.amenities
    (rating,) = pan_pacific.ratings
    assert (rating.source, rating.rating, rating.review_count) == ("google", 4.6, 9822)


def test_live_price_and_offers_sorted():
    pan_pacific = _hotels()[0]
    assert pan_pacific.price is not None
    assert pan_pacific.price.kind == "live"
    assert pan_pacific.price.nightly == Decimal("301")
    assert pan_pacific.price.total == Decimal("602")
    assert pan_pacific.price.cheapest_site == "Pan Pacific"
    assert [o.site for o in pan_pacific.offers] == ["Pan Pacific", "Agoda"]
    assert pan_pacific.offers[0].free_cancellation is True


def test_hotel_class_falls_back_to_text():
    assert _hotels()[1].hotel_class == 3


def test_total_falls_back_to_nightly_times_nights():
    example = _hotels()[2]
    assert example.price is not None
    assert example.price.total == Decimal("280")


def test_stable_id_is_deterministic_and_short():
    assert serpapi_parse.stable_id("abc") == serpapi_parse.stable_id("abc")
    assert len(serpapi_parse.stable_id("abc")) == len("gh-") + 12


def test_error_payload_raises():
    with pytest.raises(SerpApiResponseError, match="Invalid API key"):
        serpapi_parse.parse_properties({"error": "Invalid API key."}, "USD", 1)


@pytest.mark.parametrize(
    ("message", "expected"),
    [
        ("Google Hotels hasn't returned any results for this query.", True),
        ("Invalid API key.", False),
    ],
)
def test_no_results_detection(message, expected):
    assert serpapi_parse.is_no_results_error(message) is expected
