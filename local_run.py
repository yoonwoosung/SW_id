"""로컬 시연용 실행 스크립트.

app.py 는 전혀 수정하지 않는다. 대신 Flask-SQLAlchemy 엔진만 런타임에
로컬 SQLite 로 교체해서, 운영 MySQL 에 붙지 않고 로컬에서 띄운다.

실행:  python local_run.py
접속:  http://127.0.0.1:8000/

--- 공용 로그인 계정 ---
  일반 사용자: user@farmlink.com   / 12341234
  농장주:      farmer@farmlink.com / 12341234

초기화: rm farmlink_demo.db && python local_run.py
"""
import os

# .env 없어도 로컬에서 돌아가도록 기본값 세팅
os.environ.setdefault('SECRET_KEY', 'localdemo')
os.environ.setdefault('DB_USERNAME', 'x')
os.environ.setdefault('DB_PASSWORD', 'x')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_NAME', 'x')

import json
from datetime import date, timedelta, datetime
from werkzeug.security import generate_password_hash
from sqlalchemy import create_engine
import app as farmlink
from models import db, User, Experience, Review, Inquiry, Application, InquiryReply, Farm
from services.farm_service import backfill_default_farms

flask_app = farmlink.app
SQLITE_URI = 'sqlite:///farmlink_demo.db'
PW = generate_password_hash('12341234', method='pbkdf2:sha256')
today = date.today()


def seed():
    with flask_app.app_context():
        # 운영 MySQL 엔진을 로컬 SQLite 엔진으로 교체
        flask_app.extensions['sqlalchemy'].engines[None] = create_engine(SQLITE_URI)
        db.create_all()

        if User.query.filter_by(email='farmer@farmlink.com').first():
            print(f"[seed] 기존 데이터 사용 (체험 {Experience.query.count()}건, 예약 {Application.query.count()}건)")
        else:
            # ── 1. 계정 생성 ───────────────────────────────────────────
            farmer = User(
                nickname='초록농장', email='farmer@farmlink.com', password=PW,
                role='farmer', name='김농부', phone='010-1234-5678',
                farm_address='경기도 이천시 부발읍 아미리 123', farm_size='3,000평',
                profile_bio='직접 키운 신선한 농산물로 가족과 함께하는 체험을 제공합니다.',
                verification_status='verified',
            )
            farmer2 = User(
                nickname='햇살농원', email='farmer2@farmlink.com', password=PW,
                role='farmer', name='박농부', phone='010-9876-5432',
                farm_address='경상북도 상주시 낙동면 신상리 45', farm_size='5,000평',
                profile_bio='상주 곶감과 샤인머스캣으로 유명한 햇살농원입니다.',
                verification_status='verified',
            )
            user = User(
                nickname='여행하는준형', email='user@farmlink.com', password=PW,
                role='experiencer', name='강준형', phone='010-0000-1111',
                verification_status='verified',
            )
            db.session.add_all([farmer, farmer2, user])
            db.session.commit()

            # ── 2. 체험 생성 ───────────────────────────────────────────
            tt = json.dumps([
                {"time": "10:00", "available": True},
                {"time": "13:00", "available": True},
                {"time": "15:00", "available": True},
            ])

            exp_list = [
                Experience(
                    farmer_id=farmer.id, crop='딸기', location='경기도 이천',
                    address_detail='경기도 이천시 마장면 덕평리 88',
                    lat=37.22, lng=127.43, cost=25000,
                    max_participants=20, current_participants=8,
                    duration_start=today + timedelta(days=3),
                    end_date=today + timedelta(days=30), status='recruiting',
                    pesticide_free=True, has_parking=True,
                    notes='수확한 딸기는 1인당 500g 직접 가져가실 수 있습니다.',
                    includes='입장료, 체험 도구, 500g 포장 용기',
                    excludes='추가 구매 딸기',
                    timetable_data=tt, phone='010-1234-5678', farm_size='1,000평',
                ),
                Experience(
                    farmer_id=farmer.id, crop='감자', location='경기도 양평',
                    address_detail='경기도 양평군 양동면 계정리 12',
                    lat=37.48, lng=127.71, cost=18000,
                    max_participants=30, current_participants=12,
                    duration_start=today + timedelta(days=7),
                    end_date=today + timedelta(days=45), status='recruiting',
                    pesticide_free=False, has_parking=True,
                    notes='황토밭에서 직접 캐는 감자 캐기 체험. 아이들과 함께 오세요!',
                    includes='입장료, 장갑, 바구니',
                    excludes='식사',
                    timetable_data=tt, phone='010-1234-5678', farm_size='2,000평',
                ),
                Experience(
                    farmer_id=farmer.id, crop='토마토', location='경기도 광주',
                    address_detail='경기도 광주시 퇴촌면 원당리 55',
                    lat=37.41, lng=127.36, cost=20000,
                    max_participants=25, current_participants=3,
                    duration_start=today + timedelta(days=5),
                    end_date=today + timedelta(days=35), status='recruiting',
                    pesticide_free=True, has_parking=True,
                    notes='비닐하우스 완숙 토마토 수확 체험. 어린이 교육 프로그램 포함.',
                    includes='입장료, 체험 앞치마, 수확 키트',
                    excludes='추가 구매',
                    timetable_data=tt, phone='010-1234-5678', farm_size='800평',
                ),
                Experience(
                    farmer_id=farmer2.id, crop='포도', location='경상북도 상주',
                    address_detail='경상북도 상주시 낙동면 신상리 45',
                    lat=36.42, lng=128.16, cost=28000,
                    max_participants=20, current_participants=18,
                    duration_start=today + timedelta(days=2),
                    end_date=today + timedelta(days=25), status='recruiting',
                    pesticide_free=False, has_parking=True, barrier_free=True,
                    notes='상주 대표 특산물 샤인머스캣! 당도 높은 포도를 직접 수확해 보세요.',
                    includes='입장료, 포도 1송이 포장',
                    excludes='추가 구매',
                    timetable_data=tt, phone='010-9876-5432', farm_size='2,000평',
                ),
            ]
            db.session.add_all(exp_list)
            db.session.commit()

            strawberry, potato, tomato, grape = exp_list

            # ── 3. 예약 생성 (간편모드 수락/거절 테스트용) ─────────────
            apps = [
                Application(
                    user_id=user.id, experience_id=strawberry.id,
                    applicant_name='강준형', phone_number='010-0000-1111',
                    participants_count=2, count_adult=2, count_teen=0, count_child=0,
                    apply_date=today + timedelta(days=5), apply_time='10:00',
                    status='예정', can_review=False,
                ),
                Application(
                    user_id=user.id, experience_id=potato.id,
                    applicant_name='강준형', phone_number='010-0000-1111',
                    participants_count=4, count_adult=2, count_teen=1, count_child=1,
                    apply_date=today + timedelta(days=12), apply_time='13:00',
                    status='예정', can_review=False,
                ),
                Application(
                    user_id=user.id, experience_id=strawberry.id,
                    applicant_name='강준형', phone_number='010-0000-1111',
                    participants_count=2, count_adult=2, count_teen=0, count_child=0,
                    apply_date=today - timedelta(days=5), apply_time='10:00',
                    status='확정', can_review=True,
                ),
            ]
            db.session.add_all(apps)

            # ── 4. 후기 생성 (AI 리포트 분석 테스트용) ──────────────────
            reviews = [
                Review(
                    user_id=user.id, experience_id=strawberry.id, rating=5,
                    content='딸기가 정말 달고 수확 체험도 재밌었습니다. 아이가 너무 좋아해서 다음에도 꼭 오고 싶네요!',
                    timestamp=datetime.utcnow() - timedelta(days=4),
                ),
            ]
            db.session.add_all(reviews)

            # ── 5. 문의 생성 (답변 작성 테스트용) ──────────────────────
            inquiries = [
                Inquiry(
                    user_id=user.id, experience_id=strawberry.id,
                    content='유아(36개월)도 참여 가능한가요? 유모차 반입 가능한지도 알고 싶습니다.',
                    is_private=False,
                    timestamp=datetime.utcnow() - timedelta(days=2),
                ),
            ]
            db.session.add_all(inquiries)
            db.session.commit()

            print(f"[seed] 계정 3명 / 체험 {len(exp_list)}건 / 예약 {len(apps)}건 / 후기 {len(reviews)}건 / 문의 {len(inquiries)}건 생성 완료")

        # ── 6. 농장 백필 이관 실행 (백엔드 로직 유지) ─────────────────
        linked = backfill_default_farms()
        print(f"[migrate] 기본 농장 백필: 체험 {linked}건 연결")

        print("\n  공용 로그인 계정")
        print("  일반 사용자: user@farmlink.com   / 12341234")
        print("  농장주:      farmer@farmlink.com / 12341234\n")


seed()

if __name__ == '__main__':
    print("로컬 서버 시작: http://127.0.0.1:8000/")
    flask_app.run(host='127.0.0.1', port=8000, debug=False, use_reloader=False)