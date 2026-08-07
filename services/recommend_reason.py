# services/recommend_reason.py — 추천 점수에 가장 크게 기여한 요소를 한 줄 이유 문구로 변환.
from services.recommend_service import score_components


def recommendation_reason(distance, max_p, current_p, is_specialty):
    """추천 점수에 가장 크게 기여한 요소를 한 줄 이유 문구로 돌려준다."""
    components = score_components(distance, max_p, current_p, is_specialty)
    top_factor = max(components, key=components.get)
    if components[top_factor] <= 0:
        return "회원님께 추천하는 농장이에요"
    if top_factor == 'distance':
        return f"내 위치에서 약 {distance:.1f}km로 가까워요"
    if top_factor == 'specialty':
        return "이 지역 대표 특산물이에요"
    return f"신청 여유가 넉넉해요 ({current_p}/{max_p}명)"
