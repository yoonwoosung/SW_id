"""services/course_estimate — 코스의 이동·체류 시간과 비용 추정.

★전부 추정이다.★ 실제 경로·요금 API 를 쓰지 않는다(대중교통 소요시간·
입장료를 주는 공개 API 가 없다). 화면에 '예상'임을 밝히고 내역을 함께 보여준다.

예전에는 '총 8시간'이 COURSE_SLOTS 첫·마지막 시각의 뺄셈이었다.
이동·체류와 무관한 상수라 실제(약 6시간)와 달랐다.
"""
import pytest

from services import course_estimate
from services.course_estimate import (
    estimate, legs, normalize_transport, travel_minutes, travel_cost, road_distance_km,
)
from common.constants import (
    COURSE_SPEED_KMH, COURSE_ROUTE_DETOUR, COURSE_STAY_MINUTES,
    COURSE_DEFAULT_TRANSPORT, COURSE_COST_MEAL,
)

ITEMS = [
    {'name': '딸기 체험', 'type': 'experience', 'lat': 36.80, 'lng': 127.30},
    {'name': '맘앤쉐프', 'type': 'restaurant', 'lat': 36.82, 'lng': 127.33},
    {'name': '박문수묘', 'type': 'attraction', 'lat': 36.85, 'lng': 127.28},
    {'name': '이도로에커피', 'type': 'cafe', 'lat': 36.79, 'lng': 127.31},
]


# ---- 이동수단 ----

def test_default_is_public_transit():
    """미설정이면 보수적으로 — 시간을 넉넉히 잡는다."""
    assert normalize_transport([]) == COURSE_DEFAULT_TRANSPORT
    assert normalize_transport(None) == 'public_transit'
    assert normalize_transport(['nature', 'chungnam']) == 'public_transit'


def test_picks_slowest_when_multiple():
    """★여러 개 고르면 가장 느린 것을 쓴다.★

    시간을 적게 잡아 놓고 실제로 더 걸리는 것보다 넉넉한 편이 덜 위험하다.
    """
    assert normalize_transport(['car', 'public_transit']) == 'public_transit'
    assert normalize_transport(['taxi', 'car']) == 'car'
    assert normalize_transport(['taxi']) == 'taxi'


# ---- 이동 시간 ----

def test_detour_correction_applied():
    """곧은 길이 없으므로 직선거리를 보정한다."""
    assert road_distance_km(10) == pytest.approx(10 * COURSE_ROUTE_DETOUR)


def test_slower_transport_takes_longer():
    assert (travel_minutes(10, 'public_transit')
            > travel_minutes(10, 'car')
            > travel_minutes(10, 'taxi'))


def test_travel_minutes_matches_speed_constant():
    expected = round(10 * COURSE_ROUTE_DETOUR / COURSE_SPEED_KMH['car'] * 60)
    assert travel_minutes(10, 'car') == expected


@pytest.mark.parametrize('bad', [None, '', '멀리', -5])
def test_bad_distance_does_not_crash(bad):
    assert travel_minutes(bad, 'car') == 0


def test_unknown_transport_gives_zero():
    assert travel_minutes(10, '헬리콥터') == 0


# ---- 구간 ----

def test_legs_are_between_consecutive_places():
    """★이전 장소 → 다음 장소 기준이다.★ 농장 기준 거리가 아니다."""
    route = legs(ITEMS)
    assert [(l['from'], l['to']) for l in route] == [
        ('딸기 체험', '맘앤쉐프'), ('맘앤쉐프', '박문수묘'), ('박문수묘', '이도로에커피')]
    assert all(l['distance_km'] > 0 for l in route)


def test_legs_skip_items_without_coords():
    items = [ITEMS[0], {'name': '좌표없음', 'type': 'restaurant'}, ITEMS[2]]
    assert legs(items) == []          # 좌표가 끊기면 구간을 잇지 않는다


def test_legs_empty_input():
    assert legs([]) == []
    assert legs(None) == []


# ---- 비용 ----

def test_transit_cost_counts_legs():
    assert travel_cost(10, 3, 'public_transit') == 1500 * 3


def test_car_cost_scales_with_distance():
    assert travel_cost(20, 3, 'car') > travel_cost(10, 3, 'car')


def test_taxi_has_base_fare():
    assert travel_cost(0, 1, 'taxi') > 0


# ---- 전체 ----

def test_estimate_sums_time_and_cost():
    result = estimate(ITEMS, 25000, 'car')
    assert result['total_minutes'] == result['move_minutes'] + result['stay_minutes']
    assert result['stay_minutes'] == sum(
        COURSE_STAY_MINUTES[i['type']] for i in ITEMS)
    assert result['total_cost'] == sum(c['amount'] for c in result['cost_breakdown'])


def test_breakdown_marks_what_is_estimated():
    """★체험비만 실제 값이고 나머지는 추정이다.★ 화면이 구분해 보여줄 수 있어야 한다."""
    result = estimate(ITEMS, 25000, 'car')
    by_label = {c['label']: c for c in result['cost_breakdown']}
    assert by_label['체험']['estimated'] is False
    assert by_label['식사']['estimated'] is True
    assert by_label['식사']['amount'] == COURSE_COST_MEAL


def test_experience_stay_flagged_as_default():
    """체험 소요시간은 컬럼이 없어 기본값이다. 화면에 밝힌다."""
    assert estimate(ITEMS, 25000, 'car')['experience_stay_is_default'] is True


def test_transport_changes_time_not_stay():
    slow = estimate(ITEMS, 25000, 'public_transit')
    fast = estimate(ITEMS, 25000, 'taxi')
    assert slow['move_minutes'] > fast['move_minutes']
    assert slow['stay_minutes'] == fast['stay_minutes']


def test_empty_items_does_not_crash():
    result = estimate([], 0, 'car')
    assert result['total_minutes'] == 0 and result['legs'] == []
