"""SubscriptionStore 계약 테스트 — 인메모리와 SQLite 두 어댑터에 동일 적용."""
import pytest

from cgv_push.domain import SubscriptionDraft
from cgv_push.sqlite_store import SqliteSubscriptionStore
from cgv_push.store import InMemorySubscriptionStore


@pytest.fixture(params=["memory", "sqlite"])
def store(request, tmp_path):
    if request.param == "memory":
        return InMemorySubscriptionStore()
    return SqliteSubscriptionStore(str(tmp_path / "subs.db"))


def draft(start="20260815", end="20260818", alerted=frozenset()):
    return SubscriptionDraft(
        site_no="0013", site_nm="용산아이파크몰", mov_no="88", mov_nm="F1",
        start_date=start, end_date=end, slack_webhook_url="https://hooks.slack.com/x",
        special_auditorium="IMAX", alerted_dates=alerted,
    )


def test_add_assigns_id_and_is_listed(store):
    sub = store.add(draft())
    assert sub.id
    assert [s.id for s in store.list_all()] == [sub.id]
    got = store.list_all()[0]
    assert (got.start_date, got.end_date) == ("20260815", "20260818")


def test_added_subscription_is_active(store):
    sub = store.add(draft())
    assert [s.id for s in store.list_active()] == [sub.id]


def test_seeded_alerted_dates_roundtrip(store):
    store.add(draft(alerted=frozenset({"20260815", "20260816"})))
    assert store.list_all()[0].alerted_dates == frozenset({"20260815", "20260816"})


def test_record_alerted_accumulates(store):
    sub = store.add(draft(alerted=frozenset({"20260815"})))
    store.record_alerted(sub.id, {"20260816", "20260817"})
    assert store.list_all()[0].alerted_dates == frozenset({"20260815", "20260816", "20260817"})


def test_complete_removes_from_active(store):
    sub = store.add(draft())
    store.complete(sub.id, "2026-08-10T00:00:00")
    assert store.list_active() == []
    assert store.list_all()[0].completed_at == "2026-08-10T00:00:00"


def test_remove_deletes(store):
    sub = store.add(draft())
    store.remove(sub.id)
    assert store.list_all() == []


def test_fields_roundtrip(store):
    store.add(draft())
    got = store.list_all()[0]
    assert (got.site_no, got.site_nm, got.mov_no, got.mov_nm, got.special_auditorium) == \
           ("0013", "용산아이파크몰", "88", "F1", "IMAX")
