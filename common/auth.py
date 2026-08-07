# common/auth.py — API 라우트용 인증 데코레이터. 비로그인 요청을 공통 형식(403)으로 막는다.
from functools import wraps

from flask import session

from common.response import error_response


def api_login_required(view):
    """세션에 user_id가 없으면 403 LOGIN_REQUIRED(JSON)로 응답한다. API 라우트에 사용."""
    @wraps(view)
    def wrapper(*args, **kwargs):
        if 'user_id' not in session:
            return error_response("LOGIN_REQUIRED", "로그인이 필요합니다.", 403)
        return view(*args, **kwargs)
    return wrapper
