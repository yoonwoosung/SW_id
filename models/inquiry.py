# models/inquiry.py — 문의(Inquiry) 엔티티. 체험자가 농장주에게 남기는 문의글.
from datetime import datetime

from models.base import db


class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experience_id = db.Column(db.Integer, db.ForeignKey('experience.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('inquiries', lazy=True))
