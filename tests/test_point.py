"""services/point_service 통합 테스트 — 결제 적립·잔액 SUM·중복 적립 방지."""
from models import db, User, PointLog
from services.point_service import earn_points_for_payment, get_balance, get_point_summary
from common.constants import POINT_EARN_RATE, POINT_REASON_PAYMENT


def _user(email="u@x.com"):
    u = User(nickname="n", email=email, password="x", role="experiencer", name="이름")
    db.session.add(u)
    db.session.commit()
    return u


def test_earn_is_rate_of_amount_floored(db_session):
    u = _user()
    earned = earn_points_for_payment(u.id, application_id=1, amount=50000)
    assert earned == int(50000 * POINT_EARN_RATE)
    assert get_balance(u.id) == int(50000 * POINT_EARN_RATE)


def test_earn_is_idempotent_per_application(db_session):
    u = _user()
    assert earn_points_for_payment(u.id, application_id=1, amount=50000) == int(50000 * POINT_EARN_RATE)
    assert earn_points_for_payment(u.id, application_id=1, amount=50000) == 0  # 같은 예약 재적립 안 됨
    assert PointLog.query.count() == 1
    assert get_balance(u.id) == int(50000 * POINT_EARN_RATE)


def test_balance_sums_multiple_logs(db_session):
    u = _user()
    earn_points_for_payment(u.id, application_id=1, amount=20000)
    earn_points_for_payment(u.id, application_id=2, amount=60000)
    assert get_balance(u.id) == int(20000 * POINT_EARN_RATE) + int(60000 * POINT_EARN_RATE)


def test_zero_when_no_logs(db_session):
    u = _user()
    assert get_balance(u.id) == 0
    assert get_point_summary(u.id) == {"balance": 0, "logs": []}


def test_summary_lists_logs(db_session):
    u = _user()
    earn_points_for_payment(u.id, application_id=7, amount=40000)
    summary = get_point_summary(u.id)
    expected = int(40000 * POINT_EARN_RATE)
    assert summary["balance"] == expected
    assert summary["logs"][0]["amount"] == expected
    assert summary["logs"][0]["reason"] == POINT_REASON_PAYMENT
    assert summary["logs"][0]["application_id"] == 7
