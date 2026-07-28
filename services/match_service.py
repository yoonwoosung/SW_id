# services/match_service.py — 사용자 요청글 조건 ↔ 농장(체험) 특성의 매칭 점수(순수 함수).
# "농장주에게 뜨는 맞는 사용자 추천"의 근거. 파트2의 category_match 로직을 재사용한다.
import json

from services.category_match import compute_category_match


def parse_conditions(user_request):
    """요청글의 conditions(JSON 문자열)를 dict로 복원한다. 비어있거나 손상 시 {}."""
    try:
        return json.loads(user_request.conditions) if user_request.conditions else {}
    except (ValueError, TypeError):
        return {}


def compute_match_score(user_request, experience):
    """요청 조건과 체험 속성이 일치하는 정도(점수). 클수록 잘 맞음."""
    conditions = parse_conditions(user_request)
    return compute_category_match(conditions, experience)


def best_match_for_experiences(user_request, experiences):
    """농장주의 여러 체험 중 요청글과 가장 잘 맞는 점수를 반환한다(없으면 0)."""
    if not experiences:
        return 0
    return max(compute_match_score(user_request, exp) for exp in experiences)
