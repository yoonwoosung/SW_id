"""services/segment_service 단위 테스트 — 회원 세그먼트 라벨·자동 추천 카드·단축 버튼."""
from services.segment_service import user_segment_label, auto_segments, segment_buttons


class FakeUser:
    def __init__(self, age_group=None, gender=None):
        self.age_group = age_group
        self.gender = gender


def test_label_from_age_and_gender():
    assert user_segment_label(FakeUser("20s", "male")) == "20대·남성"
    assert user_segment_label(FakeUser("30s", None)) == "30대"
    assert user_segment_label(FakeUser(None, None)) is None
    assert user_segment_label(None) is None


def test_other_gender_label_omitted():
    assert user_segment_label(FakeUser("20s", "other")) == "20대"


def test_auto_segments_has_three_with_keys():
    segs = auto_segments(FakeUser("20s", "male"))
    assert [s["key"] for s in segs] == ["peers", "active", "esg"]
    assert segs[0]["title"] == "20대 인기 체험"   # 연령대 반영
    assert auto_segments(None)[0]["title"] == "요즘 인기 체험"  # 비로그인 폴백


def test_segment_buttons_from_profile():
    # 20대 남성 → 나이·성별 버튼 2개(둘 다 또래=peers 세그먼트).
    btns = segment_buttons(FakeUser("20s", "male"))
    assert len(btns) == 2
    assert btns[0]["label"] == "20대 놀러가기 좋은 곳" and btns[0]["segment"] == "peers"
    assert btns[1]["label"] == "남자끼리 가기 좋은 곳" and btns[1]["segment"] == "peers"
    assert all(b.get("icon") for b in btns)   # 아이콘 포함


def test_segment_buttons_fallback_when_no_profile():
    # 비로그인/무정보 → 기본 버튼(인기·친환경)으로 2개 채움.
    btns = segment_buttons(None)
    assert len(btns) == 2
    assert [b["segment"] for b in btns] == ["peers", "esg"]


def test_segment_buttons_partial_profile_filled_to_two():
    # 나이만 있으면 나이 버튼 1개 + 기본 버튼으로 2개를 채운다.
    btns = segment_buttons(FakeUser("30s", None))
    assert len(btns) == 2
    assert btns[0]["label"] == "30대 놀러가기 좋은 곳"
