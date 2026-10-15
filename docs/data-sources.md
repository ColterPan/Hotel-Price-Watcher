# Data sources

Everything this app shows comes from public APIs used within their terms. This page lists what each one provides, its limits, and what was checked when the app was built (October 2026).

## Why no scraping

The obvious approach, driving a browser through Booking.com, Agoda or Google Hotels with Playwright, was ruled out:

- Their terms of service forbid automated access.
- They run strong bot protection (DataDome, PerimeterX, Akamai). A scraper works for a few days, then gets blocked, then needs proxy rotation and CAPTCHA solving to keep going. That is an arms race this project doesn't want to be in.
- A public repo that does this is a liability for everyone who forks it.

Google Maps reviews are covered by the same reasoning, and scraping them also breaks the Google Maps Platform terms.

## Xotelo (default, free)

- Docs: https://xotelo.com
- Base URL: `https://data.xotelo.com/api`
- No key. No published rate limit, so the app caps itself at `XOTELO_MAX_CONCURRENCY` parallel requests (default 4) and caches results (`SEARCH_CACHE_TTL_SECONDS`, `RATES_CACHE_TTL_SECONDS`).
- Data is based on TripAdvisor.

| Endpoint | Used for | Notes |
|---|---|---|
| `/list?location_key=g294265` | Hotels in a city: name, coordinates, image, TripAdvisor rating and review count, typical price range | Free |
| `/rates?hotel_key=...&chk_in&chk_out` | Nightly price per booking site for your dates | Free. Takes about 3 seconds per hotel. Only some currencies, **not SGD**, so the app always asks for USD. |
| `/heatmap?hotel_key=...&chk_out` | Cheap, average and expensive check-in days | Free |
| `/search?query=...` | Place name to location id | **RapidAPI only** since 2026. Not used. |

Because `/search` is no longer free, the app ships `backend/src/hotel_watcher/data/cities.json`: 54 cities whose ids were checked against `/list` on 2026-10-15. Any TripAdvisor URL containing `-g<digits>-` also works in the search box.

To add a city: open its TripAdvisor hotels page, copy the `g` number from the URL, add an entry to `cities.json`, and confirm `/list?location_key=g...` returns hotels in that city.

## SerpApi Google Hotels (optional)

- Docs: https://serpapi.com/google-hotels-api
- Needs `SERPAPI_KEY`. The free plan is a few hundred searches a month (check SerpApi's pricing page for the current number).
- Each search the app runs costs one SerpApi search. `SERPAPI_MONTHLY_BUDGET` (default 200) is a hard cap stored in SQLite, so restarts don't reset it. When it's reached, the provider reports "monthly limit reached" instead of spending more.
- SerpApi is never used by the background watcher, only for searches you run.
- The test fixture `backend/tests/fixtures/serpapi_google_hotels.json` was written from SerpApi's documentation, not captured live. Run `python scripts/capture_fixtures.py` with a key to replace it with a real response.

Hotels found by both Xotelo and SerpApi are merged when they are within 250 m of each other and their names match (`backend/src/hotel_watcher/search/matching.py`).

## Frankfurter (exchange rates)

- https://frankfurter.dev, European Central Bank reference rates, free, no key.
- Rates update about once per weekday, so they are cached for an hour.
- Used for display only. Stored prices and every comparison stay in USD.

## Map tiles

The default is OpenStreetMap's standard tile server, inverted with a CSS filter to fit the dark theme.

- That server is fine for **personal, light use** under the [OSM tile usage policy](https://operations.osmfoundation.org/policies/tiles/). Don't point a busy public deployment at it.
- To use another provider, set `VITE_TILE_URL` (a `{z}/{x}/{y}` template), `VITE_TILE_ATTRIBUTION` (required by almost every provider), and `VITE_TILE_DARKEN=false` if the tiles are already dark. These are applied when the frontend is built.
- CARTO's dark basemap was the first choice, but in October 2026 it returned "API key required" tiles, so it was dropped.

## Sources that were considered and not used

| Source | Why not |
|---|---|
| Amadeus Self-Service hotel APIs | The Self-Service portal was shut down on 17 July 2026. Keys no longer work. |
| Google Places API (New) | Reviews and ratings fall under the Enterprise SKU with a small free allowance. Possible later as an optional provider. |
| LiteAPI | The free sandbox key is meant for testing. It wasn't confirmed whether it returns real prices. |
| TripAdvisor Content API | TripAdvisor data already comes through Xotelo. |
