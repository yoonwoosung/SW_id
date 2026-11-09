"""공모전 심사용 역할 전환 — ★허용된 계정만★ 바꿀 수 있어야 한다.

제출 폼에 계정을 하나만 적을 수 있어, 심사위원이 계정 하나로 체험자·농장주·
관리자 화면을 모두 봐야 한다. 권한 판정이 전부 session['role'] 하나를 보므로
세션 값만 바꾸면 기존 게이트 38곳이 그대로 따라온다(게이트 미변경).

★그래서 누가 바꿀 수 있는지가 유일한 방어선이다.★ 공모전 지정 비밀번호는
제출 서류에 공개되므로, 아무나 전환할 수 있으면 농장 승인·반려까지 뚫린다.
"""
import pytest
from werkzeug.security import generate_password_hash

import app as farmlink
from models import db, User
from common.constants import ROLE_SWITCH_ALLOWED_EMAILS, ROLE_SWITCH_ROLES

PASSWORD = "pw12345678"
ALLOWED_EMAIL = ROLE_SWITCH_ALLOWED_EMAILS[0]


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


def _login(client, email):
    return client.post('/login', data={'email': email, 'password': PASSWORD})


def _session_role(client):
    with client.session_transaction() as sess:
        return sess.get('role')


# ───────────────────── 허용 계정 ─────────────────────

@pytest.mark.parametrize('role', [code for code, _label in ROLE_SWITCH_ROLES])
def test_allowed_account_can_switch_to_every_role(client, role):
    _user(ALLOWED_EMAIL)
    _login(client, ALLOWED_EMAIL)
    client.get(f'/switch-role/{role}')
    assert _session_role(client) == role


def test_switch_does_not_change_the_stored_role(client):
    """★DB 는 그대로 둔다.★ 세션만 바꾼다 — 계정 자체가 관리자가 되면 안 된다."""
    user = _user(ALLOWED_EMAIL)
    _login(client, ALLOWED_EMAIL)
    client.get('/switch-role/admin')
    assert _session_role(client) == 'admin'
    assert User.query.get(user.id).role == 'experiencer'


def test_switch_lands_on_the_matching_home(client):
    """전환하면 그 역할의 첫 화면으로 보낸다(심사위원이 헤매지 않게)."""
    _user(ALLOWED_EMAIL)
    _login(client, ALLOWED_EMAIL)
    assert '/admin/farms/audit' in client.get('/switch-role/admin').headers['Location']
    assert '/easy_mode' in client.get('/switch-role/farmer').headers['Location']


# ───────────────────── 차단 ─────────────────────

def test_other_account_cannot_switch(client):
    """★일반 계정이 URL 을 직접 쳐도 거부된다.★"""
    _user('normal@example.com')
    _login(client, 'normal@example.com')
    client.get('/switch-role/admin')
    assert _session_role(client) == 'experiencer'


def test_team_admin_account_cannot_switch(client):
    """팀이 쓰는 관리자 계정도 목록에 없으면 전환 대상이 아니다."""
    _user('admin@farmlink.com', role='admin')
    _login(client, 'admin@farmlink.com')
    client.get('/switch-role/farmer')
    assert _session_role(client) == 'admin'


def test_anonymous_cannot_switch(client):
    res = client.get('/switch-role/admin')
    assert res.status_code == 302
    assert '/login' in res.headers['Location']
    assert _session_role(client) is None


def test_unknown_role_is_rejected(client):
    """목록에 없는 역할로는 바꿀 수 없다."""
    _user(ALLOWED_EMAIL)
    _login(client, ALLOWED_EMAIL)
    client.get('/switch-role/superuser')
    assert _session_role(client) == 'experiencer'


def test_switching_twice_does_not_bypass_the_check(client):
    """★자격 판정은 세션이 아니라 DB 의 이메일로 한다.★

    세션 role 로 판정하면 한 번 admin 이 된 뒤에는 계속 통과한다.
    """
    _user('normal@example.com')
    _login(client, 'normal@example.com')
    with client.session_transaction() as sess:
        sess['role'] = 'admin'          # 세션이 조작된 상황을 가정
    client.get('/switch-role/farmer')
    # 조작된 값이 그대로 남을 뿐, 전환은 거부된다.
    assert _session_role(client) == 'admin'


# ───────────────────── 메뉴 노출 ─────────────────────

def test_menu_hidden_for_other_accounts(client):
    _user('normal@example.com')
    _login(client, 'normal@example.com')
    assert '로 보기' not in client.get('/ai-recommend').get_data(as_text=True)


def test_menu_shown_for_allowed_account(client):
    _user(ALLOWED_EMAIL)
    _login(client, ALLOWED_EMAIL)
    html = client.get('/ai-recommend').get_data(as_text=True)
    assert '현재: 체험자' in html          # ★지금 어느 역할인지 보여준다★
    assert '농장주로 보기' in html
    assert '관리자로 보기' in html
    assert '체험자로 보기' not in html     # 지금 보고 있는 역할은 빼고 그린다


def test_menu_shows_the_current_role_after_switching(client):
    _user(ALLOWED_EMAIL)
    _login(client, ALLOWED_EMAIL)
    client.get('/switch-role/admin')
    html = client.get('/ai-recommend').get_data(as_text=True)
    assert '현재: 관리자' in html
    assert '체험자로 보기' in html
