"""화면에 그릴 조건 트리 — 동작하지 않는 선택지를 감춘다.

고르면 결과가 항상 0건인 선택지가 27개 있었다. 대응 컬럼이 없거나
등록 폼에 입력이 없어 값이 채워지지 않는 것들이다.
살릴 수 있는 것은 살렸고(무장애·와이파이·반려견 동반가능/불가·광역시 전체),
살릴 수 없는 것은 원본 트리에 남긴 채 화면에서만 뺀다.
"""
import pytest

from common.search_categories import (
    SEARCH_CATEGORIES, LEAF_CODES, CATEGORY_CODES, visible_categories,
)
from services.eco_filter import JUDGEABLE_CATEGORIES

HIDDEN_LEAF_CODES = {
    # 반려견 케어 조건 — 대응 컬럼 없음(컬럼 추가를 미뤘다)
    'leash_required', 'cage_required', 'indoor_ok', 'outdoor_only',
    # 액티비티 — activity_type 을 저장하는 코드가 없다
    'horse_riding', 'kayak', 'fishing', 'hiking', 'cycling',
    # 교통수단 — 자가용만 has_parking 과 연동된다
    'public_transit', 'walk', 'bike',
    # 편의시설 — 대응 컬럼 없음
    'restroom', 'nursing_room',
}
VISIBLE_FACILITY = {'parking', 'barrier_free', 'wifi', 'pesticide_free', 'organic'}


def _leaves(nodes):
    for node in nodes:
        if node.get('children'):
            yield from _leaves(node['children'])
        else:
            yield node


def _codes(nodes):
    return {node['code'] for node in _leaves(nodes)}


def _all_nodes(nodes):
    """그룹 노드도 포함한 전체. 'pet_allowed'·'metro' 는 잎이 아니라 그룹이다."""
    for node in nodes:
        yield node
        if node.get('children'):
            yield from _all_nodes(node['children'])


def _all_codes(nodes):
    return {node['code'] for node in _all_nodes(nodes)}


def _top(tree):
    return {node['code'] for node in tree}


# ---- 감춰야 할 것 ----

@pytest.mark.parametrize('code', sorted(HIDDEN_LEAF_CODES))
def test_dead_option_is_hidden(code):
    assert code not in _codes(visible_categories()), code


def test_activity_category_hidden_entirely():
    """액티비티는 5개 전부 죽어 있어 대분류째 감춘다."""
    assert 'activity' not in _top(visible_categories())


def test_activity_removed_from_filtering():
    """★저장된 ?cond_activity=kayak 링크가 결과를 0건으로 만들지 않아야 한다.★"""
    assert 'activity' not in JUDGEABLE_CATEGORIES


# ---- 남아야 할 것 ----

def test_revived_options_are_visible():
    """이번에 살린 선택지는 화면에 남는다."""
    visible = _all_codes(visible_categories())   # pet_allowed·metro 는 그룹 노드다
    for code in ('barrier_free', 'wifi', 'pet_allowed', 'pet_not_allowed', 'metro'):
        assert code in visible, code


def test_facility_keeps_working_options():
    facility = next(c for c in visible_categories() if c['code'] == 'facility')
    assert {n['code'] for n in facility['children']} == VISIBLE_FACILITY


def test_pet_tiers_kept_without_care_conditions():
    """몸무게 3티어는 남기고 그 아래 케어 조건만 뺀다."""
    pet = next(c for c in visible_categories() if c['code'] == 'pet_dog')
    allowed = next(n for n in pet['children'] if n['code'] == 'pet_allowed')
    tiers = {n['code'] for n in allowed['children']}
    assert tiers == {'dog_small', 'dog_medium', 'dog_large'}
    for tier in allowed['children']:
        assert not tier.get('children'), tier['code']


def test_transport_keeps_car_only():
    transport = next(c for c in visible_categories() if c['code'] == 'transport')
    assert [n['code'] for n in transport['children']] == ['car']


def test_region_untouched():
    """지역은 하나도 감추지 않는다."""
    region_full = next(c for c in SEARCH_CATEGORIES if c['code'] == 'region')
    region_vis = next(c for c in visible_categories() if c['code'] == 'region')
    assert _codes([region_full]) == _codes([region_vis])


def test_twelve_categories_remain():
    """13개 중 액티비티 하나만 빠진다."""
    assert len(visible_categories()) == len(CATEGORY_CODES) - 1


# ---- 원본은 그대로 ----

def test_original_tree_is_not_mutated():
    """★hidden 한 줄만 지우면 되살아나야 한다.★ 원본에는 그대로 남긴다."""
    full = _codes(SEARCH_CATEGORIES)
    for code in HIDDEN_LEAF_CODES:
        assert code in full, code
    assert 'activity' in CATEGORY_CODES


def test_leaf_codes_still_validate_hidden_options():
    """저장된 링크의 코드 검증은 원본을 쓴다(감췄다고 무효가 되면 안 된다)."""
    for code in HIDDEN_LEAF_CODES:
        assert code in LEAF_CODES, code


def test_visible_returns_a_copy():
    """반환 트리를 고쳐도 원본이 바뀌지 않는다."""
    tree = visible_categories()
    tree[0]['label'] = '바뀐라벨'
    tree[0]['children'] = []
    assert SEARCH_CATEGORIES[0]['label'] != '바뀐라벨'
    assert SEARCH_CATEGORIES[0]['children']


def test_signup_activity_options_unaffected():
    """회원가입 '관심 액티비티'는 원본 트리를 읽으므로 영향받지 않는다."""
    from common.profile_options import ACTIVITY_LABELS, ACTIVITY_OPTIONS
    assert len(ACTIVITY_LABELS) == 5
    assert 'kayak' in ACTIVITY_OPTIONS
