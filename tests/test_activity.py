"""services/activity_service 단위 테스트 — 예약 상태 매핑(엄격)·체험 횟수."""
from datetime import date, timedelta

from services.activity_service import (
    reservation_state, experienced_count,
    STATE_PAY_PENDING, STATE_AWAIT_ACCEPT, STATE_CONFIRMED, STATE_COMPLETED, STATE_CANCELLED,
)
from common.constants import (
    APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID,
    APPLICATION_STATUS_CONFIRMED, APPLICATION_STATUS_CANCELLED,
)

TODAY = date(2026, 8, 3)
FUTURE = TODAY + timedelta(days=7)
PAST = TODAY - timedelta(days=7)


class FakeApp:
    """Application 테스트 더블.

    reservation_state/is_experience_ended 가 실제로 읽는 속성을 전부 갖춰야 한다.
    (can_review·apply_time 이 빠져 있어 AttributeError 로 실패하던 것을 보강)
    """
    def __init__(self, status, apply_date=FUTURE, apply_time='10:00', can_review=False):
        self.status = status
        self.apply_date = apply_date
        self.apply_time = apply_time
        self.can_review = can_review


def test_pending_is_pay_pending():
    assert reservation_state(FakeApp(APPLICATION_STATUS_PENDING), TODAY) == STATE_PAY_PENDING


def test_paid_is_await_accept():
    assert reservation_state(FakeApp(APPLICATION_STATUS_PAID), TODAY) == STATE_AWAIT_ACCEPT


def test_confirmed_future_is_confirmed():
    assert reservation_state(FakeApp(APPLICATION_STATUS_CONFIRMED, FUTURE), TODAY) == STATE_CONFIRMED


def test_confirmed_past_is_completed():
    assert reservation_state(FakeApp(APPLICATION_STATUS_CONFIRMED, PAST), TODAY) == STATE_COMPLETED


def test_cancelled_takes_priority():
    # 취소는 과거/미래 무관하게 항상 취소됨.
    assert reservation_state(FakeApp(APPLICATION_STATUS_CANCELLED, PAST), TODAY) == STATE_CANCELLED


def test_experienced_count_excludes_pending_and_cancelled():
    apps = [
        FakeApp(APPLICATION_STATUS_PENDING),
        FakeApp(APPLICATION_STATUS_PAID),
        FakeApp(APPLICATION_STATUS_CONFIRMED),
        FakeApp(APPLICATION_STATUS_CANCELLED),
    ]
    assert experienced_count(apps, TODAY) == 2   # 결제완료 + 확정만
