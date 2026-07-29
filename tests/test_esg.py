"""services/esg_service.compute_esg 단위 테스트 — 기존 속성으로 ESG 점수·등급 산출."""
import pytest

from services.esg_service import compute_esg


class FakeExperience:
    def __init__(self, pesticide_free=False, organic_certification_type=None,
                 volunteer_needed=0, has_parking=False):
        self.pesticide_free = pesticide_free
        self.organic_certification_type = organic_certification_type
        self.volunteer_needed = volunteer_needed
        self.has_parking = has_parking


def test_full_score_is_a():
    e = FakeExperience(pesticide_free=True, organic_certification_type="유기농",
                       volunteer_needed=5, has_parking=True)
    r = compute_esg(e)
    assert r["score"] == 100
    assert r["grade"] == "A"


def test_zero_score_is_d():
    r = compute_esg(FakeExperience())
    assert r["score"] == 0
    assert r["grade"] == "D"


def test_partial_score_and_breakdown():
    e = FakeExperience(pesticide_free=True, has_parking=True)  # 35 + 10 = 45
    r = compute_esg(e)
    assert r["score"] == 45
    assert r["grade"] == "C"
    earned = {b["key"]: b["earned"] for b in r["breakdown"]}
    assert earned["pesticide_free"] == 35 and earned["parking"] == 10
    assert earned["organic"] == 0 and earned["volunteer"] == 0
