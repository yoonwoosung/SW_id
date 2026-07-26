# common/context.py — Jinja 템플릿에 주입되는 전역 값(context processor) 모음.
from flask import current_app


def inject_globals():
    # 카카오 지도 키를 템플릿에 하드코딩하지 않고 환경변수로 주입한다.
    return {'KAKAO_API_KEY': current_app.config['KAKAO_API_KEY']}
