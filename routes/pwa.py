# routes/pwa.py — PWA 자원을 루트 경로로 서빙한다.
#
# Service Worker 는 자신이 내려온 경로 아래만 제어한다(scope).
# /static/js/sw.js 로 두면 scope 가 /static/js/ 로 제한돼 사이트 전체를 제어하지 못하므로,
# 같은 파일을 /sw.js 로 서빙해 scope 를 / 로 만든다.
# manifest 도 start_url·scope 가 / 인 것과 맞추어 /manifest.json 으로 함께 서빙한다.
import os

from flask import current_app, send_from_directory, make_response


def _static_path():
    return current_app.static_folder


def service_worker():
    """/sw.js — 파일 실체는 static/js/sw.js 하나만 유지한다(중복 사본 금지)."""
    response = make_response(
        send_from_directory(os.path.join(_static_path(), 'js'), 'sw.js')
    )
    response.headers['Content-Type'] = 'application/javascript'
    # 워커 자체가 캐시되면 배포해도 옛 워커가 계속 돌 수 있다.
    response.headers['Cache-Control'] = 'no-cache'
    # scope 를 / 로 넓힌다(정적 경로에서 서빙될 때를 대비한 안전장치).
    response.headers['Service-Worker-Allowed'] = '/'
    return response


def manifest():
    """/manifest.json — 실체는 static/manifest.json."""
    response = make_response(send_from_directory(_static_path(), 'manifest.json'))
    response.headers['Content-Type'] = 'application/manifest+json'
    return response


def register(app):
    app.add_url_rule('/sw.js', 'pwa_service_worker', service_worker)
    app.add_url_rule('/manifest.json', 'pwa_manifest', manifest)
