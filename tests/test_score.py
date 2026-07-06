"""추천 점수 계산 함수 단위 테스트 (PR4).

대상: app.py 의 순수 함수
- calculate_score(distance, max_p, current_p, is_specialty) -> float
- matches_specialty(address_detail, crop) -> bool

기존 공식을 확정(characterize)하는 테스트다. 지금 코드에 있는 동작을 "그대로"
못박아, 이후 PR5에서 경계·예외를 고칠 때 무엇이 바뀌는지 드러나게 한다.
(0 나눗셈·None 은 현재 '터지는' 동작을 문서화한다. PR5에서 '안전값'으로 바뀔 예정.)
"""
import pytest
from app import calculate_score, matches_specialty

# 가중치: distance 0.5 / specialty 0.3 / availability 0.2
# 각 성분을 분리하려고 나머지 성분을 0으로 만드는 입력을 고른다.


# --- distance_score = max(0, 1 - distance/50) : 다른 성분을 0으로 (avail=0, spec=False) ---
def test_distance_score_0km_is_full():
    # distance 0 → distance_score 1.0 → 0.5*1.0 = 0.5
    assert calculate_score(0, 20, 20, False) == pytest.approx(0.5)


def test_distance_score_25km_is_half():
    assert calculate_score(25, 20, 20, False) == pytest.approx(0.25)  # 0.5*0.5


def test_distance_score_50km_is_zero():
    assert calculate_score(50, 20, 20, False) == pytest.approx(0.0)


def test_distance_score_60km_clamped_to_zero():
    # 1 - 60/50 = -0.2 이지만 max(0, ...) 로 클램프 → 0
    assert calculate_score(60, 20, 20, False) == pytest.approx(0.0)


# --- availability_score = (max-current)/max : distance=50(→0), spec=False 로 분리 ---
def test_availability_empty_farm_is_full():
    assert calculate_score(50, 20, 0, False) == pytest.approx(0.2)   # 0.2*1.0


def test_availability_half_full():
    assert calculate_score(50, 20, 10, False) == pytest.approx(0.1)  # 0.2*0.5


def test_availability_full_is_zero():
    assert calculate_score(50, 20, 20, False) == pytest.approx(0.0)


# --- 가중합: 각 성분만 1일 때 해당 가중치가 그대로 나와야 한다 ---
def test_weight_distance_only():
    assert calculate_score(0, 20, 20, False) == pytest.approx(0.5)


def test_weight_specialty_only():
    assert calculate_score(50, 20, 20, True) == pytest.approx(0.3)


def test_weight_availability_only():
    assert calculate_score(50, 20, 0, False) == pytest.approx(0.2)


def test_weight_all_three():
    assert calculate_score(0, 20, 0, True) == pytest.approx(1.0)


# --- 현재 '터지는' 경계 (PR5 이전 상태 문서화) ---
def test_zero_max_participants_raises():
    # max_participants=0 → (0-0)/0 → ZeroDivisionError (현재 동작). PR5에서 방어 예정.
    with pytest.raises(ZeroDivisionError):
        calculate_score(50, 0, 0, False)


def test_none_address_detail_raises():
    # address_detail=None → 'r in None' → TypeError (현재 동작). PR5에서 방어 예정.
    with pytest.raises(TypeError):
        matches_specialty(None, "쌀")


# --- matches_specialty 매칭 규칙 ---
def test_specialty_match_true():
    # REGIONAL_SPECIALTIES['이천'] = ['쌀', '복숭아']
    assert matches_specialty("이천시 부발읍", "쌀") is True


def test_specialty_no_match_false():
    assert matches_specialty("서울시 강남구", "배추") is False


def test_specialty_substring_match_is_current_behavior():
    # '철원' 특산물에 '토마토'가 있고, 'sc in crop' 부분매칭이라 '방울토마토'도 매칭된다.
    # 의도된 동작인지와 무관하게 '현재 동작'을 확정해 둔다.
    assert matches_specialty("철원군", "방울토마토") is True
