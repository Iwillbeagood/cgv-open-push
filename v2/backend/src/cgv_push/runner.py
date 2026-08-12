"""PollerLoop — Poller.run_once 를 주기적으로 도는 백그라운드 스레드.
sleep/interval 을 주입받아 테스트 가능하게 한다."""
from __future__ import annotations

import logging
import threading

from cgv_push.poller import Poller

logger = logging.getLogger(__name__)


class PollerLoop:
    def __init__(self, poller: Poller, interval_seconds: float) -> None:
        self._poller = poller
        self._interval = interval_seconds
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None

    def _run(self) -> None:
        while not self._stop.is_set():
            try:
                self._poller.run_once()
            except Exception:
                logger.exception("폴링 루프 예외 — 계속 진행")
            self._stop.wait(self._interval)

    def start(self) -> None:
        self._thread = threading.Thread(target=self._run, name="cgv-poller", daemon=True)
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=10)
