# dummy_data.py

farmer_listings = [
    {
        'id': 1,
        'farm_name': '햇살농장',
        'phone_number': '010-1111-2222',
        'address': '충남 천안시 동남구 유량동 123-45',
        'farm_size': 300,
        'crop': '유기농 상추',
        'is_organic': True,
        'period_start': '2025-10-01',
        'period_end': '2025-10-31',
        'operating_times': ['월 09:00-10:00', '월 10:00-11:00', '수 14:00-15:00'],
        'max_participants': 10,
        'cost': 20000,
        'preparation_note': '편한 복장과 신발, 모자, 선크림을 준비해주세요.',
        'included_items': '수확한 상추 500g, 친환경 비료 1kg',
        'excluded_items': '식사, 교통편',
        'needs_volunteer': True,
        'volunteer_count': 3,
        'volunteer_duties': '잡초 제거, 수확물 운반 등',
        'status': 'recruiting' # 'recruiting'(모집중), 'paused'(모집중단), 'completed'(모집완료)
    }
]

def get_farmer_listings():
    # 최신순으로 정렬하여 반환
    return sorted(farmer_listings, key=lambda x: x['id'], reverse=True)

def get_listing_by_id(item_id):
    # id로 특정 체험 정보 찾기
    for item in farmer_listings:
        if item.get('id') == item_id:
            return item
    return None

def add_farmer_listing(new_listing):
    # 새로운 체험 정보 추가
    if farmer_listings:
        new_id = max(item.get('id', 0) for item in farmer_listings) + 1
    else:
        new_id = 1
    new_listing['id'] = new_id
    new_listing['status'] = 'recruiting' # 최초 등록 시 상태는 '모집중'
    farmer_listings.insert(0, new_listing)

def update_listing_by_id(item_id, updated_data):
    # 기존 체험 정보 수정
    for i, item in enumerate(farmer_listings):
        if item.get('id') == item_id:
            farmer_listings[i].update(updated_data)
            return True
    return False

def delete_listing_by_id(item_id):
    # 체험 정보 삭제
    global farmer_listings
    original_length = len(farmer_listings)
    farmer_listings = [item for item in farmer_listings if item.get('id') != item_id]
    return len(farmer_listings) < original_length
