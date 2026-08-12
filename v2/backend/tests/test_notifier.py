"""SlackWebhookNotifier — Incoming Webhook 전송. HTTP는 주입된 poster로 관찰한다.
seam: notify() 호출 시 어떤 URL로 어떤 메시지가 나가는가.
"""
from cgv_push.domain import Subscription
from cgv_push.slack_notifier import SlackWebhookNotifier


def _sub():
    return Subscription(
        id="1", site_no="0013", site_nm="용산아이파크몰",
        mov_no="88", mov_nm="F1 더 무비", start_date="20260815", end_date="20260815",
        slack_webhook_url="https://hooks.slack.com/services/XXX",
        special_auditorium="IMAX",
    )


def test_posts_to_subscription_webhook_url():
    calls = []
    notifier = SlackWebhookNotifier(post=lambda url, json: calls.append((url, json)))

    notifier.notify(_sub(), {"20260815"})

    assert len(calls) == 1
    url, _ = calls[0]
    assert url == "https://hooks.slack.com/services/XXX"


def test_message_contains_theater_movie_and_date():
    calls = []
    notifier = SlackWebhookNotifier(post=lambda url, json: calls.append((url, json)))

    notifier.notify(_sub(), {"20260815"})

    text = calls[0][1]["text"]
    assert "용산아이파크몰" in text
    assert "F1 더 무비" in text
    assert "IMAX" in text
    assert "2026-08-15" in text  # 사람이 읽는 날짜 형식
