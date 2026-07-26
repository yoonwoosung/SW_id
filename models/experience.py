# models/experience.py — 체험(Experience) 엔티티. 농장주가 등록하는 농촌체험 상품.
from datetime import date

from models.base import db


class Experience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crop = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    address_detail = db.Column(db.String(255), nullable=True)
    pesticide_free = db.Column(db.Boolean, default=False)
    cost = db.Column(db.Integer, nullable=False)
    duration_start = db.Column(db.Date, nullable=True)
    end_date = db.Column(db.Date, nullable=True)
    max_participants = db.Column(db.Integer, default=20)
    current_participants = db.Column(db.Integer, default=0)
    images = db.Column(db.Text, nullable=True)
    lat = db.Column(db.Float, default=36.8583)
    lng = db.Column(db.Float, default=127.2943)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    notes = db.Column(db.Text, nullable=True)
    includes = db.Column(db.Text, nullable=True)
    excludes = db.Column(db.Text, nullable=True)
    timetable_data = db.Column(db.Text, nullable=True)
    phone = db.Column(db.String(50), nullable=True)
    farm_size = db.Column(db.String(100), nullable=True)
    status = db.Column(db.String(50), nullable=False, default='recruiting')
    reviews = db.relationship('Review', backref='experience', lazy=True, cascade="all, delete-orphan")
    inquiries = db.relationship('Inquiry', backref='experience', lazy=True, cascade="all, delete-orphan")
    applications = db.relationship('Application', back_populates='experience', cascade="all, delete-orphan")
    volunteer_needed = db.Column(db.Integer, default=0)
    current_volunteers = db.Column(db.Integer, default=0)
    volunteer_duties = db.Column(db.Text, nullable=True)
    has_parking = db.Column(db.Boolean, default=False, nullable=False)
    organic_certification_image = db.Column(db.String(255), nullable=True)
    organic_certification_type = db.Column(db.String(100), nullable=True)
    farmer = db.relationship('User', back_populates='experiences')

    def to_dict(self):
        return {
            'id': self.id, 'crop': self.crop, 'location': self.location, 'cost': self.cost,
            'duration_start': self.duration_start.strftime('%Y-%m-%d') if self.duration_start else None,
            'end_date': self.end_date.strftime('%Y-%m-%d') if self.end_date else None,
            'lat': self.lat, 'lng': self.lng, 'status': self.status
        }

    @property
    def d_day(self):
        if self.end_date:
            return (self.end_date - date.today()).days
        return 999
