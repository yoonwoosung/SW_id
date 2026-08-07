"""services/personalize_service 단위 테스트 — 과거 신청 작물 기반 개인화 가점."""
import pytest

from services.personalize_service import user_preferences, personalize_boost, rank_personalized
from common.constants import PERSONALIZE_CROP_BOOST


class FakeExp:
    def __init__(self, id, lat, lng, crop, addr="충남 논산시",
                 max_participants=20, current_participants=0):
        self.id = id
        self.lat = lat
        self.lng = lng
        self.crop = crop
        self.address_detail = addr
        self.max_participants = max_participants
        self.current_participants = current_participants


class FakeApp:
    def __init__(self, experience):
        self.experience = experience


class FakeUser:
    def __init__(self, applied_exps):
        self.applications = [FakeApp(e) for e in applied_exps]


def test_preferences_from_history():
    u = FakeUser([FakeExp(1, 36.8, 127.3, "딸기"), FakeExp(2, 36.8, 127.3, "포도")])
    assert user_preferences(u)["crops"] == {"딸기", "포도"}


def test_no_user_no_preference():
    assert user_preferences(None)["crops"] == set()


def test_boost_only_for_preferred_crop():
    prefs = {"crops": {"딸기"}}
    assert personalize_boost(FakeExp(1, 0, 0, "딸기"), prefs) == PERSONALIZE_CROP_BOOST
    assert personalize_boost(FakeExp(2, 0, 0, "포도"), prefs) == 0.0


def test_ranking_prefers_history_crop():
    # 두 체험이 같은 위치·조건이면, 과거 신청 작물(딸기)이 위로 온다.
    strawberry = FakeExp(1, 36.8, 127.3, "딸기")
    grape = FakeExp(2, 36.8, 127.3, "포도")
    user = FakeUser([FakeExp(9, 36.8, 127.3, "딸기")])
    ranked = rank_personalized([grape, strawberry], user, 36.8, 127.3)
    assert ranked[0][0].id == 1  # 딸기가 1위
    assert "이전에 신청한 작물이에요" in ranked[0][3]


def test_ranks_without_location():
    # 좌표가 없으면 거리 필터 없이 특산물·잔여석 기반으로 순위를 낸다(기본 추천).
    near = FakeExp(1, 0, 0, "포도")          # 좌표 무의미
    far = FakeExp(2, 99, 99, "포도")
    user = FakeUser([])
    ranked = rank_personalized([near, far], user, None, None)
    assert len(ranked) == 2                  # 150km 컷오프 없음(둘 다 포함)
    assert all(item[1] is None for item in ranked)  # distance_km None
    assert all("가까워요" not in " ".join(item[3]) for item in ranked)  # 거리 이유 없음


def test_segment_trending_boosts_experience():
    # 세그먼트 인기 체험(id=2)이 trending_ids에 있으면 위로 오고 이유가 붙는다.
    a = FakeExp(1, 36.8, 127.3, "포도")
    b = FakeExp(2, 36.8, 127.3, "포도")
    user = FakeUser([])
    ranked = rank_personalized([a, b], user, 36.8, 127.3, trending_ids={2})
    assert ranked[0][0].id == 2
    assert "나와 비슷한 분들이 많이 봤어요" in ranked[0][3]
