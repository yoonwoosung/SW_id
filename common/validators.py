# common/validators.py — 입력 검증 유틸(업로드 파일 확장자 허용 여부 등).
from flask import current_app


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in current_app.config['ALLOWED_EXTENSIONS']
