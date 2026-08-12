"""Notifier 의 Slack Incoming Webhook 어댑터."""
from __future__ import annotations

from typing import Callable

from cgv_push.domain import Subscription

# post(url, json) 형태의 주입 가능한 HTTP 전송자. 기본은 requests.post.
Poster = Callable[[str, dict], object]


def _default_post(url: str, json: dict) -> object:
    import requests

    # 폐기/오류 webhook(4xx/5xx)을 예외로 올려 Poller가 notified 처리하지 않도록 한다.
    resp = requests.post(url, json=json, timeout=10)
    resp.raise_for_status()
    return resp


def _human_date(yyyymmdd: str) -> str:
    return f"{yyyymmdd[0:4]}-{yyyymmdd[4:6]}-{yyyymmdd[6:8]}"


class SlackWebhookNotifier:
    def __init__(self, post: Poster = _default_post) -> None:
        self._post = post

    def notify(self, subscription: Subscription, opened_dates: set[str]) -> None:
        dates = ", ".join(_human_date(d) for d in sorted(opened_dates))
        auditorium = f" {subscription.special_auditorium}" if subscription.special_auditorium else ""
        text = (
            f":clapper: *예매 오픈 알림*\n"
            f"*{subscription.site_nm}{auditorium}* — {subscription.mov_nm}\n"
            f"상영일: {dates}\n"
            f"지금 CGV에서 예매하세요!"
        )
        self._post(subscription.slack_webhook_url, {"text": text})

    def notify_subscribed(self, subscription: Subscription) -> None:
        auditorium = f" {subscription.special_auditorium}" if subscription.special_auditorium else ""
        if subscription.start_date == subscription.end_date:
            period = _human_date(subscription.start_date)
        else:
            period = f"{_human_date(subscription.start_date)} ~ {_human_date(subscription.end_date)}"
        text = (
            f":bell: *구독이 시작되었어요*\n"
            f"*{subscription.site_nm}{auditorium}* — {subscription.mov_nm}\n"
            f"상영일: {period}\n"
            f"예매가 열리는 순간 바로 알려드릴게요!"
        )
        self._post(subscription.slack_webhook_url, {"text": text})
