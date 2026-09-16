"""services/recommend_service.rank_recommendations 단위 테스트(거리·점수순 정렬, 150km 제외)."""
import pytest

from services.recommend_service import rank_recommendations


class FakeExp:
    def __init__(self, id, lat, lng, crop="딸기", addr="충남 논산시",
                 max_participants=20, current_participants=0):
        self.id = id
        self.lat = lat
        self.lng = lng
        self.crop = crop
        self.address_detail = addr
        self.max_participants = max_participants
        self.current_participants = current_participants


def test_ranks_by_score_and_excludes_far():
    near = FakeExp(1, 36.81, 127.31)         # 기준점 근처
    far = FakeExp(2, 33.5, 126.5)            # 150km 초과(제주)
    ranked = rank_recommendations([far, near], 36.8, 127.3)
    ids = [e.id for e, d, s in ranked]
    assert 1 in ids           # 가까운 건 포함
    assert 2 not in ids       # 150km 초과 제외


def test_returns_distance_and_score_tuple():
    e = FakeExp(1, 36.8, 127.3)
    ranked = rank_recommendations([e], 36.8, 127.3)
    assert len(ranked) == 1
    exp, distance, score = ranked[0]
    assert exp.id == 1
    assert distance == 0.0
    assert score > 0
