from datetime import date, timedelta

import pytest
from pydantic import ValidationError

from hotel_watcher.models.stay import (
    MAX_DAYS_AHEAD,
    MAX_NIGHTS,
    SearchQuery,
    StayQuery,
    is_rateable_hotel_key,
    validate_stay_dates,
)
from tests.conftest import future_date, make_search


def test_valid_search_query_computes_nights():
    query = make_search(nights=3)
    assert query.nights == 3


def test_search_strips_location_name():
    query = make_search(location_name="  Singapore  ")
    assert query.location_name == "Singapore"


@pytest.mark.parametrize("bad_key", ["294265", "g1", "gabc", "g294265-d1", "", "g294265; DROP TABLE"])
def test_search_rejects_malformed_location_key(bad_key):
    with pytest.raises(ValidationError):
        make_search(location_key=bad_key)


def test_check_in_in_the_past_is_rejected():
    with pytest.raises(ValueError, match="past"):
        validate_stay_dates(date(2020, 1, 1), date(2020, 1, 3), today=date(2026, 1, 1))


def test_check_out_must_follow_check_in():
    day = future_date()
    with pytest.raises(ValidationError, match="after check-in"):
        make_search(check_in=day, check_out=day)


def test_stay_longer_than_limit_is_rejected():
    day = future_date()
    with pytest.raises(ValidationError, match="nights"):
        make_search(check_in=day, check_out=day + timedelta(days=MAX_NIGHTS + 1))


def test_check_in_too_far_ahead_is_rejected():
    today = date(2026, 1, 1)
    far = today + timedelta(days=MAX_DAYS_AHEAD + 1)
    with pytest.raises(ValueError, match="within"):
        validate_stay_dates(far, far + timedelta(days=1), today=today)


@pytest.mark.parametrize("adults", [0, 9])
def test_adults_out_of_range_is_rejected(adults):
    with pytest.raises(ValidationError):
        make_search(adults=adults)


def test_search_cache_key_ignores_location_name():
    a = make_search(location_name="Singapore")
    b = make_search(location_name="SG")
    assert a.cache_key() == b.cache_key()


@pytest.mark.parametrize(
    ("key", "expected"),
    [
        ("g294265-d302294", True),
        ("demo-g294265-07", True),
        ("gh-abcdef123456", False),
        ("g294265", False),
        ("../etc/passwd", False),
    ],
)
def test_rateable_hotel_keys(key, expected):
    assert is_rateable_hotel_key(key) is expected


def test_stay_query_rejects_unrateable_key():
    day = future_date()
    with pytest.raises(ValidationError):
        StayQuery(hotel_key="gh-abc", check_in=day, check_out=day + timedelta(days=1))


def test_search_query_is_immutable():
    query = make_search()
    with pytest.raises(ValidationError):
        query.adults = 3  # type: ignore[misc]
    assert isinstance(query, SearchQuery)
