# app.py
from flask import Flask, render_template, session, redirect, url_for, request
from dummy_data import get_all_experiences, get_experience_by_id, get_farmer_listings, get_all_volunteer_ops, get_volunteer_op_by_id

# ==================================
# ▼▼▼ DB 연동을 위해 추가된 코드 ▼▼▼
# ==================================
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask import jsonify
import os
import json
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
class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(255), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False)
    nickname = db.Column(db.String(50), unique=True, nullable=False)
    role = db.Column(db.String(20), nullable=False, default='user')
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


# --- 페이지 라우팅 ---

# 1. 메인 페이지 (체험자, 농부, 봉사자 뷰 전환)
@app.route('/')
def index():
    role = session.get('role', 'experiencer') # 기본값은 '체험자'
    
    if role == 'farmer':
        # 농부일 경우, 자신의 등록 리스트를 보여줌
        my_listings = get_farmer_listings()
        return render_template('farmer_dashboard.html', listings=my_listings)
    
    elif role == 'volunteer':
        # 봉사자일 경우, 지원 가능한 리스트를 보여줌
        volunteer_ops = get_all_volunteer_ops()
        return render_template('volunteer_apply.html', items=volunteer_ops)
        
    else: # 'experiencer' 또는 기본
        # 체험자일 경우, 전체 체험 리스트를 보여줌
        experiences = get_all_experiences()
        # 정렬 기능 (임시)
        sort_by = request.args.get('sort', 'imminent') # URL 파라미터로 정렬 기준 받기
        if sort_by == 'region':
            experiences = sorted(experiences, key=lambda x: x['location'])
        else:
            experiences = sorted(experiences, key=lambda x: x['d_day'])
            
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
    item = get_experience_by_id(item_id)
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
    item = get_volunteer_op_by_id(item_id)
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
@app.route('/myfarm')
def my_farm():
    # 1. 세션에 user_id가 없으면 로그인 페이지로 보냅니다 (로그인 필수).
    if 'user_id' not in session:
        return redirect(url_for('login_page'))
    
    # 2. 현재 로그인된 사용자의 id를 가져옵니다.
    user_id = session['user_id']
    
    # 3. experiences 테이블에서 현재 사용자가 등록한 모든 체험 목록을 찾습니다.
    my_experiences = Experience.query.filter_by(user_id=user_id).order_by(Experience.created_at.desc()).all()
    
    # 4. 찾은 데이터를 my_farm.html 템플릿으로 전달합니다.
    return render_template('my_farm.html', experiences=my_experiences)
# ==================================
# ▼▼▼ DB 연동을 위해 추가된 코드 ▼▼▼
# ==================================
@app.route('/api/register', methods=['POST'])
def api_register():
    data = request.get_json()
    email = data.get('email')
    nickname = data.get('nickname')
    password = data.get('password')
    
    if not all([email, nickname, password]):
        return jsonify({'error': '모든 정보를 입력해주세요.'}), 400

    if User.query.filter_by(email=email).first():
        return jsonify({'error': '이미 사용 중인 이메일입니다.'}), 409
    if User.query.filter_by(nickname=nickname).first():
        return jsonify({'error': '이미 사용 중인 닉네임입니다.'}), 409

    hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
    
    new_user = User(email=email, password=hashed_password, nickname=nickname)
    db.session.add(new_user)
    db.session.commit()
    
    return jsonify({'message': '회원가입 성공!'}), 201
# ==================================
# ▲▲▲ DB 연동을 위해 추가된 코드 ▲▲▲
# ==================================
@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.get_json()
    email = data.get('email')
    password = data.get('password')

    # 1. 이메일로 DB에서 사용자 정보 찾기
    user = User.query.filter_by(email=email).first()

    # 2. 사용자가 존재하고, 암호화된 비밀번호가 일치하는지 확인
    if user and bcrypt.check_password_hash(user.password, password):
        # 3. 세션에 사용자 정보 저장 (이것이 로그인 상태를 유지하는 핵심!)
        session['user_id'] = user.id
        session['nickname'] = user.nickname
        session['role'] = user.role # 역할 정보도 세션에 저장
        return jsonify({'message': '로그인 성공!'}), 200
    else:
        # 사용자가 없거나 비밀번호가 틀린 경우
        return jsonify({'error': '이메일 또는 비밀번호가 올바르지 않습니다.'}), 401

# ==================================
# ▼▼▼ 농장 체험 등록 API 추가 ▼▼▼
# ==================================
@app.route('/api/experiences', methods=['POST'])
def create_experience():
    # 실제 서비스에서는 로그인 여부를 확인해야 합니다.
    # 세션에 user_id가 없으면 로그인 페이지로 보냅니다.
    if 'user_id' not in session:
        return jsonify({'error': '로그인이 필요합니다.'}), 401
    
    # 이제 임시 user_id=1 대신, 세션에서 실제 로그인한 사용자의 id를 가져옵니다.
    user_id = session['user_id']

    # 폼 데이터 가져오기
    main_crops = request.form.get('crop-info')
    phone_number = request.form.get('phone-number')
    address = request.form.get('farm-address')
    area_size = request.form.get('farm-size')
    start_date = request.form.get('start-date')
    end_date = request.form.get('end-date')
    available_times = request.form.get('available-times') # JSON 문자열 형태
    recruit_count = request.form.get('max-participants')
    participation_fee = request.form.get('participation-fee')
    what_to_bring = request.form.get('preparation-notes')
    inclusions = request.form.get('included-items')
    exclusions = request.form.get('excluded-items')
    volunteer_tasks = request.form.get('volunteer-tasks')
    
    # 파일 처리
    file = request.files.get('photos-videos')
    main_image_url = None
    if file:
        filename = secure_filename(file.filename)
        # static/uploads 폴더가 미리 생성되어 있어야 합니다.
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        main_image_url = file_path.replace('\\', '/')

    # DB에 저장할 새 Experience 객체 생성
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