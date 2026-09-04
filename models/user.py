# models/user.py — 회원(User) 엔티티
from models.base import db

class User(db.Model):
    __tablename__ = 'user'

    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='experiencer') # experiencer, farmer, volunteer
    name = db.Column(db.String(100), nullable=True) # 가입 시 누락으로 인한 500 에러 방지
    phone = db.Column(db.String(50), nullable=True)
    
    # 레거시 단일 농장 필드 (하위 호환 유지)
    farm_address = db.Column(db.String(255), nullable=True)
    farm_size = db.Column(db.String(100), nullable=True)
    farm_image = db.Column(db.String(255), nullable=True)
    farmer_certificate_pdf = db.Column(db.String(255), nullable=True)
    verification_status = db.Column(db.String(50), nullable=False, default='verified') # verified, pending, unverified

    profile_image = db.Column(db.String(255), nullable=False, default='shd.png')
    profile_bio = db.Column(db.String(150), nullable=True)

    # 추천 및 통계용 프로필
    age_group = db.Column(db.String(20), nullable=True)
    gender = db.Column(db.String(10), nullable=True)
    birthdate = db.Column(db.String(20), nullable=True)
    family_type = db.Column(db.String(20), nullable=True)
    interest_activities = db.Column(db.String(255), nullable=True)
    preferred_transport = db.Column(db.String(20), nullable=True)

    # 관계 설정
    applications = db.relationship('Application', back_populates='user', cascade="all, delete-orphan")
    experiences = db.relationship('Experience', back_populates='farmer', cascade="all, delete-orphan")