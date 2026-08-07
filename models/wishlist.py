# models/wishlist.py — 찜(Wishlist) 엔티티. 누가 어떤 체험을 언제 찜했는지.
# backref로 관계를 정의해 User·Experience 모델 파일은 수정하지 않는다.
from datetime import datetime

from models.base import db


class Wishlist(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experience_id = db.Column(db.Integer, db.ForeignKey('experience.id'), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('wishlists', cascade="all, delete-orphan"))
    experience = db.relationship('Experience', backref=db.backref('wishlisted_by', cascade="all, delete-orphan"))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'experience_id', name='uq_wishlist_user_experience'),
    )
