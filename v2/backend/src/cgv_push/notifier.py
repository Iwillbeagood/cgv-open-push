"""Notifier 어댑터. (실제 Slack 구현은 slack_notifier.py)"""
from __future__ import annotations

from cgv_push.domain import Subscription


class RecordingNotifier:
    """전송을 실제로 하지 않고 기록만 하는 Notifier — 테스트용."""

    def __init__(self) -> None:
        self.sent: list[tuple[Subscription, set[str]]] = []
        self.subscribed: list[Subscription] = []

    def notify(self, subscription: Subscription, opened_dates: set[str]) -> None:
        self.sent.append((subscription, set(opened_dates)))

    def notify_subscribed(self, subscription: Subscription) -> None:
        self.subscribed.append(subscription)
