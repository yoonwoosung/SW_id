# services/nearby_service.py — 관광공사 주변 시설 결과를 거리 기준으로 정리하는 로직.
# external/*는 API 호출만, 거리 계산·정렬 같은 비즈니스 로직은 여기서 처리한다.
from external import pet_travel_api, barrier_free_api, medical_tour_api
from services.distance import haversine  # 거리 계산은 기존 함수 재사용


def get_pet_facilities(experience, radius_m):
    raw = pet_travel_api.find_pet_facilities(experience.lat, experience.lng, radius_m)
    return _enrich_and_sort(experience.lat, experience.lng, raw)


def get_barrier_free_places(experience, radius_m):
    raw = barrier_free_api.find_barrier_free_places(experience.lat, experience.lng, radius_m)
    return _enrich_and_sort(experience.lat, experience.lng, raw)


def get_medical_facilities(experience, radius_m):
    raw = medical_tour_api.find_medical_facilities(experience.lat, experience.lng, radius_m)
    return _enrich_and_sort(experience.lat, experience.lng, raw)


def _enrich_and_sort(origin_lat, origin_lng, facilities):
    """각 시설에 농장 기준 거리(distance_km)를 붙이고 가까운 순으로 정렬한다.
    좌표가 없는 항목은 제외한다."""
    result = []
    for facility in facilities:
        lat = _to_float(facility.get("lat"))
        lng = _to_float(facility.get("lng"))
        if lat is None or lng is None:
            continue
        item = dict(facility)
        item["lat"] = lat
        item["lng"] = lng
        item["distance_km"] = round(haversine(origin_lat, origin_lng, lat, lng), 2)
        result.append(item)
    result.sort(key=lambda x: x["distance_km"])
    return result


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None
