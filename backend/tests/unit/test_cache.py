from hotel_watcher.search.cache import TtlCache


class FakeClock:
    def __init__(self) -> None:
        self.now = 0.0

    def __call__(self) -> float:
        return self.now


async def test_get_returns_value_until_ttl_expires():
    clock = FakeClock()
    cache: TtlCache[str] = TtlCache(ttl_seconds=10, clock=clock)
    await cache.put("k", "v")
    clock.now = 9.9
    assert await cache.get("k") == "v"
    clock.now = 10.1
    assert await cache.get("k") is None


async def test_zero_ttl_disables_cache():
    cache: TtlCache[str] = TtlCache(ttl_seconds=0)
    await cache.put("k", "v")
    assert not cache.enabled
    assert await cache.get("k") is None


async def test_oldest_entry_is_evicted_when_full():
    clock = FakeClock()
    cache: TtlCache[int] = TtlCache(ttl_seconds=100, max_entries=2, clock=clock)
    await cache.put("a", 1)
    clock.now = 1
    await cache.put("b", 2)
    clock.now = 2
    await cache.put("c", 3)
    assert await cache.get("a") is None
    assert await cache.get("b") == 2
    assert await cache.get("c") == 3


async def test_invalidate():
    cache: TtlCache[int] = TtlCache(ttl_seconds=100)
    await cache.put("a", 1)
    await cache.invalidate("a")
    assert await cache.get("a") is None
