"""services/match_service 단위 테스트 — 요청 조건 ↔ 체험 매칭 점수(category_match 재사용).

가짜 UserRequest/Experience 객체로 순수 로직만 검증한다(DB·네트워크 불필요).
"""
import json

import pytest

from services.match_service import compute_match_score, best_match_for_experiences, parse_conditions


class FakeRequest:
    def __init__(self, conditions):
        # conditions: dict → JSON 문자열로 저장(실제 모델과 동일 형태)
        self.conditions = json.dumps(conditions) if conditions is not None else None


class FakeExperience:
    def __init__(self, address_detail="", cost=0, has_parking=False,
                 pesticide_free=False, organic_certification_type=None):
        self.address_detail = address_detail
        self.cost = cost
        self.has_parking = has_parking
        self.pesticide_free = pesticide_free
        self.organic_certification_type = organic_certification_type


def test_parse_conditions_handles_empty_and_broken():
    assert parse_conditions(FakeRequest(None)) == {}
    broken = FakeExperience()  # conditions 속성 없음 → getattr 아님, 직접
    req = FakeRequest({})
    req.conditions = "{broken json"
    assert parse_conditions(req) == {}


def test_compute_match_score_reuses_category_match():
    req = FakeRequest({"region": ["chungnam"], "facility": ["parking"]})
    exp = FakeExperience(address_detail="충남 논산시", has_parking=True)
    assert compute_match_score(req, exp) == 2


def test_best_match_picks_highest_experience():
    req = FakeRequest({"region": ["chungnam"], "facility": ["parking", "pesticide_free"]})
    weak = FakeExperience(address_detail="경기도 이천시")               # 0
    strong = FakeExperience(address_detail="충남 논산시",
                            has_parking=True, pesticide_free=True)      # 3
    assert best_match_for_experiences(req, [weak, strong]) == 3


def test_best_match_no_experiences_returns_zero():
    req = FakeRequest({"region": ["chungnam"]})
    assert best_match_for_experiences(req, []) == 0
