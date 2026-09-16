# models/inquiry_reply.py — 농장주가 문의에 남기는 답변 엔티티.
from datetime import datetime

from models.base import db


class InquiryReply(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    inquiry_id = db.Column(db.Integer, db.ForeignKey('inquiry.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    inquiry = db.relationship('Inquiry', backref=db.backref('replies', lazy=True, cascade='all, delete-orphan'))
