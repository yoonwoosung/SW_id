import os
from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

# --- 데이터베이스 모델 ---
# 이 모델들은 app.py의 모델과 정확히 일치해야 합니다.
# 별도의 models.py 파일로 분리하여 관리하는 것을 권장합니다.

db = SQLAlchemy()

class Experience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crop = db.Column(db.String(100), nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    timetable_data = db.Column(db.Text, nullable=True)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='recruiting')

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)

class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    # ... (다른 컬럼들은 스케줄링 작업에 필요 없으므로 생략 가능) ...

# --- 스케줄링 작업 함수 ---

def update_experience_status(app):
    """
    모집 기간이 만료된 체험의 상태를 'expired'로 변경하는 함수.
    """
    with app.app_context():
        now = datetime.now()
        recruiting_experiences = Experience.query.filter_by(status='recruiting').all()
        expired_experiences = []
        days_map = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}

        for exp in recruiting_experiences:
            # 모집 마감일이 오늘보다 이전인 경우
            if exp.end_date < now.date():
                expired_experiences.append(exp)
            # 모집 마감일이 오늘인 경우, 마지막 타임슬롯 시간을 확인
            elif exp.end_date == now.date():
                if exp.timetable_data:
                    day_of_week = days_map[exp.end_date.weekday()]
                    slots = exp.timetable_data.split(',')
                    last_time = None
                    for slot in slots:
                        try:
                            day, time_str = slot.split('-')
                            if day == day_of_week:
                                slot_time = datetime.strptime(time_str, '%H:%M').time()
                                if last_time is None or slot_time > last_time:
                                    last_time = slot_time
                        except ValueError:
                            continue # 타임슬롯 형식이 잘못된 경우 건너뜀
                    
                    # 마지막 타임슬롯 시간이 현재 시간보다 이전이면 만료 처리
                    if last_time and now.time() > last_time:
                        expired_experiences.append(exp)

        if expired_experiences:
            for exp in expired_experiences:
                exp.status = 'expired'
                notification = Notification(
                    user_id=exp.farmer_id,
                    message=f"'{exp.crop}' 체험의 모집 기간이 만료되었습니다."
                )
                db.session.add(notification)
            
            db.session.commit()
            print(f"[{datetime.now()}] {len(expired_experiences)}개의 체험을 '기간 만료'로 업데이트했습니다.")
        else:
            print(f"[{datetime.now()}] 상태를 업데이트할 체험이 없습니다.")


# --- 메인 실행 블록 ---

if __name__ == "__main__":
    # Flask 앱 컨텍스트 설정
    app = Flask(__name__)
    
    # app.py와 동일한 데이터베이스 설정을 사용해야 합니다.
    db_username = 'kevin4201'
    db_password = 'farmLink'
    db_hostname = 'kevin4201.mysql.pythonanywhere-services.com'
    db_name     = 'kevin4201$default'
    DATABASE_URI = f"mysql+mysqlconnector://{db_username}:{db_password}@{db_hostname}/{db_name}"

    app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['SQLALCHEMY_POOL_RECYCLE'] = 280
    app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30

    # SQLAlchemy 초기화
    db.init_app(app)

    print("--- 스케줄 작업 시작: 체험 상태 업데이트 ---")
    update_experience_status(app)
    print("--- 스케줄 작업 완료 ---")
