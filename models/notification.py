# models/notification.py — 스마트 알림(Notification) 엔티티
from datetime import datetime
from models.base import db

class Notification(db.Model):
    __tablename__ = 'notification'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    message = db.Column(db.Text, nullable=False)
    # 알림 타입: 'reservation_accepted', 'reservation_rejected', 'price_tip', 'inquiry'
    notif_type = db.Column(db.String(50), nullable=True, default='general') 
    link_url = db.Column(db.String(255), nullable=True) # 클릭 시 이동할 URL
    
    is_read = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('notifications', lazy=True, cascade="all, delete-orphan"))