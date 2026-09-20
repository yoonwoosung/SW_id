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
                 has_wifi=False, barrier_free=False):
        self.address_detail = address_detail
        self.cost = cost
        self.has_parking = has_parking
        self.pesticide_free = pesticide_free
        self.organic_certification_type = organic_certification_type
        self.activity_type = activity_type
        self.pet_allowed = pet_allowed
        self.pet_max_weight_kg = pet_max_weight_kg
        self.has_wifi = has_wifi
        self.barrier_free = barrier_free


def test_no_conditions_returns_zero():
    exp = FakeExperience(address_detail="충남 논산시", cost=25000)
    assert compute_category_match({}, exp) == 0
    assert compute_category_match(None, exp) == 0


def test_region_and_budget_and_facility_match():
    exp = FakeExperience(address_detail="충남 논산시 연무읍", cost=25000,
                         has_parking=True, pesticide_free=True)
    conditions = {
        "region": ["chungnam"],              # 대분류 충족 → +1
        "budget_range": ["course_30_50k"],   # 코스총비용 45000 → 3~5만 → +1
        "facility": ["parking", "pesticide_free"],  # ★OR: 둘 다 맞아도 대분류 1회 → +1★
    }
    assert compute_category_match(conditions, exp) == 3  # 충족 대분류 3개(region·budget·facility)


def test_unscored_categories_are_ignored():
    exp = FakeExperience(address_detail="충남 논산시", cost=25000)
    # companion_type 는 Experience에 데이터가 없어 채점되지 않는다.
    conditions = {"companion_type": ["child", "wheelchair"]}
    assert compute_category_match(conditions, exp) == 0


def test_region_province_and_city_match():
    # 도(별칭)·시 단위 코드 모두 주소 키워드로 채점된다(구 단위는 없음).
    exp = FakeExperience(address_detail="충청남도 천안시 서북구", cost=15000)
    assert compute_category_match({"region": ["cheonan"]}, exp) == 1     # 시
    assert compute_category_match({"region": ["chungnam"]}, exp) == 1    # 도(충청남도)
    assert compute_category_match({"region": ["gongju"]}, exp) == 0      # 다른 시


def test_activity_match():
    exp = FakeExperience(activity_type="kayak")
    assert compute_category_match({"activity": ["kayak"]}, exp) == 1
    assert compute_category_match({"activity": ["hiking"]}, exp) == 0


def test_pet_weight_tier_match():
    # 최대 15kg까지 허용하는 체험: 소형·중형 둘 다 골라도 OR로 대분류 1회.
    exp = FakeExperience(pet_allowed=True, pet_max_weight_kg=15)
    assert compute_category_match({"companion_type": ["dog_small", "dog_medium"]}, exp) == 1
    assert compute_category_match({"companion_type": ["dog_large"]}, exp) == 0  # 25kg 필요 → 불충족
    # 동반 불가 체험은 어떤 티어도 매칭 안 됨.
    assert compute_category_match({"companion_type": ["dog_small"]}, FakeExperience(pet_allowed=False)) == 0


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


def test_region_or_is_equal_for_each_match():
    # 지역 [가평, 춘천]을 함께 골라도, 가평 체험·춘천 체험 각각 지역 대분류 1회로 동등.
    gapyeong = FakeExperience(address_detail="경기도 가평군 상면", cost=25000)
    chuncheon = FakeExperience(address_detail="강원도 춘천시 신북읍", cost=25000)
    cond = {"region": ["gapyeong", "chuncheon"]}
    assert compute_category_match(cond, gapyeong) == 1
    assert compute_category_match(cond, chuncheon) == 1


def test_different_categories_stack():
    exp = FakeExperience(address_detail="경기도 가평군", cost=25000, has_parking=True, activity_type="kayak")
    cond = {"region": ["gapyeong"], "transport": ["car"], "activity": ["kayak", "hiking"]}
    assert compute_category_match(cond, exp) == 3  # region·transport·activity 각 1회


def test_category_bonus_scales_by_constant():
    exp = FakeExperience(address_detail="충남 논산시", cost=25000, has_parking=True)
    conditions = {"region": ["chungnam"], "facility": ["parking"]}  # 2건 일치
    assert category_bonus(conditions, exp) == pytest.approx(2 * CATEGORY_MATCH_SCORE)


# ======================================================================
# 무장애·와이파이 — 죽어 있던 선택지를 실제 데이터와 연결
# ======================================================================
#
# barrier_free 는 컬럼이 있고 ESG 점수·상세 배지에서 읽는데 필터만 안 봤다.
# 메인 페이지의 ?cond_facility=barrier_free 링크 카드가 항상 0건이었다.
# has_wifi 는 판정 분기가 있었지만 등록 폼에 입력이 없어 항상 False 였다.

def test_barrier_free_is_judged():
    assert compute_category_match(
        {"facility": ["barrier_free"]}, FakeExperience(barrier_free=True)) == 1
    assert compute_category_match(
        {"facility": ["barrier_free"]}, FakeExperience(barrier_free=False)) == 0


def test_wifi_is_judged():
    assert compute_category_match(
        {"facility": ["wifi"]}, FakeExperience(has_wifi=True)) == 1
    assert compute_category_match(
        {"facility": ["wifi"]}, FakeExperience(has_wifi=False)) == 0


def test_facility_keeps_or_within_category():
    """대분류 안은 OR — 주차만 있어도 '주차 또는 무장애'는 충족."""
    exp = FakeExperience(has_parking=True, barrier_free=False)
    assert compute_category_match({"facility": ["parking", "barrier_free"]}, exp) == 1


def test_unjudgeable_facility_codes_still_false():
    """화장실·수유실은 대응 컬럼이 없어 그대로 판정하지 않는다(화면에서 감춘다)."""
    exp = FakeExperience(has_parking=True, barrier_free=True, has_wifi=True)
    for code in ("restroom", "nursing_room"):
        assert compute_category_match({"facility": [code]}, exp) == 0, code


# ======================================================================
# 반려견 '동반가능'·'동반불가' — 둘 다 죽어 있던 선택지
# ======================================================================
#
# 예전에는 몸무게 티어(dog_small/medium/large)만 판정해, 목록의
# '동반가능'·'동반불가'를 고르면 어떤 체험도 통과하지 못했다.
# '동반가능'은 티어를 감싸는 부모 체크박스라 실제로 전송되는 값이다.

def test_pet_allowed_parent_option():
    assert compute_category_match(
        {"companion_type": ["pet_allowed"]},
        FakeExperience(pet_allowed=True, pet_max_weight_kg=15)) == 1
    assert compute_category_match(
        {"companion_type": ["pet_allowed"]}, FakeExperience(pet_allowed=False)) == 0


def test_pet_not_allowed_option():
    assert compute_category_match(
        {"companion_type": ["pet_not_allowed"]}, FakeExperience(pet_allowed=False)) == 1
    assert compute_category_match(
        {"companion_type": ["pet_not_allowed"]},
        FakeExperience(pet_allowed=True, pet_max_weight_kg=15)) == 0


def test_pet_allowed_without_weight_still_matches_parent():
    """부모 선택지는 몸무게가 비어 있어도 충족한다(티어 판정과 다르다)."""
    exp = FakeExperience(pet_allowed=True, pet_max_weight_kg=None)
    assert compute_category_match({"companion_type": ["pet_allowed"]}, exp) == 1
    assert compute_category_match({"companion_type": ["dog_small"]}, exp) == 0


def test_pet_weight_tiers_unchanged():
    """기존 몸무게 판정은 그대로다(어제 살린 동작이 깨지면 안 된다)."""
    exp = FakeExperience(pet_allowed=True, pet_max_weight_kg=15)
    assert compute_category_match({"companion_type": ["dog_medium"]}, exp) == 1   # 15 >= 15
    assert compute_category_match({"companion_type": ["dog_large"]}, exp) == 0    # 15 < 25


def test_pet_care_conditions_still_unjudged():
    """케어 조건은 대응 컬럼이 없어 그대로 판정하지 않는다(화면에서 감춘다)."""
    exp = FakeExperience(pet_allowed=True, pet_max_weight_kg=100)
    for code in ("leash_required", "cage_required", "indoor_ok", "outdoor_only"):
        assert compute_category_match({"companion_type": [code]}, exp) == 0, code


# ---- 지역: '광역시·특별시 전체' 체크박스 ----

def test_metro_group_checkbox_matches_any_metro():
    """그룹의 '전체'는 그룹 코드(metro)를 보낸다. 키워드가 없어 항상 0건이었다."""
    for address in ("서울특별시 강남구", "부산 해운대구", "세종특별자치시 조치원읍"):
        assert compute_category_match(
            {"region": ["metro"]}, FakeExperience(address_detail=address)) == 1, address


def test_metro_group_does_not_match_provinces():
    for address in ("충남 논산시", "경기도 광주시"):
        assert compute_category_match(
            {"region": ["metro"]}, FakeExperience(address_detail=address)) == 0, address


# ======================================================================
# 반려견이 동반유형 하위로 옮겨진 뒤 (2026-09-20 리팩터 대응)
# ======================================================================

def test_non_pet_companion_codes_are_skipped():
    """★'혼자'만 골랐을 때 결과가 0건이 되면 안 된다.★

    동반유형에는 반려견(판정 가능)과 인원수·동반구성(불가)이 섞여 있다.
    판정 불가만 고른 경우 그 대분류를 건너뛰어야 한다. 그러지 않으면
    지금까지 '무시되던' 조건이 '모든 체험을 제외하는' 더 나쁜 버그가 된다.
    """
    from services import eco_filter
    exp = FakeExperience(address_detail="충남 논산시", pet_allowed=True, pet_max_weight_kg=15)
    for codes in (["solo"], ["party_1"], ["family_child", "adults_only"]):
        assert eco_filter.passes_conditions({"companion_type": codes}, exp) is True, codes


def test_pet_codes_still_filter_within_companion_type():
    from services import eco_filter
    allowed = FakeExperience(address_detail="충남", pet_allowed=True, pet_max_weight_kg=15)
    denied = FakeExperience(address_detail="충남", pet_allowed=False)
    assert eco_filter.passes_conditions({"companion_type": ["dog_medium"]}, allowed) is True
    assert eco_filter.passes_conditions({"companion_type": ["dog_medium"]}, denied) is False
    assert eco_filter.passes_conditions({"companion_type": ["pet_not_allowed"]}, denied) is True


def test_mixed_selection_uses_pet_codes_only():
    """'혼자 + 중형'이면 반려견 코드만 추려 판정한다."""
    from services import eco_filter
    allowed = FakeExperience(address_detail="충남", pet_allowed=True, pet_max_weight_kg=15)
    denied = FakeExperience(address_detail="충남", pet_allowed=False)
    conditions = {"companion_type": ["solo", "dog_medium"]}
    assert eco_filter.passes_conditions(conditions, allowed) is True
    assert eco_filter.passes_conditions(conditions, denied) is False


def test_pet_selection_helper():
    from services.category_match import pet_selection
    assert pet_selection(["solo", "dog_medium", "party_1"]) == ["dog_medium"]
    assert pet_selection(["solo"]) == []
    assert pet_selection(None) == []


# ======================================================================
# 액티비티 — 체험 목록 필터 (2026-09-20)
# ======================================================================
#
# activity_type 컬럼은 있으나 저장하는 코드가 없어 모든 체험이 NULL 이다.
# 체험명·설명 키워드로 판정하되, ★컬럼이 채워지면 그쪽이 우선★ 한다.

class ActivityExp(FakeExperience):
    def __init__(self, crop='', notes='', activity_type=None):
        super().__init__(address_detail='충남 논산시')
        self.crop = crop
        self.notes = notes
        self.activity_type = activity_type


@pytest.mark.parametrize('crop,notes,code', [
    ('승마 체험', '', 'horse_riding'),
    ('딸기 따기', '인근 낚시터 이용 가능', 'fishing'),
    ('포도 수확', '둘레길 산책 포함', 'hiking'),
    ('카누 체험', '', 'kayak'),
    ('자전거 투어', '', 'cycling'),
])
def test_keyword_found_in_name_or_notes(crop, notes, code):
    assert compute_category_match({'activity': [code]}, ActivityExp(crop, notes)) == 1


def test_no_keyword_is_not_judged():
    """★억지로 맞히지 않는다.★ 키워드가 없으면 그 체험은 걸러진다."""
    assert compute_category_match({'activity': ['horse_riding']}, ActivityExp('사과 따기')) == 0


def test_empty_text_is_not_judged():
    assert compute_category_match({'activity': ['fishing']}, ActivityExp('', '')) == 0


def test_column_takes_priority_over_keywords():
    """★activity_type 이 있으면 그것을 쓴다.★

    등록 폼에 드롭다운이 생기면 키워드 폴백은 저절로 쓰이지 않는다.
    """
    # 이름에는 '승마'가 있지만 컬럼은 kayak — 컬럼이 이긴다
    exp = ActivityExp('승마 체험', '', activity_type='kayak')
    assert compute_category_match({'activity': ['horse_riding']}, exp) == 0
    assert compute_category_match({'activity': ['kayak']}, exp) == 1


def test_activity_is_an_experience_filter_again():
    from services.eco_filter import JUDGEABLE_CATEGORIES
    assert 'activity' in JUDGEABLE_CATEGORIES
