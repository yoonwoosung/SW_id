"""services/payment_service 통합 테스트 — 더미 결제(소유확인·상태전이·금액)."""
from datetime import date

from models import db, User, Experience, Application
from services.payment_service import pay, calculate_amount
from common.constants import (POINT_EARN_RATE, APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID,
                              APPLICATION_STATUS_CONFIRMED)


def _user(email):
    u = User(nickname="n", email=email, password="x", role="experiencer", name="이름")
    db.session.add(u)
    db.session.commit()
    return u


def _experience(cost=25000):
    farmer = _user(f"farmer_{cost}@x.com")
    exp = Experience(crop="포도", location="loc", cost=cost, farmer_id=farmer.id, lat=36.8, lng=127.3)
    db.session.add(exp)
    db.session.commit()
    return exp


def _application(user_id, exp_id, participants=2, status=APPLICATION_STATUS_PENDING):
    app = Application(
        applicant_name="홍길동", phone_number="01000000000", participants_count=participants,
        apply_date=date(2026, 8, 1), apply_time="10:00", status=status,
        user_id=user_id, experience_id=exp_id,
    )
    db.session.add(app)
    db.session.commit()
    return app


def test_amount_is_participants_times_cost(db_session):
    exp = _experience(cost=25000)
    app = _application(1, exp.id, participants=3)
    assert calculate_amount(app, exp) == 75000


def test_pay_success_transitions_to_paid(db_session):
    buyer = _user("buyer@x.com")
    exp = _experience(cost=25000)
    app = _application(buyer.id, exp.id, participants=2)
    status, data = pay(buyer.id, app.id)
    assert status == 'ok'
    assert data == {"application_id": app.id, "status": APPLICATION_STATUS_PAID,
                    "amount": 50000, "earned_points": int(50000 * POINT_EARN_RATE)}
    assert Application.query.get(app.id).status == APPLICATION_STATUS_PAID


def test_pay_forbidden_for_other_user(db_session):
    buyer = _user("buyer@x.com")
    other = _user("other@x.com")
    exp = _experience()
    app = _application(buyer.id, exp.id)
    status, data = pay(other.id, app.id)
    assert status == 'forbidden' and data is None
    assert Application.query.get(app.id).status == APPLICATION_STATUS_PENDING  # 변경 없음


def test_pay_not_found(db_session):
    assert pay(1, 99999) == ('not_found', None)


def test_pay_rejects_non_pending(db_session):
    buyer = _user("buyer@x.com")
    exp = _experience()
    app = _application(buyer.id, exp.id, status=APPLICATION_STATUS_CONFIRMED)
    status, data = pay(buyer.id, app.id)
    assert status == 'invalid_state' and data is None
