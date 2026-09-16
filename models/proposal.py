# models/proposal.py — 농장주가 사용자 요청글에 보낸 제안(어느 요청글에, 어느 농장이, 어떤 내용).
from datetime import datetime

from models.base import db


class Proposal(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    request_id = db.Column(db.Integer, db.ForeignKey('user_request.id'), nullable=False)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # 제안한 농장주
    experience_id = db.Column(db.Integer, db.ForeignKey('experience.id'), nullable=True)  # 제안 대상 체험(선택)
    message = db.Column(db.Text, nullable=False)
    proposed_price = db.Column(db.Integer, nullable=True)
    proposed_date = db.Column(db.Date, nullable=True)
    status = db.Column(db.String(50), nullable=False, default='pending')  # pending/accepted/rejected
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    request = db.relationship('UserRequest', back_populates='proposals')
    # 단방향 참조(건태 User·Experience 모델은 수정하지 않는다).
    farmer = db.relationship('User')
    experience = db.relationship('Experience')
