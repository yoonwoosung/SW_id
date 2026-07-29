# services/esg_service.py — 체험(농장)의 ESG 점수를 기존 속성으로 계산하는 순수 로직(테스트 가능).
# 새 DB 컬럼 없이 Experience의 무농약·유기농·봉사·주차 속성으로 0~100 점수를 낸다.
from common.constants import (
    ESG_SCORE_PESTICIDE_FREE, ESG_SCORE_ORGANIC, ESG_SCORE_VOLUNTEER, ESG_SCORE_PARKING,
    ESG_GRADE_A, ESG_GRADE_B, ESG_GRADE_C,
)


def compute_esg(experience):
    """experience의 지속가능성 관련 속성으로 ESG 점수·등급·항목별 내역을 계산한다."""
    breakdown = [
        _item("pesticide_free", "무농약 재배", bool(getattr(experience, "pesticide_free", False)), ESG_SCORE_PESTICIDE_FREE),
        _item("organic", "유기농 인증", bool(getattr(experience, "organic_certification_type", None)), ESG_SCORE_ORGANIC),
        _item("volunteer", "봉사 프로그램 운영", (getattr(experience, "volunteer_needed", 0) or 0) > 0, ESG_SCORE_VOLUNTEER),
        _item("parking", "주차 접근성", bool(getattr(experience, "has_parking", False)), ESG_SCORE_PARKING),
    ]
    score = sum(b["earned"] for b in breakdown)
    return {"score": score, "grade": _grade(score), "breakdown": breakdown}


def _item(key, label, achieved, max_score):
    return {"key": key, "label": label, "earned": max_score if achieved else 0, "max": max_score}


def _grade(score):
    if score >= ESG_GRADE_A:
        return "A"
    if score >= ESG_GRADE_B:
        return "B"
    if score >= ESG_GRADE_C:
        return "C"
    return "D"
