"""A small in-memory TTL cache.

Single user, single process: a dict behind a lock is the right size. Nothing
is persisted, which is correct because hotel prices go stale.
"""

from __future__ import annotations

import asyncio
import time
from collections.abc import Callable, Hashable
from typing import Generic, TypeVar

V = TypeVar("V")

#: Upper bound on entries so a long session cannot grow without limit.
DEFAULT_MAX_ENTRIES = 512


class TtlCache(Generic[V]):
    def __init__(
        self,
        ttl_seconds: float,
        max_entries: int = DEFAULT_MAX_ENTRIES,
        clock: Callable[[], float] = time.monotonic,
    ) -> None:
        self._ttl = ttl_seconds
        self._max_entries = max_entries
        self._clock = clock
        self._entries: dict[Hashable, tuple[float, V]] = {}
        self._lock = asyncio.Lock()

    @property
    def enabled(self) -> bool:
        return self._ttl > 0

    async def get(self, key: Hashable) -> V | None:
        if not self.enabled:
            return None
        async with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                return None
            stored_at, value = entry
            if self._clock() - stored_at > self._ttl:
                del self._entries[key]
                return None
            return value

    async def put(self, key: Hashable, value: V) -> None:
        if not self.enabled:
            return
        async with self._lock:
            if key not in self._entries and len(self._entries) >= self._max_entries:
                oldest = min(self._entries, key=lambda k: self._entries[k][0])
                del self._entries[oldest]
            self._entries[key] = (self._clock(), value)

    async def invalidate(self, key: Hashable) -> None:
        async with self._lock:
            self._entries.pop(key, None)
