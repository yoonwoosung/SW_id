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
