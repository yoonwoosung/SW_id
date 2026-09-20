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


# ---- 대분류 안에 판정 불가 값만 골랐을 때 0건이 되지 않는가 (2026-09-20) ----
# 반려견에서 한 번, 교통수단·편의시설에서 또 나온 패턴이라 대분류마다 못 박는다.

def test_transit_only_does_not_zero_everything():
    """★대중교통·택시만 고르면 결과가 0건이었다.★ (실측 확인 후 수정)

    _has_transport 는 자가용만 주차 데이터로 판정하는데, 교통수단 대분류가
    'AND 로 충족해야 할 대분류'에 들어가 어떤 체험도 통과하지 못했다.
    """
    exp = FakeExp(has_parking=False)
    assert passes_conditions({'transport': ['public_transit']}, exp) is True
    assert passes_conditions({'transport': ['taxi']}, exp) is True
    assert passes_conditions({'transport': ['public_transit', 'taxi']}, exp) is True


def test_car_still_filters_by_parking():
    """★기존 동작 유지.★ 자가용은 여전히 주차 있는 체험만 통과시킨다."""
    assert passes_conditions({'transport': ['car']}, FakeExp(has_parking=True)) is True
    assert passes_conditions({'transport': ['car']}, FakeExp(has_parking=False)) is False


def test_car_with_transit_keeps_car_rule():
    """자가용을 같이 골랐으면 자가용 기준으로 판정한다(대분류 안은 OR)."""
    conditions = {'transport': ['car', 'public_transit']}
    assert passes_conditions(conditions, FakeExp(has_parking=True)) is True
    assert passes_conditions(conditions, FakeExp(has_parking=False)) is False


def test_restroom_only_does_not_zero_everything():
    """화장실·수유실은 Experience 컬럼이 없다.

    코스 장소 기준값으로 살리며 화면 감춤을 풀었는데, 체험 목록 쪽 판정이
    없어 단독으로 고르면 0건이 됐다. ★코스 반영과 목록 판정은 별개다.★
    """
    exp = FakeExp()
    assert passes_conditions({'facility': ['restroom']}, exp) is True
    assert passes_conditions({'facility': ['nursing_room']}, exp) is True


def test_facility_judgeable_codes_still_filter():
    """★기존 동작 유지.★ 컬럼이 있는 편의시설은 그대로 거른다."""
    assert passes_conditions({'facility': ['parking']}, FakeExp(has_parking=True)) is True
    assert passes_conditions({'facility': ['parking']}, FakeExp(has_parking=False)) is False
    assert passes_conditions({'facility': ['wifi']}, FakeExp(has_wifi=True)) is True
    assert passes_conditions({'facility': ['wifi']}, FakeExp(has_wifi=False)) is False


def test_restroom_with_parking_keeps_parking_rule():
    """판정 가능한 값이 하나라도 있으면 그 값으로 판정한다."""
    conditions = {'facility': ['restroom', 'parking']}
    assert passes_conditions(conditions, FakeExp(has_parking=True)) is True
    assert passes_conditions(conditions, FakeExp(has_parking=False)) is False


def test_every_visible_leaf_can_match_some_experience():
    """★전수 확인.★ 화면에 보이는 선택지를 단독으로 골라 0건이 되면 안 된다.

    "판정 불가 값만 고르면 대분류째 건너뛴다"는 규칙이 모든 대분류에서
    지켜지는지 본다. 지역·예산대·액티비티는 값에 맞춘 체험으로 확인한다.
    """
    from common.search_categories import (visible_categories, CATEGORY_OF_CODE,
                                          REGION_ADDRESS_KEYWORDS, BUDGET_RANGES)
    from common.constants import EXPERIENCE_ACTIVITY_KEYWORDS

    def leaves(nodes):
        for node in nodes:
            if node.get('children'):
                yield from leaves(node['children'])
            else:
                yield node['code']

    def candidates(code):
        yield FakeExp(has_parking=True, has_wifi=True, pesticide_free=True,
                      organic_certification_type='유기농', barrier_free=True,
                      pet_allowed=True, pet_max_weight_kg=50.0, cost=1000)
        yield FakeExp(pet_allowed=False)
        for keyword in REGION_ADDRESS_KEYWORDS.get(code, []):
            yield FakeExp(address_detail=f'{keyword} 어딘가 1-1')
        if code in BUDGET_RANGES:
            low, high = BUDGET_RANGES[code]
            # 예산대는 코스 총비용(체험비 + 교통·식사 추정) 기준이라 체험비를 훑는다.
            for cost in range(0, (high or low) + 1, 5000):
                yield FakeExp(cost=cost)
        if code in EXPERIENCE_ACTIVITY_KEYWORDS:
            yield FakeExp(activity_type=code)

    dead = []
    for code in leaves(visible_categories()):
        category = CATEGORY_OF_CODE.get(code)
        if category not in JUDGEABLE_CATEGORIES:
            continue
        if not any(passes_conditions({category: [code]}, exp) for exp in candidates(code)):
            dead.append(code)
    assert dead == [], f"단독으로 고르면 결과가 0건이 되는 선택지: {dead}"
