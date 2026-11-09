# common/context.py — Jinja 템플릿에 주입되는 전역 값(context processor) 모음.
import json

from flask import current_app, session

from common.constants import (
    ROLE_SWITCH_ALLOWED_EMAILS,
    ROLE_SWITCH_ROLES,
    SURPLUS_DEFAULT_DISCOUNT_PERCENT,
    SURPLUS_DISCOUNT_TIERS,
    SURPLUS_UNIT_CONVERSION,
)
from services.experience_validator import discount_percent, ribbon_text, shows_surplus

# 등록 화면 JS 가 할인율·최대 체험료를 즉시 계산하는 데 쓰는 구간표.
# 파이썬 상수를 그대로 내보내 화면과 서버가 같은 표를 본다(JS 에 숫자를 다시
# 적어 두면 구간을 고칠 때 한쪽만 바뀐다). 서버는 어차피 저장 전에 다시 검증한다.
SURPLUS_TIERS_JSON = json.dumps({
    'tiers': SURPLUS_DISCOUNT_TIERS,
    'conversion': SURPLUS_UNIT_CONVERSION,
    'default': SURPLUS_DEFAULT_DISCOUNT_PERCENT,
}, ensure_ascii=False)


def can_switch_role():
    """로그인한 계정이 공모전 심사용 역할 전환을 쓸 수 있는가.

    ★세션이 아니라 DB 의 이메일로 판정한다.★ 세션의 role 은 전환으로 바뀌는
    값이라 그것으로 자격을 보면 한 번 바꾼 뒤 계속 통과한다.
    메뉴를 그릴지 정하는 용도이고, 실제 차단은 routes/auth.switch_role 이 한다.
    """
    if 'user_id' not in session or not ROLE_SWITCH_ALLOWED_EMAILS:
        return False
    from models import User
    user = User.query.get(session['user_id'])
    return bool(user and user.email in ROLE_SWITCH_ALLOWED_EMAILS)


def current_role_label():
    """지금 보고 있는 역할의 한글 표기. 심사위원이 헷갈리지 않게 화면에 띄운다."""
    return dict(ROLE_SWITCH_ROLES).get(session.get('role'), '체험자')


def inject_globals():
    # 카카오 지도 키를 템플릿에 하드코딩하지 않고 환경변수로 주입한다.
    return {
        # 공모전 심사용 역할 전환 메뉴. 허용 계정이 아니면 아예 그리지 않는다.
        'can_switch_role': can_switch_role,
        'current_role_label': current_role_label,
        'ROLE_SWITCH_ROLES': ROLE_SWITCH_ROLES,
        'KAKAO_API_KEY': current_app.config.get('KAKAO_API_KEY'),
        'KAKAO_JS_KEY': current_app.config.get('KAKAO_JS_KEY'),
        # 과생산 할인 리본 문구("사유 30%"). 템플릿마다 계산식을 흩지 않으려고 주입한다.
        'ribbon_text': ribbon_text,
        # 상세 배지도 리본과 같은 값·같은 조건을 쓰게 한다.
        # 템플릿에서 따로 계산·판정하면 같은 체험이 화면마다 달라진다.
        'discount_percent': discount_percent,
        'shows_surplus': shows_surplus,
        'SURPLUS_TIERS_JSON': SURPLUS_TIERS_JSON,
        }
