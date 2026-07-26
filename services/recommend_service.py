# services/recommend_service.py — 추천 점수 계산(특산물 매칭·점수 요소·합산).
from services.recommend_data import REGIONAL_SPECIALTIES


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
