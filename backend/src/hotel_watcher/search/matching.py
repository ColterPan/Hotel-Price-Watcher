"""Recognise the same property across providers and merge it into one hotel.

Two listings are the same place when they sit close together AND their names
agree. Distance alone is not enough (city-centre hotels share buildings and
blocks), and names alone are not enough (chains reuse names across a city).
"""

from __future__ import annotations

import math
import re
import unicodedata
from collections.abc import Sequence
from difflib import SequenceMatcher

from hotel_watcher.models.hotel import Hotel

#: Listings further apart than this are never merged.
MAX_DISTANCE_METERS = 250
#: Character-level similarity needed when names are compared whole.
MIN_NAME_RATIO = 0.8
#: Word-overlap (Jaccard) needed as an alternative to MIN_NAME_RATIO.
MIN_TOKEN_OVERLAP = 0.6

#: Words that say nothing about which property it is.
_GENERIC_WORDS = frozenset(
    {"hotel", "hotels", "the", "a", "an", "by", "and", "at", "of", "resort", "suites", "inn", "ihg", "hostel"}
)
_NON_WORD = re.compile(r"[^a-z0-9]+")


def distance_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Great-circle distance (haversine)."""
    radius = 6_371_000
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lng2 - lng1)
    a = math.sin(dphi / 2) ** 2 + math.cos(phi1) * math.cos(phi2) * math.sin(dlmb / 2) ** 2
    return 2 * radius * math.asin(math.sqrt(a))


def name_tokens(name: str) -> tuple[str, ...]:
    folded = unicodedata.normalize("NFKD", name)
    folded = "".join(ch for ch in folded if not unicodedata.combining(ch)).lower().replace("&", " and ")
    return tuple(word for word in _NON_WORD.split(folded) if word and word not in _GENERIC_WORDS)


def names_match(a: str, b: str) -> bool:
    tokens_a, tokens_b = name_tokens(a), name_tokens(b)
    if not tokens_a or not tokens_b:
        return False
    joined_a, joined_b = " ".join(tokens_a), " ".join(tokens_b)
    if joined_a == joined_b or joined_a in joined_b or joined_b in joined_a:
        return True
    if SequenceMatcher(None, joined_a, joined_b).ratio() >= MIN_NAME_RATIO:
        return True
    set_a, set_b = set(tokens_a), set(tokens_b)
    return len(set_a & set_b) / len(set_a | set_b) >= MIN_TOKEN_OVERLAP


def is_same_property(a: Hotel, b: Hotel) -> bool:
    if distance_meters(a.latitude, a.longitude, b.latitude, b.longitude) > MAX_DISTANCE_METERS:
        return False
    return names_match(a.name, b.name)


def _merge_pair(base: Hotel, extra: Hotel) -> Hotel:
    """Fold `extra` into `base`. Base wins on identity; dated data wins on price."""
    known_sources = {rating.source for rating in base.ratings}
    return base.model_copy(
        update={
            "image_url": base.image_url or extra.image_url,
            "url": base.url or extra.url,
            "hotel_class": base.hotel_class or extra.hotel_class,
            "amenities": base.amenities or extra.amenities,
            "providers": base.providers + tuple(p for p in extra.providers if p not in base.providers),
            "rates_key": base.rates_key or extra.rates_key,
            "ratings": base.ratings + tuple(r for r in extra.ratings if r.source not in known_sources),
            "offers": base.offers or extra.offers,
            "price": base.price or extra.price,
        }
    )


def merge_hotels(groups: Sequence[Sequence[Hotel]]) -> tuple[Hotel, ...]:
    """Merge provider result lists. Earlier lists are the base for later ones."""
    merged: list[Hotel] = []
    for group in groups:
        # Only match against earlier providers' hotels, and let each of those
        # absorb at most one listing from this provider. Two listings from
        # the same provider are two properties by definition.
        candidates = len(merged)
        taken: set[int] = set()
        for hotel in group:
            index = next(
                (i for i in range(candidates) if i not in taken and is_same_property(merged[i], hotel)),
                None,
            )
            if index is None:
                merged.append(hotel)
            else:
                taken.add(index)
                merged[index] = _merge_pair(merged[index], hotel)
    return tuple(merged)
