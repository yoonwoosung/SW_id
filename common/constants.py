# common/constants.py — 매직넘버 금지: 프로젝트의 숫자·가산점을 이름 붙여 한 곳에서 관리한다.

# --- 외부 API 호출 관련 ---
HTTP_TIMEOUT_SEC = 3            # 외부 API 요청 타임아웃(초)
DEFAULT_SEARCH_RADIUS_M = 3000  # 주변 시설 검색 기본 반경(미터)
MAX_SEARCH_RADIUS_M = 20000     # 한국관광공사 위치기반 API 허용 최대 반경(미터)
NEARBY_RESULT_LIMIT = 30        # 외부 API에서 가져올 최대 항목 수

# --- 한국관광공사(KTO) 조회 결과 파일 캐시 (services/tour_cache.py) ---
# KTO 일일 한도가 1,000건이라 코스 카드마다 새로 조회하면 금방 소진된다.
TOUR_CACHE_TTL_SEC = 3600        # 정상 결과 보관(초). 관광지 정보는 이보다 훨씬 느리게 바뀐다.
TOUR_CACHE_EMPTY_TTL_SEC = 300   # 빈 결과 보관(초). 일시 장애로 받은 []를 오래 물면
                                 # API가 복구돼도 '코스 생성 불가'가 굳으므로 짧게 잡는다.
TOUR_CACHE_MAX_ENTRIES = 500     # 캐시 파일 수 상한. 넘으면 오래된 것부터 지운다.

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

# --- 세그먼트별 점수 가중치 ---
# 세그먼트마다 기준을 다르게 주려고 기본 점수(calculate_score) 위에 더하는 보너스다.
# 기본 점수는 건드리지 않는다.
#
# 쓸 수 있는 축은 실제 데이터 분포를 보고 골랐다(배포 10건 기준).
#   cost 10,000~30,000(3배) · remaining 5~30(6배) · has_parking 4/10 → 변별력 있음
#   barrier_free 0/10 · pet_allowed 거의 없음 → 넣어도 전부 0점이라 제외
#
# 'peers' 세그먼트 = 화면의 '가볍게 다녀오기 좋은 코스'
SEGMENT_LIGHT_CHEAP_WEIGHT = 0.5    # 후보군 내 상대 저렴도
SEGMENT_LIGHT_NEAR_WEIGHT = 0.3     # 가까울수록 가점
# 'group' 세그먼트 = 화면의 '단체로 가기 좋은 코스'
SEGMENT_GROUP_CAPACITY_WEIGHT = 0.5  # 후보군 내 상대 잔여석(절대 인원 기준)
SEGMENT_GROUP_PARKING_WEIGHT = 0.2   # 주차 가능하면 가점
TREND_TOP_LIMIT = 20        # 세그먼트에서 뽑을 인기 대상(체험) 최대 수
TREND_KEYWORD_LIMIT = 8     # 검색창 하단 트렌드 키워드 최대 노출 수
RECENT_VIEWS_LIMIT = 10     # '내 활동 - 최근 본 체험' 최대 노출 수

# --- AI 리뷰 요약(농장 통합·작물 태그) ---
REVIEW_SUMMARY_TOP_KEYWORDS = 3   # 작물별 긍정/개선 키워드 노출 상위 수
# 종합에서 걸러낼 욕설/비속어(간단 필터, 확장 대상). 포함 리뷰는 요약 집계에서 제외.
PROFANITY_FILTER_WORDS = ['씨발', '시발', '존나', '개같', '병신', 'ㅅㅂ', 'ㅄ', '좆']

# --- 예약(Application) 상태값 ---
#
# 전이:  예정 ──결제 성공──▶ 결제완료 ──농장주 수락──▶ 확정 ──체험 종료──▶ (완료 판정)
#          │                    └──농장주 거절──▶ 취소 (+ 결제액 포인트 환급)
#          └──사용자 취소──▶ 취소
#
# ★'결제완료'가 곧 '농장주 승인 대기'다.★ 같은 뜻의 상태를 새로 만들지 말 것.
# activity_service 가 이 값을 STATE_AWAIT_ACCEPT('수락 대기중')로 판정하고,
# 사용자 화면(my_info·mypage)도 이미 그 라벨로 보여준다.
# '완료'는 별도 컬럼 값이 아니라 확정 + 체험 종료로 판정한다(activity_service).
APPLICATION_STATUS_PENDING = '예정'      # 신청됨(결제 전)
APPLICATION_STATUS_PAID = '결제완료'     # 결제 성공 — 농장주 수락 대기
APPLICATION_STATUS_CONFIRMED = '확정'    # 농장주 수락
APPLICATION_STATUS_CANCELLED = '취소'    # 사용자 취소 또는 농장주 거절

# --- 포인트 ---
POINT_EARN_RATE = 0.03           # 결제금액 대비 적립률(3%). 적립액은 정수 내림.
POINT_REASON_PAYMENT = 'payment'      # 결제 적립
POINT_REASON_USE = 'use'              # 결제 시 사용(차감)
POINT_REASON_REFUND = 'refund'        # 결제 실패·취소로 차감분 원복

# --- 과생산(잉여) 농산물 할인 구간 ---
# 농장주가 정가와 총 과생산량만 입력하면 시스템이 할인율을 정한다.
# 많이 남을수록 싸게 푸는 게 취지라 수량이 클수록 할인율이 올라간다.
#
# 읽는 법: (상한, 할인율%) 을 앞에서부터 보며 '상한 미만'이면 그 할인율.
# 마지막 항목의 상한 None 은 '그 이상 전부'다.
# 정수 퍼센트로 두는 이유는 최대 체험료를 정수 연산으로 정확히 구하기 위해서다
# (0.6 같은 부동소수를 곱하면 50000 × 0.6 이 29999.999… 가 되어 상한이 1원 줄어든다).
SURPLUS_DISCOUNT_TIERS = {
    'kg':   ((100, 20), (300, 30), (600, 40), (1000, 50), (None, 60)),
    '박스': ((10, 20),  (30, 30),  (60, 40),  (100, 50),  (None, 60)),   # 1박스 ≈ 10kg 기준
    '구좌': ((20, 20),  (50, 30),  (100, 40), (200, 50),  (None, 60)),   # 1구좌 = 1인분
}

# 자체 구간표가 없고 다른 단위로 환산해 쓰는 단위. {단위: (환산할 표, 나눌 값)}
SURPLUS_UNIT_CONVERSION = {
    'g': ('kg', 1000),
}

# 구간표가 없는 단위(포기·단)의 기본 할인율(%).
# 배추 1포기·파 1단이 몇 kg 인지는 작물마다 달라 환산 계수를 정하면 근거 없는 수치가 된다.
# 최저 구간을 주면 최대 체험료가 가장 높아 농장주에게 불리하지 않고,
# 기존 정책의 하한(20%)도 지켜진다. 화면에는 왜 20% 인지 안내를 함께 띄운다.
SURPLUS_DEFAULT_DISCOUNT_PERCENT = 20
