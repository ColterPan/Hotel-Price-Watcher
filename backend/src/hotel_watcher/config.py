"""Application configuration, loaded from environment variables or a .env file."""

from __future__ import annotations

from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # --- providers ---
    enabled_providers: str = "xotelo"

    #: Empty means the SerpApi provider reports `not_configured` instead of failing.
    serpapi_key: str = ""
    serpapi_monthly_budget: int = Field(default=200, ge=0)

    xotelo_base_url: str = "https://data.xotelo.com/api"
    xotelo_max_concurrency: int = Field(default=4, ge=1, le=10)
    xotelo_list_sort: Literal["best_value", "popularity", "distance"] = "best_value"

    # --- storage ---
    database_path: str = "data/hotels.db"

    # --- caching ---
    search_cache_ttl_seconds: float = Field(default=900.0, ge=0)
    rates_cache_ttl_seconds: float = Field(default=1800.0, ge=0)
    exchange_rate_cache_ttl_seconds: float = Field(default=3600.0, ge=0)

    # --- display ---
    #: Prices are stored in the provider's currency (USD). This only sets
    #: which currency the UI shows first.
    default_display_currency: str = "SGD"

    # --- watcher ---
    check_interval_hours: float = Field(default=6.0, gt=0)
    scheduler_enabled: bool = True

    # --- network / logging ---
    http_timeout_seconds: float = Field(default=20.0, gt=0)
    log_level: str = "INFO"

    @property
    def enabled_provider_list(self) -> list[str]:
        return [name.strip().lower() for name in self.enabled_providers.split(",") if name.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
