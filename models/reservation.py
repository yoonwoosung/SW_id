# models/reservation.py — 예약/신청(Application) 엔티티
from datetime import datetime
from models.base import db

class Application(db.Model):
    __tablename__ = 'application'

    id = db.Column(db.Integer, primary_key=True)
    applicant_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(50), nullable=False)
    
    # 인원수 정보
    participants_count = db.Column(db.Integer, nullable=False, default=1)
    count_adult = db.Column(db.Integer, default=0)
    count_teen = db.Column(db.Integer, default=0)
    count_child = db.Column(db.Integer, default=0)
    
    apply_date = db.Column(db.Date, nullable=False)
    apply_time = db.Column(db.String(50), nullable=False) # e.g. "10:00~12:00"
    
    # 상태값은 common/constants.py 의 APPLICATION_STATUS_* 를 따른다.
    #   '예정'(결제 전) → '결제완료'(농장주 수락 대기) → '확정' → '완료' / '취소'
    # 기본값이 상수(APPLICATION_STATUS_PENDING='예정')와 어긋나 있어 맞춘다.
    status = db.Column(db.String(50), nullable=False, default='예정')
    can_review = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    # 외래키 및 관계
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experience_id = db.Column(db.Integer, db.ForeignKey('experience.id'), nullable=False)

    user = db.relationship('User', back_populates='applications')
    experience = db.relationship('Experience', back_populates='applications')