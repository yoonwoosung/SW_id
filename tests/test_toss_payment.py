"""토스페이먼츠 결제 연동 테스트 — 준비·승인·금액검증·중복·실패·권한.

토스 API는 실제로 호출하지 않고 services.toss_service.confirm_payment 를 대체한다.
검증의 핵심은 "클라이언트가 보낸 금액을 신뢰하지 않는다"는 점이다.
"""
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

import app as farmlink
from models import db, User, Experience, Application, Payment
from common.constants import (APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID,
                             APPLICATION_STATUS_CONFIRMED)
from services import payment_service, toss_service

PASSWORD = "pw12345678"
COST = 20000
HEADCOUNT = 2
EXPECTED_AMOUNT = COST * HEADCOUNT


def _user(email, role='experiencer'):
    u = User(nickname="n", email=email, name="이름", role=role,
             password=generate_password_hash(PASSWORD, method='pbkdf2:sha256'))
    db.session.add(u)
    db.session.commit()
    return u


def _application(user):
    farmer = _user(f"farmer_{user.id}@x.com", 'farmer')
    exp = Experience(crop="딸기", location="충남", address_detail="충남 논산시",
                     cost=COST, farmer_id=farmer.id, status='recruiting',
                     end_date=date.today() + timedelta(days=30), lat=36.2, lng=127.1)
    db.session.add(exp)
    db.session.commit()
    app_row = Application(applicant_name="홍길동", phone_number="010-0000-0000",
                          participants_count=HEADCOUNT, apply_date=date.today() + timedelta(days=7),
                          apply_time="10:00", user_id=user.id, experience_id=exp.id,
                          status=APPLICATION_STATUS_PENDING)
    db.session.add(app_row)
    db.session.commit()
    return app_row


@pytest.fixture
def client(db_session):
    farmlink.app.secret_key = 'test-secret'
    with farmlink.app.test_client() as c:
        yield c


def _login(client, email):
    return client.post('/login', data={'email': email, 'password': PASSWORD})


def _fake_toss(monkeypatch, **overrides):
    """토스 승인 성공 응답을 흉내낸다."""
    calls = []

    def fake_confirm(payment_key, order_id, amount):
        calls.append({'payment_key': payment_key, 'order_id': order_id, 'amount': amount})
        body = {'paymentKey': payment_key, 'orderId': order_id,
                'totalAmount': amount, 'method': '카드', 'status': 'DONE'}
        body.update(overrides)
        return body

    monkeypatch.setattr(toss_service, 'confirm_payment', fake_confirm)
    monkeypatch.setattr(payment_service.toss_service, 'confirm_payment', fake_confirm)
    return calls


# ───────────────────────────── 준비(prepare) ─────────────────────────────

def test_prepare_uses_server_calculated_amount(client):
    u = _user("u@x.com"); row = _application(u)
    _login(client, "u@x.com")

    res = client.post('/api/payments/prepare', json={'application_id': row.id})
    body = res.get_json()

    assert res.status_code == 201
    assert body['success'] is True and body['error'] is None
    assert body['data']['amount'] == EXPECTED_AMOUNT      # 인원 × 단가
    assert body['data']['order_id'].startswith('farmlink-')
    # 서버가 금액을 먼저 기록해 둔다 — 승인 시 대조 기준
    assert Payment.query.filter_by(order_id=body['data']['order_id']).one().amount == EXPECTED_AMOUNT


def test_prepare_rejects_other_users_application(client):
    owner = _user("owner@x.com"); row = _application(owner)
    _user("other@x.com")
    _login(client, "other@x.com")

    res = client.post('/api/payments/prepare', json={'application_id': row.id})
    assert res.status_code == 403
    assert res.get_json()['error']['code'] == 'FORBIDDEN'


def test_prepare_rejects_already_paid(client):
    u = _user("u@x.com"); row = _application(u)
    row.status = APPLICATION_STATUS_PAID
    db.session.commit()
    _login(client, "u@x.com")

    res = client.post('/api/payments/prepare', json={'application_id': row.id})
    assert res.status_code == 400
    assert res.get_json()['error']['code'] == 'ALREADY_PROCESSED'


# ───────────────────────────── 승인(confirm) ─────────────────────────────

def test_confirm_success_confirms_application(client, monkeypatch):
    u = _user("u@x.com"); row = _application(u)
    _login(client, "u@x.com")
    order = client.post('/api/payments/prepare', json={'application_id': row.id}).get_json()['data']
    calls = _fake_toss(monkeypatch)

    res = client.post('/api/payments/confirm', json={
        'paymentKey': 'test_pk_1', 'orderId': order['order_id'], 'amount': EXPECTED_AMOUNT})
    body = res.get_json()

    assert res.status_code == 200 and body['success'] is True
    assert body['data']['status'] == APPLICATION_STATUS_CONFIRMED
    assert body['data']['redirect'].endswith(f"/reservation/complete/{row.id}") or 'complete' in body['data']['redirect']
    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_CONFIRMED
    payment = Payment.query.filter_by(order_id=order['order_id']).one()
    assert payment.status == Payment.STATUS_DONE and payment.approved_at is not None
    # 토스에는 서버가 저장한 금액이 전달돼야 한다
    assert calls[0]['amount'] == EXPECTED_AMOUNT


def test_confirm_rejects_tampered_amount(client, monkeypatch):
    """★ 클라이언트가 금액을 낮춰 보내도 승인되지 않아야 한다."""
    u = _user("u@x.com"); row = _application(u)
    _login(client, "u@x.com")
    order = client.post('/api/payments/prepare', json={'application_id': row.id}).get_json()['data']
    calls = _fake_toss(monkeypatch)

    res = client.post('/api/payments/confirm', json={
        'paymentKey': 'test_pk_1', 'orderId': order['order_id'], 'amount': 100})

    assert res.status_code == 400
    assert res.get_json()['error']['code'] == 'AMOUNT_MISMATCH'
    assert calls == []                                            # 토스 호출 자체를 안 함
    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_PENDING
    assert Payment.query.filter_by(order_id=order['order_id']).one().status == Payment.STATUS_FAILED


def test_confirm_is_idempotent(client, monkeypatch):
    """새로고침 등으로 승인이 두 번 와도 중복 처리되지 않아야 한다."""
    u = _user("u@x.com"); row = _application(u)
    _login(client, "u@x.com")
    order = client.post('/api/payments/prepare', json={'application_id': row.id}).get_json()['data']
    calls = _fake_toss(monkeypatch)
    payload = {'paymentKey': 'test_pk_1', 'orderId': order['order_id'], 'amount': EXPECTED_AMOUNT}

    first = client.post('/api/payments/confirm', json=payload)
    second = client.post('/api/payments/confirm', json=payload)

    assert first.status_code == 200 and second.status_code == 200
    assert len(calls) == 1                                        # 토스 승인은 한 번만
    assert Payment.query.filter_by(order_id=order['order_id']).count() == 1


def test_confirm_rejects_other_users_order(client, monkeypatch):
    owner = _user("owner@x.com"); row = _application(owner)
    _login(client, "owner@x.com")
    order = client.post('/api/payments/prepare', json={'application_id': row.id}).get_json()['data']
    _fake_toss(monkeypatch)

    _user("other@x.com")
    _login(client, "other@x.com")
    res = client.post('/api/payments/confirm', json={
        'paymentKey': 'x', 'orderId': order['order_id'], 'amount': EXPECTED_AMOUNT})

    assert res.status_code == 403
    assert res.get_json()['error']['code'] == 'FORBIDDEN'


def test_confirm_maps_toss_error(client, monkeypatch):
    u = _user("u@x.com"); row = _application(u)
    _login(client, "u@x.com")
    order = client.post('/api/payments/prepare', json={'application_id': row.id}).get_json()['data']

    def boom(payment_key, order_id, amount):
        raise toss_service.TossError('REJECT_CARD_COMPANY', '카드사에서 거절했습니다.', 400)
    monkeypatch.setattr(payment_service.toss_service, 'confirm_payment', boom)

    res = client.post('/api/payments/confirm', json={
        'paymentKey': 'x', 'orderId': order['order_id'], 'amount': EXPECTED_AMOUNT})
    body = res.get_json()

    assert res.status_code == 400
    assert body['success'] is False
    assert body['error']['code'] == 'REJECT_CARD_COMPANY'
    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_PENDING


def test_confirm_requires_params(client):
    _user("u@x.com"); _login(client, "u@x.com")
    res = client.post('/api/payments/confirm', json={'orderId': 'x'})
    assert res.status_code == 400
    assert res.get_json()['error']['code'] == 'INVALID_PAYMENT_PARAMS'


# ───────────────────────────── 실패·취소 ─────────────────────────────

def test_fail_url_keeps_application_pending(client):
    u = _user("u@x.com"); row = _application(u)
    _login(client, "u@x.com")
    order = client.post('/api/payments/prepare', json={'application_id': row.id}).get_json()['data']

    res = client.get(f"/payments/{row.id}/fail",
                     query_string={'code': 'USER_CANCEL', 'message': '사용자가 취소',
                                   'orderId': order['order_id']})

    assert res.status_code == 302                                  # 결제 화면으로 되돌림
    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_PENDING
    payment = Payment.query.filter_by(order_id=order['order_id']).one()
    assert payment.status == Payment.STATUS_FAILED and payment.fail_code == 'USER_CANCEL'


# ───────────────────────────── 키 노출 방지 ─────────────────────────────

def test_payment_page_never_leaks_secret_key(client, monkeypatch):
    monkeypatch.setenv('TOSS_SECRET_KEY', 'test_sk_MUST_NOT_LEAK')
    farmlink.app.config['TOSS_CLIENT_KEY'] = 'test_ck_public'
    u = _user("u@x.com"); row = _application(u)
    _login(client, "u@x.com")

    html = client.get(f'/payments/{row.id}').get_data(as_text=True)

    assert 'test_ck_public' in html          # 클라이언트 키는 필요
    assert 'test_sk_MUST_NOT_LEAK' not in html
    assert 'TOSS_SECRET_KEY' not in html
