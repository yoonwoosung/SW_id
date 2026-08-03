"""카테고리 조건 매칭·추천 가점 단위 테스트.

services/category_match.compute_category_match 와 recommend_service.category_bonus 를
Experience 속성만 흉내 낸 가짜 객체로 검증한다(네트워크·DB 불필요).
"""
import pytest

from services.category_match import compute_category_match
from services.recommend_service import category_bonus
from common.constants import CATEGORY_MATCH_SCORE


class FakeExperience:
    def __init__(self, address_detail="", cost=0, has_parking=False,
                 pesticide_free=False, organic_certification_type=None):
        self.address_detail = address_detail
        self.cost = cost
        self.has_parking = has_parking
        self.pesticide_free = pesticide_free
        self.organic_certification_type = organic_certification_type


def test_no_conditions_returns_zero():
    exp = FakeExperience(address_detail="충남 논산시", cost=25000)
    assert compute_category_match({}, exp) == 0
    assert compute_category_match(None, exp) == 0


def test_region_and_budget_and_facility_match():
    exp = FakeExperience(address_detail="충남 논산시 연무읍", cost=25000,
                         has_parking=True, pesticide_free=True)
    conditions = {
        "region": ["chungnam"],        # 주소에 '충남' 포함 → +1
        "budget_range": ["range_20k"], # 25000원 → 2만원대 → +1
        "facility": ["parking", "pesticide_free"],  # 둘 다 → +2
    }
    assert compute_category_match(conditions, exp) == 4


def test_unscored_categories_are_ignored():
    exp = FakeExperience(address_detail="충남 논산시", cost=25000)
    # experience_type·companion_type 는 Experience에 데이터가 없어 채점되지 않는다.
    conditions = {"experience_type": ["harvest"], "companion_type": ["child"]}
    assert compute_category_match(conditions, exp) == 0


def test_region_no_match():
    exp = FakeExperience(address_detail="경기도 이천시", cost=25000)
    assert compute_category_match({"region": ["chungnam"]}, exp) == 0


def test_category_bonus_scales_by_constant():
    exp = FakeExperience(address_detail="충남 논산시", cost=25000, has_parking=True)
    conditions = {"region": ["chungnam"], "facility": ["parking"]}  # 2건 일치
    assert category_bonus(conditions, exp) == pytest.approx(2 * CATEGORY_MATCH_SCORE)
