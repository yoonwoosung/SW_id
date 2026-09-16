"""포인트 사용·적립·원복 테스트.

핵심 3가지:
  1) 보유 초과·결제액 초과 사용을 서버가 막는가
  2) 결제 실패·취소 시 차감분이 원복되는가 (잔액이 새지 않는가)
  3) 적립이 '실제 결제한 금액'(포인트 차감 후) 기준 3% 인가
"""
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

import app as farmlink
from models import db, User, Experience, Application, Payment, PointLog
from common.constants import (APPLICATION_STATUS_PENDING, APPLICATION_STATUS_CONFIRMED,
                              POINT_EARN_RATE, POINT_REASON_USE, POINT_REASON_REFUND)
from services import payment_service, point_service, toss_service

PASSWORD = "pw12345678"
COST = 20000
HEADCOUNT = 2
ORDER_TOTAL = COST * HEADCOUNT      # 40,000원


def _user(email, role='experiencer'):
    u = User(nickname="n", email=email, name="이름", role=role,
             password=generate_password_hash(PASSWORD, method='pbkdf2:sha256'))
    db.session.add(u)
    db.session.commit()
    return u


def _grant(user, amount):
    """테스트용 포인트 지급."""
    db.session.add(PointLog(user_id=user.id, amount=amount, reason='seed'))
    db.session.commit()


def _application(user):
    farmer = _user(f"farmer_{user.id}@x.com", 'farmer')
    exp = Experience(crop="딸기", location="충남", address_detail="충남 논산시",
                     cost=COST, farmer_id=farmer.id, status='recruiting',
                     end_date=date.today() + timedelta(days=30), lat=36.2, lng=127.1)
    db.session.add(exp)
    db.session.commit()
    row = Application(applicant_name="홍길동", phone_number="010-0000-0000",
                      participants_count=HEADCOUNT, apply_date=date.today() + timedelta(days=7),
                      apply_time="10:00", user_id=user.id, experience_id=exp.id,
                      status=APPLICATION_STATUS_PENDING)
    db.session.add(row)
    db.session.commit()
    return row


@pytest.fixture
def client(db_session):
    farmlink.app.secret_key = 'test-secret'
    with farmlink.app.test_client() as c:
        yield c


def _login(client, email):
    return client.post('/login', data={'email': email, 'password': PASSWORD})


def _fake_toss(monkeypatch):
    calls = []

    def fake_confirm(payment_key, order_id, amount):
        calls.append({'order_id': order_id, 'amount': amount})
        return {'paymentKey': payment_key, 'orderId': order_id, 'method': '카드'}

    monkeypatch.setattr(payment_service.toss_service, 'confirm_payment', fake_confirm)
    return calls


# ───────────────────────────── 사용 검증 ─────────────────────────────

def test_point_use_reduces_charged_amount(client):
    u = _user("u@x.com"); _grant(u, 10000); row = _application(u)
    _login(client, "u@x.com")

    data = client.post('/api/payments/prepare',
                       json={'application_id': row.id, 'use_point': 5000}).get_json()['data']

    assert data['order_total'] == ORDER_TOTAL
    assert data['used_points'] == 5000
    assert data['amount'] == ORDER_TOTAL - 5000        # 토스로 청구할 금액
    assert point_service.get_balance(u.id) == 5000     # 즉시 차감


def test_cannot_use_more_than_balance(client):
    u = _user("u@x.com"); _grant(u, 1000); row = _application(u)
    _login(client, "u@x.com")

    res = client.post('/api/payments/prepare', json={'application_id': row.id, 'use_point': 5000})

    assert res.status_code == 400
    assert res.get_json()['error']['code'] == 'INSUFFICIENT_POINTS'
    assert point_service.get_balance(u.id) == 1000     # 잔액 변화 없음
    assert Payment.query.count() == 0


def test_cannot_use_more_than_order_total(client):
    u = _user("u@x.com"); _grant(u, 999999); row = _application(u)
    _login(client, "u@x.com")

    res = client.post('/api/payments/prepare',
                      json={'application_id': row.id, 'use_point': ORDER_TOTAL + 1})

    assert res.status_code == 400
    assert res.get_json()['error']['code'] == 'POINT_EXCEEDS_TOTAL'
    assert point_service.get_balance(u.id) == 999999


def test_negative_point_rejected(client):
    u = _user("u@x.com"); _grant(u, 5000); row = _application(u)
    _login(client, "u@x.com")

    res = client.post('/api/payments/prepare', json={'application_id': row.id, 'use_point': -100})
    assert res.status_code == 400
    assert res.get_json()['error']['code'] == 'INVALID_POINT_AMOUNT'


# ───────────────────────────── 적립 ─────────────────────────────

def test_earn_is_three_percent_of_charged_amount(client, monkeypatch):
    """★ 적립은 포인트로 깎고 '실제 낸' 금액 기준이어야 한다."""
    u = _user("u@x.com"); _grant(u, 10000); row = _application(u)
    _login(client, "u@x.com")
    order = client.post('/api/payments/prepare',
                        json={'application_id': row.id, 'use_point': 10000}).get_json()['data']
    _fake_toss(monkeypatch)

    body = client.post('/api/payments/confirm', json={
        'paymentKey': 'pk', 'orderId': order['order_id'], 'amount': order['amount']}).get_json()

    charged = ORDER_TOTAL - 10000                    # 30,000원
    assert body['data']['earned_points'] == int(charged * POINT_EARN_RATE)   # 3% = 900
    assert body['data']['status'] == APPLICATION_STATUS_CONFIRMED
    # 잔액 = 지급 10000 - 사용 10000 + 적립 900
    assert point_service.get_balance(u.id) == 900


def test_earn_rate_is_three_percent():
    assert POINT_EARN_RATE == 0.03


# ───────────────────────── 실패 시 원복 ─────────────────────────

def test_points_refunded_when_toss_fails(client, monkeypatch):
    """★ 차감 후 승인 실패 → 포인트가 되돌아와야 한다."""
    u = _user("u@x.com"); _grant(u, 10000); row = _application(u)
    _login(client, "u@x.com")
    order = client.post('/api/payments/prepare',
                        json={'application_id': row.id, 'use_point': 8000}).get_json()['data']
    assert point_service.get_balance(u.id) == 2000    # 차감된 상태

    def boom(payment_key, order_id, amount):
        raise toss_service.TossError('REJECT_CARD_COMPANY', '카드사 거절', 400)
    monkeypatch.setattr(payment_service.toss_service, 'confirm_payment', boom)

    client.post('/api/payments/confirm', json={
        'paymentKey': 'pk', 'orderId': order['order_id'], 'amount': order['amount']})

    assert point_service.get_balance(u.id) == 10000   # 원복
    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_PENDING
    assert PointLog.query.filter_by(reason=POINT_REASON_REFUND).count() == 1


def test_points_refunded_on_user_cancel(client):
    """결제창에서 취소해도 포인트가 되돌아와야 한다."""
    u = _user("u@x.com"); _grant(u, 10000); row = _application(u)
    _login(client, "u@x.com")
    order = client.post('/api/payments/prepare',
                        json={'application_id': row.id, 'use_point': 8000}).get_json()['data']

    client.get(f"/payments/{row.id}/fail",
               query_string={'code': 'USER_CANCEL', 'message': '취소', 'orderId': order['order_id']})

    assert point_service.get_balance(u.id) == 10000
    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_PENDING


def test_refund_is_idempotent(client):
    """중복 콜백으로 원복이 두 번 일어나 잔액이 부풀면 안 된다."""
    u = _user("u@x.com"); _grant(u, 10000); row = _application(u)
    _login(client, "u@x.com")
    order = client.post('/api/payments/prepare',
                        json={'application_id': row.id, 'use_point': 8000}).get_json()['data']

    for _ in range(3):
        client.get(f"/payments/{row.id}/fail",
                   query_string={'code': 'USER_CANCEL', 'orderId': order['order_id']})

    assert point_service.get_balance(u.id) == 10000
    assert PointLog.query.filter_by(reason=POINT_REASON_REFUND).count() == 1


def test_retry_after_cancel_works(client, monkeypatch):
    """실패 후 재시도가 가능해야 한다(예약이 살아 있어야 함)."""
    u = _user("u@x.com"); _grant(u, 10000); row = _application(u)
    _login(client, "u@x.com")
    first = client.post('/api/payments/prepare',
                        json={'application_id': row.id, 'use_point': 5000}).get_json()['data']
    client.get(f"/payments/{row.id}/fail",
               query_string={'code': 'USER_CANCEL', 'orderId': first['order_id']})

    second = client.post('/api/payments/prepare',
                         json={'application_id': row.id, 'use_point': 5000})
    assert second.status_code == 201
    _fake_toss(monkeypatch)
    data = second.get_json()['data']
    body = client.post('/api/payments/confirm', json={
        'paymentKey': 'pk', 'orderId': data['order_id'], 'amount': data['amount']}).get_json()
    assert body['success'] is True


# ───────────────────────────── 내역·조회 ─────────────────────────────

def test_point_log_records_use_and_earn(client, monkeypatch):
    u = _user("u@x.com"); _grant(u, 10000); row = _application(u)
    _login(client, "u@x.com")
    order = client.post('/api/payments/prepare',
                        json={'application_id': row.id, 'use_point': 4000}).get_json()['data']
    _fake_toss(monkeypatch)
    client.post('/api/payments/confirm', json={
        'paymentKey': 'pk', 'orderId': order['order_id'], 'amount': order['amount']})

    reasons = [l.reason for l in PointLog.query.filter_by(user_id=u.id).all()]
    assert POINT_REASON_USE in reasons and 'payment' in reasons

    summary = client.get('/api/users/me/points').get_json()
    assert summary['success'] is True
    assert summary['data']['balance'] == point_service.get_balance(u.id)
