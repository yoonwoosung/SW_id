# models/farm.py
from datetime import datetime
from models.base import db

class Farm(db.Model):
    __tablename__ = 'farm'

    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    
    name = db.Column(db.String(100), nullable=True)
    address = db.Column(db.String(255), nullable=False)
    address_detail = db.Column(db.String(255), nullable=True)
    certificate_pdf = db.Column(db.String(255), nullable=True)
    
    lat = db.Column(db.Float, nullable=True)
    lng = db.Column(db.Float, nullable=True)
    size = db.Column(db.String(100), nullable=True)
    
    is_organic = db.Column(db.Boolean, default=False)
    organic_cert_image = db.Column(db.String(255), nullable=True)
    organic_cert_type = db.Column(db.String(100), nullable=True)
    
    status = db.Column(db.String(20), nullable=False, default='PENDING')  # PENDING, APPROVED, REJECTED
    reject_reason = db.Column(db.Text, nullable=True)
    
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = db.relationship('User', backref=db.backref('farms', cascade="all, delete-orphan", lazy=True))

    __table_args__ = (
        db.UniqueConstraint('user_id', 'name', name='uq_farm_user_name'),
    )