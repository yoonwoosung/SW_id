"""관리자 기능 통합 테스트 — 권한 가드·농장 승인/거절·노출 게이트.

핵심은 '승인된 농장만 공개된다'는 규칙이다. 승인 상태가 목록·상세·예약
어디에서도 새지 않는지 확인한다.
"""
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

import app as farmlink
from models import db, User, Experience

PASSWORD = "pw12345678"


def _user(email, role, nickname="n"):
    u = User(nickname=nickname, email=email, name="이름", role=role,
             password=generate_password_hash(PASSWORD, method='pbkdf2:sha256'))
    db.session.add(u)
    db.session.commit()
    return u


def _farm(farmer, crop="딸기", approval=Experience.APPROVAL_APPROVED):
    exp = Experience(crop=crop, location="충남", address_detail="충남 논산시",
                     cost=20000, farmer_id=farmer.id, status='recruiting',
                     end_date=date.today() + timedelta(days=30),
                     lat=36.2, lng=127.1, approval_status=approval)
    db.session.add(exp)
    db.session.commit()
    return exp


@pytest.fixture
def client(db_session):
    farmlink.app.secret_key = 'test-secret'
    with farmlink.app.test_client() as c:
        yield c


def _login(client, email):
    return client.post('/login', data={'email': email, 'password': PASSWORD})


# ---------------------------------------------------------------- 권한 가드

def test_anonymous_cannot_open_admin(client):
    res = client.get('/admin')
    assert res.status_code == 302
    assert '/login' in res.headers['Location']


def test_non_admin_cannot_open_admin(client):
    _user("u@x.com", "experiencer")
    _login(client, "u@x.com")
    res = client.get('/admin')
    assert res.status_code == 302
    assert '/login' not in res.headers['Location']  # 메인으로 돌려보낸다


def test_non_admin_cannot_approve(client):
    admin_owner = _user("f@x.com", "farmer")
    farm = _farm(admin_owner, approval=Experience.APPROVAL_PENDING)
    _user("u@x.com", "experiencer")
    _login(client, "u@x.com")

    client.post(f'/admin/farms/{farm.id}/approve')
    assert db.session.get(Experience, farm.id).approval_status == Experience.APPROVAL_PENDING


# ---------------------------------------------------------------- 로그인 분기

def test_admin_login_redirects_to_dashboard(client):
    _user("admin@x.com", "admin")
    res = _login(client, "admin@x.com")
    assert res.headers['Location'].endswith('/admin')


def test_farmer_and_user_login_unchanged(client):
    """기존 로그인 흐름은 건드리지 않았음을 고정한다."""
    _user("f@x.com", "farmer")
    _user("u@x.com", "experiencer")
    assert 'my_farm_detailed' in _login(client, "f@x.com").headers['Location']
    assert _login(client, "u@x.com").headers['Location'].endswith('/')


# ---------------------------------------------------------------- 노출 게이트

def test_pending_farm_is_hidden_from_index(client):
    farmer = _user("f@x.com", "farmer")
    _farm(farmer, crop="승인된포도")
    _farm(farmer, crop="대기중딸기", approval=Experience.APPROVAL_PENDING)

    body = client.get('/').get_data(as_text=True)
    assert "승인된포도" in body
    assert "대기중딸기" not in body


def test_pending_farm_detail_is_blocked(client):
    farmer = _user("f@x.com", "farmer")
    farm = _farm(farmer, approval=Experience.APPROVAL_PENDING)
    res = client.get(f'/experience/{farm.id}')
    assert res.status_code == 302


def test_owner_can_preview_own_pending_farm(client):
    """농장주는 승인 전 자기 농장을 미리 볼 수 있어야 한다."""
    farmer = _user("f@x.com", "farmer")
    farm = _farm(farmer, approval=Experience.APPROVAL_PENDING)
    _login(client, "f@x.com")
    assert client.get(f'/experience/{farm.id}').status_code == 200


def test_pending_farm_absent_from_map_json(client):
    farmer = _user("f@x.com", "farmer")
    _farm(farmer, crop="대기중딸기", approval=Experience.APPROVAL_PENDING)
    assert "대기중딸기" not in client.get('/api/experiences').get_data(as_text=True)


# ---------------------------------------------------------------- 승인 / 거절

def test_admin_approves_then_farm_becomes_visible(client):
    farmer = _user("f@x.com", "farmer")
    farm = _farm(farmer, crop="대기중딸기", approval=Experience.APPROVAL_PENDING)
    _user("admin@x.com", "admin")
    _login(client, "admin@x.com")

    assert "대기중딸기" in client.get('/admin').get_data(as_text=True)

    client.post(f'/admin/farms/{farm.id}/approve')
    refreshed = db.session.get(Experience, farm.id)
    assert refreshed.approval_status == Experience.APPROVAL_APPROVED
    assert refreshed.approved_at is not None

    client.get('/')  # 승인 flash에 작물명이 들어가므로 먼저 소비한다
    assert "대기중딸기" in client.get('/').get_data(as_text=True)


def test_admin_rejects_with_note(client):
    farmer = _user("f@x.com", "farmer")
    farm = _farm(farmer, crop="대기중딸기", approval=Experience.APPROVAL_PENDING)
    _user("admin@x.com", "admin")
    _login(client, "admin@x.com")

    client.post(f'/admin/farms/{farm.id}/reject', data={'approval_note': '서류 미비'})
    refreshed = db.session.get(Experience, farm.id)
    assert refreshed.approval_status == Experience.APPROVAL_REJECTED
    assert refreshed.approval_note == '서류 미비'

    client.get('/')  # 거절 flash에 작물명이 들어가므로 먼저 소비한다
    assert "대기중딸기" not in client.get('/').get_data(as_text=True)


def test_new_farm_starts_pending():
    """모델 기본값이 pending 인지 고정 — 마이그레이션 backfill의 전제다."""
    assert Experience.__table__.c.approval_status.default.arg == 'pending'


# ---------------------------------------------------------------- 관리 화면

def test_admin_pages_render(client):
    farmer = _user("f@x.com", "farmer")
    _farm(farmer)
    _user("admin@x.com", "admin")
    _login(client, "admin@x.com")

    for path in ('/admin', '/admin/farms', '/admin/farms?approval=pending',
                 '/admin/users', '/admin/users?role=farmer', '/admin/reservations'):
        assert client.get(path).status_code == 200, path


def test_last_admin_cannot_be_deleted(client):
    admin = _user("admin@x.com", "admin")
    _login(client, "admin@x.com")
    client.post(f'/admin/users/{admin.id}/delete')
    assert User.query.filter_by(role='admin').count() == 1
