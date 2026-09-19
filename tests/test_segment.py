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
    assert [s["key"] for s in segs] == ["peers", "group", "esg"]


def test_auto_segment_titles_state_their_criteria():
    """제목은 '기준'을 드러내야 한다.

    예전에는 '20대 인기 체험'처럼 나이대를 붙였는데, 실제로는 나이를 기준으로
    고르지 않아 이름과 근거가 어긋났다(같은 체험이 세 섹션에 다 나온 원인의 일부).
    이제 로그인 여부·나이와 무관하게 같은 제목을 준다.
    """
    logged_in = auto_segments(FakeUser("20s", "male"))
    anonymous = auto_segments(None)
    assert [s["title"] for s in logged_in] == [s["title"] for s in anonymous]
    assert logged_in[0]["title"] == "가볍게 다녀오기"
    assert logged_in[1]["title"] == "단체로 가기 좋은 코스"
    assert logged_in[2]["title"] == "친환경 인증 농장"


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
