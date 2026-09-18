"""GET /api/experiences/surplus — 과생산 전용 섹션 API.

기존 추천 API(/api/recommendations/personalized)와 완전히 분리돼 있어야 한다.
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


def add(crop, **kw):
    base = dict(
        location='충남', address_detail='충남 논산시', cost=25000,
        farmer_id=1, status='recruiting', max_participants=100,
        current_participants=0, lat=36.8, lng=127.3,
        duration_start=date.today(), end_date=date.today() + timedelta(days=30),
    )
    base.update(kw)
    exp = Experience(crop=crop, **base)
    db.session.add(exp)
    db.session.commit()
    return exp


def surplus(crop, list_price=50000, cost=25000, qty_total=500, per_person=5,
            taken=0, **kw):
    return add(crop, cost=cost, is_surplus=True, surplus_terms_agreed=True,
               list_price=list_price, surplus_qty_total=qty_total,
               surplus_per_person=per_person, surplus_qty_taken=taken,
               surplus_unit='kg', **kw)


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.app_context():
        flask_app.extensions['sqlalchemy'].engines[None] = create_engine(
            'sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        db.create_all()
        db.session.add(User(
            nickname='농장주', email='f@test.local', role='farmer', name='f', phone='010-0',
            password=generate_password_hash('pw', method='pbkdf2:sha256'),
            farm_image='farm.jpg'))
        db.session.commit()
        yield flask_app.test_client()
        db.drop_all()


def results(res):
    body = res.get_json()
    assert body['success'], body
    return body['data']['results']


# ---- 필터 ----

def test_only_surplus_returned(client):
    add('일반딸기')
    surplus('과생산딸기')
    rows = results(client.get('/api/experiences/surplus'))
    assert [r['crop'] for r in rows] == ['과생산딸기']


def test_terms_not_agreed_excluded(client):
    """약관 미동의는 노출하지 않는다."""
    e = surplus('약관없음')
    e.surplus_terms_agreed = False
    db.session.commit()
    assert results(client.get('/api/experiences/surplus')) == []


def test_closed_experience_excluded(client):
    e = surplus('마감체험')
    e.status = 'hidden'
    db.session.commit()
    assert results(client.get('/api/experiences/surplus')) == []


def test_expired_experience_excluded(client):
    surplus('지난체험', end_date=date.today() - timedelta(days=1))
    assert results(client.get('/api/experiences/surplus')) == []


def test_empty_returns_empty_list(client):
    body = client.get('/api/experiences/surplus').get_json()
    assert body['success'] and body['data']['results'] == [] and body['data']['count'] == 0


# ---- 카드 내용 ----

def test_card_fields(client):
    surplus('과생산딸기', list_price=50000, cost=25000,
            qty_total=500, per_person=5, taken=15)
    card = results(client.get('/api/experiences/surplus'))[0]
    assert card['list_price'] == 50000
    assert card['cost'] == 25000
    assert card['discount_rate'] == 50.0
    assert card['qty_total'] == 500
    assert card['qty_left'] == 485          # 500 - 15
    assert card['per_person'] == 5
    assert card['unit'] == 'kg'
    assert card['sold_out'] is False
    assert card['pickup_only'] is True      # 택배 없음
    assert card['thumbnail_url'].startswith('/static/')


def test_sold_out_flag(client):
    surplus('소진체험', qty_total=100, per_person=5, taken=100)
    card = results(client.get('/api/experiences/surplus'))[0]
    assert card['qty_left'] == 0 and card['sold_out'] is True


def test_origin_included(client):
    surplus('원산지있음', surplus_origin='충남 논산시')
    assert results(client.get('/api/experiences/surplus'))[0]['origin'] == '충남 논산시'


# ---- 정렬 ----

def test_sorted_by_discount_desc(client):
    surplus('할인20', list_price=10000, cost=8000)    # 20%
    surplus('할인50', list_price=10000, cost=5000)    # 50%
    surplus('할인30', list_price=10000, cost=7000)    # 30%
    rows = results(client.get('/api/experiences/surplus'))
    assert [r['crop'] for r in rows] == ['할인50', '할인30', '할인20']


def test_sold_out_goes_last(client):
    surplus('소진70', list_price=10000, cost=3000, qty_total=10, per_person=5, taken=10)
    surplus('판매중20', list_price=10000, cost=8000)
    rows = results(client.get('/api/experiences/surplus'))
    assert [r['crop'] for r in rows] == ['판매중20', '소진70'], "소진은 할인율이 커도 뒤로"


# ---- limit ----

def test_limit_applied(client):
    for i in range(5):
        surplus(f'체험{i}')
    assert len(results(client.get('/api/experiences/surplus?limit=2'))) == 2


def test_bad_limit_falls_back(client):
    surplus('체험')
    assert len(results(client.get('/api/experiences/surplus?limit=abc'))) == 1
    assert len(results(client.get('/api/experiences/surplus?limit=0'))) == 1


def test_limit_capped(client):
    """상한을 넘는 limit 은 잘린다(과도한 응답 방지)."""
    surplus('체험')
    res = client.get('/api/experiences/surplus?limit=9999')
    assert res.status_code == 200


# ---- 기존 흐름 미변경 ----

def test_recommendation_api_unaffected(client):
    """과생산이 기존 추천 결과에 끼어들지 않는다(별도 섹션)."""
    add('일반딸기')
    surplus('과생산딸기')
    body = client.get('/api/recommendations/personalized').get_json()
    assert body['success']
    crops = [r['crop'] for r in body['data']['results']]
    assert '일반딸기' in crops and '과생산딸기' in crops, \
        "추천 알고리즘은 과생산을 따로 걸러내지 않는다(기존 동작 유지)"
