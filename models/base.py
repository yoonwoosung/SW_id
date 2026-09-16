# models/base.py — SQLAlchemy 확장 인스턴스(db)를 정의한다. 모든 모델이 이 db를 공유한다.
from flask_sqlalchemy import SQLAlchemy

# 기존 app.py의 `db = SQLAlchemy(app, engine_options={"pool_pre_ping": True})` 에서
# 엔진 옵션은 그대로 유지하고, 앱 바인딩만 팩토리(create_app)의 db.init_app(app)으로 넘긴다.
db = SQLAlchemy(engine_options={"pool_pre_ping": True})
