"""포트 — 각 seam의 인터페이스(Protocol). 구현(adapter)은 별도 모듈."""
from __future__ import annotations

from typing import Protocol

from cgv_push.domain import Movie, Site, Subscription, SubscriptionDraft


class CgvClient(Protocol):
    """유일한 외부 의존성 seam. CGV 신규 API 접근을 전부 숨긴다."""

    def list_sites(self) -> list[Site]:
        """특별관을 보유한 극장 목록."""
        ...

    def list_movies(self, site_no: str) -> list[Movie]:
        """해당 극장에서 선택 가능한 영화 목록."""
        ...

    def list_open_dates(self, site_no: str, mov_no: str) -> set[str]:
        """해당 극장·영화에 현재 예매 오픈된 상영일(YYYYMMDD) 집합."""
        ...


class SubscriptionStore(Protocol):
    """구독 저장 seam."""

    def add(self, draft: SubscriptionDraft) -> Subscription: ...
    def list_all(self) -> list[Subscription]: ...
    def list_active(self) -> list[Subscription]:
        """아직 종료되지 않은(completed_at is None) 구독."""
        ...
    def remove(self, subscription_id: str) -> None: ...
    def record_alerted(self, subscription_id: str, dates: set[str]) -> None:
        """이 구독에 대해 알림 보낸 상영일들을 누적 기록한다."""
        ...
    def complete(self, subscription_id: str, when: str) -> None:
        """구독을 종료 상태로 만든다(자동/수동 공통)."""
        ...


class Notifier(Protocol):
    """알림 전송 seam (Slack)."""

    def notify(self, subscription: Subscription, opened_dates: set[str]) -> None: ...

    def notify_subscribed(self, subscription: Subscription) -> None:
        """구독이 새로 등록됐을 때 '구독 시작' 안내를 보낸다."""
        ...
