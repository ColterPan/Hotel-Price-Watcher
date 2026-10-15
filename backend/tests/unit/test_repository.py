from datetime import UTC, datetime, timedelta
from decimal import Decimal

from hotel_watcher.db import repository
from hotel_watcher.models.watch import WatchCreate
from tests.conftest import make_stay, offer

T0 = datetime(2026, 10, 1, 12, 0, tzinfo=UTC)


def _watch_data(stay=None, **overrides) -> WatchCreate:
    stay = stay or make_stay()
    return WatchCreate(
        hotel_key=stay.hotel_key,
        hotel_name=overrides.pop("hotel_name", "Pan Pacific Singapore"),
        check_in=stay.check_in,
        check_out=stay.check_out,
        adults=stay.adults,
        **overrides,
    )


def test_observation_dedup_within_window(conn):
    stay = make_stay()
    assert repository.record_observation(conn, stay, offer("300"), now=T0) is not None
    assert repository.record_observation(conn, stay, offer("300"), now=T0 + timedelta(minutes=5)) is None
    assert repository.record_observation(conn, stay, offer("290"), now=T0 + timedelta(minutes=6)) is not None
    assert repository.record_observation(conn, stay, offer("290"), now=T0 + timedelta(hours=2)) is not None


def test_watch_observations_are_never_deduplicated(conn):
    stay = make_stay()
    watch = repository.create_watch(conn, _watch_data(stay), now=T0)
    repository.record_observation(conn, stay, offer("300"), watch_id=watch.id, now=T0)
    assert repository.record_observation(conn, stay, offer("300"), watch_id=watch.id, now=T0) is not None


def test_historical_min_compares_numbers_not_text(conn):
    stay = make_stay()
    # As text, "1000" < "999". As numbers it is not.
    repository.record_observation(conn, stay, offer("999"), now=T0)
    repository.record_observation(conn, stay, offer("1000"), now=T0 + timedelta(hours=1))
    assert repository.get_historical_min(conn, stay) == Decimal("999")


def test_historical_min_is_scoped_to_the_exact_stay(conn):
    two_adults = make_stay(adults=2)
    one_adult = make_stay(adults=1)
    repository.record_observation(conn, one_adult, offer("50"), now=T0)
    assert repository.get_historical_min(conn, two_adults) is None


def test_history_is_oldest_first_and_limited(conn):
    stay = make_stay()
    for i in range(5):
        repository.record_observation(conn, stay, offer(str(300 - i)), now=T0 + timedelta(hours=i))
    history = repository.get_history(conn, stay, limit=3)
    assert [p.nightly for p in history] == [Decimal("298"), Decimal("297"), Decimal("296")]


def test_create_watch_then_readd_after_delete_reactivates(conn):
    data = _watch_data(target_price=Decimal("250"))
    watch = repository.create_watch(conn, data, now=T0)
    assert watch.active and watch.target_price == Decimal("250")

    assert repository.deactivate_watch(conn, watch.id)
    assert repository.list_active_watches(conn) == []
    assert not repository.deactivate_watch(conn, watch.id)

    again = repository.create_watch(conn, data.model_copy(update={"target_price": Decimal("200")}), now=T0)
    assert again.id == watch.id
    assert again.active
    assert again.target_price == Decimal("200")


def test_failed_check_keeps_last_known_price(conn):
    watch = repository.create_watch(conn, _watch_data(), now=T0)
    repository.update_watch_check_result(conn, watch.id, "ok", Decimal("300"), "Agoda", now=T0)
    repository.update_watch_check_result(conn, watch.id, "error", None, None, now=T0 + timedelta(hours=6))
    updated = repository.get_watch(conn, watch.id)
    assert updated is not None
    assert updated.last_status == "error"
    assert updated.last_price == Decimal("300")
    assert updated.last_site == "Agoda"
    assert updated.last_checked_at == T0 + timedelta(hours=6)


def test_alerts_inbox(conn):
    watch = repository.create_watch(conn, _watch_data(), now=T0)
    first = repository.create_alert(
        conn, watch.id, "new_low", Decimal("280"), Decimal("300"), "USD", "Agoda", "m1", T0
    )
    repository.create_alert(
        conn, watch.id, "target_hit", Decimal("250"), Decimal("280"), "USD", None, "m2", T0
    )

    assert repository.count_unread_alerts(conn) == 2
    alerts = repository.list_alerts(conn)
    assert [a.message for a in alerts] == ["m2", "m1"]
    assert alerts[0].hotel_name == "Pan Pacific Singapore"

    assert repository.mark_alert_read(conn, first)
    assert not repository.mark_alert_read(conn, first)
    assert [a.message for a in repository.list_alerts(conn, unread_only=True)] == ["m2"]
    assert repository.mark_all_alerts_read(conn) == 1
    assert repository.count_unread_alerts(conn) == 0


def test_usage_budget_stops_at_limit_and_resets_monthly(conn):
    assert repository.try_consume_usage(conn, "serpapi", 2, now=T0)
    assert repository.try_consume_usage(conn, "serpapi", 2, now=T0)
    assert not repository.try_consume_usage(conn, "serpapi", 2, now=T0)
    assert repository.get_usage(conn, "serpapi", now=T0) == 2

    next_month = T0 + timedelta(days=31)
    assert repository.try_consume_usage(conn, "serpapi", 2, now=next_month)
    assert repository.get_usage(conn, "serpapi", now=next_month) == 1


def test_zero_budget_never_allows_calls(conn):
    assert not repository.try_consume_usage(conn, "serpapi", 0, now=T0)
