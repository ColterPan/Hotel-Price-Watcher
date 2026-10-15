"""Turns ENABLED_PROVIDERS into provider instances."""

from __future__ import annotations

import httpx

from hotel_watcher.config import Settings
from hotel_watcher.db import repository
from hotel_watcher.db.database import connect
from hotel_watcher.providers.base import HotelProvider
from hotel_watcher.providers.demo import DemoProvider
from hotel_watcher.providers.serpapi_hotels import SerpApiHotelsProvider
from hotel_watcher.providers.xotelo import XoteloProvider

KNOWN_PROVIDERS: tuple[str, ...] = ("xotelo", "serpapi", "demo")


class SqliteUsageBudget:
    """Monthly call budget stored in SQLite, so it survives restarts."""

    def __init__(self, database_path: str, monthly_limit: int) -> None:
        self._database_path = database_path
        self._monthly_limit = monthly_limit

    def try_consume(self, provider: str) -> bool:
        conn = connect(self._database_path)
        try:
            return repository.try_consume_usage(conn, provider, self._monthly_limit)
        finally:
            conn.close()


def build_providers(settings: Settings, client: httpx.AsyncClient) -> list[HotelProvider]:
    providers: list[HotelProvider] = []
    for name in settings.enabled_provider_list:
        if name == "xotelo":
            providers.append(
                XoteloProvider(
                    client,
                    base_url=settings.xotelo_base_url,
                    max_concurrency=settings.xotelo_max_concurrency,
                    list_sort=settings.xotelo_list_sort,
                )
            )
        elif name == "serpapi":
            budget = SqliteUsageBudget(settings.database_path, settings.serpapi_monthly_budget)
            providers.append(SerpApiHotelsProvider(client, settings.serpapi_key, budget))
        elif name == "demo":
            providers.append(DemoProvider())
        else:
            raise ValueError(f"Unknown provider {name!r}. Known providers: {', '.join(KNOWN_PROVIDERS)}")
    if not providers:
        raise ValueError("ENABLED_PROVIDERS is empty. Enable at least one of: " + ", ".join(KNOWN_PROVIDERS))
    return providers
