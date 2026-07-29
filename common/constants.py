# common/constants.py — 매직넘버 금지: 프로젝트의 숫자·가산점을 이름 붙여 한 곳에서 관리한다.

# --- 외부 API 호출 관련 ---
HTTP_TIMEOUT_SEC = 3            # 외부 API 요청 타임아웃(초)
DEFAULT_SEARCH_RADIUS_M = 3000  # 주변 시설 검색 기본 반경(미터)
MAX_SEARCH_RADIUS_M = 20000     # 한국관광공사 위치기반 API 허용 최대 반경(미터)
NEARBY_RESULT_LIMIT = 30        # 외부 API에서 가져올 최대 항목 수

# --- 추천 점수 ---
# 추천 기본 점수(calculate_score)는 0~1 스케일. 카테고리 조건 1건 일치당 이 값을 가산한다.
# (3~4건 일치 시 거리·특산물 점수를 앞서도록 설계. 실제 값은 튜닝 대상)
CATEGORY_MATCH_SCORE = 0.3

# --- AI 추천 코스 ---
COURSE_SEARCH_RADIUS_M = 10000        # 코스용 주변 장소 검색 반경(미터)
# 한국관광공사 contentTypeId (장소 종류 코드)
TOUR_CONTENT_TYPE_ATTRACTION = 12     # 관광지
TOUR_CONTENT_TYPE_RESTAURANT = 39     # 음식점(맛집·카페) — KTO에 별도 카페 타입이 없어 음식점으로 통합
# 코스 시간 슬롯: 시각·장소종류·검색할 contentType (experience는 체험 자체라 API 조회 없음)
COURSE_SLOTS = [
    {"time": "09:00", "type": "experience", "content_type": None},
    {"time": "12:30", "type": "restaurant", "content_type": TOUR_CONTENT_TYPE_RESTAURANT},
    {"time": "15:00", "type": "attraction", "content_type": TOUR_CONTENT_TYPE_ATTRACTION},
    {"time": "17:00", "type": "cafe", "content_type": TOUR_CONTENT_TYPE_RESTAURANT},
]
# 외부 장소를 하나도 못 가져왔을 때 이유 문장(코스 생성 실패와 별개로 기본 문구)
COURSE_REASON_FALLBACK = "체험과 가까운 인기 장소로 구성한 코스입니다."
