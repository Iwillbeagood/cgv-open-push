"""도메인 타입. 용어는 CONTEXT.md를 따른다."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional


@dataclass(frozen=True)
class Site:
    """극장 — 특별관을 보유한 CGV 지점."""
    site_no: str
    site_nm: str
    special_auditoriums: tuple[str, ...]  # 예: ("IMAX", "4DX", "SCREENX")
    region_code: str = ""   # 지역 코드(regnGrpCd)
    region_name: str = ""   # 지역명(예: 서울)


@dataclass(frozen=True)
class Movie:
    """영화 — 한 극장에서 선택 가능한 작품."""
    mov_no: str
    mov_nm: str
    poster_url: str | None = None


@dataclass
class Subscription:
    """구독 — 극장 + 영화 + 상영일 '기간'의 알림 조건.

    기간은 start_date~end_date(포함). 단일 날짜는 start==end.
    alerted_dates: 이미 알림 보낸 상영일들(중복 알림 방지 + 생성 시 이미 열린 날짜 시드).
    completed_at: 구독 종료 시각. None이면 활성. 단일 날짜는 그 날이 알림되면 자동 종료,
                  기간은 사용자가 '예매 완료'로 수동 종료.
    """
    id: str
    site_no: str
    site_nm: str
    mov_no: str
    mov_nm: str
    start_date: str  # YYYYMMDD
    end_date: str    # YYYYMMDD
    slack_webhook_url: str
    special_auditorium: Optional[str] = None
    alerted_dates: frozenset[str] = frozenset()
    completed_at: Optional[str] = None
    created_at: Optional[str] = None

    @property
    def is_single_day(self) -> bool:
        return self.start_date == self.end_date


@dataclass
class SubscriptionDraft:
    """아직 저장되지 않은 구독 입력."""
    site_no: str
    site_nm: str
    mov_no: str
    mov_nm: str
    start_date: str
    end_date: str
    slack_webhook_url: str
    special_auditorium: Optional[str] = None
    alerted_dates: frozenset[str] = frozenset()  # 생성 시 이미 열린 날짜로 시드
