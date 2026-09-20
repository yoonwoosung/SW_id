"""화면에 그릴 조건 트리 — 동작하지 않는 선택지를 감춘다.

고르면 결과가 항상 0건인 선택지를 원본 트리에 남긴 채 화면에서만 뺀다.
★동작하지 않는 선택지를 보여주는 것이 더 나쁘다.★

2026-09-20 리팩터(a1f54eaa 외)로 트리 구조가 크게 바뀌었다.
  · 인원 대분류 삭제 → 동반유형 하위로 통합
  · 반려견도 동반유형 하위 그룹으로
  · 일정·소요시간에 선택지 신설, 각 대분류에 '기타' 추가
그때 hidden 이 풀린 항목(도보·자전거)을 다시 감추고, 신설된 판정 불가
선택지도 함께 감춘다.
"""
import pytest

from common.search_categories import (
    SEARCH_CATEGORIES, LEAF_CODES, CATEGORY_CODES, visible_categories,
)
from services.eco_filter import JUDGEABLE_CATEGORIES

# 대분류째 감춘 것
HIDDEN_CATEGORIES = {'activity', 'schedule', 'duration_hours'}

# 개별로 감춘 잎
HIDDEN_LEAF_CODES = {
    # 교통수단 — 자가용만 has_parking 과 연동된다
    'public_transit', 'walk', 'bike', 'transport_other',
    # 편의시설 — 대응 컬럼이 없거나 불리언이라 '기타'가 성립하지 않는다
    'restroom', 'nursing_room', 'facility_other',
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


def _all_codes(nodes):
    def walk(ns):
        for n in ns:
            yield n['code']
            if n.get('children'):
                yield from walk(n['children'])
    return set(walk(nodes))


def _top(tree):
    return {node['code'] for node in tree}


# ---- 감춰야 할 것 ----

@pytest.mark.parametrize('code', sorted(HIDDEN_LEAF_CODES))
def test_dead_option_is_hidden(code):
    assert code not in _all_codes(visible_categories()), code


@pytest.mark.parametrize('code', sorted(HIDDEN_CATEGORIES))
def test_dead_category_is_hidden(code):
    """하위가 전부 판정 불가면 탭을 열어도 빈 화면이라 대분류째 감춘다."""
    assert code not in _top(visible_categories()), code


def test_activity_removed_from_filtering():
    """★저장된 ?cond_activity=kayak 링크가 결과를 0건으로 만들지 않아야 한다.★"""
    assert 'activity' not in JUDGEABLE_CATEGORIES


def test_no_empty_category_on_screen():
    """선택지가 하나도 없는 탭이 남으면 안 된다."""
    for category in visible_categories():
        assert list(_leaves(category.get('children') or [])), category['code']


# ---- 남아야 할 것 ----

def test_revived_options_are_visible():
    visible = _all_codes(visible_categories())
    for code in ('barrier_free', 'wifi', 'pet_allowed', 'pet_not_allowed',
                 'metro', 'dog_small', 'dog_medium', 'dog_large'):
        assert code in visible, code


def test_facility_keeps_working_options():
    facility = next(c for c in visible_categories() if c['code'] == 'facility')
    assert {n['code'] for n in facility['children']} == VISIBLE_FACILITY


def test_transport_keeps_car_only():
    transport = next(c for c in visible_categories() if c['code'] == 'transport')
    assert [n['code'] for n in transport['children']] == ['car']


def test_pet_group_lives_under_companion_type():
    """반려견은 독립 대분류가 아니라 동반유형 하위 그룹이다(리팩터 결과)."""
    companion = next(c for c in visible_categories() if c['code'] == 'companion_type')
    pet = next(n for n in companion['children'] if n['code'] == 'pet_allowed')
    assert {n['code'] for n in pet['children']} == {
        'dog_small', 'dog_medium', 'dog_large', 'pet_not_allowed'}
    assert 'pet_dog' not in CATEGORY_CODES


def test_region_untouched():
    region_full = next(c for c in SEARCH_CATEGORIES if c['code'] == 'region')
    region_vis = next(c for c in visible_categories() if c['code'] == 'region')
    assert _codes([region_full]) == _codes([region_vis])


# ---- 원본은 그대로 ----

def test_original_tree_is_not_mutated():
    """★hidden 한 줄만 지우면 되살아나야 한다.★"""
    full = _all_codes(SEARCH_CATEGORIES)
    for code in HIDDEN_LEAF_CODES | HIDDEN_CATEGORIES:
        assert code in full, code


def test_leaf_codes_still_validate_hidden_options():
    """저장된 링크의 코드 검증은 원본을 쓴다(감췄다고 무효가 되면 안 된다)."""
    for code in HIDDEN_LEAF_CODES:
        assert code in LEAF_CODES, code


def test_visible_returns_a_copy():
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


# ---- 조건 코드 검증은 그룹 노드까지 포함해야 한다 ----

def test_all_codes_includes_group_nodes():
    """★도·광역시 그룹·반려견 '전체'는 잎이 아니지만 고를 수 있다.★

    routes/course 가 LEAF_CODES 로만 검증하던 동안 이 코드들이 전부 걸러져
    도 단위 지역 선택이 코스에 전달되지 않았다.
    """
    from common.search_categories import ALL_CODES, LEAF_CODES
    for code in ('chungnam', 'chungbuk', 'metro', 'pet_allowed', 'headcount'):
        assert code in ALL_CODES, code
        assert code not in LEAF_CODES, code


def test_all_codes_superset_of_leaf_codes():
    from common.search_categories import ALL_CODES, LEAF_CODES
    assert LEAF_CODES < ALL_CODES


def test_unknown_code_rejected():
    from common.search_categories import ALL_CODES
    assert 'nonexistent_code' not in ALL_CODES
