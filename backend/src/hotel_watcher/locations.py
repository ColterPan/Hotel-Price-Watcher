"""Where a search can start: a bundled list of cities, or a pasted TripAdvisor link.

Xotelo's free /list endpoint needs a TripAdvisor location id ("g294265"). Its
place-name search is RapidAPI-only now, so this module ships a list of cities
whose ids were checked against the live API (data/cities.json), and also
accepts any TripAdvisor URL, which always contains the id.
"""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, ConfigDict

_CITIES_PATH = Path(__file__).parent / "data" / "cities.json"

#: TripAdvisor URLs carry the location as "-g<digits>-", e.g.
#: https://www.tripadvisor.com/Hotels-g294265-Singapore-Hotels.html
_TRIPADVISOR_URL_RE = re.compile(r"tripadvisor\.[a-z.]+/.*?-(g\d{2,10})(?:-|\.html)", re.IGNORECASE)
_BARE_KEY_RE = re.compile(r"^g\d{2,10}$", re.IGNORECASE)

MAX_RESULTS = 8


class Location(BaseModel):
    model_config = ConfigDict(frozen=True)

    name: str
    country: str
    location_key: str
    latitude: float | None = None
    longitude: float | None = None


def _fold(text: str) -> str:
    """Lowercase and strip accents so "Kyōto" matches "kyoto"."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(ch for ch in decomposed if not unicodedata.combining(ch)).lower().strip()


@lru_cache
def all_locations() -> tuple[Location, ...]:
    rows = json.loads(_CITIES_PATH.read_text(encoding="utf-8"))
    return tuple(Location(**row) for row in rows)


def find_by_key(location_key: str) -> Location | None:
    return next((loc for loc in all_locations() if loc.location_key == location_key), None)


def _from_tripadvisor_text(text: str) -> Location | None:
    match = _TRIPADVISOR_URL_RE.search(text)
    key = match.group(1).lower() if match else None
    if key is None and _BARE_KEY_RE.match(text.strip()):
        key = text.strip().lower()
    if key is None:
        return None
    return find_by_key(key) or Location(name=f"TripAdvisor area {key}", country="", location_key=key)


def search_locations(text: str) -> tuple[Location, ...]:
    """Cities matching `text`, best first. A TripAdvisor link or id resolves directly."""
    if not text or not text.strip():
        return all_locations()[:MAX_RESULTS]

    direct = _from_tripadvisor_text(text)
    if direct is not None:
        return (direct,)

    needle = _fold(text)
    starts = [loc for loc in all_locations() if _fold(loc.name).startswith(needle)]
    contains = [
        loc
        for loc in all_locations()
        if loc not in starts and (needle in _fold(loc.name) or needle in _fold(loc.country))
    ]
    return tuple((starts + contains)[:MAX_RESULTS])
