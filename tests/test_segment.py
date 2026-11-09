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
    """★두 버튼은 서로 다른 세그먼트로 간다.★

    예전에는 둘 다 'peers' 라 같은 섹션·같은 결과였다.
    나이 버튼은 나이대 인기, 성별 버튼은 성별 인기를 기준으로 삼는다.
    """
    btns = segment_buttons(FakeUser("20s", "male"))
    assert len(btns) == 2
    assert btns[0]["label"] == "20대 놀러가기 좋은 곳" and btns[0]["segment"] == "peers_age"
    assert btns[1]["label"] == "남자끼리 가기 좋은 곳" and btns[1]["segment"] == "peers_gender"
    assert btns[0]["segment"] != btns[1]["segment"]


def test_segment_buttons_fallback_when_no_profile():
    """비로그인/무정보 → 기본 버튼 2개.

    세그먼트 값은 실제 화면 섹션(nearby·esg)과 맞아야 한다.
    'peers' 로 두면 '요즘 인기 있는 곳'을 눌렀는데 '가볍게 다녀오기' 섹션으로 간다.
    """
    btns = segment_buttons(None)
    assert len(btns) == 2
    assert [b["segment"] for b in btns] == ["nearby", "esg"]
    assert [b["label"] for b in btns] == ["요즘 인기 있는 곳", "친환경으로 즐기기"]


def test_segment_buttons_map_to_real_sections():
    """버튼의 segment 는 화면에 실제로 있는 섹션이어야 한다.

    ai_recommend.js 의 SECTIONS 가 이 값으로 스크롤 대상을 찾는다.
    없는 값이면 버튼을 눌러도 아무 일도 일어나지 않는다.
    """
    sections = {'nearby', 'peers_age', 'peers_gender', 'peers', 'group', 'esg'}
    for user in (FakeUser("20s", "male"), FakeUser("30s", None),
                 FakeUser(None, "female"), None):
        for button in segment_buttons(user):
            assert button["segment"] in sections, button


def test_segment_buttons_partial_profile_filled_to_two():
    # 나이만 있으면 나이 버튼 1개 + 기본 버튼으로 2개를 채운다.
    btns = segment_buttons(FakeUser("30s", None))
    assert len(btns) == 2
    assert btns[0]["label"] == "30대 놀러가기 좋은 곳"
