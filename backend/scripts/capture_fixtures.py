"""Re-capture real API responses into tests/fixtures/.

Run this when a provider changes its response format and the parser tests need
fresh, real examples:

    python scripts/capture_fixtures.py                 # Xotelo only (free)
    SERPAPI_KEY=... python scripts/capture_fixtures.py # also SerpApi (uses 1 search)

The SerpApi capture removes your key from the saved `search_metadata` and
`search_parameters`, but read the file before committing it anyway.
"""

from __future__ import annotations

import json
import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path
from typing import Any

import httpx

FIXTURES = Path(__file__).resolve().parents[1] / "tests" / "fixtures"
XOTELO = "https://data.xotelo.com/api"
SINGAPORE = "g294265"
PAN_PACIFIC = "g294265-d302294"

logger = logging.getLogger("capture_fixtures")


def _save(name: str, payload: Any) -> None:
    path = FIXTURES / name
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    logger.info("wrote %s", path)


def _strip_secrets(payload: dict[str, Any]) -> dict[str, Any]:
    cleaned = {k: v for k, v in payload.items() if k not in ("search_metadata",)}
    params = dict(cleaned.get("search_parameters") or {})
    params.pop("api_key", None)
    cleaned["search_parameters"] = params
    return cleaned


def main() -> int:
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    check_in = date.today() + timedelta(days=35)
    check_out = check_in + timedelta(days=2)

    with httpx.Client(timeout=30, headers={"User-Agent": "hotel-price-watcher/fixture-capture"}) as client:
        try:
            _save(
                "xotelo_list.json",
                client.get(f"{XOTELO}/list", params={"location_key": SINGAPORE, "limit": 5}).json(),
            )
            _save(
                "xotelo_rates.json",
                client.get(
                    f"{XOTELO}/rates",
                    params={
                        "hotel_key": PAN_PACIFIC,
                        "chk_in": check_in,
                        "chk_out": check_out,
                        "currency": "USD",
                    },
                ).json(),
            )
            _save(
                "xotelo_heatmap.json",
                client.get(
                    f"{XOTELO}/heatmap", params={"hotel_key": PAN_PACIFIC, "chk_out": check_out}
                ).json(),
            )
        except (httpx.HTTPError, ValueError) as exc:
            logger.error("Xotelo capture failed: %s", exc)
            return 1

        key = os.environ.get("SERPAPI_KEY", "")
        if not key:
            logger.info("SERPAPI_KEY not set, skipping the SerpApi capture")
            return 0
        try:
            response = client.get(
                "https://serpapi.com/search.json",
                params={
                    "engine": "google_hotels",
                    "q": "hotels in Singapore",
                    "check_in_date": check_in.isoformat(),
                    "check_out_date": check_out.isoformat(),
                    "adults": 2,
                    "currency": "USD",
                    "hl": "en",
                    "api_key": key,
                },
            )
            _save("serpapi_google_hotels.json", _strip_secrets(response.json()))
        except (httpx.HTTPError, ValueError) as exc:
            # Never log the exception's request URL: it contains the key.
            logger.error("SerpApi capture failed: %s", type(exc).__name__)
            return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
