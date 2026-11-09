"""'기타' 조건 — 그 대분류의 다른 선택지 어디에도 걸리지 않는 값.

★값이 아예 없는 것은 제외한다.★ 값이 있는데 목록 밖인 것만 '기타'다.
5개 대분류에만 넣었다(지역·반려견·체험종류·분위기·계절제철).
"""
import pytest

from common.search_categories import (
    SEARCH_CATEGORIES, visible_categories, LEAF_CODES, OTHER_SUFFIX, PET_WEIGHT_MIN_KG,
)
from common.constants import COURSE_OTHER_SIBLINGS
from services.category_match import compute_category_match
from services.place_score import matches, judgeable, build_scorer

# 2026-09-20 리팩터로 구조가 바뀌었다.
#   · 인원(party) 대분류 삭제, 반려견도 동반유형 하위로 → pet_dog_other 는 없어졌다
#   · 팀원이 일정·소요시간·교통수단·편의시설에도 '기타'를 추가했으나
#     그 대분류들은 판정 자체가 불가해 화면에서 감췄다(test_visible_categories)
# 지역·반려견의 '기타'는 팀원이 c55255ed 에서 제거했다(의도적 결정).
WITH_OTHER = ('experience_type', 'mood', 'season')
REMOVED_OTHER = ('region', 'pet_dog')
# '기타'가 성립하지 않는 대분류(넣어도 항상 0건이라 화면에 내보내지 않는다)
NO_USABLE_OTHER = ('companion_type', 'budget_range')


class FakeExp:
    def __init__(self, address_detail='', pet_allowed=False, pet_max_weight_kg=None):
        self.address_detail = address_detail
        self.pet_allowed = pet_allowed
        self.pet_max_weight_kg = pet_max_weight_kg


def _labels(nodes):
    for node in nodes:
        if node.get('children'):
            yield from _labels(node['children'])
        else:
            yield node['label']


# ---- 어디에 넣었나 ----

@pytest.mark.parametrize('code', WITH_OTHER)
def test_five_categories_have_other(code):
    category = next(c for c in SEARCH_CATEGORIES if c['code'] == code)
    assert '기타' in list(_labels([category])), code
    assert code + OTHER_SUFFIX in LEAF_CODES


@pytest.mark.parametrize('code', NO_USABLE_OTHER)
def test_other_categories_do_not_have_other(code):
    """★넣어도 항상 0건인 곳에는 넣지 않는다.★

    예산대는 구간이 0~무한을 빈틈없이 덮어 빈틈이 없고,
    동반유형은 판정 가능한 반려견이 불리언+구간이라 '목록 밖'이 성립하지 않는다.
    """
    category = next(c for c in SEARCH_CATEGORIES if c['code'] == code)
    assert '기타' not in list(_labels([category])), code


@pytest.mark.parametrize('code', REMOVED_OTHER)
def test_removed_other_stays_removed(code):
    """지역·반려견의 '기타'는 팀원이 제거했다(c55255ed). 되살리지 않는다."""
    from common.search_categories import LEAF_CODES
    assert code + '_other' not in LEAF_CODES


def test_other_is_hidden_where_it_cannot_work():
    """팀원이 추가한 '기타' 중 판정 불가한 것은 화면에서 감췄다."""
    from common.search_categories import visible_categories
    visible = set()
    def walk(ns):
        for n in ns:
            visible.add(n['code'])
            if n.get('children'): walk(n['children'])
    walk(visible_categories())
    for code in ('transport_other', 'facility_other', 'schedule_other',
                 'duration_hours_other'):
        assert code not in visible, code


def test_other_is_visible_on_screen():
    """감춘 선택지가 아니다 — 화면에 보여야 한다."""
    for category in visible_categories():
        if category['code'] in WITH_OTHER:
            assert '기타' in list(_labels([category])), category['code']


# 지역 '기타'(region_other)는 팀원이 트리에서 제거했다(c55255ed).
# services/category_match 의 판정 코드는 남아 있어 되살리면 바로 동작한다.


# ---- 반려견 ----

# 반려견 '기타'(pet_dog_other)는 2026-09-20 리팩터로 트리에서 사라졌다.
# 반려견이 동반유형 하위로 옮겨지며 팀원이 제거했다.


# ---- 코스 장소 ----

NATURE = {'name': '천안북면계곡', 'category': 'A01010900', 'content_type_id': 12}
HISTORY = {'name': '박문수묘', 'category': 'A02010700', 'content_type_id': 12}
SHOPPING = {'name': '천안중앙시장', 'category': 'A04010100', 'content_type_id': 38}
SPORTS = {'name': '천안카약장', 'category': 'A03020200', 'content_type_id': 28}


def test_place_other_is_complement_of_siblings():
    """'기타' = 같은 대분류 다른 선택지의 여집합."""
    assert matches(SHOPPING, 'experience_type_other') is True   # A04 는 어디에도 없다
    assert matches(NATURE, 'experience_type_other') is False    # A0101 = 자연생태
    # 2026-09-20 재매핑 이후 역사관광지(A0201)는 체험종류 어디에도 안 걸린다 → 기타
    assert matches(HISTORY, 'experience_type_other') is True


def test_mood_other():
    assert matches(SHOPPING, 'mood_other') is True
    assert matches(SPORTS, 'mood_other') is False               # A03 = 액티브
    assert matches(HISTORY, 'mood_other') is False              # A0201 = 전통
    # 재매핑 후 자연관광지(A0101)는 분위기 어디에도 안 걸린다 → 기타
    assert matches(NATURE, 'mood_other') is True


def test_season_other_by_name():
    assert matches(HISTORY, 'season_other') is True
    assert matches({'name': '봄딸기체험농원', 'category': 'A01'}, 'season_other') is False


def test_place_other_is_judgeable():
    for code in COURSE_OTHER_SIBLINGS:
        assert judgeable(code) is True, code


def test_place_other_takes_weight_in_scorer():
    scorer = build_scorer(['mood_other'])
    assert scorer(SHOPPING) == pytest.approx(1.0)
    assert scorer(HISTORY) == pytest.approx(0.0)      # 전통에 걸리므로 기타가 아니다


def test_place_other_ors_with_normal_choice():
    """분위기에서 '전통 + 기타'를 고르면 둘 중 하나만 맞아도 점수가 붙는다."""
    scorer = build_scorer(['tradition', 'mood_other'])
    assert scorer(HISTORY) > 0      # 전통
    assert scorer(SHOPPING) > 0     # 기타
    park = {'name': '태조산 공원', 'category': 'A02020700', 'content_type_id': 12}
    assert scorer(park) == pytest.approx(0.0)   # 힐링이라 전통도 기타도 아니다


def test_siblings_cover_every_non_other_choice():
    """여집합 목록이 실제 선택지와 어긋나면 '기타' 판정이 틀어진다."""
    for other_code, siblings in COURSE_OTHER_SIBLINGS.items():
        category_code = other_code[:-len(OTHER_SUFFIX)]
        category = next(c for c in SEARCH_CATEGORIES if c['code'] == category_code)
        actual = {n['code'] for n in category['children'] if n['code'] != other_code}
        assert set(siblings) == actual, category_code
