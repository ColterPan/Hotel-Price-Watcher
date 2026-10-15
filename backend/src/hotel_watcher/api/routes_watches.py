"""Watches (hotels being tracked for one stay) and the in-app alert inbox."""

from __future__ import annotations

import sqlite3
from decimal import Decimal

from fastapi import APIRouter, Depends, HTTPException, Query, Response, status
from pydantic import BaseModel, ConfigDict

from hotel_watcher.api.deps import get_db, get_rates_service
from hotel_watcher.db import repository
from hotel_watcher.models.watch import Alert, PricePoint, Watch, WatchCreate
from hotel_watcher.search.rates import RatesService
from hotel_watcher.watch.jobs import CheckResult, check_watch

router = APIRouter(prefix="/api")

#: History points sent with each watch, enough for the sparkline.
SPARKLINE_POINTS = 60


class WatchView(Watch):
    lowest_price: Decimal | None
    history: tuple[PricePoint, ...]


class CheckResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    result: CheckResult
    watch: WatchView


class AlertsResponse(BaseModel):
    model_config = ConfigDict(frozen=True)

    alerts: tuple[Alert, ...]
    unread_count: int


def _view(conn: sqlite3.Connection, watch: Watch) -> WatchView:
    stay = watch.to_stay()
    return WatchView(
        **watch.model_dump(),
        lowest_price=repository.get_historical_min(conn, stay),
        history=tuple(repository.get_history(conn, stay, limit=SPARKLINE_POINTS)),
    )


def _require_watch(conn: sqlite3.Connection, watch_id: int) -> Watch:
    watch = repository.get_watch(conn, watch_id)
    if watch is None or not watch.active:
        raise HTTPException(status_code=404, detail="watch not found")
    return watch


@router.get("/watches")
def list_watches(conn: sqlite3.Connection = Depends(get_db)) -> list[WatchView]:
    return [_view(conn, watch) for watch in repository.list_active_watches(conn)]


@router.post("/watches", status_code=status.HTTP_201_CREATED)
async def create_watch(
    data: WatchCreate,
    conn: sqlite3.Connection = Depends(get_db),
    rates: RatesService = Depends(get_rates_service),
) -> CheckResponse:
    watch = repository.create_watch(conn, data)
    # Check straight away so the watch starts with a baseline price.
    result = await check_watch(conn, watch, rates)
    return CheckResponse(result=result, watch=_view(conn, _require_watch(conn, watch.id)))


@router.delete("/watches/{watch_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_watch(watch_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    if not repository.deactivate_watch(conn, watch_id):
        raise HTTPException(status_code=404, detail="watch not found")
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/watches/{watch_id}/check")
async def check_now(
    watch_id: int,
    conn: sqlite3.Connection = Depends(get_db),
    rates: RatesService = Depends(get_rates_service),
) -> CheckResponse:
    watch = _require_watch(conn, watch_id)
    result = await check_watch(conn, watch, rates)
    return CheckResponse(result=result, watch=_view(conn, _require_watch(conn, watch_id)))


@router.get("/alerts")
def list_alerts(
    unread_only: bool = Query(default=False),
    limit: int = Query(default=50, ge=1, le=200),
    conn: sqlite3.Connection = Depends(get_db),
) -> AlertsResponse:
    return AlertsResponse(
        alerts=tuple(repository.list_alerts(conn, unread_only=unread_only, limit=limit)),
        unread_count=repository.count_unread_alerts(conn),
    )


@router.post("/alerts/{alert_id}/read", status_code=status.HTTP_204_NO_CONTENT)
def mark_read(alert_id: int, conn: sqlite3.Connection = Depends(get_db)) -> Response:
    repository.mark_alert_read(conn, alert_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/alerts/read-all", status_code=status.HTTP_204_NO_CONTENT)
def mark_all_read(conn: sqlite3.Connection = Depends(get_db)) -> Response:
    repository.mark_all_alerts_read(conn)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
