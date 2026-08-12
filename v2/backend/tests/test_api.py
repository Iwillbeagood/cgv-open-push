"""Web API — FastAPI. seam: HTTP 인터페이스. FakeCgvClient + 인메모리 저장소 주입.
"""
import pytest
from fastapi.testclient import TestClient

from cgv_push.api import create_app
from cgv_push.cgv_client import FakeCgvClient
from cgv_push.domain import Movie, Site
from cgv_push.notifier import RecordingNotifier
from cgv_push.store import InMemorySubscriptionStore


@pytest.fixture
def notifier():
    return RecordingNotifier()


@pytest.fixture
def client(notifier):
    cgv = FakeCgvClient(
        sites=[
            Site("0013", "용산아이파크몰", ("IMAX", "4DX", "SCREENX"),
                 region_code="01", region_name="서울"),
            Site("0089", "센텀시티", ("IMAX",), region_code="06", region_name="부산/대구/경상"),
        ],
        movies={"0013": [Movie("88", "F1", "https://cdn.cgv.co.kr/x/88_320.jpg")]},
        open_dates={("0013", "88"): {"20260815", "20260816"}},
    )
    store = InMemorySubscriptionStore()
    app = create_app(cgv=cgv, store=store, notifier=notifier)
    return TestClient(app)


def test_list_sites(client):
    r = client.get("/api/sites")
    assert r.status_code == 200
    assert {"siteNo": "0013", "siteNm": "용산아이파크몰",
            "specialAuditoriums": ["IMAX", "4DX", "SCREENX"]} in r.json()


def test_list_regions_groups_sites_by_region(client):
    r = client.get("/api/regions")
    assert r.status_code == 200
    regions = {g["name"]: g for g in r.json()}
    assert set(regions) == {"서울", "부산/대구/경상"}
    seoul = regions["서울"]
    assert [s["siteNo"] for s in seoul["sites"]] == ["0013"]
    assert seoul["sites"][0]["specialAuditoriums"] == ["IMAX", "4DX", "SCREENX"]


def test_list_movies(client):
    r = client.get("/api/sites/0013/movies")
    assert r.status_code == 200
    assert r.json() == [
        {"movNo": "88", "movNm": "F1", "posterUrl": "https://cdn.cgv.co.kr/x/88_320.jpg"}
    ]


def test_list_open_dates(client):
    r = client.get("/api/sites/0013/movies/88/open-dates")
    assert r.status_code == 200
    assert sorted(r.json()) == ["20260815", "20260816"]


def _payload(start="20260820", end="20260820"):
    return {
        "siteNo": "0013", "siteNm": "용산아이파크몰",
        "movNo": "88", "movNm": "F1", "startDate": start, "endDate": end,
        "slackWebhookUrl": "https://hooks.slack.com/x", "specialAuditorium": "IMAX",
    }


def test_create_range_subscription(client):
    # 오픈일은 08-15,08-16. 08-20~08-22 는 아직 안 열림 -> 생성 성공
    r = client.post("/api/subscriptions", json=_payload("20260820", "20260822"))
    assert r.status_code == 201
    created = r.json()
    assert created["startDate"] == "20260820" and created["endDate"] == "20260822"
    assert created["isSingleDay"] is False
    assert client.get("/api/subscriptions").json()[0]["id"] == created["id"]


def test_create_seeds_already_open_dates_in_range(client):
    # 08-15~08-18: 08-15,08-16 은 이미 열림 -> alertedDates 로 시드되어 재알림 방지
    r = client.post("/api/subscriptions", json=_payload("20260815", "20260818"))
    assert r.status_code == 201
    assert set(r.json()["alertedDates"]) == {"20260815", "20260816"}


def test_reject_single_day_already_open(client):
    r = client.post("/api/subscriptions", json=_payload("20260815", "20260815"))
    assert r.status_code == 409


def test_create_sends_subscription_started_notice(client, notifier):
    client.post("/api/subscriptions", json=_payload("20260820", "20260822"))
    assert len(notifier.subscribed) == 1
    assert notifier.subscribed[0].mov_nm == "F1"


def test_rejected_subscription_sends_no_notice(client, notifier):
    # 이미 열린 단일 날짜 -> 409, 알림도 없어야 함
    client.post("/api/subscriptions", json=_payload("20260815", "20260815"))
    assert notifier.subscribed == []


def test_complete_subscription_ends_it(client):
    created = client.post("/api/subscriptions", json=_payload("20260820", "20260822")).json()
    r = client.post(f"/api/subscriptions/{created['id']}/complete")
    assert r.status_code == 200
    assert client.get("/api/subscriptions").json()[0]["completedAt"] is not None


def test_delete_subscription(client):
    created = client.post("/api/subscriptions", json=_payload()).json()
    r = client.delete(f"/api/subscriptions/{created['id']}")
    assert r.status_code == 204
    assert client.get("/api/subscriptions").json() == []
