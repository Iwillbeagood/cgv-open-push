"""SubscriptionStore 어댑터. (SQLite 실제 구현은 sqlite_store.py)"""
from __future__ import annotations

import itertools
from datetime import datetime, timezone

from cgv_push.domain import Subscription, SubscriptionDraft


class InMemorySubscriptionStore:
    """인메모리 구독 저장소 — 테스트 및 개발용."""

    def __init__(self) -> None:
        self._items: dict[str, Subscription] = {}
        self._ids = itertools.count(1)

    def add(self, draft: SubscriptionDraft) -> Subscription:
        sub_id = str(next(self._ids))
        sub = Subscription(
            id=sub_id,
            site_no=draft.site_no,
            site_nm=draft.site_nm,
            mov_no=draft.mov_no,
            mov_nm=draft.mov_nm,
            start_date=draft.start_date,
            end_date=draft.end_date,
            slack_webhook_url=draft.slack_webhook_url,
            special_auditorium=draft.special_auditorium,
            alerted_dates=frozenset(draft.alerted_dates),
            created_at=datetime.now(timezone.utc).isoformat(),
        )
        self._items[sub_id] = sub
        return sub

    def list_all(self) -> list[Subscription]:
        return list(self._items.values())

    def list_active(self) -> list[Subscription]:
        return [s for s in self._items.values() if s.completed_at is None]

    def remove(self, subscription_id: str) -> None:
        self._items.pop(subscription_id, None)

    def record_alerted(self, subscription_id: str, dates: set[str]) -> None:
        sub = self._items.get(subscription_id)
        if sub is not None:
            sub.alerted_dates = sub.alerted_dates | frozenset(dates)

    def complete(self, subscription_id: str, when: str) -> None:
        sub = self._items.get(subscription_id)
        if sub is not None:
            sub.completed_at = when
