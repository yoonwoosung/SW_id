import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
from sqlalchemy.sql import func
from collections import defaultdict
from datetime import date, timedelta, datetime
from sqlalchemy import or_
# from flask_apscheduler import APScheduler
from PIL import Image
import fitz  # PyMuPDF
import re
import pytesseract
import io
import json
import math
from sqlalchemy import case
from types import SimpleNamespace

# Tesseract OCR 경로 설정
pytesseract.pytesseract.tesseract_cmd = '/usr/bin/tesseract'
# --- 1. 앱 및 DB 설정 ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'mysql-secret-key-for-production')

# DB 접속 정보: farmer 기준 로컬 DB 사용.
db_username = 'kevin4201'
db_password = 'farmLink'
db_hostname = 'kevin4201.mysql.pythonanywhere-services.com'
db_name     = 'kevin4201$default'
DATABASE_URI = f"mysql+mysqlconnector://{db_username}:{db_password}@{db_hostname}/{db_name}"


app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_RECYCLE'] = 280
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30

# --- 파일 업로드 설정 ---
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf'} # farmer 기준
app.config['KAKAO_API_KEY'] = os.environ.get('KAKAO_API_KEY', '432f80fcdc8239c7c87db2520e85597e') # farmer 기준

db = SQLAlchemy(app, engine_options={"pool_pre_ping": True})



# 스케줄러 설정 (farmer 기능)
scheduler = APScheduler()
scheduler.init_app(app)
scheduler.start()

REGIONAL_SPECIALTIES = {
    # 경기도
    '이천': ['쌀', '복숭아'],
    '여주': ['쌀', '땅콩', '고구마', '참외'],
    '가평': ['잣', '사과', '포도'],
    '양평': ['부추', '수박'],
    '파주': ['쌀', '콩', '토마토', '인삼'],
    '안성': ['포도', '쌀', '인삼', '배'],
    '평택': ['쌀', '배', '오이', '애호박'],
    '화성': ['포도', '꿀참외', '알타리무'],
    '양주': ['부추', '배'],
    '포천': ['사과', '포도', '버섯', '인삼'],

    # 강원도
    '철원': ['쌀', '토마토', '파프리카'],
    '춘천': ['잣', '토마토'],
    '화천': ['토마토', '호박'],
    '양구': ['멜론', '아스파라거스', '오이'],
    '인제': ['오미자', '고추', '콩'],
    '홍천': ['찰옥수수', '잣', '인삼'],
    '횡성': ['한우', '더덕', '감자'],
    '평창': ['감자', '메밀', '토마토', '양파'],
    '강릉': ['감자', '파프리카'],
    '정선': ['감자', '마늘', '황기', '더덕'],
    '영월': ['포도', '사과', '고추'],
    '원주': ['복숭아', '배'],
    '삼척': ['마늘', '감자'],

    # 충청북도
    '충주': ['사과', '복숭아'],
    '제천': ['사과', '복숭아'],
    '단양': ['마늘', '사과', '고추'],
    '음성': ['복숭아', '고추', '인삼'],
    '진천': ['오이', '수박'],
    '청주': ['포도', '블루베리', '고구마'],
    '괴산': ['고추', '옥수수', '감자'],
    '보은': ['대추'],
    '옥천': ['포도', '복숭아', '부추'],
    '영동': ['포도', '감', '호두'],

    # 충청남도
    '논산': ['딸기', '멜론'],
    '금산': ['인삼', '깻잎', '복숭아', '포도'],
    '천안': ['포도', '배', '멜론'],
    '아산': ['배', '포도'],
    '예산': ['사과'],
    '서산': ['마늘', '생강', '배'],
    '당진': ['쌀', '꽈리고추', '오이', '배', '포도'],
    '홍성': ['마늘', '방울토마토'],
    '청양': ['고추', '구기자', '방울토마토', '멜론'],
    '부여': ['멜론', '수박', '방울토마토', '밤'],
    '공주': ['밤', '오이', '딸기'],
    '태안': ['마늘'],

    # 전라북도
    '고창': ['수박', '복분자', '땅콩', '배', '멜론', '고구마'],
    '부안': ['감자'],
    '김제': ['쌀', '배', '파프리카', '포도', '감자'],
    '정읍': ['수박', '사과', '귀리'],
    '임실': ['고추', '배', '포도', '복숭아'],
    '순창': ['복분자', '블루베리', '딸기', '멜론', '매실', '두릅'],
    '남원': ['포도', '파프리카', '사과', '상추'],
    '완주': ['딸기', '포도', '수박', '배', '생강', '마늘', '양파'],
    '진안': ['인삼', '홍삼', '더덕', '고추', '곶감'],
    '무주': ['사과', '천마', '호두', '오미자', '머루'],
    '장수': ['사과', '토마토', '오미자'],
    '익산': ['고구마', '방울토마토', '사과'],
    '전주': ['배', '복숭아', '미나리'],

    # 전라남도
    '함평': ['배', '양파'],
    '영광': ['고추'],
    '장성': ['사과', '포도'],
    '담양': ['딸기', '방울토마토', '멜론'],
    '곡성': ['멜론', '사과', '배', '딸기'],
    '구례': ['오이', '산수유'],
    '광양': ['매실'],
    '순천': ['매실', '배', '오이', '단감'],
    '화순': ['복숭아', '방울토마토', '더덕', '블루베리'],
    '나주': ['배'],
    '무안': ['양파', '고구마', '단감', '마늘'],
    '영암': ['무화과', '고구마', '수박', '대봉'],
    '강진': ['딸기', '토마토'],
    '해남': ['고구마', '배추'],
    '진도': ['대파', '구기자'],
    '완도': ['유자', '방울토마토'],
    '고흥': ['유자', '참다래', '마늘', '석류'],
    '보성': ['녹차', '키위', '쪽파'],

    # 경상북도
    '상주': ['곶감', '포도', '쌀'],
    '문경': ['사과', '오미자'],
    '예천': ['참외'],
    '영주': ['사과', '인삼', '복숭아'],
    '봉화': ['송이버섯', '사과'],
    '안동': ['사과'],
    '의성': ['마늘', '사과'],
    '청송': ['사과'],
    '영양': ['고추'],
    '영덕': ['복숭아'],
    '포항': ['부추', '토마토'],
    '경주': ['토마토'],
    '청도': ['복숭아', '반시'],
    '경산': ['대추', '포도', '복숭아', '자두'],
    '영천': ['포도'],
    '성주': ['참외'],
    '고령': ['딸기', '수박'],
    '김천': ['포도', '자두'],

    # 경상남도
    '거창': ['사과', '딸기'],
    '함양': ['양파', '사과', '밤', '곶감'],
    '산청': ['딸기', '곶감', '배'],
    '합천': ['양파', '마늘', '딸기'],
    '의령': ['수박', '새송이버섯'],
    '창녕': ['양파', '마늘', '단감'],
    '밀양': ['딸기', '사과', '깻잎', '대추'],
    '함안': ['수박', '곶감'],
    '김해': ['단감', '참외', '딸기'],
    '양산': ['딸기', '매실'],
    '진주': ['딸기', '고추', '오이', '수박'],
    '하동': ['매실', '배', '딸기'],
    '사천': ['토마토', '단감', '참다래'],
    '남해': ['마늘', '유자'],
    '거제': ['유자', '파인애플', '알로에'],
    '창원': ['단감', '수박', '포도'],

    # 제주특별자치도
    '제주': ['감귤', '한라봉', '고사리', '무', '당근', '브로콜리', '양배추'],
    '서귀포': ['감귤', '한라봉', '천혜향', '키위'],

    # 광역시, 특별자치시
    '세종': ['복숭아', '배'],
    '대전': ['포도']
}

def haversine(lat1, lon1, lat2, lon2):
    R = 6371
    dLat = math.radians(lat2 - lat1)
    dLon = math.radians(lon2 - lon1)
    a = math.sin(dLat / 2) * math.sin(dLat / 2) + math.cos(math.radians(lat1)) \
        * math.cos(math.radians(lat2)) * math.sin(dLon / 2) * math.sin(dLon / 2)
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

# PDF 텍스트 추출 및 정규화 함수 (OCR 기능 포함)
def extract_and_normalize_text_from_pdf(pdf_bytes):
    text = ""
    try:
        # 1. 텍스트 기반 추출 시도
        doc = fitz.open(stream=pdf_bytes, filetype="pdf")
        for page in doc:
            text += page.get_text()

        # 2. 텍스트가 거의 없다면 OCR 시도
        if len(text.strip()) < 50: # 텍스트가 거의 없는 경우 이미지로 간주
            print("텍스트가 거의 없어 OCR을 시도합니다.")
            text = ""
            doc = fitz.open(stream=pdf_bytes, filetype="pdf") # 바이트 스트림으로 다시 문서를 엽니다.
            for page_num in range(len(doc)):
                page = doc.load_page(page_num)
                pix = page.get_pixmap()
                img_bytes = pix.tobytes("png")
                img = Image.open(io.BytesIO(img_bytes))
                # 한국어와 영어를 포함하여 OCR 수행
                text += pytesseract.image_to_string(img, lang='kor+eng')

        # 3. 최종 텍스트 정규화
        return re.sub(r'\s+', '', text).lower()

    except Exception as e:
        print(f"PDF 처리 중 오류 발생: {e}")
        return ""

# --- Pre-load and process the sample certificate PDF for performance ---
SAMPLE_CERT_TEXT = ""
try:
    # Use the corrected path
    sample_pdf_path = os.path.join(os.path.dirname(__file__), '신청서.pdf')
    with open(sample_pdf_path, 'rb') as f:
        # Use the existing OCR function to process the sample file
        SAMPLE_CERT_TEXT = extract_and_normalize_text_from_pdf(f.read())
    
    if not SAMPLE_CERT_TEXT:
        print("Warning: Could not extract text from the sample certificate PDF on startup.")
    else:
        print("Successfully pre-loaded and processed the sample certificate PDF.")
        
except FileNotFoundError:
    print("CRITICAL ERROR: Sample certificate PDF ('신청서.pdf') not found on startup. Verification will fail.")
except Exception as e:
    print(f"CRITICAL ERROR processing sample certificate PDF on startup: {e}")

# --- 2. DB 모델(테이블) 정의 (farmer 기준으로 통합) ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    role = db.Column(db.String(50), nullable=False, default='experiencer')
    name = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(50), nullable=True)
    farm_address = db.Column(db.String(255), nullable=True)
    farm_size = db.Column(db.String(100), nullable=True)
    profile_image = db.Column(db.String(255), nullable=False, default='shd.png')
    farm_image = db.Column(db.String(255), nullable=True)
    profile_bio = db.Column(db.String(150), nullable=True)
    farmer_certificate_pdf = db.Column(db.String(255), nullable=True) # 농업인 증명서 PDF
    applications = db.relationship('Application', back_populates='user', cascade="all, delete-orphan")
    experiences = db.relationship('Experience', back_populates='farmer', cascade="all, delete-orphan")

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

class Review(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    rating = db.Column(db.Integer, nullable=False)
    content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experience_id = db.Column(db.Integer, db.ForeignKey('experience.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('reviews', lazy=True))
    analysis_result = db.Column(db.Text, nullable=True)

class Inquiry(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.Text, nullable=False)
    is_private = db.Column(db.Boolean, default=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experience_id = db.Column(db.Integer, db.ForeignKey('experience.id'), nullable=False)
    user = db.relationship('User', backref=db.backref('inquiries', lazy=True))

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

class Notification(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    message = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    is_read = db.Column(db.Boolean, default=False)
    user = db.relationship('User', backref=db.backref('notifications', lazy=True))

# app.py의 analyze_review_with_clova 함수

def analyze_review_with_clova(text):
    api_key = "nv-630074f1c8094226829c835d4a17284c09S4"
    host = "https://clovastudio.stream.ntruss.com"
    endpoint = "/v3/chat-completions/HCX-DASH-002"
    url = host + endpoint
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    request_data = {
        "messages": [
            {
                "role": "system",
                "content": "너는 사용자 후기를 분석하여 긍정적인 점과 개선점을 추출하는 전문가야. 문장에 '좋은데', '아쉽지만', '하지만' 같은 연결어가 있어도 각 부분을 독립적으로 평가해서 키워드를 추출해야 해. 결과는 반드시 JSON 형식으로 \"strengths\"와 \"improvements\" 키를 사용해줘."
            },
            {
                "role": "user",
                "content": "거리가 가까워서 좋은데 체험이 좀 힘들었어요."
            },
            {
                "role": "assistant",
                "content": "```json\n{\n  \"strengths\": [\"가까운 거리\"],\n  \"improvements\": [\"체험 난이도 조절\"]\n}\n```"
            },
            {
                "role": "user",
                "content": "화장실이 아주 깨끗한 편은 아니었지만 이정도면 괜찮았구요."
            },
            {
                "role": "assistant",
                "content": "```json\n{\n  \"strengths\": [],\n  \"improvements\": [\"화장실 청결도\"]\n}\n```"
            },
            {
                "role": "user",
                "content": text
            }
        ],
        "temperature": 0.1,
        "stream": False
    }

    try:
        response = requests.post(url, headers=headers, json=request_data)
        response.raise_for_status()

        response_data = response.json()
        content_string = response_data['result']['message']['content']

        json_match = re.search(r'\{.*\}', content_string, re.DOTALL)

        if json_match:
            json_string = json_match.group(0)
            analysis_result = json.loads(json_string)
            return analysis_result
        else:
            print(f"응답에서 JSON을 찾을 수 없음: {content_string}")
            return None

    except Exception as e:
        print(f"--- CLOVA API 에러 발생 ---")
        print(f"에러 종류: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"서버 실제 응답 내용: {response.text}")
        print("--------------------------")
        return None

# @scheduler.task('interval', id='update_experience_status', minutes=1)
def update_experience_status():
    with app.app_context():
        now = datetime.now()
        recruiting_experiences = Experience.query.filter_by(status='recruiting').all()
        expired_experiences = []
        days_map = {0: '월', 1: '화', 2: '수', 3: '목', 4: '금', 5: '토', 6: '일'}

        for exp in recruiting_experiences:
            if exp.end_date < now.date():
                expired_experiences.append(exp)
            elif exp.end_date == now.date():
                if exp.timetable_data:
                    day_of_week = days_map[exp.end_date.weekday()]
                    slots = exp.timetable_data.split(',')
                    last_time = None
                    for slot in slots:
                        day, time_str = slot.split('-')
                        if day == day_of_week:
                            slot_time = datetime.strptime(time_str, '%H:%M').time()
                            if last_time is None or slot_time > last_time:
                                last_time = slot_time
                    if last_time and now.time() > last_time:
                        expired_experiences.append(exp)

        for exp in expired_experiences:
            exp.status = 'expired'
            notification = Notification(user_id=exp.farmer_id, message=f"'{exp.crop}' 체험의 모집 기간이 만료되었습니다.")
            db.session.add(notification)

        if expired_experiences:
            db.session.commit()
            print(f"[{datetime.now()}] {len(expired_experiences)}개의 체험을 '기간 만료'로 업데이트했습니다.")

def get_coords_from_address(address):
    KAKAO_API_KEY = app.config['KAKAO_API_KEY']
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        if data['documents']:
            location = data['documents'][0]
            return float(location['y']), float(location['x'])
    except Exception as e:
        print(f"지오코딩 처리 중 오류 발생: {e}")
    return 36.8583, 127.2943

# --- 3. 핵심 라우트 ---
@app.route('/')
def index():
    print(f"Request args: {request.args}")
    role = session.get('role', 'experiencer')
    if role == 'farmer':
        farmer_id = session.get('user_id')
        if not farmer_id: return redirect(url_for('login_page'))
        user = User.query.get(farmer_id)
        if not user:
            session.clear()
            flash("세션 정보가 유효하지 않습니다.", "warning")
            return redirect(url_for('login_page'))

        notifications = Notification.query.filter_by(user_id=farmer_id).order_by(Notification.timestamp.desc()).limit(3).all()
        all_notifications = Notification.query.filter_by(user_id=farmer_id).order_by(Notification.timestamp.desc()).all()
        notifications_json = [
            {"id": n.id, "message": n.message, "timestamp": n.timestamp.isoformat()} for n in all_notifications
        ]

        my_listings = Experience.query.filter(
            Experience.farmer_id == farmer_id,
            Experience.status.in_(['recruiting', 'hidden'])
        ).all()

        experiences_json = [exp.to_dict() for exp in my_listings]
        experience_ids = [exp.id for exp in my_listings]
        applications = Application.query.filter(Application.experience_id.in_(experience_ids), Application.status != '취소').all()
        reservations_by_date = defaultdict(list)
        for app in applications:
            reservations_by_date[app.apply_date.strftime('%Y-%m-%d')].append({
                "id": app.id, "name": app.applicant_name, "phone": app.phone_number,
                "adult": app.count_adult, "teen": app.count_teen, "child": app.count_child,
                "time": app.apply_time, "crop": app.experience.crop, "status": app.status
            })

        avg_rating = 0
        if experience_ids:
            avg_result = db.session.query(func.avg(Review.rating)).filter(Review.experience_id.in_(experience_ids)).scalar()
            if avg_result is not None:
                avg_rating = round(avg_result, 1)

        latest_inquiries = []
        if experience_ids:
            latest_inquiries = Inquiry.query.filter(Inquiry.experience_id.in_(experience_ids)).order_by(Inquiry.timestamp.desc()).limit(5).all()

        total_visitors = sum(exp.current_participants for exp in my_listings)
        stats = {
            'total_experiences': len(my_listings),
            'average_rating': avg_rating if avg_rating > 0 else "N/A",
            'total_visitors': total_visitors
        }

        feedback_by_experience = {}
        my_listings_with_reviews = Experience.query.filter(
            Experience.farmer_id == farmer_id
        ).options(db.joinedload(Experience.reviews)).all()

        for exp in my_listings_with_reviews:
            if not exp.reviews:
                continue

            strength_keywords = defaultdict(int)
            improvement_keywords = defaultdict(int)

            for review in exp.reviews:
                if review.analysis_result:
                    try:
                        data = json.loads(review.analysis_result)
                        strengths_data = data.get('strengths', [])
                        if isinstance(strengths_data, list):
                            for keyword in strengths_data:
                                if keyword: strength_keywords[keyword] += 1

                        improvements_data = data.get('improvements', [])
                        if isinstance(improvements_data, list):
                            for keyword in improvements_data:
                                if keyword: improvement_keywords[keyword] += 1
                    except (json.JSONDecodeError, TypeError):
                        continue

            if strength_keywords or improvement_keywords:
                sorted_strengths = sorted(strength_keywords.items(), key=lambda item: item[1], reverse=True)
                sorted_improvements = sorted(improvement_keywords.items(), key=lambda item: item[1], reverse=True)

                feedback_by_experience[exp.id] = {
                    'name': exp.crop,
                    'strengths': sorted_strengths,
                    'improvements': sorted_improvements
                }

        return render_template('my_farm.html',
                               user=user, experiences=my_listings, experiences_json=experiences_json,
                               stats=stats, inquiries=latest_inquiries,
                               reservations_data=reservations_by_date, notifications=notifications, notifications_json=notifications_json,
                               feedback_report=feedback_by_experience)

    else: # 체험자 또는 비로그-인 사용자
        page = request.args.get('page', 1, type=int)
        sort_by = request.args.get('sort', 'recommended', type=str)
        region = request.args.get('region', type=str)
        crop_query = request.args.get('crop_query', type=str)

        today = date.today()
    # 1. 기본 쿼리 및 필터링
        base_query = Experience.query.filter(Experience.status == 'recruiting', Experience.end_date >= today)

        if region:
            base_query = base_query.filter(Experience.address_detail.like(f"%{region}%"))
        if crop_query:
            base_query = base_query.filter(Experience.crop.like(f"%{crop_query}%"))

        items_on_page = []
        pagination = None

    # [수정] 마감된 체험을 목록 맨 뒤로 보내기 위한 공통 정렬 기준
        is_closed = case(
            (Experience.current_participants >= Experience.max_participants, 1),
            else_=0
        ).label("is_closed")

    # [핵심 수정] sort_by 값을 먼저 확인하도록 로직 순서 변경
        if sort_by == 'recommended':
            user_lat = request.args.get('lat', type=float)
            user_lon = request.args.get('lon', type=float)

            if user_lat and user_lon:
                query = base_query.filter(Experience.current_participants < Experience.max_participants)
                all_experiences = query.all()
            
                ranked_experiences = []
                for exp in all_experiences:
                    distance = haversine(user_lat, user_lon, exp.lat, exp.lng)
                    if distance > 150: continue

                    distance_score = max(0, 1 - (distance / 50))
                    availability_score = (exp.max_participants - exp.current_participants) / exp.max_participants
                
                    specialty_score = 0
                    for r, specialties in REGIONAL_SPECIALTIES.items():
                        if r in exp.address_detail and any(sc in exp.crop for sc in specialties):
                            specialty_score = 1.0
                            break
                
                    w1, w2, w3 = 0.5, 0.3, 0.2
                    recommendation_score = (w1 * distance_score) + (w2 * specialty_score) + (w3 * availability_score)

                    exp.recommendation_score = recommendation_score
                    exp.distance = distance
                    ranked_experiences.append(exp)

                sorted_items = sorted(ranked_experiences, key=lambda x: x.recommendation_score, reverse=True)

                start = (page - 1) * 15
                end = start + 15
                items_on_page = sorted_items[start:end]
                total_items = len(sorted_items)
            
                total_pages = math.ceil(total_items / 15) if total_items > 0 else 1
                pagination = SimpleNamespace(
                    items=items_on_page, page=page, per_page=15, total=total_items,
                    pages=total_pages, has_prev=(page > 1), has_next=(page < total_pages),
                    prev_num=page - 1, next_num=page + 1,
                    iter_pages=lambda **kwargs: range(1, total_pages + 1)
                )
        # 추천순인데 lat, lon 값이 없으면 빈 화면을 보여주는 기존 로직은 유지
            else:
                items_on_page = []
                pagination = None


        elif sort_by == 'reviews':
            review_count = func.count(Review.id).label('review_count')
            query = base_query.outerjoin(Review).group_by(Experience.id).order_by(is_closed.asc(), review_count.desc())
            pagination = query.paginate(page=page, per_page=15, error_out=False)
            items_on_page = pagination.items

        else: # 'deadline' (모집 임박순) 및 기타
            query = base_query.order_by(is_closed.asc(), Experience.end_date.asc())
            pagination = query.paginate(page=page, per_page=15, error_out=False)
            items_on_page = pagination.items


    # '지역 특산물' 배지 표시 로직
        if items_on_page: # items_on_page가 None이 아닐 때만 실행
            for item in items_on_page:
                item.is_specialty = False
                for r, specialties in REGIONAL_SPECIALTIES.items():
                    if r in item.address_detail and any(sc in item.crop for sc in specialties):
                        item.is_specialty = True
                        break

        return render_template('index.html',
                               items=items_on_page,
                               pagination=pagination,
                               sort_by=sort_by)

# ... (이하 모든 라우트는 farmer 기준으로 유지하되, e-sibal의 고유 기능 추가) ...

# 이 코드는 매우 길기 때문에, 핵심적인 index() 라우트 통합 부분만 보여드렸습니다.
# 전체 코드는 farmer의 모든 기능(expired_experiences, update_bio, toggle_visibility 등)을 유지하면서
# e-sibal의 guide_page, volunteer_apply의 검색 기능 등을 추가하는 방식으로 통합됩니다.
# 아래는 완전한 통합본의 나머지 부분입니다.

@app.route('/my_farm/expired')
def expired_experiences():
    if session.get('role') != 'farmer':
        flash("농장주만 접근 가능합니다.", "warning")
        return redirect(url_for('index'))

    farmer_id = session.get('user_id')
    user = User.query.get(farmer_id)
    expired_list = Experience.query.filter_by(farmer_id=farmer_id, status='expired').order_by(Experience.end_date.desc()).all()

    return render_template('expired_experiences.html', user=user, experiences=expired_list)


# --- 사용자 인증 관련 라우트 ---
@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        role = request.form.get('role')
        nickname = request.form.get('nickname')
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        phone = request.form.get('phone')
        password_confirm = request.form.get('password_confirm')
        required_fields = [role, nickname, email, password, name, phone]

        if password != password_confirm:
            flash("비밀번호가 일치하지 않습니다.", "danger")
            return render_template('register.html', form_data=request.form)
        if not all(required_fields):
            flash("모든 필수 항목을 올바르게 입력해주세요.", "danger")
            return render_template('register.html', form_data=request.form)
        if User.query.filter_by(email=email).first():
            flash("이미 가입된 이메일입니다.", "danger")
            return render_template('register.html', form_data=request.form)

        cert_pdf_filename = None
        if role == 'farmer':
            cert_pdf_file = request.files.get('farmer_certificate_pdf')
            if not cert_pdf_file or cert_pdf_file.filename == '':
                flash("농장주 회원은 농업인 확인서 PDF 파일을 반드시 제출해야 합니다.", "danger")
                return render_template('register.html', form_data=request.form)

            if allowed_file(cert_pdf_file.filename):
                try:
                    # Check if the pre-loaded sample text is available
                    if not SAMPLE_CERT_TEXT:
                        flash("시스템 오류: 샘플 인증서를 처리할 수 없습니다. 관리자에게 문의하세요.", "danger")
                        return render_template('register.html', form_data=request.form)

                    uploaded_text = extract_and_normalize_text_from_pdf(cert_pdf_file.read())
                    cert_pdf_file.seek(0)  # Reset stream position after reading

                    # Compare with the pre-loaded text
                    if uploaded_text and SAMPLE_CERT_TEXT in uploaded_text:
                        cert_pdf_filename = secure_filename(f"farmer_cert_{email}_{cert_pdf_file.filename}")
                        cert_pdf_file.save(os.path.join(app.config['UPLOAD_FOLDER'], cert_pdf_filename))
                    else:
                        flash("업로드된 농업인 확인서가 유효하지 않습니다.", "danger")
                        return render_template('register.html', form_data=request.form)
                except Exception as e:
                    # A more general exception to catch any PDF processing errors
                    flash(f"인증서 파일 처리 중 오류가 발생했습니다: {e}", "danger")
                    return render_template('register.html', form_data=request.form)
            else:
                flash("허용되지 않는 파일 형식입니다. PDF 파일만 업로드 가능합니다.", "danger")
                return render_template('register.html', form_data=request.form)

        hashed_password = generate_password_hash(password)
        new_user = User(
            email=email, nickname=nickname, password=hashed_password,
            role=role, name=name, phone=phone,
            farm_address=request.form.get('farm_address'),
            farm_size=request.form.get('farm_size'),
            profile_bio=request.form.get('profile_bio'),
            farmer_certificate_pdf=cert_pdf_filename
        )
        db.session.add(new_user)
        db.session.commit()
        flash("회원가입이 완료되었습니다! 로그인해주세요.", "success")
        return redirect(url_for('login_page'))
    return render_template('register.html', form_data={})

@app.route('/check_email', methods=['POST'])
def check_email():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    return jsonify({'exists': user is not None})

@app.route('/login', methods=['GET', 'POST'])
def login_page():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()
        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['nickname'] = user.nickname
            session['role'] = user.role
            flash(f"{user.nickname}님, 환영합니다!", "success")
            return redirect(url_for('index'))
        else:
            flash("이메일 또는 비밀번호가 올바르지 않습니다.", "danger")
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash("로그아웃되었습니다.", "info")
    return redirect(url_for('index'))

@app.route('/update_bio', methods=['POST'])
def update_bio():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404

    data = request.get_json()
    new_bio = data.get('profile_bio')

    if new_bio is None:
        return jsonify({'success': False, 'message': '소개 내용이 없습니다.'}), 400

    user.profile_bio = new_bio
    db.session.commit()

    return jsonify({'success': True, 'message': '한 줄 소개가 업데이트되었습니다.'})

# --- 체험 관련 라우트 ---
@app.route('/experience/<int:item_id>')
def experience_detail(item_id):
    item = Experience.query.get_or_404(item_id)
    if item.status != 'recruiting' and session.get('user_id') != item.farmer_id:
        flash("현재 모집 중인 체험이 아닙니다.", "warning")
        return redirect(url_for('index'))

    review_status = 'not_logged_in'
    if 'user_id' in session:
        user_id = session['user_id']
        existing_review = Review.query.filter_by(user_id=user_id, experience_id=item_id).first()
        if existing_review:
            review_status = 'already_reviewed'
        else:
            application = Application.query.filter(
                Application.user_id == user_id,
                Application.experience_id == item_id
            ).order_by(Application.id.desc()).first()

            if application:
                if application.status == '확정':
                    review_status = 'allowed'
                elif application.status == '예정':
                    review_status = 'pending_confirmation'
                else: # 취소 또는 다른 상태
                    review_status = 'not_applicable'
            else:
                review_status = 'not_applied'

    reviews = Review.query.filter_by(experience_id=item_id).order_by(Review.timestamp.desc()).all()
    inquiries = Inquiry.query.filter_by(experience_id=item_id).order_by(Inquiry.timestamp.desc()).all()
    item_data_for_js = {'lat': item.lat, 'lng': item.lng}
    return render_template('detail_experience.html', item=item, item_data_for_js=item_data_for_js, reviews=reviews, inquiries=inquiries, review_status=review_status)

@app.route('/experience/apply/<int:item_id>', methods=['GET', 'POST'])
def experience_apply(item_id):
    if 'user_id' not in session:
        flash("체험을 신청하려면 로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))

    item = Experience.query.get_or_404(item_id)
    if item.status != 'recruiting':
        flash("현재 모집 중인 체험이 아닙니다.", "warning")
        return redirect(url_for('experience_detail', item_id=item.id))

    if request.method == 'POST':
        apply_date_str = request.form.get('apply_date')
        apply_time_str = request.form.get('apply_time')

        if not apply_date_str or not apply_time_str:
            flash("신청 날짜와 시간을 모두 선택해주세요.", "danger")
            return redirect(url_for('experience_apply', item_id=item.id))
        count_adult = int(request.form.get('count_adult', 0))
        count_teen = int(request.form.get('count_teen', 0))
        count_child = int(request.form.get('count_child', 0))
        total_participants = count_adult + count_teen + count_child

        if total_participants == 0:
            flash("참가 인원을 1명 이상 선택해주세요.", "danger")
            return redirect(url_for('experience_apply', item_id=item.id))

        if item.current_participants + total_participants > item.max_participants:
            flash(f"죄송합니다. 남은 자리가 부족합니다. (현재 {item.max_participants - item.current_participants}명 신청 가능)", "danger")
            return redirect(url_for('experience_detail', item_id=item.id))

        new_application = Application(
            applicant_name=request.form.get('applicant_name'),
            phone_number=request.form.get('phone_number'),
            participants_count=total_participants,
            count_adult=count_adult,
            count_teen=count_teen,
            count_child=count_child,
            apply_date=datetime.strptime(request.form.get('apply_date'), '%Y-%m-%d').date(),
            apply_time=request.form.get('apply_time'),
            user_id=session['user_id'],
            experience_id=item.id
        )

        item.current_participants += total_participants
        db.session.add(new_application)

        # 알림 추가
        notification_message = f"'{new_application.applicant_name}'님이 '{item.crop}' 체험을 신청했습니다."
        new_notification = Notification(user_id=item.farmer_id, message=notification_message)
        db.session.add(new_notification)

        db.session.commit()

        return render_template('apply_complete.html', item=item, name=new_application.applicant_name)

    return render_template('experience_apply.html', item=item)

# --- 농장주 전용 라우트 ---
@app.route('/farmer/register', methods=['GET', 'POST'])
@app.route('/farmer/modify/<int:item_id>', methods=['GET', 'POST'])
def farmer_register(item_id=None):
    if 'user_id' not in session or session['role'] != 'farmer':
        flash("농장주로 로그인해야만 접근할 수 있습니다.", "warning")
        return redirect(url_for('login_page'))
    item = Experience.query.get(item_id) if item_id else None
    if item and item.farmer_id != session['user_id']: abort(403)

    if request.method == 'POST':
        is_organic = 'is_organic' in request.form
        has_parking = 'has_parking' in request.form
        cert_filename = item.organic_certification_image if item and item.organic_certification_image else None
        cert_file = request.files.get('organic_certification_image')

        if cert_file and cert_file.filename != '':
            if allowed_file(cert_file.filename):
                cert_filename = secure_filename(f"cert_{item_id or 'new'}_{cert_file.filename}")
                cert_file.save(os.path.join(app.config['UPLOAD_FOLDER'], cert_filename))
        elif not is_organic:
            cert_filename = None

        if is_organic and not cert_filename:
            flash("친환경 인증을 선택한 경우, 인증 이미지를 반드시 업로드해야 합니다.", "danger")
            return render_template('farmer_register.html', item=item, form_data=request.form)

        end_date_str = request.form.get('duration_end')
        if datetime.strptime(end_date_str, '%Y-%m-%d').date() < date.today():
            flash("모집 마감일은 현재 날짜보다 이전일 수 없습니다.", "danger")
            return render_template('farmer_register.html', item=item, form_data=request.form)

        uploaded_files = request.files.getlist('images')
        filenames = item.images.split(',') if item and item.images else []
        if any(f.filename for f in uploaded_files):
            filenames = []
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                img = Image.open(file.stream)
                img.thumbnail((800, 600))
                img.save(filepath)
                if filename not in filenames: filenames.append(filename)
        image_string = ",".join(filter(None, filenames))

        address_detail = request.form.get('address')
        lat, lng = get_coords_from_address(address_detail)

        volunteer_needed_str = request.form.get('volunteer_needed')
        volunteer_needed = int(volunteer_needed_str) if volunteer_needed_str else 0

        if item: # 수정
            item.crop = request.form.get('crop')
            item.phone = request.form.get('phone')
            item.address_detail = address_detail
            item.farm_size = request.form.get('farm_size')
            item.duration_start = datetime.strptime(request.form.get('duration_start'), '%Y-%m-%d').date()
            item.end_date = datetime.strptime(request.form.get('duration_end'), '%Y-%m-%d').date()
            item.max_participants = int(request.form.get('max_participants'))
            item.cost = int(request.form.get('price'))
            item.images = image_string
            item.notes = request.form.get('notes')
            item.includes = request.form.get('includes')
            item.excludes = request.form.get('excludes')
            item.timetable_data = request.form.get('timetable_data')
            item.pesticide_free = is_organic
            item.organic_certification_image = cert_filename
            item.organic_certification_type = request.form.get('organic_certification_type')
            item.lat = lat
            item.lng = lng
            item.volunteer_needed = volunteer_needed
            item.volunteer_duties = request.form.get('volunteer_duties')
            item.has_parking = has_parking
            flash("체험 정보가 성공적으로 수정되었습니다!", "success")
        else: # 생성
            farmer = User.query.get(session['user_id'])
            new_experience = Experience(
                crop=request.form.get('crop'),
                phone=request.form.get('phone'),
                location=farmer.farm_address,
                address_detail=address_detail,
                farm_size=request.form.get('farm_size'),
                duration_start=datetime.strptime(request.form.get('duration_start'), '%Y-%m-%d').date(),
                end_date=datetime.strptime(request.form.get('duration_end'), '%Y-%m-%d').date(),
                max_participants=int(request.form.get('max_participants')),
                cost=int(request.form.get('price')),
                images=image_string,
                notes=request.form.get('notes'),
                includes=request.form.get('includes'),
                excludes=request.form.get('excludes'),
                timetable_data=request.form.get('timetable_data'),
                pesticide_free=is_organic,
                organic_certification_image=cert_filename,
                organic_certification_type=request.form.get('organic_certification_type'),
                lat=lat,
                lng=lng,
                farmer_id=session['user_id'],
                volunteer_needed=volunteer_needed,
                has_parking=has_parking,
                volunteer_duties=request.form.get('volunteer_duties'),
                status='recruiting'
            )
            db.session.add(new_experience)
            flash("새로운 체험이 성공적으로 등록되었습니다!", "success")

        db.session.commit()
        return redirect(url_for('index'))

    return render_template('farmer_register.html', item=item, form_data={})



@app.route('/experience/delete/<int:item_id>', methods=['POST'])
def delete_experience(item_id):
    if 'user_id' not in session or session['role'] != 'farmer': abort(403)
    item = Experience.query.get_or_404(item_id)
    if item.farmer_id != session.get('user_id'): abort(403)
    db.session.delete(item)
    db.session.commit()
    flash("체험이 삭제되었습니다.", "info")
    return redirect(url_for('index'))

@app.route('/api/experience/<int:item_id>/toggle_visibility', methods=['PATCH'])
def toggle_visibility(item_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403

    item = Experience.query.get_or_404(item_id)
    if item.farmer_id != session.get('user_id'):
        return jsonify({'success': False, 'message': '자신이 등록한 체험만 변경할 수 있습니다.'}), 403

    if item.status == 'recruiting':
        item.status = 'hidden'
        message = '체험을 비공개로 전환했습니다.'
    elif item.status == 'hidden':
        item.status = 'recruiting'
        message = '체험을 공개로 전환했습니다.'
    else:
        return jsonify({'success': False, 'message': '상태를 변경할 수 없는 체험입니다.'}), 400

    db.session.commit()
    return jsonify({'success': True, 'message': message, 'new_status': item.status})


@app.route('/experience/<int:item_id>/review', methods=['POST'])
def add_review(item_id):
    if 'user_id' not in session: return redirect(url_for('login_page'))

    user_id = session['user_id']
    has_confirmed_app = Application.query.filter(
        Application.user_id == user_id,
        Application.experience_id == item_id,
        Application.status == '확정'
    ).first()

    if not has_confirmed_app:
        flash("후기를 작성할 권한이 없습니다. 예약이 확정된 체험에만 후기를 남길 수 있습니다.", "warning")
        return redirect(url_for('experience_detail', item_id=item_id))

    existing_review = Review.query.filter_by(user_id=user_id, experience_id=item_id).first()
    if existing_review:
        flash("이미 이 체험에 대한 후기를 작성하셨습니다.", "warning")
        return redirect(url_for('experience_detail', item_id=item_id))

    review_content = request.form.get('content')
    analysis_json = None  # 기본값을 None으로 설정
    try:
        # AI 분석 함수를 try-except 블록으로 감싸서 에러를 포착합니다.
        analysis_json = analyze_review_with_clova(review_content)
        if analysis_json is None:
            # API에서 정상 응답을 받았지만, 내용이 비어있는 경우
            flash("AI 후기 분석에 실패했습니다. (API 응답 없음)", "warning")
    except Exception as e:
        # API 호출 중 네트워크 오류 등 예외가 발생한 경우
        print(f"CLOVA API 호출 중 에러 발생: {e}") # 서버 로그에 에러 기록
        flash(f"AI 후기 분석 중 오류가 발생했습니다. 관리자에게 문의하세요.", "danger")

    new_review = Review(
        rating=int(request.form.get('rating')),
        content=review_content, # review_content 변수 사용
        user_id=session['user_id'],
        experience_id=item_id,
        # AI 분석 결과를 JSON 문자열 형태로 저장
        analysis_result=json.dumps(analysis_json) if analysis_json else None
    )
    db.session.add(new_review)

    # 알림 추가
    experience = Experience.query.get_or_404(item_id)
    notification_message = f"'{new_review.user.nickname}'님이 '{experience.crop}' 체험에 새로운 후기를 작성했습니다."
    new_notification = Notification(user_id=experience.farmer_id, message=notification_message)
    db.session.add(new_notification)

    db.session.commit()
    flash("후기가 등록되었습니다.", "success")
    return redirect(url_for('experience_detail', item_id=item_id))

@app.route('/experience/<int:item_id>/inquiry', methods=['POST'])
def add_inquiry(item_id):
    if 'user_id' not in session:
        flash("문의를 작성하려면 로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))
    new_inquiry = Inquiry(
        content=request.form.get('content'), user_id=session['user_id'], experience_id=item_id
    )
    db.session.add(new_inquiry)

    # 알림 추가
    experience = Experience.query.get_or_404(item_id)
    notification_message = f"'{new_inquiry.user.nickname}'님이 '{experience.crop}' 체험에 새로운 문의를 남겼습니다."
    new_notification = Notification(user_id=experience.farmer_id, message=notification_message)
    db.session.add(new_notification)

    db.session.commit()
    flash("문의가 등록되었습니다.", "success")
    return redirect(url_for('experience_detail', item_id=item_id))

@app.route('/application/confirm/<int:app_id>', methods=['POST'])
def confirm_application(app_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        flash("권한이 없습니다.", "danger")
        return redirect(url_for('login_page'))

    application = Application.query.get_or_404(app_id)
    experience = Experience.query.get_or_404(application.experience_id)

    if experience.farmer_id != session.get('user_id'):
        flash("자신의 체험에 대한 예약만 확정할 수 있습니다.", "danger")
        return redirect(url_for('index'))

    if application.status == '예정':
        application.status = '확정'
        db.session.commit()
        flash(f"{application.applicant_name}님의 예약을 확정했습니다.", "success")
    else:
        flash("이미 처리된 예약입니다.", "warning")

    return redirect(url_for('index'))

@app.route('/notifications/delete/<int:notification_id>', methods=['POST'])
def delete_notification(notification_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    notification = Notification.query.get_or_404(notification_id)

    if notification.user_id != session.get('user_id'):
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403

    db.session.delete(notification)
    db.session.commit()

    return jsonify({'success': True, 'message': '알림이 삭제되었습니다.'})

# --- 파일 업로드 관련 ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/upload_profile', methods=['POST'])
def upload_profile():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    if 'profile_pic' not in request.files or request.files['profile_pic'].filename == '':
        flash('선택된 파일이 없습니다.', 'warning')
        return redirect(url_for('my_info'))
    file = request.files['profile_pic']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        img = Image.open(file.stream)
        img.thumbnail((400, 400))
        img.save(filepath)

        user = User.query.get(session['user_id'])
        user.profile_image = filename
        db.session.commit()
        flash('프로필 사진이 변경되었습니다.', 'success')
    else:
        flash('허용되지 않는 파일 형식입니다.', 'danger')
    return redirect(url_for('my_info'))

@app.route('/upload_farm_photo', methods=['POST'])
def upload_farm_photo():
    if 'user_id' not in session or session['role'] != 'farmer': return redirect(url_for('login_page'))
    if 'farm_photo' not in request.files or request.files['farm_photo'].filename == '':
        flash('선택된 파일이 없습니다.', 'warning')
        return redirect(url_for('index'))
    file = request.files['farm_photo']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)

        img = Image.open(file.stream)
        img.thumbnail((800, 600))
        img.save(filepath)

        user = User.query.get(session['user_id'])
        user.farm_image = filename
        db.session.commit()
        flash('농장 사진이 변경되었습니다.', 'success')
    else:
        flash('허용되지 않는 파일 형식입니다.', 'danger')
    return redirect(url_for('index'))

@app.route('/my_info', methods=['GET', 'POST'])
def my_info():
    if 'user_id' not in session:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))

    user = User.query.get_or_404(session['user_id'])

    if request.method == 'POST':
        user.nickname = request.form.get('nickname')
        user.name = request.form.get('name')
        user.phone = request.form.get('phone')
        if user.role == 'farmer':
            user.farm_address = request.form.get('farm_address')
            user.farm_size = request.form.get('farm_size')
            user.profile_bio = request.form.get('profile_bio')
        db.session.commit()
        flash("회원 정보가 성공적으로 수정되었습니다.", "success")
        session['nickname'] = user.nickname
        return redirect(url_for('my_info'))

    applications = Application.query.filter_by(user_id=user.id).order_by(Application.apply_date.desc()).all()
    return render_template('my_info.html', user=user, applications=applications)

@app.route('/application/delete/<int:app_id>', methods=['POST'])
def delete_application(app_id):
    if 'user_id' not in session: abort(403)
    application = Application.query.get_or_404(app_id)
    if application.user_id != session['user_id']: abort(403)

    experience = Experience.query.get(application.experience_id)
    if experience and application.status != '취소': # 이미 취소된 건은 인원수 복구 안함
        experience.current_participants = max(0, experience.current_participants - application.participants_count)

    application.status = '취소'

    # 알림 추가
    notification_message = f"'{application.applicant_name}'님이 '{experience.crop}' 체험 신청을 취소했습니다."
    new_notification = Notification(user_id=experience.farmer_id, message=notification_message)
    db.session.add(new_notification)

    # Delete the associated review
    existing_review = Review.query.filter_by(
        user_id=application.user_id,
        experience_id=application.experience_id
    ).first()
    if existing_review:
        db.session.delete(existing_review)

    db.session.commit()

    flash("체험 신청이 취소되었습니다.", "success")
    return redirect(url_for('my_info'))

@app.route('/volunteer')
def volunteer_apply():
    # e-sibal의 검색/필터 기능을 farmer의 status 필터와 결합
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'deadline', type=str)
    region = request.args.get('region', type=str)
    crop_query = request.args.get('crop_query', type=str)

    query = Experience.query.filter(Experience.volunteer_needed > 0, Experience.status == 'recruiting')

    if region:
        query = query.filter(Experience.address_detail.like(f"%{region}%"))
    if crop_query:
        query = query.filter(Experience.crop.like(f"%{crop_query}%"))

    if sort_by == 'reviews':
        query = query.outerjoin(Review).group_by(Experience.id).order_by(func.count(Review.id).desc(), Experience.duration_start.asc())
    else: # 'deadline' 또는 기본값
        query = query.order_by(Experience.duration_start.asc())

    pagination = query.paginate(page=page, per_page=15, error_out=False)
    items_on_page = pagination.items

    return render_template('volunteer_apply.html',
                           items=items_on_page,
                           pagination=pagination,
                           sort_by=sort_by)

@app.route('/api/experiences')
def get_experiences_json():
    experiences = Experience.query.filter_by(status='recruiting').all()
    experience_list = [exp.to_dict() for exp in experiences]
    return jsonify(experience_list)

@app.route('/guide') # e-sibal 기능 추가
def guide_page():
    return render_template('guide.html')

# --- 앱 실행 ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)