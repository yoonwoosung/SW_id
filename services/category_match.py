# services/category_match.py — 사용자가 고른 조건과 체험 속성의 일치 개수를 센다(순수 함수).
# 추천 가점(recommend_service)과 역제안 매칭(match_service)이 함께 재사용한다.
# 중첩 트리에서 프론트가 보낸 잎 코드({카테고리코드: [선택코드,...]})를 Experience 속성과 대조한다.
from common.search_categories import REGION_ADDRESS_KEYWORDS, BUDGET_RANGES, PET_WEIGHT_MIN_KG


def compute_category_match(conditions, experience):
    """conditions: {카테고리코드: [선택값, ...]}. 반환: 일치한 선택 항목 수(int)."""
    if not conditions:
        return 0
    matched = 0
    matched += _match_region(conditions.get("region"), experience)
    matched += _match_budget(conditions.get("budget_range"), experience)
    matched += _match_facility(conditions.get("facility"), experience)
    matched += _match_activity(conditions.get("activity"), experience)
    matched += _match_pet(conditions.get("pet_dog"), experience)
    matched += _match_transport(conditions.get("transport"), experience)
    return matched


def _match_region(selected, experience):
    if not selected:
        return 0
    address = experience.address_detail or ""
    return sum(
        1 for code in selected
        if any(keyword in address for keyword in REGION_ADDRESS_KEYWORDS.get(code, []))
    )


def _match_budget(selected, experience):
    if not selected or experience.cost is None:
        return 0
    matched = 0
    for code in selected:
        rng = BUDGET_RANGES.get(code)
        if not rng:
            continue
        low, high = rng
        if experience.cost >= low and (high is None or experience.cost <= high):
            matched += 1
    return matched


def _match_facility(selected, experience):
    if not selected:
        return 0
    matched = 0
    for code in selected:
        if code == "parking" and getattr(experience, "has_parking", False):
            matched += 1
        elif code == "wifi" and getattr(experience, "has_wifi", False):
            matched += 1
        elif code == "pesticide_free" and getattr(experience, "pesticide_free", False):
            matched += 1
        elif code == "organic" and getattr(experience, "organic_certification_type", None):
            matched += 1
        # restroom, barrier_free: Experience에 대응 데이터가 없어 채점하지 않는다.
    return matched


def _match_activity(selected, experience):
    if not selected:
        return 0
    activity = getattr(experience, "activity_type", None)
    return sum(1 for code in selected if activity and code == activity)


def _match_pet(selected, experience):
    # 몸무게 티어(dog_small/medium/large)만 채점: 체험이 그 몸무게 이상 허용하면 일치.
    if not selected or not getattr(experience, "pet_allowed", False):
        return 0
    allowed_kg = getattr(experience, "pet_max_weight_kg", None)
    if allowed_kg is None:
        return 0
    matched = 0
    for code in selected:
        need_kg = PET_WEIGHT_MIN_KG.get(code)
        if need_kg is not None and allowed_kg >= need_kg:
            matched += 1
        # 목줄·케이지 등 하위 조건은 Experience에 데이터가 없어 채점하지 않는다.
    return matched


def _match_transport(selected, experience):
    # 자가용(car)만 주차 데이터와 연동해 채점. 대중교통·도보·자전거는 대응 데이터 없음.
    if not selected:
        return 0
    return sum(1 for code in selected if code == "car" and getattr(experience, "has_parking", False))
