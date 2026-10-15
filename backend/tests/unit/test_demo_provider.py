from hotel_watcher.providers.demo import DRIFT_PERIOD_SECONDS, DemoProvider
from tests.conftest import make_search, make_stay


async def test_search_is_deterministic_and_centered_on_the_city():
    provider = DemoProvider(clock=lambda: 0)
    first = await provider.search(make_search(limit=10))
    second = await provider.search(make_search(limit=10))

    assert first.status == "ok"
    assert first.hotels == second.hotels
    assert len(first.hotels) == 10
    assert all(abs(h.latitude - 1.29) < 0.1 for h in first.hotels)
    assert all(h.rates_key and h.rates_key.startswith("demo-g294265-") for h in first.hotels)


async def test_demo_hotels_carry_two_sample_rating_sources():
    outcome = await DemoProvider().search(make_search(limit=5))
    sources = {r.source for r in outcome.hotels[0].ratings}
    assert sources == {"demo_a", "demo_b"}


async def test_rates_drift_over_time_but_are_stable_within_a_period():
    now = [1_000_000.0]
    provider = DemoProvider(clock=lambda: now[0])
    stay = make_stay("demo-g294265-03")

    a = await provider.rates(stay)
    now[0] += 1
    b = await provider.rates(stay)
    prices_seen = {a.cheapest.nightly if a.cheapest else None}
    for step in range(1, 6):
        now[0] += DRIFT_PERIOD_SECONDS * step
        outcome = await provider.rates(stay)
        prices_seen.add(outcome.cheapest.nightly if outcome.cheapest else None)

    assert a.status == "ok"
    assert a.offers == b.offers
    assert len(prices_seen) > 1
    assert list(a.offers) == sorted(a.offers, key=lambda o: o.nightly)


async def test_rates_for_malformed_demo_key_is_no_results():
    stay = make_stay("demo-g294265-07").model_copy(update={"hotel_key": "demo-x"})
    outcome = await DemoProvider().rates(stay)
    assert outcome.status == "no_results"


def test_handles_only_demo_keys():
    provider = DemoProvider()
    assert provider.handles_rates_for("demo-g294265-01")
    assert not provider.handles_rates_for("g294265-d302294")


async def test_heatmap_buckets_cover_35_days():
    stay = make_stay("demo-g294265-01")
    heatmap = await DemoProvider().heatmap(stay.hotel_key, stay.check_out)
    assert heatmap is not None
    assert len(heatmap.cheap) + len(heatmap.average) + len(heatmap.high) == 35
