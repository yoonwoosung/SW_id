# dummy_data.py
from datetime import date, timedelta

# D-day 계산을 위한 헬퍼 함수
def calculate_d_day(end_date_str):
    end_date = date.fromisoformat(end_date_str)
    delta = end_date - date.today()
    return delta.days

# 임시 체험 데이터
EXPERIENCES = [
    {'id': 1, 'crop': '유기농 상추', 'location': '충남 천안시', 'pesticide_free': True, 'cost': 15000, 'end_date': (date.today() + timedelta(days=7)).isoformat(), 'd_day': 7, 'image': 'https://via.placeholder.com/300x200.png?text=Farm1'},
    {'id': 2, 'crop': '고당도 사과', 'location': '경북 영주시', 'pesticide_free': False, 'cost': 20000, 'end_date': (date.today() + timedelta(days=3)).isoformat(), 'd_day': 3, 'image': 'https://via.placeholder.com/300x200.png?text=Farm2'},
    {'id': 3, 'crop': '해남 고구마', 'location': '전남 해남군', 'pesticide_free': True, 'cost': 18000, 'end_date': (date.today() + timedelta(days=12)).isoformat(), 'd_day': 12, 'image': 'https://via.placeholder.com/300x200.png?text=Farm3'},
]

# 임시 봉사활동 데이터
VOLUNTEER_OPS = [
    {'id': 1, 'farm_name': '햇살농장', 'location': '충남 천안시 동남구', 'hours_per_day': 9, 'start_date': '2025-09-20', 'end_date': '2025-09-22', 'needed_staff': 5, 'current_staff': 2},
    {'id': 2, 'farm_name': '바람농장', 'location': '강원도 평창군', 'hours_per_day': 9, 'start_date': '2025-09-18', 'end_date': '2025-09-19', 'needed_staff': 3, 'current_staff': 3},
]

def get_all_experiences():
    for exp in EXPERIENCES:
        exp['d_day'] = calculate_d_day(exp['end_date'])
    return EXPERIENCES

def get_experience_by_id(item_id):
    return next((item for item in EXPERIENCES if item['id'] == item_id), None)

def get_farmer_listings(): # 농부가 등록한 리스트 (임시로 전체 리스트 반환)
    return get_all_experiences()

def get_all_volunteer_ops():
    return VOLUNTEER_OPS

def get_volunteer_op_by_id(item_id):
    return next((item for item in VOLUNTEER_OPS if item['id'] == item_id), None)