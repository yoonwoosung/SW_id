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
    farm_id = db.Column(db.Integer, db.ForeignKey('farm.id'), nullable=True)
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
    organic_cert_status = db.Column(db.String(20), nullable=True, default=None)  # None / PENDING / APPROVED / REJECTED
    organic_cert_reject_reason = db.Column(db.Text, nullable=True)
    activity_type = db.Column(db.String(50), nullable=True)
    pet_allowed = db.Column(db.Boolean, default=False, nullable=False)
    pet_max_weight_kg = db.Column(db.Integer, nullable=True)
    has_wifi = db.Column(db.Boolean, default=False, nullable=False)
    barrier_free = db.Column(db.Boolean, default=False, nullable=False)

    # --- 과생산(잉여) 수확 체험 ---
    # 별도 커머스가 아니라 체험의 한 종류다. 방문객이 직접 수확·운반하므로 물류비가 없다.
    # 판매가는 기존 cost 를 그대로 쓴다(결제 흐름 미변경).
    # 남은 수량은 컬럼으로 두지 않고 surplus_qty_total - surplus_qty_taken 으로 계산한다.
    is_surplus = db.Column(db.Boolean, default=False, nullable=False)      # 과생산 체험 여부
    surplus_terms_agreed = db.Column(db.Boolean, default=False, nullable=False)  # 20% 할인 약관 동의
    list_price = db.Column(db.Integer, nullable=True)                     # 정가(1인). cost 가 할인가
    surplus_qty_total = db.Column(db.Integer, nullable=True)              # 총 수량
    surplus_qty_taken = db.Column(db.Integer, default=0, nullable=False)  # 예약된 누적 수량
    surplus_per_person = db.Column(db.Integer, nullable=True)             # 1인당 수확량(단위는 surplus_unit)
    surplus_unit = db.Column(db.String(20), default='kg', nullable=True)  # kg·박스·구좌
    surplus_origin = db.Column(db.String(255), nullable=True)             # 원산지 표시(시도+시군구)
    surplus_reason = db.Column(db.String(20), nullable=True)              # 할인 사유(리본 문구). 선택지 또는 기타 6자

    # 👇 --- 새로 추가된 레시피 전수 기능 --- 👇
    has_recipe = db.Column(db.Boolean, default=False, nullable=False) # 레시피 전수 여부
    recipe_name = db.Column(db.String(255), nullable=True)            # 레시피 이름 (예: 가을 송이버섯 소금구이)
    recipe_ingredients = db.Column(db.Text, nullable=True)            # 재료
    recipe_steps = db.Column(db.Text, nullable=True)                  # 만드는 방법
    recipe_tip = db.Column(db.Text, nullable=True)                    # 팁
    recipe_image = db.Column(db.String(255), nullable=True)           # 업로드된 레시피 사진 경로

    farmer = db.relationship('User', back_populates='experiences')
    farm = db.relationship('Farm', backref='experiences')

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