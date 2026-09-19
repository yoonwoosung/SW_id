"""services/segment_score 단위 테스트 — 세그먼트별로 기준이 달라야 한다.

기존 문제: peers 는 분기가 없어 nearby 와 같은 결과였다.
기본 점수(calculate_score)는 건드리지 않고 보너스만 더해 순서를 바꾼다.
"""
import pytest

from services import segment_score
from common.constants import (
    SEGMENT_LIGHT_CHEAP_WEIGHT,
    SEGMENT_LIGHT_NEAR_WEIGHT,
    SEGMENT_GROUP_CAPACITY_WEIGHT,
    SEGMENT_GROUP_PARKING_WEIGHT,
)


class FakeExp:
    def __init__(self, id, cost=20000, max_p=20, current_p=0, parking=False):
        self.id = id
        self.cost = cost
        self.max_participants = max_p
        self.current_participants = current_p
        self.has_parking = parking


def ranked_of(items):
    """(experience, distance, score, reasons) 형태로 만든다. 기본 점수는 전부 동일."""
    return [(e, dist, 1.0, []) for e, dist in items]


# ---- 상대 평가 ----

def test_relative_normalizes_within_candidates():
    """절대 기준이 아니라 후보군 안에서 상대 평가한다."""
    ctx = segment_score.build_context([FakeExp(1, cost=10000), FakeExp(2, cost=30000)])
    assert ctx['cost_min'] == 10000 and ctx['cost_max'] == 30000


def test_relative_all_same_gives_zero():
    """값이 전부 같으면 변별할 수 없으므로 0."""
    ctx = segment_score.build_context([FakeExp(1, cost=20000), FakeExp(2, cost=20000)])
    b = segment_score.bonus('peers', FakeExp(1, cost=20000), None, ctx)
    assert b == 0.0


def test_remaining_uses_absolute_count():
    """비율이 아니라 절대 인원. 정원 4명에 4명 남은 곳이 만점이 되면 안 된다."""
    small_full = FakeExp(1, max_p=4, current_p=0)     # 4석
    big_partial = FakeExp(2, max_p=30, current_p=10)  # 20석
    ctx = segment_score.build_context([small_full, big_partial])
    b_small = segment_score.bonus('group', small_full, None, ctx)
    b_big = segment_score.bonus('group', big_partial, None, ctx)
    assert b_big > b_small, "20석이 4석보다 단체에 적합하다"


# ---- 가볍게(peers) ----

def test_light_prefers_cheap():
    cheap, pricey = FakeExp(1, cost=10000), FakeExp(2, cost=30000)
    ctx = segment_score.build_context([cheap, pricey])
    assert segment_score.bonus('peers', cheap, None, ctx) == pytest.approx(SEGMENT_LIGHT_CHEAP_WEIGHT)
    assert segment_score.bonus('peers', pricey, None, ctx) == 0.0


def test_light_adds_distance_when_known():
    e = FakeExp(1, cost=10000)
    ctx = segment_score.build_context([e, FakeExp(2, cost=30000)])
    near = segment_score.bonus('peers', e, 0, ctx)      # 거리 0 → 만점
    far = segment_score.bonus('peers', e, 50, ctx)      # 50km → 0
    assert near - far == pytest.approx(SEGMENT_LIGHT_NEAR_WEIGHT)


def test_light_without_location_uses_price_only():
    """좌표가 없으면 거리 요소를 빼고 가격만 본다(비로그인·위치 거부)."""
    e = FakeExp(1, cost=10000)
    ctx = segment_score.build_context([e, FakeExp(2, cost=30000)])
    assert segment_score.bonus('peers', e, None, ctx) == pytest.approx(SEGMENT_LIGHT_CHEAP_WEIGHT)


# ---- 단체(group) ----

def test_group_prefers_more_seats():
    few, many = FakeExp(1, max_p=5), FakeExp(2, max_p=30)
    ctx = segment_score.build_context([few, many])
    assert segment_score.bonus('group', many, None, ctx) == pytest.approx(SEGMENT_GROUP_CAPACITY_WEIGHT)
    assert segment_score.bonus('group', few, None, ctx) == 0.0


def test_group_adds_parking():
    e_no = FakeExp(1, max_p=20, parking=False)
    e_yes = FakeExp(2, max_p=20, parking=True)
    ctx = segment_score.build_context([e_no, e_yes])
    diff = segment_score.bonus('group', e_yes, None, ctx) - segment_score.bonus('group', e_no, None, ctx)
    assert diff == pytest.approx(SEGMENT_GROUP_PARKING_WEIGHT)


def test_group_counts_booked_seats():
    e = FakeExp(1, max_p=30, current_p=25)   # 5석만 남음
    other = FakeExp(2, max_p=30, current_p=0)
    ctx = segment_score.build_context([e, other])
    assert segment_score.bonus('group', e, None, ctx) < segment_score.bonus('group', other, None, ctx)


# ---- 세그먼트별 결과가 갈리는가 (핵심) ----

def test_segments_produce_different_order():
    """★같은 후보인데 세그먼트마다 1위가 달라야 한다.★

    싼데 자리 적은 곳 vs 비싼데 자리 많고 주차 되는 곳.
    """
    cheap_small = FakeExp(1, cost=10000, max_p=5, parking=False)
    pricey_big = FakeExp(2, cost=30000, max_p=30, parking=True)
    ranked = ranked_of([(cheap_small, 10), (pricey_big, 10)])

    light = segment_score.apply('peers', ranked)
    group = segment_score.apply('group', ranked)

    assert light[0][0].id == 1, "가볍게 → 싼 쪽이 1위"
    assert group[0][0].id == 2, "단체 → 자리 많고 주차 되는 쪽이 1위"
    assert light[0][0].id != group[0][0].id


def test_base_score_is_not_overwritten():
    """보너스는 정렬에만 쓰고 기본 점수 값은 그대로 둔다."""
    e = FakeExp(1, cost=10000)
    ranked = ranked_of([(e, 10)])
    out = segment_score.apply('peers', ranked)
    assert out[0][2] == 1.0, "score 필드가 바뀌면 안 된다"


# ---- 해당 없는 세그먼트 ----

def test_unknown_segment_keeps_order():
    a, b = FakeExp(1, cost=30000), FakeExp(2, cost=10000)
    ranked = ranked_of([(a, 10), (b, 10)])
    assert segment_score.apply('esg', ranked) == ranked
    assert segment_score.apply(None, ranked) == ranked


def test_empty_list():
    assert segment_score.apply('peers', []) == []


def test_missing_attributes_do_not_crash():
    class Bare:
        pass
    ctx = segment_score.build_context([Bare()])
    assert segment_score.bonus('peers', Bare(), None, ctx) == 0.0
    assert segment_score.bonus('group', Bare(), None, ctx) == 0.0


# ═══════════ 나이·성별 섹션: 클릭 로그 인기 기준 ═══════════
#
# 예전에는 peers_age·peers_gender 가 apply('peers') 를 재사용해
# '가볍게'(저렴·근접)와 완전히 같은 순서가 나왔다.
# 화면 부제는 "같은 나이대에서 인기"인데 계산은 가격이었다.

from common.constants import SEGMENT_TREND_POPULARITY_WEIGHT


@pytest.mark.parametrize('segment', ['peers_age', 'peers_gender'])
def test_trend_segments_rank_by_click_count(segment):
    """★많이 눌린 순으로 줄 세운다.★ 기본 점수가 같으면 클릭 수가 순서를 정한다."""
    a, b, c = FakeExp(1), FakeExp(2), FakeExp(3)
    ranked = ranked_of([(a, 10), (b, 10), (c, 10)])
    out = segment_score.apply(segment, ranked, trend_counts={1: 3, 2: 10, 3: 7})
    assert [item[0].id for item in out] == [2, 3, 1]


@pytest.mark.parametrize('segment', ['peers_age', 'peers_gender'])
def test_unclicked_experience_gets_no_bonus(segment):
    """한 번도 안 눌린 체험은 가점 0 이라 뒤로 밀린다."""
    ctx = segment_score.build_context([FakeExp(1)], trend_counts={1: 5})
    assert segment_score.bonus(segment, FakeExp(99), None, ctx) == 0.0


def test_top_clicked_gets_full_weight():
    """최댓값으로 정규화한다 — 1등은 가중치를 다 받는다."""
    ctx = segment_score.build_context([FakeExp(1)], trend_counts={1: 20, 2: 5})
    assert segment_score.bonus('peers_age', FakeExp(1), None, ctx) == pytest.approx(
        SEGMENT_TREND_POPULARITY_WEIGHT)
    assert segment_score.bonus('peers_age', FakeExp(2), None, ctx) == pytest.approx(
        SEGMENT_TREND_POPULARITY_WEIGHT * 0.25)


def test_trend_segments_ignore_price_and_capacity():
    """★'가볍게'(저렴)·'단체로'(잔여석) 기준을 쓰면 안 된다.★

    싼 체험과 자리 많은 체험이 클릭 수와 어긋나게 배치해도
    클릭 수 순서가 유지돼야 한다.
    """
    cheap_roomy = FakeExp(1, cost=5000, max_p=100, parking=True)   # 가격·정원 1등
    pricey_tiny = FakeExp(2, cost=50000, max_p=2)                  # 가격·정원 꼴등
    ranked = ranked_of([(cheap_roomy, 1), (pricey_tiny, 1)])
    out = segment_score.apply('peers_age', ranked, trend_counts={2: 10, 1: 1})
    assert [item[0].id for item in out] == [2, 1], "클릭 수가 기준이어야 한다"


def test_no_click_logs_keeps_base_order():
    """클릭 로그가 없으면 가점이 없어 기본 점수순 그대로다(폴백)."""
    a, b = FakeExp(1), FakeExp(2)
    ranked = [(a, 10, 0.9, []), (b, 10, 0.5, [])]
    assert segment_score.apply('peers_age', ranked, trend_counts={}) == ranked
    assert segment_score.apply('peers_age', ranked, trend_counts=None) == ranked


def test_trend_counts_do_not_leak_into_other_segments():
    """클릭 수는 나이·성별 섹션에서만 쓴다. peers·group 기준은 그대로."""
    cheap = FakeExp(1, cost=5000)
    pricey = FakeExp(2, cost=50000)
    ranked = ranked_of([(cheap, 10), (pricey, 10)])
    out = segment_score.apply('peers', ranked, trend_counts={2: 99})
    assert [item[0].id for item in out] == [1, 2], "peers 는 싼 쪽이 먼저다"


def test_nearby_is_untouched():
    """nearby 는 보너스가 없어 기본 점수순 그대로."""
    ranked = [(FakeExp(1), 10, 0.3, []), (FakeExp(2), 10, 0.9, [])]
    assert segment_score.apply('nearby', ranked, trend_counts={1: 99}) == ranked


def test_base_score_is_not_overwritten():
    """기본 점수는 건드리지 않는다. 보너스는 정렬에만 쓴다."""
    ranked = ranked_of([(FakeExp(1), 10), (FakeExp(2), 10)])
    out = segment_score.apply('peers_age', ranked, trend_counts={2: 10})
    assert all(item[2] == 1.0 for item in out)
