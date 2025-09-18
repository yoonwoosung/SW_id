# app.py
from flask import Flask, render_template, session, redirect, url_for, request
# from dummy_data import get_all_experiences, get_experience_by_id, get_farmer_listings, get_all_volunteer_ops, get_volunteer_op_by_id

# ==================================
# ▼▼▼ DB 연동을 위해 추가된 코드 ▼▼▼
# ==================================
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask import jsonify
import os
import json
import datetime
from werkzeug.utils import secure_filename
# ==================================
# ▲▲▲ DB 연동을 위해 추가된 코드 ▲▲▲
# ==================================


app = Flask(__name__)
# session을 사용하기 위해 secret_key가 필요합니다.
app.secret_key = 'supersecretkey'


# ==================================
# ▼▼▼ DB 연동을 위해 추가된 코드 ▼▼▼
# ==================================
# DB 연결 설정 (⭐⭐⭐ 자신의 비밀번호로 꼭 수정해주세요! ⭐⭐⭐)
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:dbsdntjd03!@localhost/farmlink_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

# ==================================
# ▼▼▼ 파일 업로드를 위해 추가된 설정 ▼▼▼
# ==================================
UPLOAD_FOLDER = 'static/uploads'
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
# ==================================
# ▲▲▲ 파일 업로드를 위해 추가된 설정 ▲▲▲
# ==================================


db = SQLAlchemy(app)
bcrypt = Bcrypt(app)

# User 모델(테이블) 정의
# User 모델(테이블) 정의
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(50), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
    
    # ▼▼▼ age와 gender 두 줄이 추가되었습니다 ▼▼▼
    age = db.Column(db.Integer)
    gender = db.Column(db.String(10))

    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
# app.py의 User 클래스 아래에 추가

class Experience(db.Model):
    __tablename__ = 'experiences'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable=False)
    main_crops = db.Column(db.String(255), nullable=False)
    phone_number = db.Column(db.String(20))
    address = db.Column(db.String(255), nullable=False)
    area_size = db.Column(db.String(50))
    start_date = db.Column(db.Date)
    end_date = db.Column(db.Date)
    available_times = db.Column(db.Text) # JSON 형태의 문자열로 저장
    recruit_count = db.Column(db.Integer)
    participation_fee = db.Column(db.Integer)
    main_image_url = db.Column(db.String(255))
    what_to_bring = db.Column(db.Text)
    inclusions = db.Column(db.Text)
    exclusions = db.Column(db.Text)
    volunteer_tasks = db.Column(db.Text)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
    updated_at = db.Column(db.TIMESTAMP, server_default=db.func.now(), onupdate=db.func.now())
# ==================================
# ▲▲▲ DB 연동을 위해 추가된 코드 ▲▲▲
# ==================================

# app.py

# ... class Experience ... 바로 아래에 추가

class Farm(db.Model):
    __tablename__ = 'farms'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique=True, nullable=False)
    farm_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.TIMESTAMP, server_default=db.func.now())
# --- 페이지 라우팅 ---

# 1. 메인 페이지 (체험자, 농부, 봉사자 뷰 전환)
# app.py

# 파일 상단에 datetime 라이브러리를 import 해주세요
import datetime

# ... (다른 코드) ...

@app.route('/')
def index():
    role = session.get('role', 'experiencer')
    
    # 농부일 경우, 자신의 농장 관리 페이지로 리다이렉트 (기존 로직 유지)
    if role == 'farmer':
        return redirect(url_for('my_farm'))
    
    # 체험자 또는 봉사자일 경우, DB에서 모든 체험 목록을 가져옴
    experiences = Experience.query.order_by(Experience.start_date.asc()).all()
    
    # ▼▼▼ [수정된 부분] D-Day 계산 및 volunteer 역할에 필요한 추가 정보 주입 ▼▼▼
    today = datetime.date.today()
    for item in experiences:
        # D-Day 계산
        if item.start_date:
            delta = item.start_date - today
            item.d_day = delta.days
        else:
            item.d_day = None # 시작일이 없으면 D-Day도 없음

        # 봉사자 목록에 필요한 추가 정보 (농장 이름, 현재 지원자 수)
        if role == 'volunteer':
            farm = Farm.query.filter_by(user_id=item.user_id).first()
            item.farm_name = farm.farm_name if farm else "농장 이름 없음"
            # TODO: 실제 지원자 수를 계산하는 로직이 필요합니다.
            item.current_staff = 0 
    # ▲▲▲ [수정된 부분] ▲▲▲
            
    # 역할에 따라 다른 템플릿을 렌더링합니다. (기존 로직 유지)
    if role == 'volunteer':
        return render_template('volunteer_apply.html', items=experiences)
    else: # 'experiencer' 또는 기본
        return render_template('index.html', items=experiences)

# 2. 역할(직업) 선택 및 세션 저장
@app.route('/set_role/<role_name>')
def set_role(role_name):
    if role_name in ['experiencer', 'farmer', 'volunteer']:
        session['role'] = role_name
    return redirect(url_for('index'))

# 3. 체험 상세 페이지
@app.route('/experience/<int:item_id>')
def experience_detail(item_id):
    item = Experience.query.get_or_404(item_id)
    # 구글 플레이 스토어 같은 평점 구조 (임시 데이터)
    reviews = {
        'average': 4.3,
        'total_count': 120,
        'ratings': [
            {'star': 5, 'count': 80},
            {'star': 4, 'count': 25},
            {'star': 3, 'count': 10},
            {'star': 2, 'count': 3},
            {'star': 1, 'count': 2},
        ],
        'comments': [
            {'user': '김체험', 'rating': 5, 'text': '아이들과 좋은 경험하고 갑니다!'},
            {'user': '박여행', 'rating': 4, 'text': '생각보다 힘들었지만 보람있었어요.'},
        ]
    }
    return render_template('detail_experience.html', item=item, reviews=reviews)

# 4. 농부 - 체험 등록 페이지
@app.route('/farmer/register')
def farmer_register():
    return render_template('farmer_register.html')
    
# 5. 봉사자 - 지원 상세 페이지
@app.route('/volunteer/<int:item_id>')
def volunteer_detail(item_id):
    item = Experience.query.get_or_404(item_id)
    return render_template('volunteer_detail.html', item=item)
    
# 6. 봉사자 - 내 정보 페이지
@app.route('/myinfo')
def my_info():
    # 실제로는 DB에서 해당 유저의 봉사 정보를 가져와야 함 (지금은 임시 데이터)
    my_activities = {
        'total_hours': 32,
        'completed_hours': 8,
        'upcoming': [
            {'farm_name': '햇살농장', 'date': '2025-09-20', 'status': 'upcoming'},
            {'farm_name': '초록농원', 'date': '2025-09-27', 'status': 'upcoming'},
        ],
        'completed': [
            {'farm_name': '바람농장', 'date': '2025-08-15', 'status': 'completed'},
        ]
    }
    return render_template('volunteer_myinfo.html', activities=my_activities)
# app.py 파일에 이 코드를 추가해주세요.

@app.route('/register')
def register_page():
    return render_template('register.html')

@app.route('/login')
def login_page():
    return render_template('login.html')

# 9. 로그아웃 처리
@app.route('/logout')
def logout():
    session.clear() # 세션에 저장된 모든 정보를 삭제
    return redirect(url_for('index'))
# 10. 농부 - 내 농장 대시보드 페이지
# app.py

# app.py

@app.route('/myfarm')
def my_farm():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    
    user_id = session['user_id']
    
    # 1. DB에서 이 농장주의 농장 정보를 찾습니다. (farms 테이블 사용)
    farm = Farm.query.filter_by(user_id=user_id).first()
    
    # 2. 이 농장주가 등록한 모든 체험 목록을 찾습니다.
    my_experiences = Experience.query.filter_by(user_id=user_id).order_by(Experience.created_at.desc()).all()
    
    # 3. 간단한 통계 정보 계산
    stats = {
        'total_experiences': len(my_experiences)
        # 나중에 여기에 총 참여자 수, 평균 평점 등 더 복잡한 통계를 추가할 수 있습니다.
    }
    
    # 4. 농장 정보, 체험 목록, 통계 정보를 템플릿으로 전달합니다.
    return render_template('my_farm.html', farm=farm, experiences=my_experiences, stats=stats)
# ==================================
# ▼▼▼ DB 연동을 위해 추가된 코드 ▼▼▼
# ==================================

@app.route('/api/register', methods=['POST'])
def api_register():
    # 1. 프론트엔드에서 보낸 JSON 데이터를 받습니다.
    data = request.get_json()
    if not data:
        return jsonify({'error': '잘못된 요청입니다.'}), 400

    # 2. 각 데이터를 변수에 저장합니다.
    email = data.get('email')
    nickname = data.get('nickname')
    password = data.get('password')
    role = data.get('role')
    age = data.get('age')
    gender = data.get('gender')
    farm_name = data.get('farm_name') # 농장 이름 데이터 받아오기

    # 3. 필수 정보가 모두 있는지 확인합니다.
    if not all([email, nickname, password, role]):
        return jsonify({'error': '필수 정보를 모두 입력해주세요.'}), 400
    
    # 역할이 농장주일 경우, 농장 이름도 필수값으로 검사
    if role == 'farmer' and not farm_name:
        return jsonify({'error': '농장 이름을 입력해주세요.'}), 400

    # 4. 이메일, 닉네임 중복 여부를 확인합니다.
    if User.query.filter_by(email=email).first():
        return jsonify({'error': '이미 사용 중인 이메일입니다.'}), 409
    if User.query.filter_by(nickname=nickname).first():
        return jsonify({'error': '이미 사용 중인 닉네임입니다.'}), 409

    # 5. 비밀번호는 암호화(해싱)해서 저장해야 합니다.
    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    # 6. 모든 정보를 담아 새로운 사용자 객체를 만듭니다.
    new_user = User(
        email=email, 
        password=hashed_password, 
        nickname=nickname,
        role=role,
        age=age,
        gender=gender
    )
    
    db.session.add(new_user)
    db.session.commit() # 먼저 user를 저장해야 user.id가 생성됩니다.

    # 7. 역할이 '농장주'라면, farms 테이블에도 정보를 저장합니다.
    if role == 'farmer':
        new_farm = Farm(user_id=new_user.id, farm_name=farm_name)
        db.session.add(new_farm)
        db.session.commit()
    
    # 8. 성공 메시지를 프론트엔드로 보냅니다.
    return jsonify({'message': '회원가입 성공!'}), 201
# app.py

# (파일 상단에 필요한 import가 있는지 확인하세요: request, jsonify, session)
# (User 모델과 bcrypt 객체도 필요합니다)

@app.route('/api/login', methods=['POST'])
def api_login():
    # 1. 프론트엔드에서 보낸 JSON 데이터 받기
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # 2. 이메일로 DB에서 사용자 정보 찾기
    user = User.query.filter_by(email=email).first()

    # 3. 사용자가 존재하고, 암호화된 비밀번호가 일치하는지 확인
    if user and bcrypt.check_password_hash(user.password, password):
        # 4. 세션에 사용자 정보 저장 (로그인 상태 유지의 핵심!)
        session['user_id'] = user.id
        session['nickname'] = user.nickname
        session['role'] = user.role # 역할 정보 저장
        
        return jsonify({'message': '로그인 성공!'}), 200
    else:
        # 5. 사용자가 없거나 비밀번호가 틀린 경우
        return jsonify({'error': '이메일 또는 비밀번호가 올바르지 않습니다.'}), 401
# ==================================
# ▼▼▼ 농장 체험 등록 API 추가 ▼▼▼
# ==================================
# app.py

@app.route('/api/experiences', methods=['POST'])
def create_experience():
    if 'user_id' not in session:
        return jsonify({'error': '로그인이 필요합니다.'}), 401
    
    user_id = session['user_id']

    # ▼▼▼ html의 name 속성과 동일한 이름으로 데이터를 받습니다 ▼▼▼
    main_crops = request.form.get('main_crops')
    phone_number = request.form.get('phone_number')
    address = request.form.get('address')
    area_size = request.form.get('area_size')
    start_date = request.form.get('start_date')
    end_date = request.form.get('end_date')
    available_times = request.form.get('available_times') # JavaScript에서 JSON 문자열로 넘어옵니다.
    recruit_count = request.form.get('recruit_count')
    participation_fee = request.form.get('participation_fee')
    what_to_bring = request.form.get('what_to_bring')
    inclusions = request.form.get('inclusions')
    exclusions = request.form.get('exclusions')
    volunteer_tasks = request.form.get('volunteer_tasks')
    
    # 파일 처리 (html의 name="main_image"와 일치)
    file = request.files.get('main_image')
    main_image_url = None
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        main_image_url = file_path.replace('\\', '/') # URL 경로를 위해 / 사용

    # DB에 저장
    new_experience = Experience(
        user_id=user_id,
        main_crops=main_crops,
        phone_number=phone_number,
        address=address,
        area_size=area_size,
        start_date=start_date if start_date else None,
        end_date=end_date if end_date else None,
        available_times=available_times,
        recruit_count=recruit_count,
        participation_fee=participation_fee,
        main_image_url=main_image_url,
        what_to_bring=what_to_bring,
        inclusions=inclusions,
        exclusions=exclusions,
        volunteer_tasks=volunteer_tasks
    )

    db.session.add(new_experience)
    db.session.commit()

    return jsonify({'message': '체험 등록에 성공했습니다!'}), 201
# ==================================
# ▲▲▲ 농장 체험 등록 API 추가 ▲▲▲
# ==================================


if __name__ == '__main__':
    app.run(debug=True)