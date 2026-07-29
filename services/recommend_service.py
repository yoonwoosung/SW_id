# services/recommend_service.py — 추천 점수 계산(특산물 매칭·점수 요소·합산·조건 가점).
from common.constants import CATEGORY_MATCH_SCORE
from services.recommend_data import REGIONAL_SPECIALTIES
from services.category_match import compute_category_match
from services.distance import haversine


def matches_specialty(address_detail, crop):
    if address_detail is None or crop is None:
        return False
    for r, specialties in REGIONAL_SPECIALTIES.items():
        if r in address_detail and any(sc in crop for sc in specialties):
            return True
    return False


def score_components(distance, max_p, current_p, is_specialty):
    """추천 점수의 3요소별 가중 기여도를 반환한다.
    calculate_score(합산)와 recommendation_reason(최대 기여 요소 선택)이 공유한다."""
    distance_score = max(0, 1 - (distance / 50))
    if max_p > 0:
        availability_score = (max_p - current_p) / max_p
    else:
        availability_score = 0
    specialty_score = 1.0 if is_specialty else 0
    w1, w2, w3 = 0.5, 0.3, 0.2
    return {
        'distance': w1 * distance_score,
        'specialty': w2 * specialty_score,
        'availability': w3 * availability_score,
    }


def calculate_score(distance, max_p, current_p, is_specialty):
    return sum(score_components(distance, max_p, current_p, is_specialty).values())


def category_bonus(conditions, experience):
    """사용자가 고른 조건과 일치하는 항목 수 × CATEGORY_MATCH_SCORE 가점."""
    return CATEGORY_MATCH_SCORE * compute_category_match(conditions, experience)


def rank_recommendations(experiences, user_lat, user_lon, max_distance_km=150, limit=15):
    """좌표 기준으로 체험들을 추천 점수순 정렬해 (experience, distance_km, score) 목록을 반환한다.
    150km 초과는 제외. 목록/화면 라우트에서 재사용 가능한 순수 로직."""
    ranked = []
    for exp in experiences:
        distance = haversine(user_lat, user_lon, exp.lat, exp.lng)
        if distance > max_distance_km:
            continue
        is_specialty = matches_specialty(exp.address_detail, exp.crop)
        score = calculate_score(distance, exp.max_participants, exp.current_participants, is_specialty)
        ranked.append((exp, round(distance, 1), score))
    ranked.sort(key=lambda x: x[2], reverse=True)
    return ranked[:limit]
