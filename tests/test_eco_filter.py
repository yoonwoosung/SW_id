"""services/eco_filter 단위 테스트 — 조건을 정렬이 아니라 '제외'로 쓴다.

기존 문제: ESG 섹션은 sort 만, 조건은 score 가점만 해서
조건에 맞지 않는 체험이 목록에 남았다.
"""
import pytest

from services.eco_filter import (
    passes_conditions,
    selected_categories,
    is_eco_certified,
    is_organic_certified,
    passes_eco_section,
    JUDGEABLE_CATEGORIES,
)
from common.constants import ESG_GRADE_B


class FakeExp:
    """ESG·조건 판정에 쓰이는 속성만 가진 가짜 체험."""

    def __init__(self, pesticide_free=False, organic_certification_type=None,
                 organic_certification_image=None, volunteer_needed=0,
                 barrier_free=False, has_parking=False,
                 address_detail='충남 논산시', cost=25000,
                 activity_type=None, pet_allowed=False, pet_max_weight_kg=None,
                 has_wifi=False):
        self.pesticide_free = pesticide_free
        self.organic_certification_type = organic_certification_type
        self.organic_certification_image = organic_certification_image
        self.volunteer_needed = volunteer_needed
        self.barrier_free = barrier_free
        self.has_parking = has_parking
        self.address_detail = address_detail
        self.cost = cost
        self.activity_type = activity_type
        self.pet_allowed = pet_allowed
        self.pet_max_weight_kg = pet_max_weight_kg
        self.has_wifi = has_wifi


# ---- 친환경 판정 (E축) ----

def test_eco_true_with_pesticide_free():
    assert is_eco_certified(FakeExp(pesticide_free=True)) is True


def test_eco_true_with_organic():
    assert is_eco_certified(FakeExp(organic_certification_type='유기농')) is True


def test_eco_false_without_e_axis():
    """봉사·무장애·주차(S축)만 있으면 친환경이 아니다."""
    exp = FakeExp(volunteer_needed=5, barrier_free=True, has_parking=True)
    assert is_eco_certified(exp) is False


def test_eco_handles_none():
    assert is_eco_certified(None) is False


# ---- 유기농 판정 (무농약 제외) ----

def test_organic_only_counts_certification():
    assert is_organic_certified(FakeExp(organic_certification_type='유기농')) is True


def test_organic_excludes_pesticide_free():
    """★무농약은 유기농이 아니다.★ 별개 인증이라 섞으면 잘못된 결과다."""
    assert is_organic_certified(FakeExp(pesticide_free=True)) is False


def test_organic_false_when_blank():
    assert is_organic_certified(FakeExp(organic_certification_type=None)) is False


# ---- 친환경 인증 농장 섹션 ----

def test_section_requires_both_conditions():
    """친환경 항목 + ESG B 이상, 둘 다 있어야 한다."""
    # 무농약30 + 유기농25 + 증빙10 = 65 >= 60
    exp = FakeExp(pesticide_free=True, organic_certification_type='유기농',
                  organic_certification_image='c.jpg')
    assert passes_eco_section(exp) is True


def test_section_rejects_low_grade_even_with_eco():
    """★친환경 항목은 있지만 등급이 낮으면 제외.★ 무농약만이면 30점."""
    exp = FakeExp(pesticide_free=True)
    assert passes_eco_section(exp) is False


def test_section_rejects_high_s_axis_without_eco():
    """★무장애·주차·봉사로 점수를 올려도 친환경이 아니면 제외.★

    지적된 문제: ESG 는 E·S·G 를 포괄해서 사회 항목만으로 등급이 오른
    농장이 '친환경' 섹션에 나오면 사용자 기대와 어긋난다.
    """
    exp = FakeExp(volunteer_needed=10, barrier_free=True, has_parking=True,
                  organic_certification_image='c.jpg')
    assert is_eco_certified(exp) is False
    assert passes_eco_section(exp) is False


def test_section_boundary_at_grade_b():
    """경계: 정확히 60점이면 통과(이상 조건)."""
    # 무농약30 + 유기농25 = 55 < 60 → 제외
    below = FakeExp(pesticide_free=True, organic_certification_type='유기농')
    assert passes_eco_section(below) is False
    # + 주차5 = 60 → 통과
    at = FakeExp(pesticide_free=True, organic_certification_type='유기농',
                 has_parking=True)
    assert passes_eco_section(at) is True


def test_section_rejects_plain_experience():
    assert passes_eco_section(FakeExp()) is False


# ---- 조건 필터 (대분류 단위 AND) ----

def test_no_conditions_passes_everything():
    assert passes_conditions({}, FakeExp()) is True
    assert passes_conditions(None, FakeExp()) is True


def test_empty_lists_pass_everything():
    """모든 키가 있지만 값이 비면 조건을 고르지 않은 것이다."""
    conditions = {code: [] for code in JUDGEABLE_CATEGORIES}
    assert passes_conditions(conditions, FakeExp()) is True


def test_single_category_match():
    exp = FakeExp(organic_certification_type='유기농')
    assert passes_conditions({'facility': ['organic']}, exp) is True


def test_single_category_mismatch_excluded():
    """★유기농 필터를 켰는데 유기농이 아니면 제외.★"""
    exp = FakeExp(pesticide_free=True)      # 무농약만
    assert passes_conditions({'facility': ['organic']}, exp) is False


def test_or_within_category():
    """대분류 안에서는 OR — 무농약·유기농 중 하나만 맞아도 통과."""
    exp = FakeExp(pesticide_free=True)
    assert passes_conditions({'facility': ['organic', 'pesticide_free']}, exp) is True


def test_and_across_categories():
    """★대분류가 다르면 AND — 전부 충족해야 통과.★"""
    exp = FakeExp(organic_certification_type='유기농', address_detail='충남 논산시')
    both = {'facility': ['organic'], 'region': ['nonsan']}
    one_only = {'facility': ['organic'], 'region': ['seoul']}
    assert passes_conditions(both, exp) is True
    assert passes_conditions(one_only, exp) is False


def test_unjudgeable_categories_ignored():
    """★판정 로직이 없는 대분류는 AND 에서 뺀다.★

    companion_type 등 7개는 Experience 에 대응 데이터가 없어 절대 매칭되지
    않는다. AND 에 넣으면 '가족(아이)' 하나만 켜도 결과가 항상 0건이 된다.
    """
    exp = FakeExp(organic_certification_type='유기농')
    conditions = {'facility': ['organic'], 'companion_type': ['family_child']}
    assert passes_conditions(conditions, exp) is True


def test_selected_categories_filters_unjudgeable():
    conditions = {
        'facility': ['organic'],
        'companion_type': ['family_child'],   # 판정 불가
        'mood': ['healing'],                  # 판정 불가
        'region': [],                         # 미선택
    }
    assert selected_categories(conditions) == {'facility'}


def test_all_judgeable_codes_are_real():
    """JUDGEABLE_CATEGORIES 가 실제 카테고리 코드인지 확인."""
    from common.search_categories import CATEGORY_CODES
    assert JUDGEABLE_CATEGORIES.issubset(set(CATEGORY_CODES))
