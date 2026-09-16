# models/point_log.py — 포인트 적립·사용 내역. 잔액은 이 내역의 SUM(amount)으로 계산한다.
# backref로 관계를 정의해 User 모델 파일은 수정하지 않는다.
from datetime import datetime

from models.base import db


class PointLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    amount = db.Column(db.Integer, nullable=False)            # 적립 +, 사용 -
    reason = db.Column(db.String(30), nullable=False)         # 사유 코드('payment' 등)
    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=True)  # 적립 근거 예약(중복 적립 방지)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('point_logs', cascade="all, delete-orphan"))
