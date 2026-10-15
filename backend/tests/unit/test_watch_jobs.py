from datetime import UTC, datetime, timedelta
from decimal import Decimal

from hotel_watcher.db import repository
from hotel_watcher.db.database import connect
from hotel_watcher.models.hotel import Offer, RatesOutcome
from hotel_watcher.models.watch import WatchCreate
from hotel_watcher.watch.jobs import check_watch, run_watch_check_job
from tests.conftest import make_stay


class ScriptedRates:
    """Returns a scripted sequence of nightly prices (None means a failed check)."""

    def __init__(self, prices: list[str | None]) -> None:
        self._prices = list(prices)
        self.calls: list[bool] = []

    async def rates(self, stay, use_cache=True):
        self.calls.append(use_cache)
        price = self._prices.pop(0)
        if price is None:
            return RatesOutcome(provider="xotelo", status="error"), False
        offers = (Offer(site="Agoda", nightly=Decimal(price), currency="USD"),)
        return RatesOutcome(provider="xotelo", status="ok", offers=offers), False


def _create(conn, target: str | None = None, hotel_key: str = "g294265-d302294"):
    stay = make_stay(hotel_key)
    data = WatchCreate(
        hotel_key=stay.hotel_key,
        hotel_name="Pan Pacific Singapore",
        check_in=stay.check_in,
        check_out=stay.check_out,
        adults=stay.adults,
        target_price=Decimal(target) if target else None,
    )
    return repository.create_watch(conn, data)


async def test_first_check_sets_baseline_without_alert(conn):
    watch = _create(conn)
    result = await check_watch(conn, watch, ScriptedRates(["300"]))

    assert result.status == "ok"
    assert result.price == Decimal("300")
    assert result.alert_kind is None
    assert repository.get_watch(conn, watch.id).last_price == Decimal("300")


async def test_price_drop_creates_new_low_alert(conn):
    watch = _create(conn)
    rates = ScriptedRates(["300", "280", "290"])
    await check_watch(conn, watch, rates)
    dropped = await check_watch(conn, watch, rates)
    rebound = await check_watch(conn, watch, rates)

    assert dropped.alert_kind == "new_low"
    assert rebound.alert_kind is None
    (alert,) = repository.list_alerts(conn)
    assert alert.price == Decimal("280")
    assert alert.previous_low == Decimal("300")
    assert "Agoda" in alert.message
    # Watch checks always ask for a fresh price.
    assert rates.calls == [False, False, False]


async def test_target_hit_on_first_check(conn):
    watch = _create(conn, target="350")
    result = await check_watch(conn, watch, ScriptedRates(["300"]))
    assert result.alert_kind == "target_hit"


async def test_target_met_on_first_check_alerts_even_after_browsing(conn):
    watch = _create(conn, target="350")
    # The user looked at this hotel before watching it, so 300 is already in history.
    repository.record_observation(
        conn, watch.to_stay(), Offer(site="A", nightly=Decimal("300"), currency="USD")
    )
    result = await check_watch(conn, watch, ScriptedRates(["300"]))
    assert result.alert_kind == "target_hit"


async def test_failed_check_records_status_and_keeps_price(conn):
    watch = _create(conn)
    rates = ScriptedRates(["300", None])
    await check_watch(conn, watch, rates)
    result = await check_watch(conn, watch, rates)

    assert result.status == "error"
    stored = repository.get_watch(conn, watch.id)
    assert stored.last_status == "error"
    assert stored.last_price == Decimal("300")


async def test_failed_first_check_does_not_use_up_the_first_check(conn):
    watch = _create(conn, target="350")
    rates = ScriptedRates([None, "300"])
    await check_watch(conn, watch, rates)
    result = await check_watch(conn, repository.get_watch(conn, watch.id), rates)
    assert result.alert_kind == "target_hit"


async def test_stay_in_the_past_is_not_checked(conn):
    watch = _create(conn)
    rates = ScriptedRates([])
    later = datetime.combine(watch.check_in + timedelta(days=1), datetime.min.time(), tzinfo=UTC)
    result = await check_watch(conn, watch, rates, now=later)
    assert result.status == "stay_passed"
    assert rates.calls == []


async def test_job_checks_every_watch_and_survives_a_crash(tmp_path):
    db_path = str(tmp_path / "jobs.db")
    setup = connect(db_path)
    first = _create(setup, hotel_key="g294265-d11")
    second = _create(setup, hotel_key="g294265-d22")
    setup.close()

    class FlakyRates:
        async def rates(self, stay, use_cache=True):
            if stay.hotel_key == first.hotel_key:
                raise RuntimeError("provider bug")
            return RatesOutcome(
                provider="xotelo",
                status="ok",
                offers=(Offer(site="A", nightly=Decimal("99"), currency="USD"),),
            ), False

    results = await run_watch_check_job(db_path, FlakyRates())

    by_id = {r.watch_id: r.status for r in results}
    assert by_id == {first.id: "error", second.id: "ok"}
    check = connect(db_path)
    assert repository.get_watch(check, first.id).last_status == "error"
    check.close()
