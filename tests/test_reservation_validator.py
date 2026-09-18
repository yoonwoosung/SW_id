"""services/reservation_validator 단위 테스트 — 예약 신청 입력 검증.

핵심은 음수 차단이다. 총합만 검사하면 성인 1 · 청소년 -5 처럼
총합을 음수로 만들어 정원을 되돌리는 우회가 가능했다.
"""
from datetime import date

import pytest

from services.reservation_validator import (
    parse_participants,
    parse_apply_date,
    MAX_PER_CATEGORY,
    MAX_TOTAL,
)


def form(adult=0, teen=0, child=0):
    return {'count_adult': adult, 'count_teen': teen, 'count_child': child}


# ---- 정상 ----

def test_normal_counts():
    counts, total, err = parse_participants(form(adult=2, teen=1, child=0))
    assert err is None
    assert counts == {'count_adult': 2, 'count_teen': 1, 'count_child': 0}
    assert total == 3


def test_string_digits_accepted():
    # 폼은 문자열로 들어온다
    counts, total, err = parse_participants(form(adult='3', teen='0', child='1'))
    assert err is None and total == 4


def test_blank_treated_as_zero():
    counts, total, err = parse_participants(form(adult='2', teen='', child=None))
    assert err is None
    assert counts['count_teen'] == 0 and counts['count_child'] == 0
    assert total == 2


def test_missing_field_treated_as_zero():
    counts, total, err = parse_participants({'count_adult': 1})
    assert err is None and total == 1


# ---- 음수 (핵심 버그) ----

def test_negative_single_field_rejected():
    _, _, err = parse_participants(form(teen=-1))
    assert err is not None


def test_negative_offset_by_positive_rejected():
    """★성인 1 · 청소년 -5 → 총합 -4. 예전에는 통과해 정원을 늘렸다.★"""
    counts, total, err = parse_participants(form(adult=1, teen=-5))
    assert err is not None, "음수가 섞인 입력이 통과해선 안 된다"
    assert counts is None and total == 0


def test_negative_that_still_sums_positive_rejected():
    """총합은 양수(10-3=7)여도 개별 음수면 거부한다."""
    _, _, err = parse_participants(form(adult=10, teen=-3))
    assert err is not None


# ---- 0명 ----

def test_all_zero_rejected():
    _, _, err = parse_participants(form())
    assert err == "참가 인원을 1명 이상 선택해주세요."


def test_empty_form_rejected():
    _, _, err = parse_participants({})
    assert err is not None


# ---- 비정수 ----

def test_non_numeric_rejected_without_exception():
    """예전에는 int('abc') 가 ValueError 를 던져 500 이 났다."""
    _, _, err = parse_participants(form(adult='abc'))
    assert err == "인원 수는 숫자로 입력해 주세요."


def test_float_string_rejected():
    _, _, err = parse_participants(form(adult='1.5'))
    assert err is not None


# ---- 상한 ----

def test_per_category_cap_boundary_ok():
    _, total, err = parse_participants(form(adult=MAX_PER_CATEGORY))
    assert err is None and total == MAX_PER_CATEGORY


def test_per_category_cap_exceeded():
    _, _, err = parse_participants(form(adult=MAX_PER_CATEGORY + 1))
    assert err is not None


def test_huge_value_rejected():
    _, _, err = parse_participants(form(adult=999999))
    assert err is not None


def test_max_possible_total_is_within_cap():
    """개별 상한 3개를 다 채워도 총합 상한 안에 든다(총합 상한은 여유분)."""
    _, total, err = parse_participants(
        form(adult=MAX_PER_CATEGORY, teen=MAX_PER_CATEGORY, child=MAX_PER_CATEGORY))
    assert err is None
    assert total == MAX_PER_CATEGORY * 3 <= MAX_TOTAL


# ---- 날짜 ----

def test_valid_date():
    d, err = parse_apply_date('2026-09-21')
    assert err is None and d == date(2026, 9, 21)


def test_date_with_whitespace():
    d, err = parse_apply_date('  2026-09-21  ')
    assert err is None and d == date(2026, 9, 21)


def test_impossible_date_rejected_without_exception():
    """예전에는 strptime 이 ValueError 를 던져 500 이 났다."""
    d, err = parse_apply_date('2026-13-45')
    assert d is None and err == "신청 날짜 형식이 올바르지 않습니다."


def test_wrong_format_rejected():
    for bad in ('2026/09/21', '21-09-2026', 'tomorrow', '20260921'):
        d, err = parse_apply_date(bad)
        assert d is None and err is not None, bad


def test_empty_date_rejected():
    for bad in ('', '   ', None):
        d, err = parse_apply_date(bad)
        assert d is None and err is not None
