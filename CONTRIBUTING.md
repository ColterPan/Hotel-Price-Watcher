# Contributing

Thanks for helping. A few things keep this project easy to work on.

## Setup

See "Running without Docker" in the [README](README.md). Then:

```bash
cd backend && pytest && ruff check src tests scripts && ruff format --check src tests scripts
cd frontend && npm run typecheck && npm test && npm run build
```

All of these run in CI and must pass.

## Ground rules

- **Data sources must be legal to use.** New providers have to use a public API within its terms. Pull requests that scrape sites whose terms forbid it, or that add proxy rotation or CAPTCHA solving, will be closed.
- **Providers never raise.** Catch errors inside the provider and return an outcome with a status (`ok`, `no_results`, `not_configured`, `quota_exhausted`, `error`). See `backend/src/hotel_watcher/providers/base.py`.
- **Parsing is separate from fetching.** Put response parsing in a `*_parse.py` module of plain functions, and test it against a real captured response in `backend/tests/fixtures/`.
- **Money stays in Decimal and in the provider currency.** Convert only for display.
- **Tests come with the change.** Bug fixes get a test that fails without the fix.
- **No secrets in commits.** Keys go in `.env`, which is git-ignored.

## Adding a provider

1. Write `providers/<name>_parse.py` (pure functions) and `providers/<name>.py` (implements `HotelProvider`).
2. Capture a real response into `tests/fixtures/` and test the parser against it.
3. Test the provider with `respx` for success, empty and failure cases.
4. Register it in `providers/registry.py` and add any settings to `config.py` and `.env.example`.
5. Add a friendly name in `frontend/src/lib/hotels.ts` (`PROVIDER_NAMES`) and document it in `docs/data-sources.md`.

## Writing style

UI text and docs are plain and direct. Short sentences, no marketing words, and no em dashes (a test checks for them). Use a comma, a colon or a new sentence instead.
