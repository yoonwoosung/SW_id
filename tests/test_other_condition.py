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

WITH_OTHER = ('region', 'pet_dog', 'experience_type', 'mood', 'season')
WITHOUT_OTHER = ('companion_type', 'party', 'schedule', 'budget_range',
                 'transport', 'duration_hours', 'facility', 'activity')


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


@pytest.mark.parametrize('code', WITHOUT_OTHER)
def test_other_categories_do_not_have_other(code):
    """★넣어도 항상 0건인 곳에는 넣지 않는다.★

    예산대는 구간이 0~무한을 빈틈없이 덮고, 편의시설·교통수단은 불리언이라
    '목록 밖 값'이라는 개념이 없다. 나머지는 대응 데이터가 아예 없다.
    """
    category = next(c for c in SEARCH_CATEGORIES if c['code'] == code)
    assert '기타' not in list(_labels([category])), code


def test_other_is_visible_on_screen():
    """감춘 선택지가 아니다 — 화면에 보여야 한다."""
    for category in visible_categories():
        if category['code'] in WITH_OTHER:
            assert '기타' in list(_labels([category])), category['code']


# ---- 지역 ----

def test_region_other_matches_unknown_address():
    exp = FakeExp(address_detail='Hokkaido Japan')
    assert compute_category_match({'region': ['region_other']}, exp) == 1


@pytest.mark.parametrize('address', ['충남 논산시', '서울특별시 강남구', '경기도 가평군'])
def test_region_other_skips_known_regions(address):
    assert compute_category_match({'region': ['region_other']}, FakeExp(address)) == 0


@pytest.mark.parametrize('address', ['', '   ', None])
def test_region_other_excludes_missing_address(address):
    """★주소가 없는 것은 '기타'가 아니다.★ 값 없음과 목록 밖은 다르다."""
    assert compute_category_match({'region': ['region_other']}, FakeExp(address or '')) == 0


def test_region_other_ors_with_normal_choice():
    """대분류 안은 OR — 충남이거나 목록 밖."""
    conditions = {'region': ['chungnam', 'region_other']}
    assert compute_category_match(conditions, FakeExp('충남 논산시')) == 1
    assert compute_category_match(conditions, FakeExp('Hokkaido Japan')) == 1
    assert compute_category_match(conditions, FakeExp('경기도 가평군')) == 0


# ---- 반려견 ----

def test_pet_other_matches_below_smallest_tier():
    """★동반가능인데 허용 몸무게가 소형 기준(5kg)에 못 미치는 경우.★"""
    exp = FakeExp('충남', pet_allowed=True, pet_max_weight_kg=3)
    assert compute_category_match({'pet_dog': ['pet_dog_other']}, exp) == 1
    assert compute_category_match({'pet_dog': ['dog_small']}, exp) == 0


@pytest.mark.parametrize('weight', [5, 15, 25, 100])
def test_pet_other_skips_tiered_weights(weight):
    exp = FakeExp('충남', pet_allowed=True, pet_max_weight_kg=weight)
    assert compute_category_match({'pet_dog': ['pet_dog_other']}, exp) == 0


def test_pet_other_excludes_missing_weight():
    """몸무게 미입력은 '기타'가 아니다."""
    exp = FakeExp('충남', pet_allowed=True, pet_max_weight_kg=None)
    assert compute_category_match({'pet_dog': ['pet_dog_other']}, exp) == 0


def test_pet_other_excludes_not_allowed():
    exp = FakeExp('충남', pet_allowed=False)
    assert compute_category_match({'pet_dog': ['pet_dog_other']}, exp) == 0


def test_pet_other_boundary_is_smallest_tier():
    smallest = min(PET_WEIGHT_MIN_KG.values())
    below = FakeExp('충남', pet_allowed=True, pet_max_weight_kg=smallest - 1)
    at = FakeExp('충남', pet_allowed=True, pet_max_weight_kg=smallest)
    assert compute_category_match({'pet_dog': ['pet_dog_other']}, below) == 1
    assert compute_category_match({'pet_dog': ['pet_dog_other']}, at) == 0


# ---- 코스 장소 ----

NATURE = {'name': '천안북면계곡', 'category': 'A01010900', 'content_type_id': 12}
HISTORY = {'name': '박문수묘', 'category': 'A02010700', 'content_type_id': 12}
SHOPPING = {'name': '천안중앙시장', 'category': 'A04010100', 'content_type_id': 38}
SPORTS = {'name': '천안카약장', 'category': 'A03020200', 'content_type_id': 28}


def test_place_other_is_complement_of_siblings():
    """'기타' = 같은 대분류 다른 선택지의 여집합."""
    assert matches(SHOPPING, 'experience_type_other') is True   # A04 는 어디에도 없다
    assert matches(NATURE, 'experience_type_other') is False    # A01 = 자연생태
    assert matches(HISTORY, 'experience_type_other') is False   # A02 = 공예


def test_mood_other():
    assert matches(SHOPPING, 'mood_other') is True
    assert matches(SPORTS, 'mood_other') is False               # A03 = 액티브
    assert matches(NATURE, 'mood_other') is False               # A01 = 힐링


def test_season_other_by_name():
    assert matches(HISTORY, 'season_other') is True
    assert matches({'name': '봄딸기체험농원', 'category': 'A01'}, 'season_other') is False


def test_place_other_is_judgeable():
    for code in COURSE_OTHER_SIBLINGS:
        assert judgeable(code) is True, code


def test_place_other_takes_weight_in_scorer():
    scorer = build_scorer(['mood_other'])
    assert scorer(SHOPPING) == pytest.approx(1.0)
    assert scorer(NATURE) == pytest.approx(0.0)


def test_place_other_ors_with_normal_choice():
    """분위기에서 '전통 + 기타'를 고르면 둘 중 하나만 맞아도 점수가 붙는다."""
    scorer = build_scorer(['tradition', 'mood_other'])
    assert scorer(HISTORY) > 0      # 전통
    assert scorer(SHOPPING) > 0     # 기타
    assert scorer(NATURE) == pytest.approx(0.0)


def test_siblings_cover_every_non_other_choice():
    """여집합 목록이 실제 선택지와 어긋나면 '기타' 판정이 틀어진다."""
    for other_code, siblings in COURSE_OTHER_SIBLINGS.items():
        category_code = other_code[:-len(OTHER_SUFFIX)]
        category = next(c for c in SEARCH_CATEGORIES if c['code'] == category_code)
        actual = {n['code'] for n in category['children'] if n['code'] != other_code}
        assert set(siblings) == actual, category_code
