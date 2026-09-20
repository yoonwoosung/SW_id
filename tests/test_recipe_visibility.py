"""레시피 버튼이 ★체험이 끝난 뒤★ 보이는지 — 내 활동 화면.

예전에는 data-state 에 원본 status 를 넣고 JS 가 "확정"을 찾았다. 그런데
체험이 끝나면 상태가 '확정' → '완료'로 자동 전환되므로 정확히 거꾸로였다.

  체험 전  status='확정'  → 레시피 버튼 보임   (아직 체험을 안 했는데)
  체험 후  status='완료'  → 레시피 버튼 사라짐 (지금 필요한데)

이제 계산된 상태(reservation_state)를 넘긴다. mypage.html 과 같은 규칙이다.
"""
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

import app as farmlink
from models import db, User, Experience, Application
from services.activity_service import STATE_COMPLETED, STATE_CONFIRMED

PASSWORD = "pw12345678"


@pytest.fixture
def client(db_session):
    farmlink.app.secret_key = 'test-secret'
    with farmlink.app.test_client() as c:
        yield c


def _user(email, role='experiencer'):
    user = User(nickname="n", email=email, name="이름", role=role,
                password=generate_password_hash(PASSWORD, method='pbkdf2:sha256'))
    db.session.add(user)
    db.session.commit()
    return user


def _experience(farmer):
    exp = Experience(crop="딸기", location="충남", address_detail="충남 논산시",
                     cost=10000, farmer_id=farmer.id, status='recruiting',
                     duration_start=date.today() - timedelta(days=10),
                     end_date=date.today() + timedelta(days=30),
                     max_participants=10, current_participants=0,
                     lat=36.2, lng=127.1, has_recipe=True,
                     recipe_name="딸기잼", recipe_steps="졸인다")
    db.session.add(exp)
    db.session.commit()
    return exp


def _application(user, exp, status, apply_date, can_review=False):
    app_row = Application(user_id=user.id, experience_id=exp.id, status=status,
                          applicant_name="이름", phone_number="010-0000-0000",
                          apply_date=apply_date, apply_time='10:00',
                          participants_count=2, can_review=can_review)
    db.session.add(app_row)
    db.session.commit()
    return app_row


def _my_info(client, email):
    client.post('/login', data={'email': email, 'password': PASSWORD})
    return client.get('/my_info').get_data(as_text=True)


def _card(state):
    """예약 카드 자체의 마크업. JS 선택자 문자열과 헷갈리지 않게 구분한다."""
    return f'class="mi-res-card" data-state="{state}"' 


def test_finished_reservation_is_marked_completed(client):
    """★체험이 끝났으면 completed 다.★ 레시피 버튼이 여기에 붙는다."""
    user = _user('done@example.com')
    exp = _experience(_user('farmer1@example.com', role='farmer'))
    _application(user, exp, '확정', date.today() - timedelta(days=3))

    html = _my_info(client, 'done@example.com')
    assert _card(STATE_COMPLETED) in html
    assert _card('확정') not in html, "원본 status 를 그대로 내보내면 안 된다"


def test_upcoming_reservation_is_not_completed(client):
    """★체험 전에는 레시피가 뜨면 안 된다.★ 아직 하지도 않았다."""
    user = _user('soon@example.com')
    exp = _experience(_user('farmer2@example.com', role='farmer'))
    _application(user, exp, '확정', date.today() + timedelta(days=5))

    html = _my_info(client, 'soon@example.com')
    assert _card(STATE_CONFIRMED) in html
    assert _card(STATE_COMPLETED) not in html


def test_status_completed_is_also_completed(client):
    """이미 '완료'로 전환된 예약도 당연히 completed 다."""
    user = _user('done2@example.com')
    exp = _experience(_user('farmer3@example.com', role='farmer'))
    _application(user, exp, '완료', date.today() - timedelta(days=1), can_review=True)

    assert _card(STATE_COMPLETED) in _my_info(client, 'done2@example.com')


def test_script_looks_for_the_computed_state(client):
    """★화면과 스크립트가 같은 값을 봐야 한다.★

    템플릿이 계산된 상태를 넣는데 스크립트가 '확정'을 찾으면 영영 못 만난다.
    """
    user = _user('js@example.com')
    exp = _experience(_user('farmer4@example.com', role='farmer'))
    _application(user, exp, '확정', date.today() - timedelta(days=2))

    html = _my_info(client, 'js@example.com')
    assert f'.mi-res-card[data-state="{STATE_COMPLETED}"]' in html
    assert '[data-state="확정"]' not in html


def test_matches_mypage_rule(client):
    """★두 화면이 같은 규칙을 쓴다.★ 예전에는 my_info 만 한글 원본이었다."""
    import io
    mypage = io.open('templates/mypage.html', encoding='utf-8').read()
    my_info = io.open('templates/my_info.html', encoding='utf-8').read()
    marker = f'[data-state="{STATE_COMPLETED}"]'
    assert marker in mypage and marker in my_info
