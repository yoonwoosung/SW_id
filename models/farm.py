# models/farm.py — 농장주 농장 정보 엔티티 (FE + BE 병합본)
from datetime import datetime
from models.base import db

class Farm(db.Model):
    __tablename__ = 'farm'

    id = db.Column(db.Integer, primary_key=True)
    
    # [외래키] BE와 통일감을 위해 user_id 사용 (FE routes에서 user_id로 매핑 필요)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    # [BE 필드] 농장 이름 (FE에서 미입력 시 에러 방지를 위해 nullable=True로 설정 권장)
    name = db.Column(db.String(100), nullable=True)
    
    # [공통 필드] 주소 및 증빙 서류
    address = db.Column(db.String(255), nullable=False)
    certificate_pdf = db.Column(db.String(255), nullable=True)
    
    # [BE 필드] 카카오 지오코딩 및 지도 좌표
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    
    # [FE 필드] 농장 규모 및 친환경 인증 정보
    size = db.Column(db.String(100), nullable=True)
    is_organic = db.Column(db.Boolean, default=False)
    organic_cert_image = db.Column(db.String(255), nullable=True)
    organic_cert_type = db.Column(db.String(100), nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # [관계 설정] User 모델 연동 (Cascade 옵션 포함)
    user = db.relationship('User', backref=db.backref('farms', cascade="all, delete-orphan", lazy=True))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uq_farm_user_name'),
    )