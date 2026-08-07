"""pytest 공용 픽스처. DB가 필요한 테스트는 in-memory SQLite로 격리 실행한다.

app.py 는 import 시점에 SECRET_KEY/DB_* 를 읽으므로 먼저 더미값을 채운 뒤,
Flask-SQLAlchemy 엔진만 런타임에 SQLite 로 교체한다(local_run 과 동일 기법, app.py 미변경).
"""
import os

os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('DB_USERNAME', 'x')
os.environ.setdefault('DB_PASSWORD', 'x')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_NAME', 'x')

import pytest
from sqlalchemy import create_engine

import app as farmlink
from models import db


@pytest.fixture
def db_session():
    flask_app = farmlink.app
    with flask_app.app_context():
        flask_app.extensions['sqlalchemy'].engines[None] = create_engine('sqlite:///:memory:')
        db.create_all()
        try:
            yield db.session
        finally:
            db.session.remove()
            db.drop_all()
