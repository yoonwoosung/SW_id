# services/place_score.py — 사용자가 고른 여행 조건으로 관광공사 장소에 점수를 매긴다(순수 함수).
#
# 지금까지 조건은 '체험 목록'만 걸렀고 코스에 들어가는 장소 선정에는 쓰이지 않았다.
# 그래서 조건을 바꿔도 코스가 똑같아 보였다. 여기서는 장소마다 조건 충족 점수를
# 계산해 슬롯 안에서 어떤 장소를 고를지 정한다.
#
# ★조건이 없으면 모든 점수가 0 이라 호출부가 기존 거리순을 그대로 쓴다.★
# 기존 코스 생성을 깨뜨리지 않는 것이 이 모듈의 첫 번째 규칙이다.
from common.search_categories import REGION_ADDRESS_KEYWORDS
from common.constants import (  # noqa: F401  (COURSE_RULE_* 는 routes/course 가 재사용)
    COURSE_ACTIVITY_KAKAO,
    COURSE_CONDITION_WEIGHTS,
    COURSE_FACILITY_NEARBY,
    COURSE_PARTY_RULES,
    COURSE_OTHER_SIBLINGS,
    COURSE_CONDITION_TAIL_WEIGHT,
    COURSE_PLACE_RULES,
    COURSE_RULE_BARRIER_FREE,
    COURSE_RULE_PET,
    COURSE_SEASON_KEYWORDS,
)

# 전용 API 로만 판정하는 조건(분류 코드로는 알 수 없다).
# 전용 API·외부 검색으로만 판정하는 조건(분류 코드로는 알 수 없다).
_API_RULES = ({COURSE_RULE_BARRIER_FREE} | set(COURSE_RULE_PET)
              | set(COURSE_ACTIVITY_KAKAO) | set(COURSE_FACILITY_NEARBY))


def judgeable(code, api_sets=None):
    """이 조건 코드를 장소 판정에 쓸 수 있는가.

    분류 규칙이 있거나, 계절 키워드가 있거나,
    전용 API 결과가 실제로 들어와 있으면 판정할 수 있다.
    ★반려동물 API 가 빈 결과면 반려견 조건은 판정 불가로 빠진다★ —
    가중치를 차지한 채 아무 일도 하지 않으면 다른 조건의 몫을 훔치게 된다.
    """
    if code in COURSE_PLACE_RULES or code in COURSE_SEASON_KEYWORDS:
        return True
    if code in COURSE_OTHER_SIBLINGS:
        return True
    if code in COURSE_PARTY_RULES:
        # 주차가 필요한 규칙은 주차장 조회 결과가 있어야 판정할 수 있다.
        if COURSE_PARTY_RULES[code]["parking"] is None:
            return True
        return bool((api_sets or {}).get("parking"))
    if code in REGION_ADDRESS_KEYWORDS:
        return True      # 지역은 장소 주소로 판정한다(추가 API 호출 없음)
    if code in _API_RULES:
        return bool((api_sets or {}).get(code))
    return False


def ordered_weights(codes):
    """고른 순서대로 가중치를 나눈다. 반환: {코드: 가중치}

    1순위 40% · 2순위 25% · 3순위 15% · 4순위 10% ·
    5순위 이하가 남은 10% 를 균등 분배한다.
    개수가 4개 이하면 남는 몫이 생기므로 전체를 1.0 으로 다시 정규화한다
    (그래야 조건을 2개만 골라도 '1순위가 지배적'이라는 성질이 유지된다).
    """
    codes = list(codes)
    if not codes:
        return {}

    head = list(COURSE_CONDITION_WEIGHTS)
    weights = []
    for index in range(len(codes)):
        if index < len(head):
            weights.append(head[index])
        else:
            tail_count = len(codes) - len(head)
            weights.append(COURSE_CONDITION_TAIL_WEIGHT / tail_count)

    total = sum(weights) or 1.0
    return {code: weight / total for code, weight in zip(codes, weights)}


def _matches_rule(place, rule):
    """분류 규칙 하나를 장소에 대어 본다. cat1/cat2 는 접두사 비교."""
    category = str(place.get("category") or "")      # cat3 (예: A02010700)
    if "content_type" in rule:
        try:
            if int(place.get("content_type_id") or 0) == int(rule["content_type"]):
                return True
        except (TypeError, ValueError):
            pass
    for key in ("cat1", "cat2", "cat3"):
        prefix = rule.get(key)
        if prefix and category.startswith(prefix):
            return True
    return False


def _matches_season(place, code):
    keywords = COURSE_SEASON_KEYWORDS.get(code) or ()
    name = str(place.get("name") or "")
    return any(word in name for word in keywords)


def _place_key(place):
    """전용 API 결과와 대조할 때 쓸 이름. 공백을 털어 표기 차이를 흡수한다."""
    return "".join(str(place.get("name") or "").split())


def _matches_region(place, code):
    """장소 주소가 그 지역인가.

    체험 목록 필터(services/category_match._has_region)와 ★같은 키워드 표★를 쓴다.
    관광공사·CSV 장소 모두 address 를 갖고 있어 추가 호출 없이 판정된다.
    지역은 사용자가 가장 많이 만지는 조건인데 지금까지 코스에 전혀 반영되지 않았다.
    """
    address = str(place.get("address") or "")
    if not address:
        return False
    return any(word in address for word in REGION_ADDRESS_KEYWORDS.get(code, ()))


def _matches_party(place, code, api_sets):
    """인원수 판정 — 주차 여부와 장소 성격을 함께 본다."""
    rule = COURSE_PARTY_RULES[code]
    has_parking = _place_key(place) in ((api_sets or {}).get("parking") or set())

    if rule["parking"] == "required" and not has_parking:
        return False
    if rule["cat"]:
        category = str(place.get("category") or "")
        return any(category.startswith(prefix) for prefix in rule["cat"])
    return has_parking      # 주차만 보는 규칙(3~4명)


def matches(place, code, api_sets=None):
    """장소 하나가 조건 하나를 충족하는가."""
    if code in COURSE_PARTY_RULES:
        return _matches_party(place, code, api_sets)
    if code in REGION_ADDRESS_KEYWORDS:
        return _matches_region(place, code)
    siblings = COURSE_OTHER_SIBLINGS.get(code)
    if siblings is not None:
        # '기타' = 같은 대분류의 다른 선택지 어디에도 걸리지 않는 장소.
        # 범위가 넓어 후보의 상당수가 걸린다. "정해진 성격이 아닌 곳"을 고르는 뜻이다.
        return not any(matches(place, sibling, api_sets) for sibling in siblings)
    if code in _API_RULES:
        names = (api_sets or {}).get(code) or set()
        return _place_key(place) in names
    rule = COURSE_PLACE_RULES.get(code)
    if rule is not None:
        return _matches_rule(place, rule)
    if code in COURSE_SEASON_KEYWORDS:
        return _matches_season(place, code)
    return False


def build_api_sets(barrier_free_places=None, pet_places=None, activity_names=None,
                   facility_names=None):
    """외부 조회 결과를 '이름 집합'으로 바꾼다. 빈 결과면 그 조건은 판정 불가가 된다.

    activity_names: {조건코드: {장소이름, ...}} — 카카오 키워드 검색 결과.
    facility_names: {조건코드: {장소이름, ...}} — 좌표 근접으로 미리 판정한 결과.
    """
    bf = {_place_key(p) for p in (barrier_free_places or []) if p.get("name")}
    pet = {_place_key(p) for p in (pet_places or []) if p.get("name")}
    sets = {}
    if bf:
        sets[COURSE_RULE_BARRIER_FREE] = bf
    if pet:
        for code in COURSE_RULE_PET:
            sets[code] = pet
    for source in (activity_names, facility_names):
        for code, names in (source or {}).items():
            if names:
                sets[code] = set(names)
    return sets


def score_place(place, weights, api_sets=None):
    """장소 하나의 총점(0~1). 충족한 조건의 가중치를 더한다."""
    if not weights:
        return 0.0
    return sum(w for code, w in weights.items() if matches(place, code, api_sets))


def usable_codes(selected_codes, api_sets=None):
    """고른 조건 중 ★실제로 장소 판정에 쓰이는★ 것만 순서대로."""
    return [code for code in (selected_codes or []) if judgeable(code, api_sets)]


def applied_weights(selected_codes, api_sets=None):
    """조건별 반영 비율(%). 화면에 '무엇이 얼마나 반영됐는지' 보여줄 때 쓴다.

    판정 불가 조건은 빠지고 남은 것끼리 다시 나눈 뒤의 값이라,
    사용자가 보는 숫자와 실제 계산이 같다.
    """
    usable = usable_codes(selected_codes, api_sets)
    if not usable:
        return {}
    return {code: round(weight * 100, 1)
            for code, weight in ordered_weights(usable).items()}


def build_scorer(selected_codes, api_sets=None):
    """조건 코드 목록(고른 순서)으로 장소 점수 함수를 만든다.

    판정할 수 없는 조건은 빼고 남은 것끼리 가중치를 다시 나눈다.
    ★판정 불가 조건이 가중치를 들고 있으면 다른 조건의 몫이 줄어든다.★
    쓸 수 있는 조건이 하나도 없으면 None 을 주고, 호출부는 기존 거리순을 쓴다.
    """
    usable = [code for code in (selected_codes or []) if judgeable(code, api_sets)]
    if not usable:
        return None
    weights = ordered_weights(usable)
    return lambda place: score_place(place, weights, api_sets)
