"""app.py:183 haversine() 거리 계산 단위 테스트 (PR1).

운영 코드(app.py)는 변경하지 않고, 실제 app.haversine 함수를 import 해서 검증한다.
haversine(lat1, lon1, lat2, lon2) -> 두 좌표 사이 거리(km).
"""
from app import haversine

# 대표 좌표 (위도, 경도)
SEOUL = (37.5665, 126.9780)
BUSAN = (35.1796, 129.0756)


def test_seoul_to_busan_about_325km():
    # 서울시청 ↔ 부산시청 직선거리는 약 325km. 오차 ±5km 허용.
    d = haversine(SEOUL[0], SEOUL[1], BUSAN[0], BUSAN[1])
    assert abs(d - 325) <= 5


def test_symmetry():
    # 거리는 방향과 무관해야 한다: haversine(a, b) == haversine(b, a)
    forward = haversine(SEOUL[0], SEOUL[1], BUSAN[0], BUSAN[1])
    backward = haversine(BUSAN[0], BUSAN[1], SEOUL[0], SEOUL[1])
    assert forward == backward


def test_same_point_is_zero():
    # 같은 좌표 사이 거리는 0.0
    assert haversine(37.5, 127.0, 37.5, 127.0) == 0.0
