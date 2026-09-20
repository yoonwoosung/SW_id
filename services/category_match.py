# services/category_match.py — 사용자가 고른 조건과 체험의 대분류별 일치 여부를 판정한다(순수 함수).
# ★규칙: 한 대분류 안에서 선택값 중 하나라도 맞으면(OR) 그 대분류는 '충족' 1회로 친다(중복 가산 없음).★
# 추천 가점(recommend_service)과 역제안 매칭(match_service)이 함께 재사용한다.
from common.search_categories import (REGION_ADDRESS_KEYWORDS, BUDGET_RANGES,
                                      PET_WEIGHT_MIN_KG, OTHER_SUFFIX)
from common.constants import EXPERIENCE_ACTIVITY_KEYWORDS
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
    if _has_pet(pet_selection(conditions.get("companion_type")), experience):
        matched.add("companion_type")
    if _has_transport(conditions.get("transport"), experience):
        matched.add("transport")
    return matched


def compute_category_match(conditions, experience):
    """조건을 충족한 대분류 수(OR 규칙). 추천 가점·역제안 match_score가 공용으로 쓴다."""
    return len(matched_categories(conditions, experience))


REGION_OTHER = "region" + OTHER_SUFFIX

# 지역 판정에 쓰는 전체 키워드(어느 지역에도 안 걸리는지 볼 때 쓴다).
_ALL_REGION_KEYWORDS = tuple(
    keyword for keywords in REGION_ADDRESS_KEYWORDS.values() for keyword in keywords
)


def _has_region(selected, experience):
    if not selected:
        return False
    address = experience.address_detail or ""

    # '기타' = 주소는 있는데 어떤 시도·시군에도 걸리지 않는 체험.
    # ★주소가 비어 있으면 제외한다★ — 값이 없는 것과 목록 밖인 것은 다르다.
    if REGION_OTHER in selected and address.strip():
        if not any(keyword in address for keyword in _ALL_REGION_KEYWORDS):
            return True

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
        if code == "barrier_free" and getattr(experience, "barrier_free", False):
            return True
        # restroom, nursing_room: Experience 에 대응 컬럼이 없어 판정할 수 없다.
        # 화면에서도 감춘다(common/search_categories 의 hidden).
    return False


def _has_activity(selected, experience):
    """체험의 액티비티 종류를 판정한다.

    ★activity_type 컬럼이 있으면 그것을 우선한다.★ 등록 폼에 드롭다운이
    생기면 아래 키워드 폴백은 저절로 쓰이지 않는다.

    지금은 저장하는 코드가 없어 모든 체험이 NULL 이라, 체험명·설명에서
    키워드를 찾는다. 하나도 없으면 판정하지 않는다 — 억지로 맞히지 않는다.
    """
    if not selected:
        return False

    activity = getattr(experience, "activity_type", None)
    if activity:
        return activity in selected

    text = " ".join(str(getattr(experience, field, "") or "")
                    for field in ("crop", "notes"))
    if not text.strip():
        return False
    return any(
        word in text
        for code in selected
        for word in EXPERIENCE_ACTIVITY_KEYWORDS.get(code, ())
    )


# 반려견은 2026-09-20 리팩터로 'pet_dog' 대분류에서 '동반유형(companion_type)'
# 하위 그룹으로 옮겨졌다. 그룹 노드의 코드가 'pet_allowed' 라서 그룹의 '전체'
# 체크박스가 이 값을 보낸다.
PET_ALLOWED = "pet_allowed"
PET_NOT_ALLOWED = "pet_not_allowed"

# ★동반유형 안에서 실제로 판정할 수 있는 코드.★
# 같은 대분류에 인원수(party_*)·동반구성(solo 등)이 섞여 있는데 이들은
# Experience 에 대응 데이터가 없다. 걸러내지 않으면 사용자가 '혼자'만 골랐을 때
# 동반유형이 '충족해야 할 대분류'로 잡히고 아무 체험도 통과하지 못해
# ★결과가 통째로 0건★ 이 된다(지금까지 무시되던 것이 더 나쁜 버그로 바뀐다).
PET_CODES = frozenset({PET_ALLOWED, PET_NOT_ALLOWED}) | frozenset(PET_WEIGHT_MIN_KG)


def pet_selection(selected):
    """동반유형 선택값에서 반려견 코드만 추린다. 없으면 빈 리스트(판정 건너뜀)."""
    return [code for code in (selected or []) if code in PET_CODES]


def _has_pet(selected, experience):
    """반려견 조건 충족 여부.

    예전에는 몸무게 티어(dog_small/medium/large)만 봤다. 그래서 목록의
    ★'동반가능'·'동반불가'를 고르면 어떤 체험도 통과하지 못했다.★
    '동반가능'은 티어를 감싸는 부모 체크박스라 실제로 전송되는 값이다.

    케어 조건(목줄·케이지·실내·야외)은 대응 컬럼이 없어 여전히 판정하지
    않는다. 화면에서도 감춘다(common/search_categories 의 hidden).
    """
    if not selected:
        return False
    pet_allowed = bool(getattr(experience, "pet_allowed", False))

    if PET_NOT_ALLOWED in selected and not pet_allowed:
        return True
    if not pet_allowed:
        return False
    if PET_ALLOWED in selected:
        return True

    # 몸무게 티어: 체험이 그 몸무게 이상 허용하면 충족.
    allowed_kg = getattr(experience, "pet_max_weight_kg", None)
    if allowed_kg is None:
        return False      # 값이 없으면 '기타'도 아니다(목록 밖이 아니라 미입력이다)

    return any(
        PET_WEIGHT_MIN_KG.get(code) is not None and allowed_kg >= PET_WEIGHT_MIN_KG[code]
        for code in selected
    )


def _has_transport(selected, experience):
    # 자가용(car)만 주차 데이터와 연동해 판정. 대중교통·도보·자전거는 대응 데이터 없음.
    if not selected:
        return False
    return "car" in selected and getattr(experience, "has_parking", False)
