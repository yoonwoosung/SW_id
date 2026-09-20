# services/course_estimate.py — 코스의 이동 시간·체류 시간·비용을 추정한다(순수 함수).
#
# ★전부 '추정'이다.★ 실제 경로·요금 API 를 쓰지 않는다.
#   · 카카오 모빌리티는 자동차 경로만 주고 대중교통 소요시간은 제공하지 않는다
#   · 관광지 입장료·식비를 주는 공개 API 가 없다
# 그래서 좌표 직선거리와 평균값으로 추정한다. 대신 ★화면에 '예상'임을 밝히고
# 산출 내역을 함께 내려보낸다★ — 근거 없는 숫자를 단정적으로 보여주지 않는다.
#
# 예전에는 코스 화면의 '총 8시간'이 COURSE_SLOTS 의 첫 시각과 마지막 시각을
# 뺀 값이었다. 이동·체류와 무관한 상수 뺄셈이라 실제와 달랐다.
from common.constants import (
    COURSE_COST_ATTRACTION,
    COURSE_COST_CAFE,
    COURSE_COST_CAR_PER_KM,
    COURSE_COST_MEAL,
    COURSE_COST_TAXI_BASE,
    COURSE_COST_TAXI_PER_KM,
    COURSE_COST_TRANSIT_PER_LEG,
    COURSE_DEFAULT_TRANSPORT,
    COURSE_ROUTE_DETOUR,
    COURSE_SPEED_KMH,
    COURSE_STAY_MINUTES,
)
from services.distance import haversine

# 슬롯 종류 → 1인 비용 추정
_SLOT_COST = {
    "restaurant": COURSE_COST_MEAL,
    "attraction": COURSE_COST_ATTRACTION,
    "cafe": COURSE_COST_CAFE,
}
_SLOT_LABEL = {
    "experience": "체험",
    "restaurant": "식사",
    "attraction": "관광",
    "cafe": "카페",
}


def normalize_transport(codes):
    """고른 조건에서 이동수단을 고른다. 없으면 기본값(대중교통).

    여러 개를 골랐으면 ★가장 느린 것★을 쓴다 — 시간을 적게 잡아 놓고
    실제로 더 걸리는 것보다, 넉넉히 잡는 편이 덜 위험하다.
    """
    picked = [code for code in (codes or []) if code in COURSE_SPEED_KMH]
    if not picked:
        return COURSE_DEFAULT_TRANSPORT
    return min(picked, key=lambda code: COURSE_SPEED_KMH[code])


def road_distance_km(straight_km):
    """직선거리 → 실제 도로 거리 추정. 곧은 길이 없으므로 보정한다."""
    try:
        return max(0.0, float(straight_km)) * COURSE_ROUTE_DETOUR
    except (TypeError, ValueError):
        return 0.0


def travel_minutes(straight_km, transport=None):
    """구간 이동 시간(분)."""
    speed = COURSE_SPEED_KMH.get(transport or COURSE_DEFAULT_TRANSPORT)
    if not speed:
        return 0
    return int(round(road_distance_km(straight_km) / speed * 60))


def stay_minutes(slot_type):
    return COURSE_STAY_MINUTES.get(slot_type, 0)


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def legs(items):
    """코스 항목 사이의 구간 목록.

    ★이전 장소 → 다음 장소 기준이다.★ 코스 항목의 distance_km 는 '농장에서의
    거리'라 구간 거리가 아니다. 그대로 더하면 실제 동선과 달라진다.
    좌표가 없는 항목이 있으면 그 구간은 건너뛴다.
    """
    result = []
    previous = None
    for item in items or []:
        lat, lng = _to_float(item.get("lat")), _to_float(item.get("lng"))
        if lat is None or lng is None:
            previous = None          # 좌표가 끊기면 다음 구간도 잇지 않는다
            continue
        if previous is not None:
            result.append({
                "from": previous["name"],
                "to": item.get("name"),
                "distance_km": round(haversine(previous["lat"], previous["lng"], lat, lng), 2),
            })
        previous = {"name": item.get("name"), "lat": lat, "lng": lng}
    return result


def travel_cost(total_km, leg_count, transport):
    """교통비(1인, 원)."""
    road = road_distance_km(total_km)
    if transport == "car":
        return int(road * COURSE_COST_CAR_PER_KM)
    if transport == "taxi":
        return int(COURSE_COST_TAXI_BASE + road * COURSE_COST_TAXI_PER_KM)
    return int(COURSE_COST_TRANSIT_PER_LEG * max(0, leg_count))


def estimate(items, experience_cost=0, transport=None):
    """코스 전체의 예상 시간·비용과 산출 내역.

    반환 dict — 화면이 '예상'임을 밝히고 내역을 펼쳐 보여줄 수 있게
    breakdown 을 함께 준다. items 가 비었거나 계산이 안 되면 0 을 돌려주고,
    호출부는 그대로 코스를 만든다(표시만 생략).
    """
    transport = transport or COURSE_DEFAULT_TRANSPORT
    route = legs(items)
    total_km = round(sum(leg["distance_km"] for leg in route), 2)

    for leg in route:
        leg["minutes"] = travel_minutes(leg["distance_km"], transport)

    move_minutes = sum(leg["minutes"] for leg in route)
    stay_total = sum(stay_minutes(item.get("type")) for item in items or [])

    cost_items = []
    if experience_cost:
        cost_items.append({"label": "체험", "amount": int(experience_cost), "estimated": False})
    for item in items or []:
        amount = _SLOT_COST.get(item.get("type"))
        if amount:
            cost_items.append({"label": _SLOT_LABEL.get(item["type"], item["type"]),
                               "amount": amount, "estimated": True})
    moving = travel_cost(total_km, len(route), transport)
    if moving:
        cost_items.append({"label": "교통", "amount": moving, "estimated": True,
                           "note": f"{round(road_distance_km(total_km), 1)}km"})

    return {
        "transport": transport,
        "total_minutes": move_minutes + stay_total,
        "move_minutes": move_minutes,
        "stay_minutes": stay_total,
        "total_distance_km": total_km,
        "total_cost": sum(c["amount"] for c in cost_items),
        "cost_breakdown": cost_items,
        "legs": route,
        # 체험 소요시간은 Experience 에 컬럼이 없어 기본값이다. 화면에 밝힌다.
        "experience_stay_is_default": True,
    }
