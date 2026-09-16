# models/review.py — 후기(Review) 엔티티. 체험자가 남기는 별점·후기와 AI 분석 결과.
from datetime import datetime

from models.base import db


class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experience_id = db.Column(db.Integer, db.ForeignKey('experience.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))
    analysis_result = db.Column(db.Text, nullable=True)
