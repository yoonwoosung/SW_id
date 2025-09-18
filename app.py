# app.py

from flask import Flask, render_template, request, redirect, url_for, flash, session, abort
from flask_sqlalchemy import SQLAlchemy
from werkzeug.security import generate_password_hash, check_password_hash # 비밀번호 암호화를 위한 라이브러리
from datetime import date, timedelta

# --- 1. 앱 및 DB 설정 ---
app = Flask(__name__)
app.secret_key = 'mysql-secret-key-for-production'

# 내 PC의 MySQL 서버에 연결하는 설정
# 'your_password' 부분에 본인의 MySQL root 비밀번호를 입력하세요.
# 'myfarm_db'는 이전에 생성한 데이터베이스 이름입니다.
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+mysqlconnector://root:rootpass0723@localhost/myfarm_db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

db = SQLAlchemy(app)


# --- 2. DB 모델(테이블) 정의 ---
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nickname = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(255), nullable=False) # 해시된 비밀번호는 길이가 길어질 수 있음
    role = db.Column(db.String(50), nullable=False, default='experiencer')
    experiences = db.relationship('Experience', backref='farmer', lazy=True)

class Experience(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    crop = db.Column(db.String(100), nullable=False)
    location = db.Column(db.String(200), nullable=False)
    address_detail = db.Column(db.String(255), nullable=True)
    pesticide_free = db.Column(db.Boolean, default=False)
    cost = db.Column(db.Integer, nullable=False)
    end_date = db.Column(db.Date, nullable=True)
    max_participants = db.Column(db.Integer, default=20)
    current_participants = db.Column(db.Integer, default=0)
    image = db.Column(db.String(255), default='https://via.placeholder.com/800x400.png?text=Farm+Image')
    lat = db.Column(db.Float, default=36.8151)
    lng = db.Column(db.Float, default=127.1139)
    farmer_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    @property
    def d_day(self):
        if self.end_date:
            return (self.end_date - date.today()).days
        return 999


# --- 3. 핵심 라우트 (DB 연동) ---

@app.route('/')
def index():
    role = session.get('role', 'experiencer')
    if role == 'farmer':
        farmer_id = session.get('user_id')
        if not farmer_id:
            flash("로그인이 필요합니다.", "warning")
            return redirect(url_for('login_page'))
        my_listings = Experience.query.filter_by(farmer_id=farmer_id).order_by(Experience.id.desc()).all()
        return render_template('my_farm.html', experiences=my_listings, farm={'farm_name': session.get('nickname')})
    # ... (봉사자 로직은 생략) ...
    else:
        experiences = Experience.query.order_by(Experience.end_date.asc()).all()
        return render_template('index.html', items=experiences)

@app.route('/register', methods=['GET', 'POST'])
def register_page():
    if request.method == 'POST':
        email = request.form.get('email')
        nickname = request.form.get('nickname')
        password = request.form.get('password')
        role = request.form.get('role', 'experiencer')

        existing_user = User.query.filter_by(email=email).first()
        if existing_user:
            flash("이미 가입된 이메일입니다.", "danger")
            return redirect(url_for('register_page'))

        hashed_password = generate_password_hash(password)
        new_user = User(email=email, nickname=nickname, password=hashed_password, role=role)

        db.session.add(new_user)
        db.session.commit()

        flash("회원가입이 완료되었습니다! 로그인해주세요.", "success")
        return redirect(url_for('login_page'))
    return render_template('register.html')

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

@app.route('/experience/<int:item_id>')
def experience_detail(item_id):
    item = Experience.query.get_or_404(item_id)
    return render_template('detail_experience.html', item=item)
    
@app.route('/farmer/register', methods=['GET', 'POST'])
def farmer_register():
    if 'user_id' not in session or session['role'] != 'farmer':
        flash("농장주로 로그인해야만 체험을 등록할 수 있습니다.", "warning")
        return redirect(url_for('login_page'))

    if request.method == 'POST':
        new_experience = Experience(
            crop=request.form.get('crop'),
            location="충남 천안시",
            address_detail=request.form.get('address'),
            pesticide_free=request.form.get('is_organic') == 'true',
            cost=int(request.form.get('price')),
            end_date=date.fromisoformat(request.form.get('duration')),
            farmer_id=session['user_id']
        )
        db.session.add(new_experience)
        db.session.commit()
        flash("새로운 체험이 성공적으로 등록되었습니다!", "success")
        return redirect(url_for('index'))
    return render_template('farmer_register.html')

# (그 외 다른 라우트들은 이전과 유사하게 DB 조회로 변경)

if __name__ == '__main__':
    with app.app_context():
        db.create_all() # DB와 모델을 기반으로 실제 테이블을 생성
    app.run(debug=True)