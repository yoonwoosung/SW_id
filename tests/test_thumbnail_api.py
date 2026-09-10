"""thumbnail_url 응답 회귀 테스트 — 코스·추천·검색 API가 계약을 지키는지.

계약: thumbnail_url 은 항상 존재하고 non-null 이며 /static/ 으로 시작하는 완전한 경로.
폴백 3단계(체험 사진 → 농장 사진 → 기본 이미지)를 API 레벨에서 확인한다.
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
from services.thumbnail_service import DEFAULT_THUMBNAIL_URL

flask_app = app_module.app
db = app_module.db
User = app_module.User
Experience = app_module.Experience


def _user(nickname, email, farm_image):
    return User(
        nickname=nickname, email=email,
        password=generate_password_hash('pw1234', method='pbkdf2:sha256'),
        role='farmer', name=nickname, phone='010-0', farm_image=farm_image,
    )


@pytest.fixture
def client():
    flask_app.config['TESTING'] = True
    with flask_app.app_context():
        flask_app.extensions['sqlalchemy'].engines[None] = create_engine(
            'sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        db.create_all()

        # 세 농장주가 각각 다른 폴백 단계를 타게 한다
        db.session.add_all([
            _user('체험사진', 'f1@test.local', 'farm1.jpg'),
            _user('농장사진', 'f2@test.local', 'farm2.jpg'),
            _user('사진없음', 'f3@test.local', None),
        ])
        db.session.commit()

        common = dict(
            location='충남 논산', address_detail='충남 논산시', cost=25000,
            status='recruiting', lat=36.8, lng=127.3,
            duration_start=date.today(), end_date=date.today() + timedelta(days=30),
        )
        db.session.add_all([
            # 선행 콤마 — 옛 split(',')[0] 이 빈 문자열을 내던 케이스
            Experience(crop='딸기', farmer_id=1, images=',exp1.jpg', **common),
            Experience(crop='포도', farmer_id=2, images=None, **common),
            # 공백뿐인 값 → 농장 사진도 없으므로 기본 이미지까지 내려가야 한다
            Experience(crop='사과', farmer_id=3, images='  ,  ', **common),
        ])
        db.session.commit()
        yield flask_app.test_client()
        db.drop_all()


def _results(res):
    body = res.get_json()
    assert body['success'], body
    return body['data']['results']


def _by_crop(results):
    return {r['crop']: r for r in results}


def test_personalized_includes_thumbnail_url(client):
    by = _by_crop(_results(client.get('/api/recommendations/personalized')))
    assert by['딸기']['thumbnail_url'] == '/static/uploads/exp1.jpg'   # 체험 사진
    assert by['포도']['thumbnail_url'] == '/static/uploads/farm2.jpg'  # 농장 사진 폴백
    assert by['사과']['thumbnail_url'] == DEFAULT_THUMBNAIL_URL        # 기본 이미지


def test_personalized_keeps_first_image_field(client):
    # 프론트가 아직 쓰는 필드라 지우지 않는다(파일명만 담김)
    by = _by_crop(_results(client.get('/api/recommendations/personalized')))
    assert by['딸기']['first_image'] == 'exp1.jpg'
    assert by['포도']['first_image'] is None


def test_recommendations_includes_thumbnail_url(client):
    by = _by_crop(_results(client.get('/api/experiences/recommendations?lat=36.8&lon=127.3')))
    assert by['딸기']['thumbnail_url'] == '/static/uploads/exp1.jpg'
    assert by['사과']['thumbnail_url'] == DEFAULT_THUMBNAIL_URL


def test_course_includes_thumbnail_url(client):
    # 주변 장소를 못 가져와도(외부 API 없음) 카드는 그려지므로 사진이 있어야 한다
    res = client.get('/api/experiences/1/course')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data['thumbnail_url'] == '/static/uploads/exp1.jpg'


def test_course_thumbnail_falls_back_to_default(client):
    data = client.get('/api/experiences/3/course').get_json()['data']
    assert data['thumbnail_url'] == DEFAULT_THUMBNAIL_URL


def test_search_includes_thumbnail_url(client):
    # /api/search 는 success_response 봉투가 아니라 평평한 구조로 응답한다
    body = client.get('/api/search').get_json()
    assert body['success'], body
    by = {item['crop']: item for item in body['items']}
    assert by['딸기']['thumbnail_url'] == '/static/uploads/exp1.jpg'
    assert by['포도']['thumbnail_url'] == '/static/uploads/farm2.jpg'
    assert by['사과']['thumbnail_url'] == DEFAULT_THUMBNAIL_URL
    # 선행 콤마가 있어도 파일명만 정확히 뽑혀야 한다
    assert by['딸기']['first_image'] == 'exp1.jpg'


def test_contract_never_null(client):
    """어떤 API를 타든 thumbnail_url 은 null 이 아니고 완전한 경로여야 한다."""
    urls = [
        '/api/recommendations/personalized',
        '/api/experiences/recommendations?lat=36.8&lon=127.3',
    ]
    for url in urls:
        for row in _results(client.get(url)):
            assert row['thumbnail_url'] is not None, url
            assert row['thumbnail_url'].startswith('/static/'), url


def test_default_image_file_exists():
    """기본 이미지 경로가 실제 파일을 가리켜야 한다(깨진 링크 방지)."""
    path = os.path.join(flask_app.static_folder,
                        DEFAULT_THUMBNAIL_URL.replace('/static/', '', 1))
    assert os.path.exists(path), path
