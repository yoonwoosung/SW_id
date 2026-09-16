"""services/profile_service 단위 테스트 — 가입 프로필 입력 검증·정규화(파트2 핵심 로직)."""
from services.profile_service import clean_profile, has_recommendation_profile


def _getters(single, multi):
    return (lambda k: single.get(k), lambda k: multi.get(k, []))


def test_valid_profile_is_kept():
    single, multi = _getters(
        {"age_group": "20s", "gender": "female", "family_type": "couple", "preferred_transport": "car"},
        {"interest_activities": ["kayak", "hiking"]},
    )
    out = clean_profile(single, multi)
    assert out["age_group"] == "20s"
    assert out["gender"] == "female"
    assert out["family_type"] == "couple"
    assert out["preferred_transport"] == "car"
    assert out["interest_activities"] == "kayak,hiking"


def test_invalid_or_empty_values_become_none():
    single, multi = _getters(
        {"age_group": "999s", "gender": "", "family_type": "unknown", "preferred_transport": None},
        {"interest_activities": ["not_a_code"]},
    )
    out = clean_profile(single, multi)
    assert out == {
        "age_group": None, "gender": None, "family_type": None,
        "interest_activities": None, "preferred_transport": None,
    }


def test_partial_profile_allowed():
    single, multi = _getters({"age_group": "30s"}, {})
    out = clean_profile(single, multi)
    assert out["age_group"] == "30s"
    assert out["gender"] is None


class FakeUser:
    def __init__(self, **kw):
        for f in ("age_group", "gender", "family_type", "interest_activities", "preferred_transport"):
            setattr(self, f, kw.get(f))


def test_has_recommendation_profile():
    assert has_recommendation_profile(None) is False
    assert has_recommendation_profile(FakeUser()) is False
    assert has_recommendation_profile(FakeUser(gender="male")) is True
    assert has_recommendation_profile(FakeUser(interest_activities="harvest")) is True
