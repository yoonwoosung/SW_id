"""external/tour_csv — 관광지정보 표준데이터 CSV 로 코스 장소를 보강한다.

충남 올담 API 가 복구되지 않아 같은 성격의 공공데이터를 파일로 대신 쓴다.
★관광공사 API 를 대체하지 않는다.★ 보강만 한다.
"""
import io
import os

import pytest

from external import tour_csv
from common.constants import (
    TOUR_CSV_CONTENT_TYPE, TOUR_CSV_SOURCE, NEARBY_RESULT_LIMIT,
    TOUR_CONTENT_TYPE_RESTAURANT,
)

CHEONAN = (36.80, 127.30)
NAJU = (35.01, 126.71)


# ---- 로드 ----

def test_csv_file_exists_and_loads():
    places = tour_csv.all_places()
    assert len(places) > 800, "전국 840건 기준"


def test_every_place_has_usable_fields():
    for place in tour_csv.all_places():
        assert place["name"]
        assert isinstance(place["lat"], float) and isinstance(place["lng"], float)
        assert place["content_type_id"] == TOUR_CSV_CONTENT_TYPE
        assert place["source"] == TOUR_CSV_SOURCE


def test_address_falls_back_to_jibun(monkeypatch):
    """도로명이 비면 지번 주소를 쓴다."""
    row = {"관광지명": "가", "위도": "36.8", "경도": "127.3",
           "소재지도로명주소": "", "소재지지번주소": "충남 논산시 1-2"}
    assert tour_csv._to_place(row)["address"] == "충남 논산시 1-2"


@pytest.mark.parametrize('row', [
    {"관광지명": "가", "위도": "", "경도": "127.3"},
    {"관광지명": "가", "위도": "없음", "경도": "127.3"},
    {"관광지명": "", "위도": "36.8", "경도": "127.3"},
])
def test_broken_rows_are_skipped(row):
    assert tour_csv._to_place(row) is None


def test_missing_file_returns_empty(monkeypatch):
    """★파일이 없어도 코스 생성은 그대로 동작해야 한다.★"""
    monkeypatch.setattr(tour_csv, '_csv_path', lambda: '/no/such/file.csv')
    monkeypatch.setattr(tour_csv, '_places', None)
    assert tour_csv._load() == []


def test_reads_with_or_without_bom():
    """utf-8-sig 로 읽는다 — BOM 이 있든 없든 안전하다.

    지금 파일에는 BOM 이 없지만, 공공데이터포털 CSV 는 BOM 이 붙어 오는 경우가 흔하다.
    그때 utf-8 로 읽으면 첫 컬럼명이 '\ufeff시스템키'가 되어 행 전체를 못 읽는다.
    파일을 다시 받아 교체해도 깨지지 않도록 utf-8-sig 를 쓴다.
    """
    import csv as _csv
    raw = open(tour_csv._csv_path(), 'rb').read()
    for prefix in (b'', b'\xef\xbb\xbf'):
        body = prefix + (raw[3:] if raw.startswith(b'\xef\xbb\xbf') else raw)
        rows = list(_csv.DictReader(io.StringIO(body.decode('utf-8-sig'))))
        assert list(rows[0].keys())[0] == '시스템키'


# ---- 반경 조회 ----

def test_finds_places_within_radius():
    near = tour_csv.find_nearby_places(*NAJU, 20000)
    assert near, "나주 주변에는 표준데이터 장소가 있다"
    assert near[0]['name']


def test_results_are_sorted_by_distance():
    near = tour_csv.find_nearby_places(*NAJU, 20000)
    from external.tour_csv import _distance_km
    distances = [_distance_km(NAJU[0], NAJU[1], p['lat'], p['lng']) for p in near]
    assert distances == sorted(distances)


def test_radius_narrowing_reduces_results():
    wide = tour_csv.find_nearby_places(*NAJU, 20000)
    narrow = tour_csv.find_nearby_places(*NAJU, 2000)
    assert len(narrow) <= len(wide)


def test_result_limit_respected():
    assert len(tour_csv.find_nearby_places(*NAJU, 200000)) <= NEARBY_RESULT_LIMIT


def test_far_away_returns_empty():
    assert tour_csv.find_nearby_places(0.0, 0.0, 20000) == []


# ---- 슬롯 배치 ----

def test_restaurant_slot_gets_nothing():
    """★CSV 는 전부 관광지다. 맛집·카페 슬롯에 섞이면 안 된다.★"""
    assert tour_csv.find_nearby_places(*CHEONAN, 20000, TOUR_CONTENT_TYPE_RESTAURANT) == []


def test_attraction_slot_gets_places():
    assert tour_csv.find_nearby_places(*CHEONAN, 20000, TOUR_CSV_CONTENT_TYPE)


def test_no_content_type_returns_all():
    assert tour_csv.find_nearby_places(*CHEONAN, 20000) == \
           tour_csv.find_nearby_places(*CHEONAN, 20000, TOUR_CSV_CONTENT_TYPE)


# ---- 잘못된 입력 ----

@pytest.mark.parametrize('lat,lng,radius', [
    (None, 127.3, 20000), (36.8, None, 20000), ('없음', 127.3, 20000), (36.8, 127.3, '멀리'),
])
def test_bad_arguments_return_empty(lat, lng, radius):
    assert tour_csv.find_nearby_places(lat, lng, radius) == []


# ---- 조건 점수와의 관계 ----

def test_category_is_korean_text_not_kto_code():
    """★관광공사 cat3 코드와 성격이 다르다.★

    '관광지'·'관광단지' 두 값뿐이라 cat1·cat2 접두사 판정에 걸리지 않는다.
    억지로 코드로 바꾸면 틀린 판정이 되므로 원문을 그대로 둔다 —
    조건 점수는 0 이고 거리순 폴백으로 처리된다.
    """
    from services.place_score import matches
    categories = {p['category'] for p in tour_csv.all_places()}
    assert categories <= {'관광지', '관광단지'}
    sample = tour_csv.find_nearby_places(*NAJU, 20000)[0]
    for code in ('nature', 'craft', 'tradition', 'active', 'healing'):
        assert matches(sample, code) is False, code


def test_facility_fields_carried_for_later():
    """편의시설 판정에 쓸 정보를 실어만 둔다(지금은 아무 데서도 쓰지 않는다)."""
    with_facilities = [p for p in tour_csv.all_places() if p['facilities']]
    with_parking = [p for p in tour_csv.all_places() if p['parking_count']]
    assert len(with_facilities) > 800
    assert len(with_parking) > 700
