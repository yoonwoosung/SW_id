# services/course_builder.py — 주변 장소를 시간순 코스로 조립하는 규칙 기반 로직(순수 함수, 테스트 가능).
# 장소 선정·순서는 여기서 규칙으로 정한다(LLM이 장소를 지어내지 않게 함).
from common.constants import COURSE_SLOTS, COURSE_TRANSPORT_ESTIMATE, COURSE_MEAL_ESTIMATE
from services.distance import haversine  # 거리 계산은 기존 함수 재사용


def estimate_course_cost_per_person(experience):
    """코스 총비용(1인당) 추정 = 체험비(입장) + 교통 + 식사. 외부 호출 없이 상수로 추정한다.
    예산대 채점(category_match)과 코스 카드 요약이 이 값을 공유한다."""
    cost = getattr(experience, "cost", 0) or 0
    return cost + COURSE_TRANSPORT_ESTIMATE + COURSE_MEAL_ESTIMATE


def build_course_summary(experience):
    """코스 카드용 요약: 예상 비용(1인 코스 총비용)·이동수단·무장애 여부. Experience 속성만 사용."""
    return {
        "estimated_cost": estimate_course_cost_per_person(experience),
        "transport": "자가용" if getattr(experience, "has_parking", False) else "대중교통",
        "barrier_free": bool(getattr(experience, "barrier_free", False)),
    }


def build_course(experience, places_by_type, scorer=None):
    """체험 좌표를 기준으로 시간순 코스 항목 리스트를 만든다.

    places_by_type: {슬롯 type: [place, ...]} — 각 place는 name·lat·lng를 가진다.
    같은 장소가 여러 슬롯에 중복되지 않게 하고, 가까운 순으로 고른다.
    가져온 장소가 없으면 체험 항목만 담아 반환한다(호출부에서 실패 처리).

    scorer: 장소 하나를 받아 0~1 점수를 주는 함수(services/place_score).
      ★주면 슬롯 안에서 '점수 높은 순 → 가까운 순'으로 고른다.★
      ★없으면(조건 미선택·판정 불가) 예전 그대로 거리순이다.★
      슬롯 구조(09:00 체험 → 12:30 맛집 → 15:00 관광 → 17:00 카페)는 바뀌지 않는다.
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
        candidates = _apply_scorer(candidates, scorer)
        picked = _first_unused(candidates, used_names)
        if picked is None:
            continue
        used_names.add(picked["name"])
        item = {
            "time": slot["time"],
            "type": slot["type"],
            "name": picked["name"],
            "address": picked.get("address"),
            "distance_km": picked["distance_km"],
            # 출처를 화면까지 넘긴다. 충남 데이터면 '충남도 제공'을 표시한다.
            "source": picked.get("source"),
        }
        if scorer is not None:
            # 조건이 얼마나 반영됐는지 화면·디버깅에서 확인할 수 있게 남긴다.
            item["match_score"] = round(picked.get("match_score", 0.0), 3)
        items.append(item)
    return items


def _apply_scorer(candidates, scorer):
    """조건 점수를 붙여 '점수 높은 순 → 가까운 순'으로 다시 세운다.

    거리는 동점일 때의 기준으로 남긴다. 점수가 전부 0 이면(조건에 맞는 장소가
    하나도 없으면) 정렬 결과가 거리순 그대로라 기존 동작과 같다.
    """
    if scorer is None or not candidates:
        return candidates
    scored = []
    for place in candidates:
        item = dict(place)
        try:
            item["match_score"] = float(scorer(place))
        except Exception:
            item["match_score"] = 0.0      # 점수 계산이 실패해도 코스는 만들어야 한다
        scored.append(item)
    scored.sort(key=lambda x: (-x["match_score"], x["distance_km"]))
    return scored


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
