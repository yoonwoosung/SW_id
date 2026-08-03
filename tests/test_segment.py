"""services/segment_service 단위 테스트 — 회원 세그먼트 라벨·자동 추천 카드."""
from services.segment_service import user_segment_label, auto_segments


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
