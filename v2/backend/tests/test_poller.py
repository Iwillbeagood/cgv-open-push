"""Poller — 오케스트레이션. 가짜 4종 주입으로 기간 구독의 알림/자동종료를 검증."""
from cgv_push.cgv_client import FakeCgvClient
from cgv_push.domain import SubscriptionDraft
from cgv_push.notifier import RecordingNotifier
from cgv_push.poller import Poller
from cgv_push.store import InMemorySubscriptionStore


def make_poller(cgv):
    store = InMemorySubscriptionStore()
    notifier = RecordingNotifier()
    poller = Poller(cgv=cgv, store=store, notifier=notifier, clock=lambda: "2026-08-10T00:00:00")
    return poller, store, notifier


def draft(site="0013", mov="88", start="20260815", end="20260815"):
    return SubscriptionDraft(
        site_no=site, site_nm="용산아이파크몰", mov_no=mov, mov_nm="F1",
        start_date=start, end_date=end, slack_webhook_url="https://hooks.slack.com/x",
    )


def test_notifies_when_subscribed_date_opens():
    cgv = FakeCgvClient(open_dates={("0013", "88"): {"20260815"}})
    poller, store, notifier = make_poller(cgv)
    sub = store.add(draft(start="20260815", end="20260815"))

    poller.run_once()

    assert len(notifier.sent) == 1
    sent_sub, opened = notifier.sent[0]
    assert sent_sub.id == sub.id
    assert opened == {"20260815"}


def test_single_day_auto_completes_after_alert():
    cgv = FakeCgvClient(open_dates={("0013", "88"): {"20260815"}})
    poller, store, notifier = make_poller(cgv)
    store.add(draft(start="20260815", end="20260815"))

    poller.run_once()
    poller.run_once()  # 자동 종료되어 재알림 없어야 함

    assert len(notifier.sent) == 1
    assert store.list_active() == []


def test_range_stays_active_and_alerts_new_dates_incrementally():
    cgv = FakeCgvClient(open_dates={("0013", "88"): {"20260815"}})
    poller, store, notifier = make_poller(cgv)
    store.add(draft(start="20260815", end="20260820"))

    poller.run_once()                # 15일 오픈 -> 알림
    cgv.set_open_dates("0013", "88", {"20260815", "20260817"})
    poller.run_once()                # 17일 추가 오픈 -> 알림(15일은 재알림 안 함)

    assert [d for _, d in notifier.sent] == [{"20260815"}, {"20260817"}]
    assert len(store.list_active()) == 1  # 기간 구독은 수동 종료 전까지 활성


def test_manual_complete_stops_alerts():
    cgv = FakeCgvClient(open_dates={("0013", "88"): {"20260815"}})
    poller, store, notifier = make_poller(cgv)
    sub = store.add(draft(start="20260815", end="20260820"))

    store.complete(sub.id, "2026-08-10T00:00:00")
    poller.run_once()

    assert notifier.sent == []
    assert store.list_active() == []


def test_only_dates_within_range_are_alerted():
    cgv = FakeCgvClient(open_dates={("0013", "88"): {"20260815", "20260825"}})
    poller, store, notifier = make_poller(cgv)
    store.add(draft(start="20260815", end="20260820"))

    poller.run_once()

    assert notifier.sent[0][1] == {"20260815"}  # 25일은 범위 밖


def test_one_group_failure_does_not_stop_others():
    cgv = FakeCgvClient(open_dates={("0013", "88"): {"20260815"}})
    cgv.fail_keys.add(("0089", "99"))
    poller, store, notifier = make_poller(cgv)
    store.add(draft(site="0089", mov="99", start="20260815", end="20260815"))
    good = store.add(draft(site="0013", mov="88", start="20260815", end="20260815"))

    poller.run_once()

    assert len(notifier.sent) == 1
    assert notifier.sent[0][0].id == good.id
