"""Poller — 오케스트레이션. 의존성을 주입받아(생성하지 않음) 주기적으로
활성 구독의 대상 상영일이 오픈되었는지 확인하고 알림을 보낸다.
"""
from __future__ import annotations

import logging
from collections import defaultdict
from typing import Callable

from cgv_push.detector import due_dates
from cgv_push.ports import CgvClient, Notifier, SubscriptionStore

logger = logging.getLogger(__name__)


class Poller:
    def __init__(
        self,
        cgv: CgvClient,
        store: SubscriptionStore,
        notifier: Notifier,
        clock: Callable[[], str],
    ) -> None:
        self._cgv = cgv
        self._store = store
        self._notifier = notifier
        self._now = clock

    def run_once(self) -> None:
        """활성 구독 한 바퀴. 극장·영화로 묶어 CGV 호출을 최소화한다.
        한 그룹의 실패가 전체를 죽이지 않도록 그룹 단위로 예외를 격리한다."""
        active = self._store.list_active()
        groups: dict[tuple[str, str], list] = defaultdict(list)
        for sub in active:
            groups[(sub.site_no, sub.mov_no)].append(sub)

        for (site_no, mov_no), subs in groups.items():
            try:
                open_dates = self._cgv.list_open_dates(site_no, mov_no)
            except Exception:
                logger.exception("CGV 오픈 상영일 조회 실패: site=%s mov=%s", site_no, mov_no)
                continue

            for sub in subs:
                due = due_dates(sub, open_dates)
                if not due:
                    continue
                try:
                    self._notifier.notify(sub, due)
                except Exception:
                    logger.exception("알림 전송 실패: subscription=%s", sub.id)
                    continue
                self._store.record_alerted(sub.id, due)
                # 단일 날짜 구독은 그 날이 알림되면 자동 종료. 기간 구독은 수동 종료.
                if sub.is_single_day:
                    self._store.complete(sub.id, self._now())
