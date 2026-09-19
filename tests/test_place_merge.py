"""services/place_merge 단위 테스트 — 충남 판정과 장소 병합.

관광공사 결과를 대체하지 않고 '보강'한다. 겹치면 도 데이터를 남긴다.
"""
import pytest

from services.place_merge import (
    is_chungnam,
    is_same_place,
    merge,
    CHUNGNAM_KEYWORDS,
    DUPLICATE_DISTANCE_M,
)


class FakeExp:
    def __init__(self, address_detail=None, location=None):
        self.address_detail = address_detail
        self.location = location


def place(name, lat=None, lng=None, source=None, address=None):
    return {'name': name, 'lat': lat, 'lng': lng, 'source': source, 'address': address}


# ---- 충남 판정 ----

@pytest.mark.parametrize('address', [
    '충남 논산시 연무읍', '충청남도 천안시 동남구', '충남 예산군',
])
def test_sido_keywords_detected(address):
    assert is_chungnam(FakeExp(address_detail=address)) is True


@pytest.mark.parametrize('address', [
    '논산시 연무읍 123', '천안시 서북구', '서산시', '태안군 안면읍',
])
def test_city_only_address_detected(address):
    """★시도명이 빠진 주소도 잡아야 한다.★ 시군명 15개를 함께 본다."""
    assert is_chungnam(FakeExp(address_detail=address)) is True


@pytest.mark.parametrize('address', [
    '경기도 이천시', '전라남도 해남군', '서울특별시 강남구', '충청북도 청주시',
])
def test_other_regions_not_detected(address):
    assert is_chungnam(FakeExp(address_detail=address)) is False


def test_충북_not_confused_with_충남():
    """충청북도를 충남으로 잘못 잡으면 안 된다."""
    assert is_chungnam(FakeExp(address_detail='충북 청주시')) is False
    assert is_chungnam(FakeExp(address_detail='충청북도 충주시')) is False


def test_falls_back_to_location():
    assert is_chungnam(FakeExp(address_detail=None, location='충남 보령시')) is True


def test_no_address_is_false():
    """주소가 없으면 판정 불가. 충남 호출을 안 할 뿐 코스는 그대로 만들어진다."""
    assert is_chungnam(FakeExp()) is False
    assert is_chungnam(None) is False


def test_keywords_include_all_cities():
    for word in ('충남', '충청남도', '천안', '논산', '태안'):
        assert word in CHUNGNAM_KEYWORDS


# ---- 같은 장소 판정 ----

def test_same_by_close_coords():
    a = place('○○사', 36.8000, 127.3000)
    b = place('○○사 대웅전', 36.8001, 127.3001)   # 약 14m
    assert is_same_place(a, b) is True


def test_different_by_far_coords():
    a = place('가나다', 36.8000, 127.3000)
    b = place('마바사', 36.8100, 127.3100)        # 약 1.4km
    assert is_same_place(a, b) is False


def test_same_by_normalized_name():
    """좌표가 멀어도 이름이 같으면 같은 곳으로 본다(좌표 오기 대응)."""
    a = place('현충사 (충무공)', 36.80, 127.30)
    b = place('현충사(충무공)', 36.95, 127.55)
    assert is_same_place(a, b) is True


def test_name_normalization_ignores_spacing():
    assert is_same_place(place('백제 문화 단지'), place('백제문화단지')) is True


def test_empty_name_does_not_match_everything():
    """이름이 없는 두 장소가 서로 같다고 판정되면 안 된다."""
    assert is_same_place(place(''), place('')) is False
    assert is_same_place(place(None), place(None)) is False


def test_missing_coords_falls_back_to_name():
    a = place('가나다', None, None)
    assert is_same_place(a, place('가나다', 36.8, 127.3)) is True
    assert is_same_place(a, place('마바사', 36.8, 127.3)) is False


def test_distance_boundary():
    # 위도 0.00045도 ≈ 50m
    near = place('A', 36.80000, 127.3)
    just_in = place('B', 36.80040, 127.3)     # 약 44m
    just_out = place('C', 36.80100, 127.3)    # 약 111m
    assert is_same_place(near, just_in) is True
    assert is_same_place(near, just_out) is False


# ---- 병합 ----

def test_chungnam_comes_first():
    tour = [place('관광공사A', 36.80, 127.30)]
    cn = [place('충남A', 36.90, 127.40, source='chungnam')]
    out = merge(tour, cn)
    assert out[0]['name'] == '충남A'
    assert len(out) == 2, "겹치지 않으면 둘 다 남는다"


def test_duplicate_keeps_chungnam():
    """★겹치면 도 데이터를 남긴다.★"""
    tour = [place('현충사', 36.8000, 127.3000)]
    cn = [place('현충사', 36.8001, 127.3000, source='chungnam')]
    out = merge(tour, cn)
    assert len(out) == 1
    assert out[0]['source'] == 'chungnam'


def test_tour_only_when_chungnam_empty():
    """★충남 호출이 실패해도 관광공사 결과가 그대로 남는다.★"""
    tour = [place('관광공사A'), place('관광공사B')]
    assert merge(tour, []) == tour
    assert merge(tour, None) == tour


def test_chungnam_only_when_tour_empty():
    cn = [place('충남A', source='chungnam')]
    assert merge([], cn) == cn


def test_both_empty():
    assert merge([], []) == []
    assert merge(None, None) == []


def test_multiple_duplicates_collapse():
    tour = [place('A', 36.80, 127.30), place('B', 36.81, 127.31), place('C', 36.82, 127.32)]
    cn = [place('A', 36.80, 127.30, source='chungnam'),
          place('C', 36.82, 127.32, source='chungnam')]
    out = merge(tour, cn)
    names = [p['name'] for p in out]
    assert names.count('A') == 1 and names.count('C') == 1
    assert 'B' in names, "겹치지 않는 관광공사 결과는 남는다"
    assert len(out) == 3
