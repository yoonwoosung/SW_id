# models/user_request.py — 사용자 요청글(역제안). 원하는 조건(카테고리 선택)과 일자·인원을 담는다.
from datetime import datetime

from models.base import db


class UserRequest(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 요청 올린 체험자
    title = db.Column(db.String(200), nullable=False)
    conditions = db.Column(db.Text, nullable=True)  # 파트2 선택조건 JSON 문자열
    desired_date_start = db.Column(db.Date, nullable=True)
    desired_date_end = db.Column(db.Date, nullable=True)
    participants = db.Column(db.Integer, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='open')  # open/matched/closed
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    # 단방향 참조(건태 User 모델은 수정하지 않는다).
    user = db.relationship('User')
    proposals = db.relationship('Proposal', back_populates='request', cascade="all, delete-orphan")
