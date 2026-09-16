"""농장 입점 심사(관리자) 회귀 테스트.

핵심: 심사 상세 화면이 nullable 컬럼 때문에 500 나지 않아야 한다.
organic_cert_type 은 nullable 인데 템플릿이 문자열 연결을 하고 있어,
친환경으로 등록했지만 인증 종류가 비어 있으면 심사 상세가 통째로 500 났다.
"""
import pytest
from werkzeug.security import generate_password_hash

import app as farmlink
from models import db, User, Farm

PASSWORD = "pw12345678"


def _user(email, role):
    u = User(nickname="n", email=email, name="이름", role=role,
             password=generate_password_hash(PASSWORD, method='pbkdf2:sha256'))
    db.session.add(u)
    db.session.commit()
    return u


def _farm(owner, **kw):
    farm = Farm(user_id=owner.id, address="경북 상주시 낙동면 신상리 45", status='PENDING', **kw)
    db.session.add(farm)
    db.session.commit()
    return farm


@pytest.fixture
def client(db_session):
    farmlink.app.secret_key = 'test-secret'
    with farmlink.app.test_client() as c:
        yield c


def _login(client, email):
    return client.post('/login', data={'email': email, 'password': PASSWORD})


@pytest.mark.parametrize("kw", [
    {},                                                   # 최소 정보만
    {"is_organic": True, "organic_cert_type": None},       # ★ 친환경인데 인증 종류 없음 → 예전엔 500
    {"is_organic": True, "organic_cert_type": "무농약"},
    {"is_organic": False},
    {"name": "기본 농장", "size": "300평", "certificate_pdf": None},
])
def test_audit_detail_renders_for_nullable_fields(client, kw):
    farmer = _user("f@x.com", "farmer")
    farm = _farm(farmer, **kw)
    _user("admin@x.com", "admin")
    _login(client, "admin@x.com")

    res = client.get(f'/admin/farms/audit/{farm.id}')
    assert res.status_code == 200, f"{kw} 에서 심사 상세가 {res.status_code}"


def test_audit_queue_lists_pending_farm(client):
    farmer = _user("f@x.com", "farmer")
    _farm(farmer, name="기본 농장")
    _user("admin@x.com", "admin")
    _login(client, "admin@x.com")

    body = client.get('/admin/farms/audit').get_data(as_text=True)
    assert "기본 농장" in body


def test_reject_requires_reason(client):
    """반려 사유 없이 반려하면 처리되지 않아야 한다."""
    farmer = _user("f@x.com", "farmer")
    farm = _farm(farmer)
    _user("admin@x.com", "admin")
    _login(client, "admin@x.com")

    client.post(f'/admin/farms/{farm.id}/reject', data={'reject_reason': '  '})
    assert db.session.get(Farm, farm.id).status == 'PENDING'


def test_approve_then_reject_updates_status(client):
    farmer = _user("f@x.com", "farmer")
    farm = _farm(farmer)
    _user("admin@x.com", "admin")
    _login(client, "admin@x.com")

    client.post(f'/admin/farms/{farm.id}/approve')
    assert db.session.get(Farm, farm.id).status == 'APPROVED'

    client.post(f'/admin/farms/{farm.id}/reject', data={'reject_reason': '주소 불일치'})
    refreshed = db.session.get(Farm, farm.id)
    assert refreshed.status == 'REJECTED' and refreshed.reject_reason == '주소 불일치'


def test_non_admin_cannot_open_audit(client):
    _user("u@x.com", "experiencer")
    _login(client, "u@x.com")
    assert client.get('/admin/farms/audit').status_code == 302
