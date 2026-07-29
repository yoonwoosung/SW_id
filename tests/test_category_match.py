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
                 pesticide_free=False, organic_certification_type=None,
                 activity_type=None, pet_allowed=False, pet_max_weight_kg=None,
                 has_wifi=False):
        self.address_detail = address_detail
        self.cost = cost
        self.has_parking = has_parking
        self.pesticide_free = pesticide_free
        self.organic_certification_type = organic_certification_type
        self.activity_type = activity_type
        self.pet_allowed = pet_allowed
        self.pet_max_weight_kg = pet_max_weight_kg
        self.has_wifi = has_wifi


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
    # companion_type 는 Experience에 데이터가 없어 채점되지 않는다.
    conditions = {"companion_type": ["child", "wheelchair"]}
    assert compute_category_match(conditions, exp) == 0


def test_sub_region_district_match():
    # 시/군·구 단위 코드도 주소 키워드로 채점된다.
    exp = FakeExperience(address_detail="충청남도 천안시 동남구 목천읍", cost=15000)
    assert compute_category_match({"region": ["cheonan"]}, exp) == 1
    assert compute_category_match({"region": ["cheonan_dongnam"]}, exp) == 1
    assert compute_category_match({"region": ["cheonan_seobuk"]}, exp) == 0


def test_activity_match():
    exp = FakeExperience(activity_type="kayak")
    assert compute_category_match({"activity": ["kayak"]}, exp) == 1
    assert compute_category_match({"activity": ["hiking"]}, exp) == 0


def test_pet_weight_tier_match():
    # 최대 15kg까지 허용하는 체험: 소형·중형은 매칭, 대형(25kg 필요)은 불매칭.
    exp = FakeExperience(pet_allowed=True, pet_max_weight_kg=15)
    assert compute_category_match({"pet_dog": ["dog_small", "dog_medium"]}, exp) == 2
    assert compute_category_match({"pet_dog": ["dog_large"]}, exp) == 0
    # 동반 불가 체험은 어떤 티어도 매칭 안 됨.
    assert compute_category_match({"pet_dog": ["dog_small"]}, FakeExperience(pet_allowed=False)) == 0


def test_transport_car_uses_parking():
    assert compute_category_match({"transport": ["car"]}, FakeExperience(has_parking=True)) == 1
    assert compute_category_match({"transport": ["car"]}, FakeExperience(has_parking=False)) == 0
    # 대중교통·도보는 대응 데이터 없음 → 미채점.
    assert compute_category_match({"transport": ["public_transit", "walk"]}, FakeExperience(has_parking=True)) == 0


def test_wifi_facility_match():
    assert compute_category_match({"facility": ["wifi"]}, FakeExperience(has_wifi=True)) == 1
    assert compute_category_match({"facility": ["wifi"]}, FakeExperience(has_wifi=False)) == 0


def test_region_no_match():
    exp = FakeExperience(address_detail="경기도 이천시", cost=25000)
    assert compute_category_match({"region": ["chungnam"]}, exp) == 0


def test_category_bonus_scales_by_constant():
    exp = FakeExperience(address_detail="충남 논산시", cost=25000, has_parking=True)
    conditions = {"region": ["chungnam"], "facility": ["parking"]}  # 2건 일치
    assert category_bonus(conditions, exp) == pytest.approx(2 * CATEGORY_MATCH_SCORE)
