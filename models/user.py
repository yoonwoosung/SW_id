# models/user.py — 회원(User) 엔티티. 체험자·농장주 공통 계정 정보를 담는다.
from models.base import db


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='experiencer')
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    farm_address = db.Column(db.String(255), nullable=True)
    farm_size = db.Column(db.String(100), nullable=True)
    profile_image = db.Column(db.String(255), nullable=False, default='shd.png')
    farm_image = db.Column(db.String(255), nullable=True)
    profile_bio = db.Column(db.String(150), nullable=True)
    farmer_certificate_pdf = db.Column(db.String(255), nullable=True) # 농업인 증명서 PDF
    # highlight-start
    verification_status = db.Column(db.String(50), nullable=False, default='verified') # 인증 상태 컬럼 추가
    # highlight-end
    # 자동 추천 근거용 프로필(파트2). 전부 선택 입력(nullable) → 없으면 인기순 폴백.
    age_group = db.Column(db.String(20), nullable=True)            # 연령대 코드(10s, 20s, ...). 생년월일은 저장하지 않음.
    gender = db.Column(db.String(10), nullable=True)              # male/female/other (민감정보, 선택)
    family_type = db.Column(db.String(20), nullable=True)         # single/couple/family/friends
    interest_activities = db.Column(db.String(255), nullable=True)  # activity 코드 CSV(harvest,fishing)
    preferred_transport = db.Column(db.String(20), nullable=True)  # transport 코드(car, public_transit, ...)
    applications = db.relationship('Application', back_populates='user', cascade="all, delete-orphan")
    experiences = db.relationship('Experience', back_populates='farmer', cascade="all, delete-orphan")
