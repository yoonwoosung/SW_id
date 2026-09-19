"""농장주 승인 단계 테스트 — 결제 성공은 '확정'이 아니라 '결제완료'(승인 대기)다.

핵심: 농장주가 수락하지 않았는데 예약이 확정되면 안 된다.
'결제완료'는 이미 있던 상태값이고(activity_service 가 '수락 대기중'으로 판정),
토스 승인 경로만 '확정'으로 건너뛰고 있었다.
"""
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

import app as farmlink
from models import db, User, Experience, Application
from common.constants import (APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID,
                              APPLICATION_STATUS_CONFIRMED, APPLICATION_STATUS_CANCELLED)

PASSWORD = "pw12345678"
COST = 20000
HEADCOUNT = 2


def _user(email, role='experiencer'):
    u = User(nickname="n", email=email, name="이름", role=role,
             password=generate_password_hash(PASSWORD, method='pbkdf2:sha256'))
    db.session.add(u)
    db.session.commit()
    return u


def _experience(farmer, max_participants=20):
    exp = Experience(crop="딸기", location="충남", address_detail="충남 논산시",
                     cost=COST, farmer_id=farmer.id, status='recruiting',
                     max_participants=max_participants, current_participants=HEADCOUNT,
                     end_date=date.today() + timedelta(days=30), lat=36.2, lng=127.1)
    db.session.add(exp)
    db.session.commit()
    return exp


def _application(user, exp, status=APPLICATION_STATUS_PAID):
    row = Application(applicant_name="홍길동", phone_number="010-0000-0000",
                      participants_count=HEADCOUNT,
                      apply_date=date.today() + timedelta(days=7),
                      apply_time="10:00", user_id=user.id, experience_id=exp.id,
                      status=status)
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


# ───────────────────── 농장주 '수락 대기' 목록 ─────────────────────

def test_paid_reservation_appears_in_pending_list(client):
    """★결제를 마친 예약이 농장주의 수락 대기 목록에 떠야 한다.★

    예전에는 이 목록이 '예정'(결제 전)을 봐서, 결제 성공을 '결제완료'로
    바꾸면 돈을 낸 예약이 농장주 화면에서 사라졌다.
    """
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)

    _login(client, "f@x.com")
    html = client.get('/easy_mode').get_data(as_text=True)

    assert f'/application/confirm/{row.id}' in html
    assert f'/application/reject/{row.id}' in html


def test_unpaid_reservation_not_in_pending_list(client):
    """결제 전('예정') 건은 수락 대기 목록에 뜨지 않는다."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PENDING)

    _login(client, "f@x.com")
    html = client.get('/easy_mode').get_data(as_text=True)

    assert f'/application/confirm/{row.id}' not in html


def test_confirmed_reservation_not_in_pending_list(client):
    """이미 확정된 건도 수락 대기 목록에 남지 않는다."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_CONFIRMED)

    _login(client, "f@x.com")
    html = client.get('/easy_mode').get_data(as_text=True)

    assert f'/application/confirm/{row.id}' not in html


# ───────────────────── 수락 ─────────────────────

def test_farmer_accept_moves_paid_to_confirmed(client):
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)

    _login(client, "f@x.com")
    client.post(f'/application/confirm/{row.id}', follow_redirects=True)

    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_CONFIRMED


def test_other_farmer_cannot_accept(client):
    """남의 체험 예약은 수락할 수 없다."""
    owner = _user("f@x.com", 'farmer')
    stranger = _user("f2@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(owner), APPLICATION_STATUS_PAID)

    _login(client, "f2@x.com")
    client.post(f'/application/confirm/{row.id}', follow_redirects=True)

    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_PAID


def test_already_confirmed_is_not_reprocessed(client):
    """기존 '확정' 예약은 그대로 둔다(재처리 금지)."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_CONFIRMED)

    _login(client, "f@x.com")
    client.post(f'/application/confirm/{row.id}', follow_redirects=True)

    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_CONFIRMED


def test_cancelled_cannot_be_accepted(client):
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_CANCELLED)

    _login(client, "f@x.com")
    client.post(f'/application/confirm/{row.id}', follow_redirects=True)

    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_CANCELLED
