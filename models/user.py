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

    birthdate = db.Column(db.String(20), nullable=True) # 생년월일 (예: 20000131)
    gender = db.Column(db.String(10), nullable=True)    # 성별 (male / female)
    
    # highlight-end
    applications = db.relationship('Application', back_populates='user', cascade="all, delete-orphan")
    experiences = db.relationship('Experience', back_populates='farmer', cascade="all, delete-orphan")
