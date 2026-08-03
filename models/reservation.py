# models/reservation.py — 예약/신청(Application) 엔티티. 클래스명은 기존 Application을 그대로 유지한다.
from models.base import db


class Application(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    applicant_name = db.Column(db.String(100), nullable=False)
    phone_number = db.Column(db.String(50), nullable=False)
    participants_count = db.Column(db.Integer, nullable=False, default=1)
    count_adult = db.Column(db.Integer, default=0)
    count_teen = db.Column(db.Integer, default=0)
    count_child = db.Column(db.Integer, default=0)
    apply_date = db.Column(db.Date, nullable=False)
    apply_time = db.Column(db.String(50), nullable=False)
    status = db.Column(db.String(50), nullable=False, default='예정')
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experience_id = db.Column(db.Integer, db.ForeignKey('experience.id'), nullable=False)
    can_review = db.Column(db.Boolean, default=False)
    user = db.relationship('User', back_populates='applications')
    experience = db.relationship('Experience', back_populates='applications')
