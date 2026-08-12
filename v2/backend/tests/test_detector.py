"""오픈 감지의 순수 로직. 외부 행동만 테스트한다 (mock 불필요).

구독은 [start_date, end_date] 기간을 지목하므로, 규칙은
'그 기간 안에서 지금 오픈되었고 아직 알리지 않은 상영일들'이다.
"""
from cgv_push.detector import due_dates
from cgv_push.domain import Subscription


def _sub(start="20260815", end="20260815", alerted=frozenset(), completed=None):
    return Subscription(
        id="1", site_no="0013", site_nm="용산아이파크몰",
        mov_no="88", mov_nm="F1", start_date=start, end_date=end,
        slack_webhook_url="https://hooks.slack.com/x",
        alerted_dates=alerted, completed_at=completed,
    )


def test_single_day_open_and_unalerted_is_due():
    assert due_dates(_sub("20260815", "20260815"), {"20260815", "20260816"}) == {"20260815"}


def test_date_outside_range_is_not_due():
    assert due_dates(_sub("20260815", "20260817"), {"20260820"}) == set()


def test_range_returns_all_open_dates_within():
    got = due_dates(_sub("20260815", "20260818"), {"20260815", "20260817", "20260820"})
    assert got == {"20260815", "20260817"}


def test_already_alerted_dates_are_excluded():
    got = due_dates(_sub("20260815", "20260818", alerted=frozenset({"20260815"})),
                    {"20260815", "20260816"})
    assert got == {"20260816"}


def test_completed_subscription_is_never_due():
    assert due_dates(_sub("20260815", "20260818", completed="2026-08-10T00:00:00"),
                     {"20260815", "20260816"}) == set()


def test_no_open_dates_is_not_due():
    assert due_dates(_sub("20260815", "20260818"), set()) == set()
