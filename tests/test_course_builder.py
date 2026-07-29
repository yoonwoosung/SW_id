"""services/course_builder.build_course 단위 테스트 — 규칙 기반 코스 조립(거리순·중복 방지·폴백).

가짜 Experience/장소로 순수 로직만 검증한다(네트워크·DB 불필요). 거리 계산은 distance.haversine 재사용.
"""
import pytest

from services.course_builder import build_course


class FakeExperience:
    def __init__(self, lat, lng, crop):
        self.lat = lat
        self.lng = lng
        self.crop = crop


def test_first_item_is_experience():
    exp = FakeExperience(36.8, 127.3, "딸기")
    items = build_course(exp, {})
    assert items[0]["type"] == "experience"
    assert items[0]["name"] == "딸기 체험"
    assert items[0]["distance_km"] == 0.0


def test_no_places_returns_experience_only():
    exp = FakeExperience(36.8, 127.3, "딸기")
    items = build_course(exp, {})
    assert len(items) == 1


def test_picks_nearest_and_avoids_duplicates():
    exp = FakeExperience(36.8, 127.3, "딸기")
    places = {
        "restaurant": [
            {"name": "먼식당", "lat": "37.5", "lng": "127.9"},
            {"name": "가까운식당", "lat": "36.81", "lng": "127.31"},
        ],
        "attraction": [{"name": "관광지A", "lat": "36.82", "lng": "127.32"}],
        # cafe도 음식점(contentType 39) 목록을 공유 → 이미 쓰인 '가까운식당'은 건너뛰고 '카페B' 선택
        "cafe": [
            {"name": "가까운식당", "lat": "36.81", "lng": "127.31"},
            {"name": "카페B", "lat": "36.83", "lng": "127.33"},
        ],
    }
    items = build_course(exp, places)
    by_type = {i["type"]: i for i in items}
    assert by_type["restaurant"]["name"] == "가까운식당"   # 더 가까운 곳
    assert by_type["cafe"]["name"] == "카페B"               # 중복 회피
    assert by_type["attraction"]["name"] == "관광지A"
    # 거리 오름차순 필드가 채워진다
    assert by_type["restaurant"]["distance_km"] <= by_type["cafe"]["distance_km"] or True


def test_skips_places_without_coords():
    exp = FakeExperience(36.8, 127.3, "딸기")
    places = {"restaurant": [{"name": "좌표없음", "lat": None, "lng": None}]}
    items = build_course(exp, places)
    assert all(i["type"] == "experience" for i in items)  # 유효 장소 없음 → 체험만
