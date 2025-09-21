import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, jsonify
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
from sqlalchemy.sql import func
from collections import defaultdict
from datetime import date, timedelta, datetime

# --- 1. 앱 및 DB 설정 ---
app = Flask(__name__)
app.secret_key = 'mysql-secret-key-for-production'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:rootpass0723@localhost/myfarm_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# --- 파일 업로드 설정 ---
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif'}

db = SQLAlchemy(app)

# --- 2. DB 모델(테이블) 정의 ---
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
    applications = db.relationship('Application', back_populates='user', cascade="all, delete-orphan")
    

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
    reviews = db.relationship('Review', backref='experience', lazy=True, cascade="all, delete-orphan")
    inquiries = db.relationship('Inquiry', backref='experience', lazy=True, cascade="all, delete-orphan")
    applications = db.relationship('Application', back_populates='experience', cascade="all, delete-orphan")
    volunteer_needed = db.Column(db.Integer, default=0)
    current_volunteers = db.Column(db.Integer, default=0)
    volunteer_duties = db.Column(db.Text, nullable=True)
    has_parking = db.Column(db.Boolean, default=False, nullable=False)

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
    status = db.Column(db.String(50), nullable=False, default='예정') # '예정', '완료', '취소'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    experience_id = db.Column(db.Integer, db.ForeignKey('experience.id'), nullable=False)

    user = db.relationship('User', back_populates='applications')
    experience = db.relationship('Experience', back_populates='applications')   
        
def get_coords_from_address(address):
    # --- 중요! ---
    # 카카오 개발자 사이트에서 발급받은 'REST API 키'를 여기에 입력해주세요.
    KAKAO_API_KEY = "54569873db07a9b66faf2a7be5c41a1c"
    
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    
    print("========================================")
    print(f"1. 좌표 변환을 시도하는 주소: {address}")

    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        print(f"2. 카카오 API 응답 결과: {data}")
        print("========================================")

        if data['documents']:
            location = data['documents'][0]
            return float(location['y']), float(location['x'])
        else:
            return 36.8583, 127.2943
    except Exception as e:
        print(f"지오코딩 처리 중 오류 발생: {e}")
        return 36.8583, 127.2943

# --- 3. 핵심 라우트 ---
@app.route('/')
def index():
    role = session.get('role', 'experiencer')
    if role == 'farmer':
        farmer_id = session.get('user_id')
        if not farmer_id: return redirect(url_for('login_page'))
        user = User.query.get(farmer_id)
        if not user:
            session.clear()
            flash("세션 정보가 유효하지 않습니다.", "warning")
            return redirect(url_for('login_page'))

        my_listings = Experience.query.filter_by(farmer_id=farmer_id).all()
        experience_ids = [exp.id for exp in my_listings]
        
        applications = Application.query.filter(Application.experience_id.in_(experience_ids)).all()
        
        reservations_by_date = defaultdict(list)
        for app in applications:
            reservations_by_date[app.apply_date.strftime('%Y-%m-%d')].append({
                "name": app.applicant_name,
                "phone": app.phone_number,
                "adult": app.count_adult,
                "teen": app.count_teen,
                "child": app.count_child,
                "time": app.apply_time
            })

        # 평균 별점 계산
        avg_rating = 0
        if experience_ids:
            avg_result = db.session.query(func.avg(Review.rating)).filter(Review.experience_id.in_(experience_ids)).scalar()
            if avg_result is not None:
                avg_rating = round(avg_result, 1)

        # 최신 문의 조회
        latest_inquiries = []
        if experience_ids:
            latest_inquiries = Inquiry.query.filter(Inquiry.experience_id.in_(experience_ids)).order_by(Inquiry.timestamp.desc()).limit(5).all()

        total_visitors = sum(exp.current_participants for exp in my_listings)
        stats = {
            'total_experiences': len(my_listings),
            'average_rating': avg_rating if avg_rating > 0 else "N/A",
            'total_visitors': total_visitors
        }
        
        return render_template('my_farm.html', 
                               user=user, 
                               experiences=my_listings, 
                               stats=stats,
                               inquiries=latest_inquiries,
                               reservations_data=reservations_by_date)
    else:
        # 체험자에게 보여주는 페이지 로직 (기존과 동일)
        page = request.args.get('page', 1, type=int)
        sort_by = request.args.get('sort', 'deadline', type=str)
        query_order = Experience.location.asc() if sort_by == 'location' else Experience.end_date.asc()
        experiences_query = Experience.query.order_by(query_order)
        pagination = experiences_query.paginate(page=page, per_page=15, error_out=False)
        items_on_page = sorted(pagination.items, key=lambda x: x.current_participants >= x.max_participants)
        return render_template('index.html', items=items_on_page, pagination=pagination, sort_by=sort_by)

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

        # 필수 필드 목록 정의
        required_fields = [role, nickname, email, password, name, phone]

        if password != password_confirm:
            flash("비밀번호가 일치하지 않습니다.", "danger")
            # 아래에서 form_data를 넘겨주도록 수정할 것이므로 여기선 일단 redirect
            return render_template('register.html', form_data=request.form)
        # 하나라도 비어있는 필드가 있는지 확인
        if not all(required_fields):
            flash("모든 필수 항목을 올바르게 입력해주세요.", "danger")
            return render_template('register.html', form_data=request.form)
        email = request.form.get('email')
        if User.query.filter_by(email=email).first():
            flash("이미 가입된 이메일입니다.", "danger")
            return render_template('register.html', form_data=request.form)
        hashed_password = generate_password_hash(request.form.get('password'))
        new_user = User(
            email=email, nickname=request.form.get('nickname'), password=hashed_password,
            role=request.form.get('role', 'experiencer'), name=request.form.get('name'),
            phone=request.form.get('phone'), farm_address=request.form.get('farm_address'),
            farm_size=request.form.get('farm_size')
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

# --- 체험 관련 라우트 ---
@app.route('/experience/<int:item_id>')
def experience_detail(item_id):
    item = Experience.query.get_or_404(item_id)
    reviews = Review.query.filter_by(experience_id=item_id).order_by(Review.timestamp.desc()).all()
    inquiries = Inquiry.query.filter_by(experience_id=item_id).order_by(Inquiry.timestamp.desc()).all()
    item_data_for_js = {'lat': item.lat, 'lng': item.lng}
    return render_template('detail_experience.html', item=item, item_data_for_js=item_data_for_js, reviews=reviews, inquiries=inquiries)

@app.route('/experience/apply/<int:item_id>', methods=['GET', 'POST'])
def experience_apply(item_id):
    if 'user_id' not in session:
        flash("체험을 신청하려면 로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))
    
    item = Experience.query.get_or_404(item_id)
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
        has_parking = 'has_parking' in request.form
        volunteer_needed_str = request.form.get('volunteer_needed')
        volunteer_needed = int(volunteer_needed_str) if volunteer_needed_str else 0
        uploaded_files = request.files.getlist('images')
        filenames = item.images.split(',') if item and item.images else []
        if any(f.filename for f in uploaded_files):
            filenames = []
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                file.save(filepath)
                if filename not in filenames: filenames.append(filename)
        image_string = ",".join(filter(None, filenames))
        address_detail = request.form.get('address')
        lat, lng = get_coords_from_address(address_detail)
        if item:
            item.crop, item.phone, item.address_detail, item.farm_size = request.form.get('crop'), request.form.get('phone'), address_detail, request.form.get('farm_size')
            item.duration_start, item.end_date = datetime.strptime(request.form.get('duration_start'), '%Y-%m-%d').date(), datetime.strptime(request.form.get('duration_end'), '%Y-%m-%d').date()
            item.max_participants, item.cost = int(request.form.get('max_participants')), int(request.form.get('price'))
            item.images, item.notes, item.includes, item.excludes = image_string, request.form.get('notes'), request.form.get('includes'), request.form.get('excludes')
            item.timetable_data, item.pesticide_free = request.form.get('timetable_data'), 'is_organic' in request.form
            item.lat, item.lng = lat, lng
            item.volunteer_needed = volunteer_needed
            item.volunteer_duties = request.form.get('volunteer_duties')
            item.has_parking = has_parking
            flash("체험 정보가 성공적으로 수정되었습니다!", "success")
        else:
            farmer = User.query.get(session['user_id'])
            new_experience = Experience(
                crop=request.form.get('crop'), phone=request.form.get('phone'), location=farmer.farm_address, address_detail=address_detail,
                farm_size=request.form.get('farm_size'), duration_start=datetime.strptime(request.form.get('duration_start'), '%Y-%m-%d').date(),
                end_date=datetime.strptime(request.form.get('duration_end'), '%Y-%m-%d').date(), max_participants=int(request.form.get('max_participants')),
                cost=int(request.form.get('price')), images=image_string, notes=request.form.get('notes'), includes=request.form.get('includes'),
                excludes=request.form.get('excludes'), timetable_data=request.form.get('timetable_data'), pesticide_free='is_organic' in request.form,
                lat=lat, lng=lng, farmer_id=session['user_id'],
                volunteer_needed=volunteer_needed,
                has_parking=has_parking,
                volunteer_duties=request.form.get('volunteer_duties')
            )
            db.session.add(new_experience)
            flash("새로운 체험이 성공적으로 등록되었습니다!", "success")
        db.session.commit()
        return redirect(url_for('index'))
    return render_template('farmer_register.html', item=item)

@app.route('/experience/delete/<int:item_id>', methods=['POST'])
def delete_experience(item_id):
    if 'user_id' not in session or session['role'] != 'farmer': abort(403)
    item = Experience.query.get_or_404(item_id)
    if item.farmer_id != session.get('user_id'): abort(403)
    db.session.delete(item)
    db.session.commit()
    flash("체험이 삭제되었습니다.", "info")
    return redirect(url_for('index'))

@app.route('/experience/<int:item_id>/review', methods=['POST'])
def add_review(item_id):
    if 'user_id' not in session: return redirect(url_for('login_page'))
    new_review = Review(
        rating=int(request.form.get('rating')), content=request.form.get('content'),
        user_id=session['user_id'], experience_id=item_id
    )
    db.session.add(new_review)
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
    db.session.commit()
    flash("문의가 등록되었습니다.", "success")
    return redirect(url_for('experience_detail', item_id=item_id))

# --- 파일 업로드 관련 ---
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

@app.route('/upload_profile', methods=['POST'])
def upload_profile():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    if 'profile_pic' not in request.files or request.files['profile_pic'].filename == '':
        flash('선택된 파일이 없습니다.', 'warning')
        return redirect(url_for('index'))
    file = request.files['profile_pic']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        user = User.query.get(session['user_id'])
        user.profile_image = filename
        db.session.commit()
        flash('프로필 사진이 변경되었습니다.', 'success')
    else:
        flash('허용되지 않는 파일 형식입니다.', 'danger')
    return redirect(url_for('index'))

@app.route('/upload_farm_photo', methods=['POST'])
def upload_farm_photo():
    if 'user_id' not in session or session['role'] != 'farmer': return redirect(url_for('login_page'))
    if 'farm_photo' not in request.files or request.files['farm_photo'].filename == '':
        flash('선택된 파일이 없습니다.', 'warning')
        return redirect(url_for('index'))
    file = request.files['farm_photo']
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
        user = User.query.get(session['user_id'])
        user.farm_image = filename
        db.session.commit()
        flash('농장 사진이 변경되었습니다.', 'success')
    else:
        flash('허용되지 않는 파일 형식입니다.', 'danger')
    return redirect(url_for('index'))
# app.py의 기존 my_info 함수를 찾아 아래 코드로 교체

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
        db.session.commit()
        flash("회원 정보가 성공적으로 수정되었습니다.", "success")
        session['nickname'] = user.nickname
        return redirect(url_for('my_info'))

    # 사용자가 신청한 체험 목록을 DB에서 조회
    applications = Application.query.filter_by(user_id=user.id).order_by(Application.apply_date.desc()).all()
    
    return render_template('my_info.html', user=user, applications=applications)

@app.route('/application/delete/<int:app_id>', methods=['POST'])
def delete_application(app_id):
    if 'user_id' not in session:
        abort(403)
    
    application = Application.query.get_or_404(app_id)
    if application.user_id != session['user_id']:
        abort(403) # 본인의 신청 건이 아니면 삭제 불가

    # 체험의 현재 참가 인원 수 되돌리기
    experience = Experience.query.get(application.experience_id)
    experience.current_participants -= application.participants_count
    
    db.session.delete(application)
    db.session.commit()
    
    flash("체험 신청이 취소되었습니다.", "success")
    return redirect(url_for('my_info'))

@app.route('/volunteer')
def volunteer_apply():
    # Experience 테이블에서 volunteer_needed가 0보다 큰 데이터만 조회
    items = Experience.query.filter(Experience.volunteer_needed > 0).order_by(Experience.duration_start.asc()).all()
    return render_template('volunteer_apply.html', items=items)
# --- 앱 실행 ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True)