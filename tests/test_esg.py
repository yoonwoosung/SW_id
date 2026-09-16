"""services/esg_service.compute_esg 단위 테스트 — E·S·G 균형 배점(E55·S35·G10)으로 점수·등급 산출."""
import pytest

from services.esg_service import compute_esg
from common.constants import (
    ESG_SCORE_PESTICIDE_FREE, ESG_SCORE_ORGANIC, ESG_SCORE_VOLUNTEER,
    ESG_SCORE_BARRIER_FREE, ESG_SCORE_PARKING, ESG_SCORE_TRANSPARENCY,
)


class FakeExperience:
    def __init__(self, pesticide_free=False, organic_certification_type=None,
                 volunteer_needed=0, has_parking=False, barrier_free=False,
                 organic_certification_image=None):
        self.pesticide_free = pesticide_free
        self.organic_certification_type = organic_certification_type
        self.volunteer_needed = volunteer_needed
        self.has_parking = has_parking
        self.barrier_free = barrier_free
        self.organic_certification_image = organic_certification_image


def test_full_score_is_a():
    e = FakeExperience(pesticide_free=True, organic_certification_type="유기농",
                       volunteer_needed=5, has_parking=True, barrier_free=True,
                       organic_certification_image="cert.jpg")
    r = compute_esg(e)
    assert r["score"] == 100        # 30+25+20+10+5+10
    assert r["grade"] == "A"


def test_axis_balance_totals():
    # 배점이 E55 · S35 · G10 균형을 이루는지(항목 max 합).
    r = compute_esg(FakeExperience())
    by_axis = {}
    for b in r["breakdown"]:
        by_axis[b["axis"]] = by_axis.get(b["axis"], 0) + b["max"]
    assert by_axis == {"E": 55, "S": 35, "G": 10}


def test_zero_score_is_d():
    r = compute_esg(FakeExperience())
    assert r["score"] == 0
    assert r["grade"] == "D"


def test_new_items_scored():
    # 무장애(S)·인증투명성(G) 신설 항목이 실제로 채점되는지.
    e = FakeExperience(barrier_free=True, organic_certification_image="c.jpg")
    earned = {b["key"]: b["earned"] for b in compute_esg(e)["breakdown"]}
    assert earned["barrier_free"] == ESG_SCORE_BARRIER_FREE
    assert earned["transparency"] == ESG_SCORE_TRANSPARENCY


def test_partial_score_and_breakdown():
    e = FakeExperience(pesticide_free=True, has_parking=True)   # 30 + 5 = 35
    r = compute_esg(e)
    assert r["score"] == ESG_SCORE_PESTICIDE_FREE + ESG_SCORE_PARKING == 35
    assert r["grade"] == "D"        # 35 < 40 → D
    earned = {b["key"]: b["earned"] for b in r["breakdown"]}
    assert earned["pesticide_free"] == 30 and earned["parking"] == 5
    assert earned["organic"] == 0 and earned["volunteer"] == 0 and earned["barrier_free"] == 0
