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
    suggest_origin, auto_discount_percent, max_cost,
)
from common.constants import SURPLUS_DEFAULT_DISCOUNT_PERCENT


def surplus_form(**kw):
    base = {
        'is_surplus': 'true', 'surplus_terms_agreed': 'true',
        'list_price': '50000', 'surplus_qty_total': '500',
        'surplus_per_person': '5', 'surplus_unit': 'kg',
        'surplus_reason': '과잉생산',
    }
    base.update(kw)
    return {k: v for k, v in base.items() if v is not None}


# ---- 실제 할인율(리본에 쓰는 값) ----

def test_discount_rate_basic():
    assert discount_rate(50000, 25000) == 0.5
    assert discount_rate(10000, 8000) == pytest.approx(0.2)


def test_discount_rate_guards():
    assert discount_rate(0, 100) is None
    assert discount_rate(None, 100) is None
    assert discount_rate(10000, None) is None


# ---- 자동 할인율(수량·단위로 정한다) ----

@pytest.mark.parametrize('qty,expected', [
    (1, 20), (99, 20),          # 100 미만
    (100, 30), (299, 30),
    (300, 40), (599, 40),
    (600, 50), (999, 50),
    (1000, 60), (99999, 60),    # 1000 이상
])
def test_kg_tier_boundaries(qty, expected):
    """★구간 경계.★ '상한 미만'이라 100kg 은 2구간이지 1구간이 아니다."""
    assert auto_discount_percent(qty, 'kg') == expected


@pytest.mark.parametrize('qty,expected', [(9, 20), (10, 30), (59, 40), (100, 60)])
def test_box_tier(qty, expected):
    assert auto_discount_percent(qty, '박스') == expected


@pytest.mark.parametrize('qty,expected', [(19, 20), (20, 30), (99, 40), (200, 60)])
def test_slot_tier(qty, expected):
    assert auto_discount_percent(qty, '구좌') == expected


def test_gram_converts_to_kg_table():
    """★g 은 1000으로 나눠 kg 표를 본다.★ 200g = 0.2kg 이므로 최저 구간."""
    assert auto_discount_percent(200, 'g') == 20
    assert auto_discount_percent(150_000, 'g') == 30      # 150kg
    assert auto_discount_percent(1_000_000, 'g') == 60    # 1000kg


def test_units_without_tier_table_get_default():
    """포기·단은 kg 환산 계수가 작물마다 달라 기본 할인율을 준다.

    근거 없는 환산 계수를 만드는 대신 최저 구간을 주면 최대 체험료가
    가장 높아 농장주에게 불리하지 않다.
    """
    for unit in ('포기', '단'):
        assert auto_discount_percent(99999, unit) == SURPLUS_DEFAULT_DISCOUNT_PERCENT


def test_auto_discount_percent_guards():
    assert auto_discount_percent(0, 'kg') is None
    assert auto_discount_percent(None, 'kg') is None


# ---- 최대 체험료(상한) ----

def test_max_cost_matches_spec_example():
    """★정가 50,000 / 500kg → 할인율 40% → 최대 30,000원.★"""
    assert max_cost(50000, 500, 'kg') == 30000


def test_max_cost_is_exact_integer():
    """부동소수로 곱하면 50000 × 0.6 이 29999.999… 가 되어 1원이 샌다."""
    assert max_cost(50000, 1000, 'kg') == 20000
    assert max_cost(33333, 500, 'kg') == 19999      # 33333 × 60 // 100


def test_max_cost_guards():
    assert max_cost(50000, 0, 'kg') is None
    assert max_cost(0, 500, 'kg') is None
    assert max_cost(None, 500, 'kg') is None


# ---- 상한 검증 ----

def test_cost_equal_to_cap_allowed():
    """경계값: 상한과 같으면 통과한다."""
    data, err = parse_surplus_fields(surplus_form(), cost=30000)
    assert err is None and data['is_surplus'] is True


def test_cost_below_cap_allowed():
    """더 싸게 파는 건 언제나 허용한다."""
    data, err = parse_surplus_fields(surplus_form(), cost=25000)
    assert err is None


def test_cost_above_cap_rejected():
    """★상한 초과는 거부한다. 잘라서 저장하지 않는다.★"""
    data, err = parse_surplus_fields(surplus_form(), cost=35000)
    assert data is None
    assert "30,000원" in err and "40%" in err


def test_cost_above_list_price_rejected():
    """상한이 정가보다 항상 낮으므로 정가 초과는 자동으로 걸린다."""
    data, err = parse_surplus_fields(surplus_form(list_price='20000'), cost=25000)
    assert data is None and err is not None


def test_cost_missing_rejected():
    data, err = parse_surplus_fields(surplus_form(), cost=None)
    assert data is None and "체험비" in err


def test_larger_quantity_lowers_the_cap():
    """수량이 많을수록 할인율이 올라가 상한이 내려간다."""
    ok, err = parse_surplus_fields(surplus_form(surplus_qty_total='500'), cost=30000)
    assert err is None
    bad, err = parse_surplus_fields(surplus_form(surplus_qty_total='1000'), cost=30000)
    assert bad is None and err is not None     # 1000kg → 60% → 상한 20,000


# ---- 이미 등록된 과생산 체험이 깨지지 않는지 ----

@pytest.mark.parametrize('label,list_price,cost,qty,unit', [
    ('파인애플(600kg)', 150000, 15000, '600', 'kg'),
    ('만두(200g)', 30000, 20000, '200', 'g'),
])
def test_existing_rows_still_valid(label, list_price, cost, qty, unit):
    """배포된 과생산 체험 2건이 새 규칙에서도 저장된다(수정 시 막히면 안 된다)."""
    data, err = parse_surplus_fields(
        surplus_form(list_price=str(list_price), surplus_qty_total=qty,
                     surplus_per_person='1', surplus_unit=unit),
        cost=cost)
    assert err is None, f"{label}: {err}"


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

@pytest.mark.parametrize('unit,qty', [
    ('kg', '500'), ('g', '500'), ('박스', '20'), ('구좌', '30'), ('포기', '500'), ('단', '500'),
])
def test_valid_units(unit, qty):
    """허용 단위 6개 모두 등록된다. 상한을 넘지 않게 체험비를 낮게 잡는다."""
    data, err = parse_surplus_fields(
        surplus_form(surplus_unit=unit, surplus_qty_total=qty, surplus_per_person='1'),
        cost=10000)
    assert err is None, err
    assert data['surplus_unit'] == unit


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


# ---- 할인 사유 (리본 문구) ----

from services.experience_validator import SURPLUS_REASONS, SURPLUS_REASON_MAX_LEN


@pytest.mark.parametrize('reason', SURPLUS_REASONS)
def test_preset_reasons_accepted(reason):
    data, err = parse_surplus_fields(surplus_form(surplus_reason=reason), cost=25000)
    assert err is None and data['surplus_reason'] == reason


def test_reason_required():
    form = surplus_form()
    form.pop('surplus_reason', None)
    data, err = parse_surplus_fields(form, cost=25000)
    assert data is None and "사유" in err


def test_unknown_reason_rejected():
    data, err = parse_surplus_fields(surplus_form(surplus_reason='세일'), cost=25000)
    assert data is None and err is not None


def test_etc_uses_free_text():
    data, err = parse_surplus_fields(
        surplus_form(surplus_reason='기타', surplus_reason_etc='잔여물량'), cost=25000)
    assert err is None and data['surplus_reason'] == '잔여물량'


def test_etc_without_text_rejected():
    data, err = parse_surplus_fields(surplus_form(surplus_reason='기타'), cost=25000)
    assert data is None and "기타" in err


def test_etc_over_limit_rejected_not_truncated():
    """★6자 초과는 잘라서 저장하지 않고 거부한다.★

    잘라 두면 농장주는 모르는 채 어중간한 문구가 사용자에게 보이고
    나중에 원인을 찾기 어렵다.
    """
    long_text = '가' * (SURPLUS_REASON_MAX_LEN + 1)
    data, err = parse_surplus_fields(
        surplus_form(surplus_reason='기타', surplus_reason_etc=long_text), cost=25000)
    assert data is None
    assert '6자 이내' in err and '7자' in err


def test_etc_at_limit_allowed():
    text = '가' * SURPLUS_REASON_MAX_LEN
    data, err = parse_surplus_fields(
        surplus_form(surplus_reason='기타', surplus_reason_etc=text), cost=25000)
    assert err is None and data['surplus_reason'] == text


def test_etc_whitespace_trimmed():
    data, err = parse_surplus_fields(
        surplus_form(surplus_reason='기타', surplus_reason_etc='  잔여  '), cost=25000)
    assert err is None and data['surplus_reason'] == '잔여'


def test_reason_cleared_when_not_surplus():
    data, err = parse_surplus_fields({'surplus_reason': '과잉생산'}, cost=25000)
    assert err is None and data['surplus_reason'] is None


# ======================================================================
# 리본 문구 — 사유·정가가 없어도 떠야 한다
# ======================================================================
#
# 증상: 과생산 탭에 3건이 나오는데 리본은 2건만 떴다.
# 사유 컬럼이 생기기 전에 등록된 체험(surplus_reason=NULL)이 걸러졌다.

from services.experience_validator import (
    ribbon_text, discount_percent, SURPLUS_RIBBON_DEFAULT_REASON,
)


class FakeSurplus:
    def __init__(self, is_surplus=True, terms=True, list_price=50000,
                 cost=25000, reason='과잉생산'):
        self.is_surplus = is_surplus
        self.surplus_terms_agreed = terms
        self.list_price = list_price
        self.cost = cost
        self.surplus_reason = reason


# ---- 할인율(정수 %) ----

def test_discount_percent_floors():
    """★내림한다.★ 66.67% 를 67% 로 올리면 실제보다 더 깎아준 것처럼 보인다."""
    assert discount_percent(FakeSurplus(list_price=30000, cost=10000)) == 66   # 66.67%
    assert discount_percent(FakeSurplus(list_price=30000, cost=20000)) == 33   # 33.33%
    assert discount_percent(FakeSurplus(list_price=50000, cost=25000)) == 50


def test_discount_percent_none_without_list_price():
    assert discount_percent(FakeSurplus(list_price=None)) is None
    assert discount_percent(FakeSurplus(list_price=0)) is None
    assert discount_percent(FakeSurplus(cost=None)) is None


# ---- 리본 문구 4가지 ----

def test_ribbon_with_reason_and_rate():
    assert ribbon_text(FakeSurplus(list_price=30000, cost=20000)) == '과잉생산 33%'


def test_ribbon_without_reason_uses_default_label():
    """★사유가 없어도 뜬다.★ (배포된 '저렴한 좋은 파인애플' 사례)

    '90%' 만 띄우면 무엇이 90% 인지 알 수 없어 기본 문구를 붙인다.
    """
    pineapple = FakeSurplus(list_price=150000, cost=15000, reason=None)
    assert ribbon_text(pineapple) == '과생산 90%'
    assert SURPLUS_RIBBON_DEFAULT_REASON == '과생산'


def test_ribbon_without_list_price_shows_reason_only():
    """정가가 없으면 할인율을 못 구한다. 그래도 과생산인 건 알려준다."""
    assert ribbon_text(FakeSurplus(list_price=None)) == '과잉생산'


def test_ribbon_without_reason_and_rate():
    assert ribbon_text(FakeSurplus(list_price=None, reason=None)) == '과생산'


def test_ribbon_empty_reason_treated_as_missing():
    assert ribbon_text(FakeSurplus(list_price=50000, cost=25000, reason='')) == '과생산 50%'


# ---- 떠서는 안 되는 경우 ----

def test_ribbon_none_when_not_surplus():
    assert ribbon_text(FakeSurplus(is_surplus=False)) is None


def test_ribbon_none_when_terms_not_agreed():
    """★약관 미동의는 리본을 띄우지 않는다.★

    목록 쿼리가 이미 거르지만, 상세처럼 쿼리를 거치지 않는 화면도 있어
    함수에서 한 번 더 막는다.
    """
    assert ribbon_text(FakeSurplus(terms=False)) is None


def test_ribbon_none_for_none():
    assert ribbon_text(None) is None


# ---- 목록과 상세가 같은 값을 쓰는가 ----

def test_ribbon_and_badge_use_same_percent():
    """상세 배지는 discount_percent() 를, 리본은 ribbon_text() 를 쓴다.

    예전에는 리본이 반올림·배지가 내림이라 66.67% 가 67%·66% 로 달랐다.
    두 값이 같은 숫자를 내는지 고정한다.
    """
    for lp, cost in ((30000, 10000), (30000, 20000), (150000, 15000), (50000, 25000)):
        exp = FakeSurplus(list_price=lp, cost=cost)
        assert f"{discount_percent(exp)}%" in ribbon_text(exp)
