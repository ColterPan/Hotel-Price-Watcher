"""FastAPI application factory and lifespan wiring."""

from __future__ import annotations

from collections.abc import AsyncIterator
from contextlib import asynccontextmanager

import httpx
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from hotel_watcher import __version__
from hotel_watcher.api import routes_meta, routes_search, routes_watches
from hotel_watcher.config import Settings, get_settings
from hotel_watcher.currency import ExchangeRateCache
from hotel_watcher.logging_config import configure_logging, get_logger
from hotel_watcher.providers.registry import build_providers
from hotel_watcher.search.cache import TtlCache
from hotel_watcher.search.rates import RatesService
from hotel_watcher.watch.jobs import run_watch_check_job

logger = get_logger(__name__)

USER_AGENT = f"hotel-price-watcher/{__version__} (+https://github.com/)"


def _lifespan(settings: Settings):
    @asynccontextmanager
    async def lifespan(app: FastAPI) -> AsyncIterator[None]:
        configure_logging(settings.log_level.upper())
        client = httpx.AsyncClient(timeout=settings.http_timeout_seconds, headers={"User-Agent": USER_AGENT})
        providers = build_providers(settings, client)
        rates_service = RatesService(providers, TtlCache(settings.rates_cache_ttl_seconds))

        app.state.settings = settings
        app.state.providers = providers
        app.state.rates_service = rates_service
        app.state.search_cache = TtlCache(settings.search_cache_ttl_seconds, max_entries=64)
        app.state.exchange_rate_cache = ExchangeRateCache(settings.exchange_rate_cache_ttl_seconds)

        scheduler = AsyncIOScheduler()
        if settings.scheduler_enabled:
            scheduler.add_job(
                run_watch_check_job,
                trigger="interval",
                hours=settings.check_interval_hours,
                args=[settings.database_path, rates_service],
                id="watch_check",
                replace_existing=True,
                max_instances=1,
                coalesce=True,
            )
            scheduler.start()
        logger.info(
            "started: providers=%s, watch check every %sh (scheduler %s)",
            [p.name for p in providers],
            settings.check_interval_hours,
            "on" if settings.scheduler_enabled else "off",
        )
        try:
            yield
        finally:
            if scheduler.running:
                scheduler.shutdown(wait=False)
            await client.aclose()

    return lifespan


async def _validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
    """Return the first problem as one readable sentence instead of pydantic's error list."""
    errors = exc.errors()
    first = errors[0] if errors else {}
    field = ".".join(str(part) for part in first.get("loc", ())[1:])
    message = str(first.get("msg", "invalid request")).removeprefix("Value error, ")
    detail = f"{field}: {message}" if field and first.get("type") != "value_error" else message
    return JSONResponse(status_code=422, content={"detail": detail})


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()
    app = FastAPI(title="Hotel Price Watcher", version=__version__, lifespan=_lifespan(settings))
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.include_router(routes_meta.router)
    app.include_router(routes_search.router)
    app.include_router(routes_watches.router)
    return app
