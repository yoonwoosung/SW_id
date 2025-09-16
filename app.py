# app.py
from flask import Flask, render_template, session, redirect, url_for, request, abort
from dummy_data import get_all_experiences, get_experience_by_id, get_farmer_listings, get_all_volunteer_ops, get_volunteer_op_by_id

app = Flask(__name__)
# session을 사용하기 위해 secret_key가 필요합니다.
app.secret_key = 'supersecretkey'

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

        # ▼▼▼▼▼ 이 부분을 추가해야 합니다 ▼▼▼▼▼
    if item is None:
        abort(404)
        
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

if __name__ == '__main__':
    app.run(debug=True)