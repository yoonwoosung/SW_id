"""나이·성별 단축버튼 섹션이 실제로 다른 결과를 내는지 — 라우트 통합.

문제였던 것 두 가지:
  1) peers_age·peers_gender 가 apply('peers') 를 재사용해 '가볍게'와 같은 순서였다.
  2) 클릭 집계가 세 섹션 모두 '성별 AND 나이대' 교집합이라, 해당자가 없으면
     0건이 되어 가점이 아예 붙지 않았다.
"""
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

import app as farmlink
from models import db, User, Experience, ClickLog
from services.trend_service import trending_experience_counts

PASSWORD = "pw12345678"


def _user(email, role='experiencer', age=None, gender=None):
    u = User(nickname="n", email=email, name="이름", role=role, age_group=age, gender=gender,
             password=generate_password_hash(PASSWORD, method='pbkdf2:sha256'))
    db.session.add(u)
    db.session.commit()
    return u


def _experience(farmer, crop, cost, cap, parking=False):
    e = Experience(crop=crop, location="충남", address_detail="충남 논산시", cost=cost,
                   farmer_id=farmer.id, status='recruiting', max_participants=cap,
                   current_participants=0, end_date=date.today() + timedelta(days=30),
                   lat=36.2, lng=127.1, has_parking=parking)
    db.session.add(e)
    db.session.commit()
    return e


def _click(user, experience, times):
    for _ in range(times):
        db.session.add(ClickLog(user_id=user.id, target_type='experience',
                                target_id=str(experience.id)))
    db.session.commit()


@pytest.fixture
def world(db_session):
    """20대 남성이 본다. 20대 여성과 50대 남성이 서로 다른 체험을 눌러 뒀다."""
    farmer = _user("f@x.com", 'farmer')
    me = _user("me@x.com", age='20s', gender='male')
    peer_age = _user("w20@x.com", age='20s', gender='female')   # 같은 나이대, 다른 성별
    peer_gender = _user("m50@x.com", age='50s', gender='male')  # 같은 성별, 다른 나이대

    # 가격·정원을 클릭 수와 어긋나게 둔다(역상관이면 우연히 같은 순서가 나온다).
    exps = {
        '딸기': _experience(farmer, '딸기', 10000, 8),
        '포도': _experience(farmer, '포도', 20000, 40, parking=True),
        '사과': _experience(farmer, '사과', 30000, 12),
        '배':   _experience(farmer, '배',   25000, 30, parking=True),
    }
    _click(peer_age, exps['사과'], 10)      # 20대가 많이 누름
    _click(peer_gender, exps['배'], 10)     # 남성이 많이 누름
    return exps


@pytest.fixture
def client(db_session):
    farmlink.app.secret_key = 'test-secret'
    with farmlink.app.test_client() as c:
        yield c


def _login(client, email):
    return client.post('/login', data={'email': email, 'password': PASSWORD})


def _crops(client, segment=None):
    url = '/api/recommendations/personalized?lat=36.2&lon=127.1'
    if segment:
        url += '&segment=' + segment
    return [r['crop'] for r in client.get(url).get_json()['data']['results']]


# ───────────── 클릭 집계가 세그먼트별로 갈리는지 ─────────────

def test_click_counts_split_by_segment(world):
    """★교집합이 아니라 한 축만 본다.★

    20대 남성에게 '20대 AND 남성' 집계를 쓰면 해당자가 없어 0건이 나온다.
    그래서 가점이 안 붙고 섹션이 구분되지 않았다.
    """
    assert trending_experience_counts('male', '20s') == {}, "교집합은 비어 있다"
    assert set(trending_experience_counts(None, '20s')) == {world['사과'].id}
    assert set(trending_experience_counts('male', None)) == {world['배'].id}


# ───────────── 섹션별 결과 ─────────────

def test_age_section_ranks_by_age_group_clicks(client, world):
    """'내 또래가 즐기는 코스' → 같은 나이대가 많이 누른 체험이 1위."""
    _login(client, "me@x.com")
    assert _crops(client, 'peers_age')[0] == '사과'


def test_gender_section_ranks_by_gender_clicks(client, world):
    """'함께 가기 좋은 코스' → 같은 성별이 많이 누른 체험이 1위."""
    _login(client, "me@x.com")
    assert _crops(client, 'peers_gender')[0] == '배'


def test_age_and_gender_sections_differ(client, world):
    """★핵심: 두 단축버튼이 다른 결과를 낸다.★"""
    _login(client, "me@x.com")
    assert _crops(client, 'peers_age') != _crops(client, 'peers_gender')


def test_peer_sections_differ_from_light(client, world):
    """'가볍게'(저렴·근접) 기준을 그대로 쓰지 않는다."""
    _login(client, "me@x.com")
    light = _crops(client, 'peers')
    assert _crops(client, 'peers_age') != light
    assert _crops(client, 'peers_gender') != light


def test_all_sections_are_distinct(client, world):
    """nearby·peers_age·peers_gender·peers·group 5개가 서로 다르다."""
    _login(client, "me@x.com")
    orders = [tuple(_crops(client, s))
              for s in (None, 'peers_age', 'peers_gender', 'peers', 'group')]
    assert len(set(orders)) == 5, orders


def test_light_still_prefers_cheap(client, world):
    """기존 기준은 그대로다 — '가볍게'는 싼 체험이 먼저."""
    _login(client, "me@x.com")
    assert _crops(client, 'peers')[0] == '딸기'      # 10,000원


def test_group_still_prefers_capacity(client, world):
    """'단체로'는 자리 많은 체험이 먼저."""
    _login(client, "me@x.com")
    assert _crops(client, 'group')[0] == '포도'      # 40석 + 주차


# ───────────── 폴백 ─────────────

def test_no_clicks_falls_back_to_base_order(client, db_session):
    """클릭 로그가 하나도 없으면 기본 점수순으로 돌아간다(빈 화면이 되면 안 된다)."""
    farmer = _user("f@x.com", 'farmer')
    _user("me@x.com", age='20s', gender='male')
    _experience(farmer, '딸기', 10000, 8)
    _experience(farmer, '포도', 20000, 40)

    _login(client, "me@x.com")
    assert len(_crops(client, 'peers_age')) == 2
    assert _crops(client, 'peers_age') == _crops(client, None)


def test_anonymous_user_gets_results(client, world):
    """비로그인도 결과가 나온다(프로필이 없어 인기 가점만 빠진다)."""
    assert len(_crops(client, 'peers_age')) == 4


# ---- 근거가 없으면 섹션을 그리지 않는다 (2026-09-20) ----
# 배포 서버 확인: 비로그인 상태에서 '내 주변'·'내 또래'·'함께 가기' 상위 3건이
# [6, 7, 9] 로 전부 같았다. 제목은 또래·성별인데 기준은 기본 점수순이었다.

def test_peer_availability_without_profile():
    from services.segment_service import peer_segment_availability
    assert peer_segment_availability(None) == {'age': False, 'gender': False}


def test_peer_availability_needs_the_matching_field():
    """★나이 섹션은 나이가, 성별 섹션은 성별이 있어야 한다.★

    has_recommendation_profile 은 가족구성·관심활동만 있어도 참이라 기준이
    될 수 없다. 나이대가 없으면 나이 집계가 0건이라 섹션이 '내 주변'과
    같아진다.
    """
    from services.segment_service import peer_segment_availability

    class FakeUser:
        age_group = None
        gender = None

    user = FakeUser()
    assert peer_segment_availability(user) == {'age': False, 'gender': False}

    user.age_group = '20s'
    assert peer_segment_availability(user) == {'age': True, 'gender': False}

    user.gender = 'M'
    assert peer_segment_availability(user) == {'age': True, 'gender': True}


def test_segments_api_exposes_peer_availability(client):
    """프론트가 섹션을 숨길 수 있게 응답에 실어 보낸다."""
    res = client.get('/api/recommendations/segments')
    assert res.status_code == 200
    data = res.get_json()['data']
    assert data['peer_segments'] == {'age': False, 'gender': False}
