import pytest

from hotel_watcher.scoring import quality
from tests.conftest import make_hotel, rating


def test_normalize_puts_every_scale_on_ten():
    assert quality.normalize(rating(4.5, 10)) == pytest.approx(9.0)
    assert quality.normalize(rating(8.6, 10, scale=10)) == pytest.approx(8.6)


def test_normalize_clamps_out_of_range_values():
    assert quality.normalize(rating(6.0, 10)) == 10.0


@pytest.mark.parametrize(
    ("score", "label"),
    [
        (9.4, "Exceptional"),
        (8.7, "Excellent"),
        (8.0, "Very good"),
        (7.2, "Good"),
        (6.0, "Fair"),
        (4.0, "Poor"),
    ],
)
def test_labels(score, label):
    assert quality.label_for(score) == label


def test_few_reviews_are_pulled_toward_the_area_mean():
    perfect_but_tiny = quality.quality_for([rating(5.0, 3)], prior_mean=7.5)
    solid_and_large = quality.quality_for([rating(4.6, 2000)], prior_mean=7.5)
    assert perfect_but_tiny is not None and solid_and_large is not None
    assert solid_and_large.score > perfect_but_tiny.score


def test_many_reviews_barely_move():
    result = quality.quality_for([rating(4.6, 20000)], prior_mean=5.0)
    assert result is not None
    assert result.score == pytest.approx(9.2, abs=0.05)


def test_sources_are_weighted_by_review_count():
    result = quality.quality_for(
        [rating(5.0, 9000, source="tripadvisor"), rating(3.0, 1000, source="google")], prior_mean=8.0
    )
    assert result is not None
    assert result.review_count == 10000
    # Dominated by the 9000-review source, so much closer to 10 than to 6.
    assert result.score > 9.0


def test_low_confidence_flag():
    result = quality.quality_for([rating(4.0, 12)], prior_mean=8.0)
    assert result is not None
    assert result.low_confidence is True


def test_zero_review_ratings_fall_back_to_prior():
    result = quality.quality_for([rating(5.0, 0)], prior_mean=7.0)
    assert result is not None
    assert result.score == 7.0
    assert result.review_count == 0


def test_no_ratings_means_no_score():
    assert quality.quality_for([], prior_mean=8.0) is None


def test_area_mean_ignores_zero_count_ratings_and_falls_back():
    assert quality.area_mean([make_hotel()]) == quality.FALLBACK_AREA_MEAN
    hotels = [make_hotel("A", ratings=(rating(4.0, 10),)), make_hotel("B", ratings=(rating(5.0, 0),))]
    assert quality.area_mean(hotels) == pytest.approx(8.0)


def test_score_hotels_returns_new_objects():
    original = make_hotel(ratings=(rating(4.5, 500),))
    (scored,) = quality.score_hotels([original])
    assert original.quality is None
    assert scored.quality is not None
    assert scored is not original
