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
