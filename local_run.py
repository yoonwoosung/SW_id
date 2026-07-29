"""로컬 시연용 실행 스크립트.

app.py 는 전혀 수정하지 않는다. 대신 Flask-SQLAlchemy 엔진만 런타임에
로컬 SQLite 로 교체해서, 운영 MySQL 에 붙지 않고 로컬에서 띄운다.

실행:  이 파일을 그대로 실행(IDE Run 버튼 또는 `python local_run.py`).
       환경변수(.env)가 없어도 아래 기본값으로 로컬 구동된다.
접속:  http://127.0.0.1:8000/
"""
import os

# app.py 는 import 시점에 SECRET_KEY / DB_* 환경변수를 읽으므로,
# `import app` 보다 먼저 로컬 기본값을 채워준다(.env가 있으면 그 값이 우선).
os.environ.setdefault('SECRET_KEY', 'localdemo')
os.environ.setdefault('DB_USERNAME', 'x')
os.environ.setdefault('DB_PASSWORD', 'x')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_NAME', 'x')

from datetime import date, timedelta
from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine
import app as farmlink

flask_app = farmlink.app
db = farmlink.db
User = farmlink.User
Experience = farmlink.Experience

SQLITE_URI = 'sqlite:////tmp/farmlink_demo.db'

with flask_app.app_context():
    # 운영 MySQL 엔진을 로컬 SQLite 엔진으로 교체 (app.py 미변경)
    flask_app.extensions['sqlalchemy'].engines[None] = create_engine(SQLITE_URI)
    db.create_all()

    if Experience.query.count() == 0:
        farmer = User(
            nickname='데모농장', email='demo@farmlink.local',
            password=generate_password_hash('demo1234', method='pbkdf2:sha256'),
            role='farmer', name='홍길동', phone='010-0000-0000',
        )
        db.session.add(farmer)
        db.session.commit()

        today = date.today()
        seeds = [
            dict(crop='쌀', location='경기도 이천', address_detail='경기도 이천시 부발읍',
                 lat=37.27, lng=127.44, cost=30000, max_participants=20, current_participants=5,
                 has_parking=True),
            dict(crop='포도', location='경기도 안성', address_detail='경기도 안성시 서운면',
                 lat=37.01, lng=127.27, cost=25000, max_participants=20, current_participants=15,
                 has_parking=True, barrier_free=True),
            dict(crop='잣', location='경기도 가평', address_detail='경기도 가평군 상면',
                 lat=37.83, lng=127.51, cost=40000, max_participants=20, current_participants=0),
        ]
        for s in seeds:
            db.session.add(Experience(
                farmer_id=farmer.id, status='recruiting',
                duration_start=today + timedelta(days=7),
                end_date=today + timedelta(days=30),
                **s,
            ))
        db.session.commit()
        print(f"[seed] 농장주 1명 + 체험 {len(seeds)}건 생성")
    else:
        print(f"[seed] 기존 데이터 사용 (체험 {Experience.query.count()}건)")

if __name__ == '__main__':
    print("로컬 서버 시작: http://127.0.0.1:8000/")
    flask_app.run(host='127.0.0.1', port=8000, debug=False, use_reloader=False)
