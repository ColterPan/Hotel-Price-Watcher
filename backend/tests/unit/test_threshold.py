from decimal import Decimal as D

import pytest

from hotel_watcher.watch.threshold import describe, evaluate


@pytest.mark.parametrize(
    ("price", "target", "historical_min", "expected"),
    [
        # First check: the baseline, unless it already meets a target.
        ("200", None, None, None),
        ("200", "250", None, "target_hit"),
        ("200", "150", None, None),
        # Later checks without a target: any new low.
        ("190", None, "200", "new_low"),
        ("200", None, "200", None),
        ("210", None, "200", None),
        # Later checks with a target: a new low that is also at or under it.
        ("190", "195", "200", "target_hit"),
        ("195", "195", "200", "target_hit"),
        ("190", "150", "200", None),
        # Under target but not a new low: already announced, stay quiet.
        ("140", "150", "130", None),
    ],
)
def test_evaluate(price, target, historical_min, expected):
    result = evaluate(D(price), D(target) if target else None, D(historical_min) if historical_min else None)
    assert result == expected


def test_first_check_ignores_browsing_history_for_targets():
    # Browsing already recorded 200, so 200 is not a new low, but it does meet the target.
    assert evaluate(D("200"), D("250"), D("200"), first_check=True) == "target_hit"
    assert evaluate(D("150"), None, D("200"), first_check=True) is None


def test_describe_new_low_mentions_previous_low_and_site():
    text = describe("Pan Pacific", "new_low", D("290"), D("306"), "USD", "Trip.com")
    assert text == "Pan Pacific hit a new low of USD 290 a night on Trip.com (lowest before: USD 306)."


def test_describe_target_hit():
    text = describe("Mi Rochor", "target_hit", D("99"), None, "USD", None)
    assert text == "Mi Rochor is down to USD 99 a night, at or under your target."
