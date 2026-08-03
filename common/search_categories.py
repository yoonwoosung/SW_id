# common/search_categories.py — 검색 필터와 역제안 요청글이 공유하는 조건 카테고리(고정값, 단일 출처).
# 프론트는 SEARCH_CATEGORIES(중첩 트리)로 아코디언 드롭박스를 그리고, 채점은 아래 내부 매핑을 사용한다.
# 구조: 각 노드 = {code(영문), label(한글), children?(하위 노드 리스트)}. children 없으면 잎(선택 가능).


def _pet_conditions():
    # 반려견 몸무게 노드 하위 공통 조건(목줄·케이지 등) — 티어마다 새 리스트로 생성.
    return [
        {"code": "leash_required", "label": "목줄필수"},
        {"code": "cage_required", "label": "케이지필요"},
        {"code": "indoor_ok", "label": "실내동반"},
        {"code": "outdoor_only", "label": "야외만"},
    ]


# 최상위 카테고리 묶음(프론트 드롭박스 섹션 구분용).
CATEGORY_GROUPS = [
    {"code": "travel", "label": "여행 조건"},
    {"code": "taste", "label": "취향·활동"},
    {"code": "practical", "label": "실용 조건"},
]

SEARCH_CATEGORIES = [
    {"code": "region", "label": "지역", "group": "travel", "children": [
        {"code": "gyeonggi", "label": "경기", "children": [
            {"code": "icheon", "label": "이천"}, {"code": "anseong", "label": "안성"},
            {"code": "gapyeong", "label": "가평"}, {"code": "yongin", "label": "용인"},
            {"code": "yeoju", "label": "여주"}, {"code": "paju", "label": "파주"}]},
        {"code": "chungnam", "label": "충남", "children": [
            {"code": "cheonan", "label": "천안", "children": [
                {"code": "cheonan_dongnam", "label": "동남구"},
                {"code": "cheonan_seobuk", "label": "서북구"}]},
            {"code": "gongju", "label": "공주"}, {"code": "nonsan", "label": "논산"},
            {"code": "asan", "label": "아산"}]},
        {"code": "chungbuk", "label": "충북", "children": [
            {"code": "cheongju", "label": "청주"}, {"code": "chungju", "label": "충주"},
            {"code": "jecheon", "label": "제천"}]},
        {"code": "gangwon", "label": "강원", "children": [
            {"code": "chuncheon", "label": "춘천"}, {"code": "wonju", "label": "원주"},
            {"code": "gangneung", "label": "강릉"}, {"code": "pyeongchang", "label": "평창"}]},
        {"code": "jeonbuk", "label": "전북", "children": [
            {"code": "jeonju", "label": "전주"}, {"code": "namwon", "label": "남원"},
            {"code": "gochang", "label": "고창"}]},
        {"code": "jeonnam", "label": "전남", "children": [
            {"code": "suncheon", "label": "순천"}, {"code": "damyang", "label": "담양"},
            {"code": "boseong", "label": "보성"}]},
        {"code": "gyeongbuk", "label": "경북", "children": [
            {"code": "gyeongju", "label": "경주"}, {"code": "andong", "label": "안동"},
            {"code": "yeongju", "label": "영주"}]},
        {"code": "gyeongnam", "label": "경남", "children": [
            {"code": "jinju", "label": "진주"}, {"code": "hadong", "label": "하동"},
            {"code": "sancheong", "label": "산청"}]},
        {"code": "jeju", "label": "제주", "children": [
            {"code": "jeju_si", "label": "제주시"}, {"code": "seogwipo", "label": "서귀포"}]},
    ]},
    {"code": "companion_type", "label": "동반유형", "group": "travel", "children": [
        {"code": "solo", "label": "혼자"}, {"code": "couple", "label": "커플"},
        {"code": "family_child", "label": "가족(아이)"}, {"code": "friends", "label": "친구"},
        {"code": "parents", "label": "부모님"}, {"code": "with_pet", "label": "반려견"}]},
    {"code": "pet_dog", "label": "반려견", "group": "travel", "children": [
        {"code": "pet_allowed", "label": "동반가능", "children": [
            {"code": "dog_small", "label": "소형(5kg 미만)", "children": _pet_conditions()},
            {"code": "dog_medium", "label": "중형(5~15kg)", "children": _pet_conditions()},
            {"code": "dog_large", "label": "대형(15kg 이상)", "children": _pet_conditions()},
        ]},
        {"code": "pet_not_allowed", "label": "동반불가"},
    ]},
    {"code": "party", "label": "인원", "group": "travel", "children": [
        {"code": "headcount", "label": "인원수", "children": [
            {"code": "party_1", "label": "1명"}, {"code": "party_2", "label": "2명"},
            {"code": "party_3_4", "label": "3~4명"}, {"code": "party_5plus", "label": "5명 이상"}]},
        {"code": "age_composition", "label": "연령대 구성", "children": [
            {"code": "adults_only", "label": "성인만"}, {"code": "with_child", "label": "아이 동반"},
            {"code": "with_parents", "label": "부모님 동반"}]},
    ]},
    {"code": "schedule", "label": "일정", "group": "travel", "children": [
        {"code": "day_trip", "label": "당일"}, {"code": "one_night", "label": "1박 2일"}]},
    {"code": "experience_type", "label": "체험종류", "group": "taste", "children": [
        {"code": "harvest", "label": "수확"}, {"code": "food", "label": "먹거리"},
        {"code": "craft", "label": "공예"}, {"code": "animal", "label": "동물교감"},
        {"code": "nature", "label": "자연생태"}]},
    {"code": "activity", "label": "액티비티", "group": "taste", "children": [
        {"code": "horse_riding", "label": "승마"}, {"code": "kayak", "label": "카약"},
        {"code": "fishing", "label": "낚시"}, {"code": "hiking", "label": "등산"},
        {"code": "cycling", "label": "자전거"}]},
    {"code": "mood", "label": "분위기", "group": "taste", "children": [
        {"code": "healing", "label": "힐링"}, {"code": "active", "label": "액티브"},
        {"code": "photo", "label": "인생샷"}, {"code": "educational", "label": "교육적"},
        {"code": "tradition", "label": "전통"}]},
    {"code": "season", "label": "계절·제철", "group": "taste", "children": [
        {"code": "spring_strawberry", "label": "봄 딸기"}, {"code": "summer_blueberry", "label": "여름 블루베리"},
        {"code": "autumn_harvest", "label": "가을 수확"}, {"code": "winter_experience", "label": "겨울 체험"}]},
    {"code": "budget_range", "label": "예산대", "group": "practical",
     "note": "*1인당 코스 총비용(교통·식사 포함) 기준입니다", "children": [
        {"code": "course_under_30k", "label": "3만원 이하"}, {"code": "course_30_50k", "label": "3~5만원"},
        {"code": "course_50_100k", "label": "5~10만원"}, {"code": "course_over_100k", "label": "10만원 이상"}]},
    {"code": "transport", "label": "교통수단", "group": "practical", "children": [
        {"code": "car", "label": "자가용"}, {"code": "public_transit", "label": "대중교통"},
        {"code": "walk", "label": "도보"}, {"code": "bike", "label": "자전거"}]},
    {"code": "duration_hours", "label": "소요시간", "group": "practical", "children": [
        {"code": "hours_2", "label": "2시간"}, {"code": "half_day", "label": "반나절"},
        {"code": "full_day", "label": "종일"}]},
    {"code": "facility", "label": "편의시설", "group": "practical", "children": [
        {"code": "parking", "label": "주차"}, {"code": "restroom", "label": "화장실"},
        {"code": "barrier_free", "label": "무장애"}, {"code": "wifi", "label": "와이파이"},
        {"code": "nursing_room", "label": "수유실"},
        {"code": "pesticide_free", "label": "무농약"}, {"code": "organic", "label": "유기농인증"}]},
]

CATEGORY_CODES = [category["code"] for category in SEARCH_CATEGORIES]


def _iter_leaf_codes(nodes):
    for node in nodes:
        children = node.get("children")
        if children:
            yield from _iter_leaf_codes(children)
        else:
            yield node["code"]


# 트리 전체의 잎 코드 집합(유효성 검증·테스트용).
LEAF_CODES = set(_iter_leaf_codes(SEARCH_CATEGORIES))


def _iter_all_nodes(nodes):
    for node in nodes:
        yield node
        if node.get("children"):
            yield from _iter_all_nodes(node["children"])


# 코드 → 한글 라벨(트렌드 키워드 표시 등에 사용).
LABEL_BY_CODE = {node["code"]: node["label"] for node in _iter_all_nodes(SEARCH_CATEGORIES)}


# ============================================================
# 채점용 내부 매핑 (Experience에 실제 데이터가 있는 항목만)
# ============================================================

# 지역 코드(시/도·시군구·구) → 주소(address_detail)에서 찾을 키워드.
REGION_ADDRESS_KEYWORDS = {
    # 시/도
    "gyeonggi": ["경기"], "chungnam": ["충남", "충청남도"], "chungbuk": ["충북", "충청북도"],
    "gangwon": ["강원"], "jeonbuk": ["전북", "전라북도"], "jeonnam": ["전남", "전라남도"],
    "gyeongbuk": ["경북", "경상북도"], "gyeongnam": ["경남", "경상남도"], "jeju": ["제주"],
    # 시/군
    "icheon": ["이천"], "anseong": ["안성"], "gapyeong": ["가평"], "yongin": ["용인"],
    "yeoju": ["여주"], "paju": ["파주"], "cheonan": ["천안"], "gongju": ["공주"],
    "nonsan": ["논산"], "asan": ["아산"], "cheongju": ["청주"], "chungju": ["충주"],
    "jecheon": ["제천"], "chuncheon": ["춘천"], "wonju": ["원주"], "gangneung": ["강릉"],
    "pyeongchang": ["평창"], "jeonju": ["전주"], "namwon": ["남원"], "gochang": ["고창"],
    "suncheon": ["순천"], "damyang": ["담양"], "boseong": ["보성"], "gyeongju": ["경주"],
    "andong": ["안동"], "yeongju": ["영주"], "jinju": ["진주"], "hadong": ["하동"],
    "sancheong": ["산청"], "jeju_si": ["제주시"], "seogwipo": ["서귀포"],
    # 구(천안)
    "cheonan_dongnam": ["동남구"], "cheonan_seobuk": ["서북구"],
}

# 예산대 코드 → (최소원, 최대원). ★코스 총비용(1인당) 기준★. 최대 None = 상한 없음.
BUDGET_RANGES = {
    "course_under_30k": (0, 29999),
    "course_30_50k": (30000, 49999),
    "course_50_100k": (50000, 99999),
    "course_over_100k": (100000, None),
}

# 반려견 몸무게 티어 코드 → 체험이 최소 이 kg 이상 허용해야 매칭(Experience.pet_max_weight_kg 기준).
PET_WEIGHT_MIN_KG = {
    "dog_small": 5,
    "dog_medium": 15,
    "dog_large": 25,
}
