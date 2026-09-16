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

# 지역: 8도(+제주) → 시/군. 구 단위는 나누지 않는다. (code, 라벨, 도 별칭, [(시/군코드, 라벨)])
_REGIONS = [
    ("gyeonggi", "경기", ["경기"], [
        ("suwon", "수원"), ("seongnam", "성남"), ("yongin", "용인"), ("bucheon", "부천"),
        ("ansan", "안산"), ("anyang", "안양"), ("namyangju", "남양주"), ("hwaseong", "화성"),
        ("pyeongtaek", "평택"), ("uijeongbu", "의정부"), ("siheung", "시흥"), ("paju", "파주"),
        ("gimpo", "김포"), ("gwangmyeong", "광명"), ("gwangju_gg", "광주(경기)"), ("gunpo", "군포"),
        ("osan", "오산"), ("icheon", "이천"), ("yangju", "양주"), ("anseong", "안성"),
        ("guri", "구리"), ("pocheon", "포천"), ("uiwang", "의왕"), ("hanam", "하남"),
        ("yeoju", "여주"), ("dongducheon", "동두천"), ("gwacheon", "과천"),
        ("gapyeong", "가평"), ("yangpyeong", "양평"), ("yeoncheon", "연천")]),
    ("gangwon", "강원", ["강원"], [
        ("chuncheon", "춘천"), ("wonju", "원주"), ("gangneung", "강릉"), ("donghae", "동해"),
        ("taebaek", "태백"), ("sokcho", "속초"), ("samcheok", "삼척"), ("hongcheon", "홍천"),
        ("hoengseong", "횡성"), ("yeongwol", "영월"), ("pyeongchang", "평창"), ("jeongseon", "정선"),
        ("cheorwon", "철원"), ("hwacheon", "화천"), ("yanggu", "양구"), ("inje", "인제"),
        ("goseong_gw", "고성(강원)"), ("yangyang", "양양")]),
    ("chungbuk", "충북", ["충북", "충청북도"], [
        ("cheongju", "청주"), ("chungju", "충주"), ("jecheon", "제천"), ("boeun", "보은"),
        ("okcheon", "옥천"), ("yeongdong", "영동"), ("jeungpyeong", "증평"), ("jincheon", "진천"),
        ("goesan", "괴산"), ("eumseong", "음성"), ("danyang", "단양")]),
    ("chungnam", "충남", ["충남", "충청남도"], [
        ("cheonan", "천안"), ("gongju", "공주"), ("boryeong", "보령"), ("asan", "아산"),
        ("seosan", "서산"), ("nonsan", "논산"), ("gyeryong", "계룡"), ("dangjin", "당진"),
        ("geumsan", "금산"), ("buyeo", "부여"), ("seocheon", "서천"), ("cheongyang", "청양"),
        ("hongseong", "홍성"), ("yesan", "예산"), ("taean", "태안")]),
    ("jeonbuk", "전북", ["전북", "전라북도"], [
        ("jeonju", "전주"), ("gunsan", "군산"), ("iksan", "익산"), ("jeongeup", "정읍"),
        ("namwon", "남원"), ("gimje", "김제"), ("wanju", "완주"), ("jinan", "진안"),
        ("muju", "무주"), ("jangsu", "장수"), ("imsil", "임실"), ("sunchang", "순창"),
        ("gochang", "고창"), ("buan", "부안")]),
    ("jeonnam", "전남", ["전남", "전라남도"], [
        ("mokpo", "목포"), ("yeosu", "여수"), ("suncheon", "순천"), ("naju", "나주"),
        ("gwangyang", "광양"), ("damyang", "담양"), ("gokseong", "곡성"), ("gurye", "구례"),
        ("goheung", "고흥"), ("boseong", "보성"), ("hwasun", "화순"), ("jangheung", "장흥"),
        ("gangjin", "강진"), ("haenam", "해남"), ("yeongam", "영암"), ("muan", "무안"),
        ("hampyeong", "함평"), ("yeonggwang", "영광"), ("jangseong", "장성"), ("wando", "완도"),
        ("jindo", "진도"), ("sinan", "신안")]),
    ("gyeongbuk", "경북", ["경북", "경상북도"], [
        ("pohang", "포항"), ("gyeongju", "경주"), ("gimcheon", "김천"), ("andong", "안동"),
        ("gumi", "구미"), ("yeongju", "영주"), ("yeongcheon", "영천"), ("sangju", "상주"),
        ("mungyeong", "문경"), ("gyeongsan", "경산"), ("uiseong", "의성"), ("cheongsong", "청송"),
        ("yeongyang", "영양"), ("yeongdeok", "영덕"), ("cheongdo", "청도"), ("goryeong", "고령"),
        ("seongju", "성주"), ("chilgok", "칠곡"), ("yecheon", "예천"), ("bonghwa", "봉화"),
        ("uljin", "울진"), ("ulleung", "울릉")]),
    ("gyeongnam", "경남", ["경남", "경상남도"], [
        ("changwon", "창원"), ("jinju", "진주"), ("tongyeong", "통영"), ("sacheon", "사천"),
        ("gimhae", "김해"), ("miryang", "밀양"), ("geoje", "거제"), ("yangsan", "양산"),
        ("uiryeong", "의령"), ("haman", "함안"), ("changnyeong", "창녕"), ("goseong_gn", "고성(경남)"),
        ("namhae", "남해"), ("hadong", "하동"), ("sancheong", "산청"), ("hamyang", "함양"),
        ("geochang", "거창"), ("hapcheon", "합천")]),
    ("jeju", "제주", ["제주"], [
        ("jeju_si", "제주시"), ("seogwipo", "서귀포")]),
]


def _region_node():
    return {"code": "region", "label": "지역", "group": "travel", "children": [
        {"code": prov_code, "label": prov_label,
         "children": [{"code": c, "label": cl} for c, cl in cities]}
        for prov_code, prov_label, _aliases, cities in _REGIONS
    ]}


SEARCH_CATEGORIES = [
    _region_node(),
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

# 지역 코드(도·시/군) → 주소(address_detail)에서 찾을 키워드. _REGIONS에서 자동 생성한다.
# 도: 별칭 포함 / 시·군: 라벨(괄호 주석 제거)로 매칭. 예: '안성' 키워드가 '경기도 안성시'를 매칭.
def _build_region_keywords():
    keywords = {}
    for prov_code, prov_label, aliases, cities in _REGIONS:
        keywords[prov_code] = list(aliases)
        for city_code, city_label in cities:
            keywords[city_code] = [city_label.split("(")[0]]  # '광주(경기)' → '광주'
    return keywords


REGION_ADDRESS_KEYWORDS = _build_region_keywords()

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
