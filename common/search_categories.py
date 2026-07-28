# common/search_categories.py — 검색 필터와 역제안 요청글이 공유하는 조건 카테고리(고정값, 단일 출처).
# 프론트는 SEARCH_CATEGORIES 로 드롭박스를 그리고, 매칭 채점은 아래 내부 매핑을 사용한다.

# 공개 트리: 각 항목은 code(영문) + label(한글).
SEARCH_CATEGORIES = [
    {"code": "region", "label": "지역", "items": [
        {"code": "seoul", "label": "서울"}, {"code": "busan", "label": "부산"},
        {"code": "daegu", "label": "대구"}, {"code": "incheon", "label": "인천"},
        {"code": "gwangju", "label": "광주"}, {"code": "daejeon", "label": "대전"},
        {"code": "ulsan", "label": "울산"}, {"code": "sejong", "label": "세종"},
        {"code": "gyeonggi", "label": "경기"}, {"code": "gangwon", "label": "강원"},
        {"code": "chungbuk", "label": "충북"}, {"code": "chungnam", "label": "충남"},
        {"code": "jeonbuk", "label": "전북"}, {"code": "jeonnam", "label": "전남"},
        {"code": "gyeongbuk", "label": "경북"}, {"code": "gyeongnam", "label": "경남"},
        {"code": "jeju", "label": "제주"},
    ]},
    {"code": "experience_type", "label": "체험종류", "items": [
        {"code": "harvest", "label": "수확"}, {"code": "food", "label": "먹거리"},
        {"code": "craft", "label": "공예"}, {"code": "animal", "label": "동물교감"},
        {"code": "farming", "label": "농사체험"}, {"code": "nature", "label": "자연·생태"},
    ]},
    {"code": "companion_type", "label": "동반유형", "items": [
        {"code": "child", "label": "아이"}, {"code": "pet", "label": "반려견"},
        {"code": "elderly", "label": "노약자"}, {"code": "stroller", "label": "유모차"},
        {"code": "group", "label": "단체"},
    ]},
    {"code": "budget_range", "label": "예산대", "items": [
        {"code": "under_10k", "label": "1만원 이하"}, {"code": "range_10k", "label": "1만원대"},
        {"code": "range_20k", "label": "2만원대"}, {"code": "over_30k", "label": "3만원 이상"},
    ]},
    {"code": "facility", "label": "편의시설", "items": [
        {"code": "parking", "label": "주차"}, {"code": "barrier_free", "label": "무장애"},
        {"code": "restroom", "label": "화장실"}, {"code": "pesticide_free", "label": "무농약"},
        {"code": "organic", "label": "유기농인증"},
    ]},
]

CATEGORY_CODES = [category["code"] for category in SEARCH_CATEGORIES]

# --- 채점용 내부 매핑 (Experience에 실제 데이터가 있는 항목만) ---
# 지역 코드 → 주소(address_detail)에서 찾을 키워드.
REGION_ADDRESS_KEYWORDS = {
    "seoul": ["서울"], "busan": ["부산"], "daegu": ["대구"], "incheon": ["인천"],
    "gwangju": ["광주"], "daejeon": ["대전"], "ulsan": ["울산"], "sejong": ["세종"],
    "gyeonggi": ["경기"], "gangwon": ["강원"], "chungbuk": ["충북", "충청북도"],
    "chungnam": ["충남", "충청남도"], "jeonbuk": ["전북", "전라북도"],
    "jeonnam": ["전남", "전라남도"], "gyeongbuk": ["경북", "경상북도"],
    "gyeongnam": ["경남", "경상남도"], "jeju": ["제주"],
}

# 예산대 코드 → (최소원, 최대원). 최대 None = 상한 없음.
BUDGET_RANGES = {
    "under_10k": (0, 9999),
    "range_10k": (10000, 19999),
    "range_20k": (20000, 29999),
    "over_30k": (30000, None),
}
