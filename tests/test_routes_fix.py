"""라우트 회귀 테스트 — 추천 폴백(위치 없음)과 my_info 수정(NOT NULL 방어).

app.py의 DB 엔진을 인메모리 SQLite로 교체해 test_client로 검증한다(운영 DB 불필요).
"""
import os

os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('DB_USERNAME', 'x')
os.environ.setdefault('DB_PASSWORD', 'x')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_NAME', 'x')

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool
from werkzeug.security import generate_password_hash

import app as app_module

flask_app = app_module.app
db = app_module.db
User = app_module.User
Experience = app_module.Experience


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.app_context():
        # 단일 커넥션 인메모리 SQLite로 엔진 교체(테스트 격리)
        flask_app.extensions['sqlalchemy'].engines[None] = create_engine(
            'sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        db.create_all()
        user = User(
            nickname='기존닉', email='u@test.local',
            password=generate_password_hash('pw1234', method='pbkdf2:sha256'),
            role='experiencer', name='기존이름', phone='010-0',
        )
        db.session.add(user)
        db.session.add(Experience(
            crop='딸기', location='충남 논산', address_detail='충남 논산시',
            cost=25000, farmer_id=1, status='recruiting',
            duration_start=date.today(), end_date=date.today() + timedelta(days=10),
        ))
        db.session.commit()
        yield flask_app.test_client()
        db.drop_all()


def test_index_recommended_without_coords_falls_back(client):
    # 기본 정렬은 recommended. 좌표가 없어도 빈 화면이 아니라 목록(딸기)이 떠야 한다.
    res = client.get('/')
    assert res.status_code == 200
    assert '딸기'.encode() in res.data


def test_my_info_post_without_nickname_does_not_500(client):
    client.post('/login', data={'email': 'u@test.local', 'password': 'pw1234'})
    # 폼에 nickname이 없어도 500이 아니라 정상 처리(리다이렉트)되어야 한다.
    res = client.post('/my_info', data={'name': '새이름', 'phone': '010-1'})
    assert res.status_code == 302
    with flask_app.app_context():
        user = User.query.filter_by(email='u@test.local').first()
        assert user.nickname == '기존닉'   # nickname은 보존
        assert user.name == '새이름'        # name은 갱신


def test_index_survives_null_address_detail(client):
    """address_detail 이 NULL 인 농장이 있어도 메인 페이지가 500 나지 않아야 한다.

    회귀 방지: 예전에는 REGIONAL_SPECIALTIES 판정에서 `r in item.address_detail` 이
    None 을 만나 TypeError 를 내고 메인 전체가 500 이 됐다.
    """
    with flask_app.app_context():
        db.session.add(Experience(
            crop='포도', location='경기', address_detail=None,   # ← NULL
            cost=10000, farmer_id=1, status='recruiting',
            duration_start=date.today(), end_date=date.today() + timedelta(days=10),
            approval_status=Experience.APPROVAL_APPROVED,
        ))
        db.session.commit()

    assert client.get('/').status_code == 200
