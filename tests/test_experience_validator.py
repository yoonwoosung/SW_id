"""services/experience_validator 단위 테스트 — 체험 등록 폼 검증."""
import pytest

from services.experience_validator import parse_pet_fields, PET_MAX_WEIGHT_KG


# ---- 동반 불가 ----

def test_unchecked_returns_false_and_none():
    allowed, weight, err = parse_pet_fields({})
    assert (allowed, weight, err) == (False, None, None)


def test_unchecked_clears_previous_weight():
    """체크를 껐으면 몸무게가 폼에 남아 있어도 비운다(옛 값이 살아남지 않게)."""
    allowed, weight, err = parse_pet_fields({'pet_max_weight_kg': '15'})
    assert allowed is False and weight is None and err is None


# ---- 정상 ----

def test_checked_with_weight():
    allowed, weight, err = parse_pet_fields({'pet_allowed': 'true', 'pet_max_weight_kg': '15'})
    assert (allowed, weight, err) == (True, 15, None)


def test_weight_with_whitespace():
    allowed, weight, err = parse_pet_fields({'pet_allowed': 'on', 'pet_max_weight_kg': ' 20 '})
    assert (allowed, weight, err) == (True, 20, None)


# ---- 몸무게 누락 (검색에서 사라지는 함정) ----

def test_checked_without_weight_rejected():
    """★체크만 하고 몸무게가 없으면 어떤 티어에도 안 잡혀 검색에서 사라진다.★"""
    allowed, weight, err = parse_pet_fields({'pet_allowed': 'true'})
    assert allowed is None and weight is None
    assert err is not None


def test_checked_with_blank_weight_rejected():
    for blank in ('', '   ', None):
        allowed, weight, err = parse_pet_fields({'pet_allowed': 'true', 'pet_max_weight_kg': blank})
        assert err is not None, blank


# ---- 잘못된 값 ----

def test_non_numeric_weight_rejected():
    _, _, err = parse_pet_fields({'pet_allowed': 'true', 'pet_max_weight_kg': 'abc'})
    assert err == "반려견 허용 몸무게는 숫자로 입력해 주세요."


def test_zero_and_negative_rejected():
    for bad in ('0', '-5'):
        _, _, err = parse_pet_fields({'pet_allowed': 'true', 'pet_max_weight_kg': bad})
        assert err is not None, bad


def test_over_cap_rejected():
    _, _, err = parse_pet_fields(
        {'pet_allowed': 'true', 'pet_max_weight_kg': str(PET_MAX_WEIGHT_KG + 1)})
    assert err is not None


def test_cap_boundary_ok():
    allowed, weight, err = parse_pet_fields(
        {'pet_allowed': 'true', 'pet_max_weight_kg': str(PET_MAX_WEIGHT_KG)})
    assert err is None and weight == PET_MAX_WEIGHT_KG


# ---- 검색 티어와 맞물리는지 ----

@pytest.mark.parametrize('weight,tier_min', [(5, 5), (15, 15), (25, 25)])
def test_weight_matches_search_tier(weight, tier_min):
    """입력한 몸무게가 search_categories 의 티어 하한과 맞물려야 한다."""
    from common.search_categories import PET_WEIGHT_MIN_KG
    allowed, parsed, err = parse_pet_fields(
        {'pet_allowed': 'true', 'pet_max_weight_kg': str(weight)})
    assert err is None
    assert parsed >= tier_min
    assert tier_min in PET_WEIGHT_MIN_KG.values()


# ======================================================================
# 과생산(잉여) 수확 체험
# ======================================================================

from services.experience_validator import (
    parse_surplus_fields, discount_rate, capacity_from_quantity,
    suggest_origin, SURPLUS_MIN_DISCOUNT_RATE,
)


def surplus_form(**kw):
    base = {
        'is_surplus': 'true', 'surplus_terms_agreed': 'true',
        'list_price': '50000', 'surplus_qty_total': '500',
        'surplus_per_person': '5', 'surplus_unit': 'kg',
    }
    base.update(kw)
    return {k: v for k, v in base.items() if v is not None}


# ---- 할인율 ----

def test_discount_rate_basic():
    assert discount_rate(50000, 25000) == 0.5
    assert discount_rate(10000, 8000) == pytest.approx(0.2)


def test_discount_rate_guards():
    assert discount_rate(0, 100) is None
    assert discount_rate(None, 100) is None
    assert discount_rate(10000, None) is None


def test_exactly_20_percent_allowed():
    """경계값: 정확히 20% 는 통과한다(이상 조건)."""
    data, err = parse_surplus_fields(surplus_form(list_price='10000'), cost=8000)
    assert err is None and data['is_surplus'] is True


def test_just_under_20_percent_rejected():
    data, err = parse_surplus_fields(surplus_form(list_price='10000'), cost=8001)
    assert data is None and "20%" in err


def test_no_discount_rejected():
    data, err = parse_surplus_fields(surplus_form(list_price='25000'), cost=25000)
    assert data is None and err is not None


def test_cost_above_list_price_rejected():
    data, err = parse_surplus_fields(surplus_form(list_price='20000'), cost=25000)
    assert data is None and err is not None


# ---- 약관 ----

def test_terms_required():
    form = surplus_form()
    del form['surplus_terms_agreed']
    data, err = parse_surplus_fields(form, cost=25000)
    assert data is None and "약관" in err


def test_not_surplus_returns_all_off():
    data, err = parse_surplus_fields({}, cost=25000)
    assert err is None
    assert data['is_surplus'] is False and data['surplus_terms_agreed'] is False
    assert data['list_price'] is None and data['surplus_qty_total'] is None


def test_unchecking_clears_previous_values():
    """체크를 껐으면 폼에 값이 남아 있어도 전부 비운다."""
    data, err = parse_surplus_fields(
        {'list_price': '50000', 'surplus_qty_total': '500'}, cost=25000)
    assert err is None and data['is_surplus'] is False and data['list_price'] is None


# ---- 수량 ----

def test_normal_quantity():
    data, err = parse_surplus_fields(surplus_form(), cost=25000)
    assert err is None
    assert data['surplus_qty_total'] == 500 and data['surplus_per_person'] == 5


def test_per_person_over_total_rejected():
    data, err = parse_surplus_fields(
        surplus_form(surplus_qty_total='3', surplus_per_person='5'), cost=25000)
    assert data is None and err is not None


def test_zero_and_negative_quantity_rejected():
    for bad in ('0', '-10'):
        data, err = parse_surplus_fields(surplus_form(surplus_qty_total=bad), cost=25000)
        assert data is None, bad


def test_non_numeric_quantity_rejected():
    data, err = parse_surplus_fields(surplus_form(surplus_qty_total='많이'), cost=25000)
    assert data is None and "숫자" in err


def test_missing_quantity_rejected():
    form = surplus_form()
    del form['surplus_qty_total']
    data, err = parse_surplus_fields(form, cost=25000)
    assert data is None and err is not None


# ---- 단위 ----

def test_valid_units():
    for unit in ('kg', '박스', '구좌'):
        data, err = parse_surplus_fields(surplus_form(surplus_unit=unit), cost=25000)
        assert err is None and data['surplus_unit'] == unit


def test_unit_defaults_to_kg():
    form = surplus_form()
    del form['surplus_unit']
    data, err = parse_surplus_fields(form, cost=25000)
    assert err is None and data['surplus_unit'] == 'kg'


def test_unknown_unit_rejected():
    data, err = parse_surplus_fields(surplus_form(surplus_unit='자루'), cost=25000)
    assert data is None and err is not None


# ---- 정원 계산 (버림) ----

def test_capacity_exact_division():
    assert capacity_from_quantity(500, 5) == 100


def test_capacity_floors_remainder():
    """★503 ÷ 5 = 100.6 → 100명. 자투리 3kg 은 예약받지 않는다.★"""
    assert capacity_from_quantity(503, 5) == 100


def test_capacity_guards():
    assert capacity_from_quantity(None, 5) is None
    assert capacity_from_quantity(500, 0) is None
    assert capacity_from_quantity(500, None) is None


def test_capacity_smaller_than_one_person():
    assert capacity_from_quantity(3, 5) == 0


# ---- 원산지 제안 ----

@pytest.mark.parametrize('address,expected', [
    ('충남 논산시 연무읍 123-4', '충남 논산시'),
    ('경기도 이천시 부발읍', '경기도 이천시'),
    ('전라남도 해남군 송지면 1', '전라남도 해남군'),
    ('서울특별시 강남구 역삼동', '서울특별시 강남구'),
])
def test_suggest_origin(address, expected):
    assert suggest_origin(address) == expected


def test_suggest_origin_fallback_to_first_token():
    # 시군구가 없으면 시도만이라도 준다
    assert suggest_origin('제주특별자치도') == '제주특별자치도'


def test_suggest_origin_empty():
    for bad in ('', '   ', None):
        assert suggest_origin(bad) is None


# ---- 정원 조정 (줄이기 허용 / 늘리기 차단) ----

from services.experience_validator import resolve_max_participants


def test_non_surplus_uses_input_as_is():
    value, err = resolve_max_participants('20', capacity=None)
    assert err is None and value == 20


def test_non_surplus_bad_input_rejected():
    value, err = resolve_max_participants('abc', capacity=None)
    assert value is None and err is not None


def test_blank_uses_capacity():
    """비워 두면 수량으로 계산한 정원을 그대로 쓴다."""
    value, err = resolve_max_participants('', capacity=100)
    assert err is None and value == 100


def test_reducing_allowed():
    """★재고는 100명분이지만 하루 20명만 받고 싶은 경우 — 허용.★"""
    value, err = resolve_max_participants('20', capacity=100)
    assert err is None and value == 20


def test_equal_to_capacity_allowed():
    value, err = resolve_max_participants('100', capacity=100)
    assert err is None and value == 100


def test_increasing_blocked():
    """★재고를 넘는 정원은 막는다.★"""
    value, err = resolve_max_participants('101', capacity=100)
    assert value is None and '100명' in err


def test_capacity_zero_rejected():
    value, err = resolve_max_participants('5', capacity=0)
    assert value is None and err is not None
