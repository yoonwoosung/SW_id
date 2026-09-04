# common/constants.py — 매직넘버 금지: 프로젝트의 숫자·가산점을 이름 붙여 한 곳에서 관리한다.

# --- 외부 API 호출 관련 ---
HTTP_TIMEOUT_SEC = 3            # 외부 API 요청 타임아웃(초)
DEFAULT_SEARCH_RADIUS_M = 3000  # 주변 시설 검색 기본 반경(미터)
MAX_SEARCH_RADIUS_M = 20000     # 한국관광공사 위치기반 API 허용 최대 반경(미터)
NEARBY_RESULT_LIMIT = 30        # 외부 API에서 가져올 최대 항목 수

# --- 추천 점수 ---
# 추천 기본 점수(calculate_score)는 0~1 스케일. 충족한 '대분류'당 이 값을 가산한다(대분류당 OR·1회).
# (3~4개 대분류 충족 시 거리·특산물 점수를 앞서도록 설계. 실제 값은 튜닝 대상)
CATEGORY_MATCH_SCORE = 0.3
# 대분류별 가중치 override(비우면 전부 CATEGORY_MATCH_SCORE 동일). 예: {"region": 0.4}
CATEGORY_WEIGHTS = {}

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
# 코스 총비용(1인당) 추정 = 체험비(입장) + 교통 + 식사. 예산대 채점·코스 카드가 공유. 튜닝 대상.
COURSE_TRANSPORT_ESTIMATE = 8000   # 교통비 추정(1인)
COURSE_MEAL_ESTIMATE = 12000       # 식사·카페 추정(1인)

# --- ESG 점수 (체험의 기존 속성 기반, 항목 합계 100. E·S·G 균형: E55·S35·G10) ---
ESG_SCORE_PESTICIDE_FREE = 30  # 무농약 재배 (환경 E)
ESG_SCORE_ORGANIC = 25         # 유기농 인증 (환경 E)
ESG_SCORE_VOLUNTEER = 20       # 봉사 프로그램 운영 (사회 S)
ESG_SCORE_BARRIER_FREE = 10    # 무장애 접근성 (사회 S)
ESG_SCORE_PARKING = 5          # 주차 접근성 (사회 S)
ESG_SCORE_TRANSPARENCY = 10    # 인증 투명성 - 유기농 증빙 이미지 제출 (지배구조 G)
# 등급 경계
ESG_GRADE_A = 80
ESG_GRADE_B = 60
ESG_GRADE_C = 40

# --- 회원 기반 개인화 추천 (기본 추천점수 0~1 스케일에 더함) ---
PERSONALIZE_CROP_BOOST = 0.4  # 과거 신청한 작물과 같은 작물이면 가점

# --- 클릭 로그 기반 세그먼트 추천 (파트3) ---
SEGMENT_TREND_BOOST = 0.5   # 같은 성별·나이대가 많이 누른 체험이면 가점(취향 신호 강함)
TREND_TOP_LIMIT = 20        # 세그먼트에서 뽑을 인기 대상(체험) 최대 수
TREND_KEYWORD_LIMIT = 8     # 검색창 하단 트렌드 키워드 최대 노출 수
RECENT_VIEWS_LIMIT = 10     # '내 활동 - 최근 본 체험' 최대 노출 수

# --- AI 리뷰 요약(농장 통합·작물 태그) ---
REVIEW_SUMMARY_TOP_KEYWORDS = 3   # 작물별 긍정/개선 키워드 노출 상위 수
# 종합에서 걸러낼 욕설/비속어(간단 필터, 확장 대상). 포함 리뷰는 요약 집계에서 제외.
PROFANITY_FILTER_WORDS = ['씨발', '시발', '존나', '개같', '병신', 'ㅅㅂ', 'ㅄ', '좆']

# --- 예약(Application) 상태값 ---
APPLICATION_STATUS_PENDING = '예정'      # 신청됨(결제 전)
APPLICATION_STATUS_PAID = '결제완료'     # 더미 결제 성공(농장주 수락 대기)
APPLICATION_STATUS_CONFIRMED = '확정'    # 농장주 확정
APPLICATION_STATUS_CANCELLED = '취소'    # 사용자 예약 취소(reservation.py에서 이미 쓰던 값)

# --- 포인트 ---
POINT_EARN_RATE = 0.03           # 결제금액 대비 적립률(3%). 적립액은 정수 내림.
POINT_REASON_PAYMENT = 'payment'      # 결제 적립
POINT_REASON_USE = 'use'              # 결제 시 사용(차감)
POINT_REASON_REFUND = 'refund'        # 결제 실패·취소로 차감분 원복
