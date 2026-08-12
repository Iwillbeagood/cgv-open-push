"""Web API (FastAPI) — CgvClient·SubscriptionStore 위의 얇은 변환층.
로직은 두지 않는다. create_app 으로 의존성을 주입해 테스트한다.
"""
from __future__ import annotations

from datetime import datetime, timezone

from fastapi import FastAPI, HTTPException, Response
from pydantic import BaseModel

import logging

from cgv_push.domain import SubscriptionDraft
from cgv_push.ports import CgvClient, Notifier, SubscriptionStore

logger = logging.getLogger(__name__)


class SubscriptionIn(BaseModel):
    siteNo: str
    siteNm: str
    movNo: str
    movNm: str
    startDate: str
    endDate: str
    slackWebhookUrl: str
    specialAuditorium: str | None = None


def _sub_out(sub) -> dict:
    return {
        "id": sub.id,
        "siteNo": sub.site_no,
        "siteNm": sub.site_nm,
        "movNo": sub.mov_no,
        "movNm": sub.mov_nm,
        "startDate": sub.start_date,
        "endDate": sub.end_date,
        "isSingleDay": sub.is_single_day,
        "specialAuditorium": sub.special_auditorium,
        "alertedDates": sorted(sub.alerted_dates),
        "completedAt": sub.completed_at,
    }


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def create_app(cgv: CgvClient, store: SubscriptionStore, notifier: Notifier | None = None) -> FastAPI:
    app = FastAPI(title="CGV 예매 오픈 알리미")

    @app.get("/api/sites")
    def list_sites() -> list[dict]:
        return [
            {"siteNo": s.site_no, "siteNm": s.site_nm,
             "specialAuditoriums": list(s.special_auditoriums)}
            for s in cgv.list_sites()
        ]

    @app.get("/api/regions")
    def list_regions() -> list[dict]:
        """CGV 실제 UI처럼 지역별로 묶은 특별관 극장 목록."""
        groups: dict[str, dict] = {}
        for s in cgv.list_sites():
            key = s.region_code or "_"
            grp = groups.setdefault(
                key, {"code": s.region_code, "name": s.region_name or "기타", "sites": []}
            )
            grp["sites"].append({
                "siteNo": s.site_no, "siteNm": s.site_nm,
                "specialAuditoriums": list(s.special_auditoriums),
            })
        return list(groups.values())

    @app.get("/api/sites/{site_no}/movies")
    def list_movies(site_no: str) -> list[dict]:
        return [
            {"movNo": m.mov_no, "movNm": m.mov_nm, "posterUrl": m.poster_url}
            for m in cgv.list_movies(site_no)
        ]

    @app.get("/api/sites/{site_no}/movies/{mov_no}/open-dates")
    def list_open_dates(site_no: str, mov_no: str) -> list[str]:
        return sorted(cgv.list_open_dates(site_no, mov_no))

    @app.post("/api/subscriptions", status_code=201)
    def create_subscription(body: SubscriptionIn) -> dict:
        if body.startDate > body.endDate:
            raise HTTPException(400, "시작일이 종료일보다 늦습니다.")
        # 현재 이미 열린 상영일을 파악: 범위 내 오픈일은 알림 대상에서 제외(시드),
        # 단일 날짜가 이미 열려 있으면 구독 자체를 거부한다.
        open_in_range = {
            d for d in cgv.list_open_dates(body.siteNo, body.movNo)
            if body.startDate <= d <= body.endDate
        }
        if body.startDate == body.endDate and body.startDate in open_in_range:
            raise HTTPException(409, "이미 예매가 열려 있어 구독할 수 없습니다.")
        draft = SubscriptionDraft(
            site_no=body.siteNo, site_nm=body.siteNm,
            mov_no=body.movNo, mov_nm=body.movNm,
            start_date=body.startDate, end_date=body.endDate,
            slack_webhook_url=body.slackWebhookUrl,
            special_auditorium=body.specialAuditorium,
            alerted_dates=frozenset(open_in_range),
        )
        sub = store.add(draft)
        # 구독 시작 안내(best-effort): 웹훅 오류가 구독 등록을 막지 않도록 격리.
        if notifier is not None:
            try:
                notifier.notify_subscribed(sub)
            except Exception:
                logger.warning("구독 시작 알림 전송 실패 (sub_id=%s)", sub.id, exc_info=True)
        return _sub_out(sub)

    @app.get("/api/subscriptions")
    def list_subscriptions() -> list[dict]:
        return [_sub_out(s) for s in store.list_all()]

    @app.post("/api/subscriptions/{subscription_id}/complete", status_code=200)
    def complete_subscription(subscription_id: str) -> dict:
        """예매 완료 — 구독을 수동 종료한다(기간 구독용)."""
        store.complete(subscription_id, _now())
        return {"ok": True}

    @app.delete("/api/subscriptions/{subscription_id}", status_code=204)
    def delete_subscription(subscription_id: str) -> Response:
        store.remove(subscription_id)
        return Response(status_code=204)

    return app
