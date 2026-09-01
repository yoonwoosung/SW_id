# common/auth.py — 라우트 인증/권한 데코레이터.
#   api_login_required : API 라우트용. 비로그인을 공통 형식(403 JSON)으로 막는다.
#   admin_required     : 관리자 화면 라우트용. 비관리자를 리다이렉트한다.
from functools import wraps

from flask import session, redirect, url_for, flash

from common.response import error_response


def api_login_required(view):
    """세션에 user_id가 없으면 403 LOGIN_REQUIRED(JSON)로 응답한다. API 라우트에 사용."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return error_response("LOGIN_REQUIRED", "로그인이 필요합니다.", 403)
        return view(*args, **kwargs)
    return wrapper


ADMIN_ROLE = 'admin'


def is_admin():
    """현재 세션이 관리자인지. 템플릿 주입(common/context.py)에서도 쓴다."""
    return session.get('role') == ADMIN_ROLE


def admin_required(view):
    """관리자 전용 화면 라우트 데코레이터. 위 api_login_required와 달리 화면용(리다이렉트)이다.

    - 비로그인 → 로그인 페이지
    - 로그인했지만 role != 'admin' → 메인으로
    - 세션 role은 로그인 시점 값이므로 DB의 현재 role을 다시 확인한다.
      (관리자 권한이 회수된 뒤 옛 세션으로 접근하는 것을 막는다.)
    """
    @wraps(view)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            flash("로그인이 필요합니다.", "warning")
            return redirect(url_for('login_page'))

        # 지연 import: common/auth.py 가 models를 최상단에서 import하면
        # models → app 초기화 순서와 얽히므로 호출 시점에 가져온다.
        from models import User

        user = User.query.get(session['user_id'])
        if user is None:
            session.clear()
            flash("세션 정보가 유효하지 않습니다.", "warning")
            return redirect(url_for('login_page'))

        if user.role != ADMIN_ROLE:
            flash("관리자만 접근할 수 있습니다.", "danger")
            return redirect(url_for('index'))

        return view(*args, **kwargs)
    return wrapper
