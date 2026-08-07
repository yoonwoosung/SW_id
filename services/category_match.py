# services/category_match.py — 사용자가 고른 조건과 체험의 대분류별 일치 여부를 판정한다(순수 함수).
# ★규칙: 한 대분류 안에서 선택값 중 하나라도 맞으면(OR) 그 대분류는 '충족' 1회로 친다(중복 가산 없음).★
# 추천 가점(recommend_service)과 역제안 매칭(match_service)이 함께 재사용한다.
from common.search_categories import REGION_ADDRESS_KEYWORDS, BUDGET_RANGES, PET_WEIGHT_MIN_KG
from services.course_builder import estimate_course_cost_per_person


def matched_categories(conditions, experience):
    """조건을 충족한 대분류 코드 집합을 반환한다(대분류당 OR, 최대 1회)."""
    if not conditions:
        return set()
    matched = set()
    if _has_region(conditions.get("region"), experience):
        matched.add("region")
    if _has_budget(conditions.get("budget_range"), experience):
        matched.add("budget_range")
    if _has_facility(conditions.get("facility"), experience):
        matched.add("facility")
    if _has_activity(conditions.get("activity"), experience):
        matched.add("activity")
    if _has_pet(conditions.get("pet_dog"), experience):
        matched.add("pet_dog")
    if _has_transport(conditions.get("transport"), experience):
        matched.add("transport")
    return matched


def compute_category_match(conditions, experience):
    """조건을 충족한 대분류 수(OR 규칙). 추천 가점·역제안 match_score가 공용으로 쓴다."""
    return len(matched_categories(conditions, experience))


def _has_region(selected, experience):
    if not selected:
        return False
    address = experience.address_detail or ""
    return any(
        keyword in address
        for code in selected
        for keyword in REGION_ADDRESS_KEYWORDS.get(code, [])
    )


def _has_budget(selected, experience):
    # 예산대는 코스 총비용(1인당) 기준. 선택 구간 중 하나에 들면 충족.
    if not selected:
        return False
    course_cost = estimate_course_cost_per_person(experience)
    for code in selected:
        rng = BUDGET_RANGES.get(code)
        if not rng:
            continue
        low, high = rng
        if course_cost >= low and (high is None or course_cost <= high):
            return True
    return False


def _has_facility(selected, experience):
    if not selected:
        return False
    for code in selected:
        if code == "parking" and getattr(experience, "has_parking", False):
            return True
        if code == "wifi" and getattr(experience, "has_wifi", False):
            return True
        if code == "pesticide_free" and getattr(experience, "pesticide_free", False):
            return True
        if code == "organic" and getattr(experience, "organic_certification_type", None):
            return True
        # restroom, barrier_free, nursing_room: Experience에 대응 데이터가 없어 판정하지 않는다.
    return False


def _has_activity(selected, experience):
    if not selected:
        return False
    activity = getattr(experience, "activity_type", None)
    return bool(activity) and activity in selected


def _has_pet(selected, experience):
    # 몸무게 티어(dog_small/medium/large)만 판정: 체험이 그 몸무게 이상 허용하면 충족.
    if not selected or not getattr(experience, "pet_allowed", False):
        return False
    allowed_kg = getattr(experience, "pet_max_weight_kg", None)
    if allowed_kg is None:
        return False
    return any(
        PET_WEIGHT_MIN_KG.get(code) is not None and allowed_kg >= PET_WEIGHT_MIN_KG[code]
        for code in selected
    )


def _has_transport(selected, experience):
    # 자가용(car)만 주차 데이터와 연동해 판정. 대중교통·도보·자전거는 대응 데이터 없음.
    if not selected:
        return False
    return "car" in selected and getattr(experience, "has_parking", False)
