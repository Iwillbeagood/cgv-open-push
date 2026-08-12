"""오픈 감지의 순수 도메인 로직 (I/O 없음).

CONTEXT: 오픈 감지 = 구독한 기간 안의 상영일이 예매 오픈된 상태로 새로 관찰되는 것.
구독은 [start_date, end_date] 기간을 지목하므로, 그 기간 안에서 현재 오픈되었고
아직 알리지 않은 상영일들을 '알림 대상(due)'으로 판정한다. 날짜는 YYYYMMDD
문자열이라 사전식 비교가 곧 날짜 비교다. 완료된 구독은 대상에서 제외한다.
"""
from cgv_push.domain import Subscription


def due_dates(subscription: Subscription, open_dates: set[str]) -> set[str]:
    """구독 기간 안에서 지금 오픈되었고 아직 알리지 않은 상영일 집합."""
    if subscription.completed_at is not None:
        return set()
    return {
        d
        for d in open_dates
        if subscription.start_date <= d <= subscription.end_date
        and d not in subscription.alerted_dates
    }
