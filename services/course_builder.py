# services/course_builder.py — 주변 장소를 시간순 코스로 조립하는 규칙 기반 로직(순수 함수, 테스트 가능).
# 장소 선정·순서는 여기서 규칙으로 정한다(LLM이 장소를 지어내지 않게 함).
from common.constants import COURSE_SLOTS
from services.distance import haversine  # 거리 계산은 기존 함수 재사용


def build_course(experience, places_by_type):
    """체험 좌표를 기준으로 시간순 코스 항목 리스트를 만든다.

    places_by_type: {슬롯 type: [place, ...]} — 각 place는 name·lat·lng를 가진다.
    같은 장소가 여러 슬롯에 중복되지 않게 하고, 가까운 순으로 고른다.
    가져온 장소가 없으면 체험 항목만 담아 반환한다(호출부에서 실패 처리).
    """
    origin_lat, origin_lng = experience.lat, experience.lng
    used_names = set()
    items = []
    for slot in COURSE_SLOTS:
        if slot["type"] == "experience":
            name = f"{experience.crop} 체험"
            items.append({"time": slot["time"], "type": "experience", "name": name, "distance_km": 0.0})
            used_names.add(name)
            continue
        candidates = _sorted_by_distance(origin_lat, origin_lng, places_by_type.get(slot["type"], []))
        picked = _first_unused(candidates, used_names)
        if picked is None:
            continue
        used_names.add(picked["name"])
        items.append({
            "time": slot["time"],
            "type": slot["type"],
            "name": picked["name"],
            "address": picked.get("address"),
            "distance_km": picked["distance_km"],
        })
    return items


def _sorted_by_distance(origin_lat, origin_lng, places):
    result = []
    for place in places:
        lat, lng = _to_float(place.get("lat")), _to_float(place.get("lng"))
        if lat is None or lng is None or not place.get("name"):
            continue
        item = dict(place)
        item["distance_km"] = round(haversine(origin_lat, origin_lng, lat, lng), 2)
        result.append(item)
    result.sort(key=lambda x: x["distance_km"])
    return result


def _first_unused(candidates, used_names):
    for candidate in candidates:
        if candidate["name"] not in used_names:
            return candidate
    return None


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
