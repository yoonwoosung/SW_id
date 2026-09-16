"""services/nearby_service._enrich_and_sort 단위 테스트.

외부 API 응답을 거리(distance_km) 기준으로 정리·정렬하는 순수 로직을 검증한다.
네트워크를 타지 않고 거리 계산은 services/distance.haversine 를 재사용한다.
"""
import pytest

from services.nearby_service import _enrich_and_sort, _to_float


ORIGIN_LAT, ORIGIN_LNG = 36.8, 127.3


def test_sorted_by_distance_ascending():
    facilities = [
        {"name": "먼 곳", "lat": "37.5", "lng": "127.9"},
        {"name": "가까운 곳", "lat": "36.81", "lng": "127.31"},
    ]
    result = _enrich_and_sort(ORIGIN_LAT, ORIGIN_LNG, facilities)
    assert [f["name"] for f in result] == ["가까운 곳", "먼 곳"]
    assert result[0]["distance_km"] <= result[1]["distance_km"]


def test_distance_km_field_added():
    facilities = [{"name": "테스트", "lat": "36.8", "lng": "127.3"}]
    result = _enrich_and_sort(ORIGIN_LAT, ORIGIN_LNG, facilities)
    assert result[0]["distance_km"] == 0.0  # 같은 좌표 → 0km


def test_items_without_coords_are_dropped():
    facilities = [
        {"name": "좌표없음", "lat": None, "lng": None},
        {"name": "정상", "lat": "36.8", "lng": "127.3"},
    ]
    result = _enrich_and_sort(ORIGIN_LAT, ORIGIN_LNG, facilities)
    assert [f["name"] for f in result] == ["정상"]


def test_to_float_handles_invalid():
    assert _to_float("36.8") == 36.8
    assert _to_float(None) is None
    assert _to_float("없음") is None
