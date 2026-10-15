# Architecture

A single-user, self-hosted app: one FastAPI process, one SQLite file, one static React build. No queue, no cache server, no login.

```
frontend/ (React, Vite, TypeScript)          backend/ (FastAPI, Python 3.11+)
  App.tsx           state + wiring              api/          thin routes, validation
  components/map    Leaflet map, pins           search/       orchestrator, matching, cache, rates
  components/...    drawer, detail, watches     providers/    xotelo, serpapi, demo (+ *_parse.py)
  lib/value.ts      value grade                 scoring/      quality score
  lib/collision.ts  which pins get labels       watch/        threshold rules, scheduled job
  hooks/queries.ts  TanStack Query hooks        db/           schema.sql, repository.py (raw SQL)
```

## Search

```
POST /api/search {location_key, location_name, check_in, check_out, adults, limit}
  -> SearchQuery validates (dates not past, at most 30 nights, 1 to 8 adults)
  -> search cache (15 min) unless ?refresh=true
  -> run_search(): every enabled provider in parallel with asyncio.gather
       each provider returns ProviderOutcome(status, hotels, diagnostic) and never raises;
       a backstop in the orchestrator catches anything that slips through
  -> merge_hotels(): same property from several providers becomes one hotel
  -> score_hotels(): quality score per hotel
  <- hotels + per-provider status + map centre
```

Xotelo's list gives each hotel a *typical* price range, not a price for your dates. The browser then asks for live rates per hotel:

```
GET /api/hotels/{hotel_key}/rates?check_in&check_out&adults
  -> rates service: picks the provider that owns this key, rates cache (30 min)
  -> the cheapest quote is stored in price_observations (deduplicated within 30 min)
```

The frontend fires these in parallel and lets pins and cards update as answers arrive. The backend's semaphore keeps no more than `XOTELO_MAX_CONCURRENCY` requests going to Xotelo at once, so the browser can ask for everything without being rude to the API.

## Provider statuses

Every provider call ends in one of:

| Status | Meaning | UI text |
|---|---|---|
| `ok` | Got results | live |
| `no_results` | Worked, but nothing there | nothing found |
| `not_configured` | Missing key | needs an API key |
| `quota_exhausted` | Monthly SerpApi budget used | monthly limit reached |
| `error` | Network, server or format problem | unavailable |

Keeping these apart is the point: the app must never say "no hotels here" when the truth is "the source is down".

## Watches and alerts

```
POST /api/watches -> row in watches (unique per hotel + dates + adults; re-adding reactivates)
                  -> immediate first check to set a baseline
APScheduler, every CHECK_INTERVAL_HOURS, inside the FastAPI process:
  for each active watch:
    skip if the stay has passed
    historical min for this exact stay
    fresh rates (cache bypassed)
    store observation, update last_price/last_status
    threshold.evaluate() -> maybe an alerts row
  one failing watch is logged and marked "error"; the rest still run
```

Alerts live in SQLite and show in the bell menu. The frontend polls `/api/alerts` once a minute.

## Money

- Prices are stored as Decimal text in SQLite, never floats.
- All stored and compared prices are in the provider currency (USD).
- Conversion to the display currency happens only in the browser (`state/currency.tsx`), using rates from `/api/currency/rates`. A target typed in SGD is converted to USD once, when the watch is saved.

## Security posture

- No authentication, so both the dev server and Docker bind to localhost only.
- All input is validated with pydantic at the API boundary (location and hotel keys are checked against strict patterns before they reach any URL).
- Third-party URLs (photos, listings, review links) are only rendered if they are http(s) (`frontend/src/lib/safeUrl.ts`, plus a check on watch creation).
- Hotel names placed into Leaflet's HTML pins are escaped.
- The SerpApi key travels as a query parameter, so httpx request logging is turned down to WARNING and errors never include request URLs.
- nginx sends a Content-Security-Policy that only allows scripts from the app itself.

## Why these choices

- **Raw SQL over an ORM**: four small tables. Plain SQL is short, explicit and easy to test against `:memory:`.
- **In-process scheduler**: one command starts everything. No cron, no worker container.
- **In-memory caches**: hotel prices go stale, so losing the cache on restart is correct.
- **Value grade in the browser**: it depends on the slider and on which live prices have arrived, both client-side state.
- **Collision-aware pins instead of a clustering library**: about 40 lines (`lib/collision.ts`) and pins stay readable, without another dependency.
