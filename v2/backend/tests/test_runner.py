"""PollerLoop — 백그라운드 폴링 루프. seam: run_once 호출과 정지 동작."""
from cgv_push.runner import PollerLoop


def test_loop_calls_run_once_then_stops_on_signal():
    calls = []
    holder = {}

    class OneShotPoller:
        def run_once(self):
            calls.append(1)
            holder["loop"]._stop.set()  # 첫 실행 후 정지 신호

    loop = PollerLoop(OneShotPoller(), interval_seconds=0)
    holder["loop"] = loop
    loop.start()
    loop._thread.join(timeout=2)

    assert calls == [1]
    assert not loop._thread.is_alive()


def test_run_once_exception_does_not_kill_loop():
    calls = []
    holder = {}

    class FlakyPoller:
        def run_once(self):
            calls.append(1)
            if len(calls) == 1:
                raise RuntimeError("일시 오류")
            holder["loop"]._stop.set()  # 두 번째 실행에서 정지

    loop = PollerLoop(FlakyPoller(), interval_seconds=0)
    holder["loop"] = loop
    loop.start()
    loop._thread.join(timeout=2)

    assert len(calls) >= 2  # 예외가 난 뒤에도 루프가 계속 돎
    assert not loop._thread.is_alive()
