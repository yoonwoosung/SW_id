# common/context.py — Jinja 템플릿에 주입되는 전역 값(context processor) 모음.
import json

from flask import current_app

from common.constants import (
    SURPLUS_DEFAULT_DISCOUNT_PERCENT,
    SURPLUS_DISCOUNT_TIERS,
    SURPLUS_UNIT_CONVERSION,
)
from services.experience_validator import ribbon_text

# 등록 화면 JS 가 할인율·최대 체험료를 즉시 계산하는 데 쓰는 구간표.
# 파이썬 상수를 그대로 내보내 화면과 서버가 같은 표를 본다(JS 에 숫자를 다시
# 적어 두면 구간을 고칠 때 한쪽만 바뀐다). 서버는 어차피 저장 전에 다시 검증한다.
SURPLUS_TIERS_JSON = json.dumps({
    'tiers': SURPLUS_DISCOUNT_TIERS,
    'conversion': SURPLUS_UNIT_CONVERSION,
    'default': SURPLUS_DEFAULT_DISCOUNT_PERCENT,
}, ensure_ascii=False)


def inject_globals():
    # 카카오 지도 키를 템플릿에 하드코딩하지 않고 환경변수로 주입한다.
    return {
        'KAKAO_API_KEY': current_app.config.get('KAKAO_API_KEY'),
        'KAKAO_JS_KEY': current_app.config.get('KAKAO_JS_KEY'),
        # 과생산 할인 리본 문구("사유 30%"). 템플릿마다 계산식을 흩지 않으려고 주입한다.
        'ribbon_text': ribbon_text,
        'SURPLUS_TIERS_JSON': SURPLUS_TIERS_JSON,
        }
