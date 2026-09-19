# common/context.py — Jinja 템플릿에 주입되는 전역 값(context processor) 모음.
from flask import current_app

from services.experience_validator import ribbon_text


def inject_globals():
    # 카카오 지도 키를 템플릿에 하드코딩하지 않고 환경변수로 주입한다.
    return {
        'KAKAO_API_KEY': current_app.config.get('KAKAO_API_KEY'),
        'KAKAO_JS_KEY': current_app.config.get('KAKAO_JS_KEY'),
        # 과생산 할인 리본 문구("사유 30%"). 템플릿마다 계산식을 흩지 않으려고 주입한다.
        'ribbon_text': ribbon_text,
        }
