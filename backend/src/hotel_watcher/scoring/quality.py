"""Combine review scores from several sources into one 0 to 10 quality score.

The method, in plain words (also in docs/scoring.md):

1. Put every rating on a 0 to 10 scale (4.5 out of 5 becomes 9.0).
2. Pull each rating toward the area's average in proportion to how few
   reviews it has. A 5.0 from 3 reviews ends up close to average, a 4.6
   from 2,000 reviews barely moves. This is a Bayesian average with a prior
   worth PRIOR_REVIEWS reviews.
3. Average the adjusted ratings across sources, weighted by review count.
"""

from __future__ import annotations

from collections.abc import Iterable, Sequence

from hotel_watcher.models.hotel import Hotel, QualityScore, SourceRating

#: How many reviews the area average is "worth" when shrinking a rating.
PRIOR_REVIEWS = 50
#: Below this many reviews in total, the score is flagged as low confidence.
LOW_CONFIDENCE_REVIEWS = 30
#: Used as the prior when no hotel in the result set has any rating.
FALLBACK_AREA_MEAN = 7.5

_LABELS: tuple[tuple[float, str], ...] = (
    (9.0, "Exceptional"),
    (8.5, "Excellent"),
    (8.0, "Very good"),
    (7.0, "Good"),
    (6.0, "Fair"),
)


def normalize(rating: SourceRating) -> float:
    return max(0.0, min(10.0, rating.rating / rating.scale * 10.0))


def label_for(score: float) -> str:
    return next((label for threshold, label in _LABELS if score >= threshold), "Poor")


def area_mean(hotels: Iterable[Hotel]) -> float:
    """Average normalized rating across every rating in the result set."""
    values = [normalize(rating) for hotel in hotels for rating in hotel.ratings if rating.review_count > 0]
    return sum(values) / len(values) if values else FALLBACK_AREA_MEAN


def shrink(rating: SourceRating, prior_mean: float, prior_reviews: int = PRIOR_REVIEWS) -> float:
    n = rating.review_count
    return (n * normalize(rating) + prior_reviews * prior_mean) / (n + prior_reviews)


def quality_for(ratings: Sequence[SourceRating], prior_mean: float) -> QualityScore | None:
    if not ratings:
        return None
    adjusted = [shrink(rating, prior_mean) for rating in ratings]
    counts = [rating.review_count for rating in ratings]
    total_reviews = sum(counts)
    if total_reviews > 0:
        score = sum(a * n for a, n in zip(adjusted, counts, strict=True)) / total_reviews
    else:
        score = sum(adjusted) / len(adjusted)
    score = round(score, 1)
    return QualityScore(
        score=score,
        label=label_for(score),
        review_count=total_reviews,
        low_confidence=total_reviews < LOW_CONFIDENCE_REVIEWS,
    )


def score_hotels(hotels: Sequence[Hotel]) -> tuple[Hotel, ...]:
    """Return copies of `hotels` with `quality` filled in."""
    prior = area_mean(hotels)
    return tuple(hotel.model_copy(update={"quality": quality_for(hotel.ratings, prior)}) for hotel in hotels)
