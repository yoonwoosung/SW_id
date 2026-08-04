# models/farm.py — 농장(Farm) 엔티티. User 1:N Farm. 농장주가 여러 농장을 등록한다.
# Experience는 farm_id로 Farm에 연결(Experience→Farm→User). backref로 User는 수정하지 않는다.
from datetime import datetime

from models.base import db


class Farm(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    name = db.Column(db.String(100), nullable=False)            # 농장명
    address = db.Column(db.String(255), nullable=False)         # 주소
    lat = db.Column(db.Float, nullable=True)                    # 카카오 지오코딩 위도
    lng = db.Column(db.Float, nullable=True)                    # 경도
    certificate_pdf = db.Column(db.String(255), nullable=True)  # 농장별 증빙 PDF 경로
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('farms', cascade="all, delete-orphan"))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uq_farm_user_name'),
    )
