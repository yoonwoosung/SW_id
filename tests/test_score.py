"""추천 점수 계산 함수 단위 테스트 (PR4).

대상: app.py 의 순수 함수
- calculate_score(distance, max_p, current_p, is_specialty) -> float
- matches_specialty(address_detail, crop) -> bool

기존 공식을 확정(characterize)하는 테스트다.
PR5 이후: max_p<=0 이면 availability_score 0, address_detail/crop None 이면 매칭 False 로
방어하므로, 예전에 '터지던' 경계도 이제 안전값을 반환한다.
"""
import pytest
# 추천 점수 함수는 app.py에서 services/ 패키지로 분리됨(리팩터링). import 경로만 갱신, 로직 동일.
from services.recommend_service import calculate_score, matches_specialty, score_components
from services.recommend_reason import recommendation_reason

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
def test_zero_max_participants_returns_zero():
    # PR5: max_p<=0 이면 availability_score를 0으로 방어 → 더 이상 터지지 않는다.
    # distance=50 → distance_score 0, spec False → score 0.0
    assert calculate_score(50, 0, 0, False) == pytest.approx(0.0)


def test_none_address_or_crop_returns_false():
    # PR5: address_detail 또는 crop 이 None 이면 매칭 False 로 방어 → 더 이상 터지지 않는다.
    assert matches_specialty(None, "쌀") is False
    assert matches_specialty("이천", None) is False


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


# --- score_components: 합이 calculate_score와 일치해야 한다(리팩터 회귀 방지) ---
def test_components_sum_equals_calculate_score():
    args = (10, 20, 5, True)
    assert sum(score_components(*args).values()) == pytest.approx(calculate_score(*args))


def test_components_keys_and_weights():
    c = score_components(0, 20, 0, True)  # 세 성분 모두 최대
    assert set(c) == {'distance', 'specialty', 'availability'}
    assert c['distance'] == pytest.approx(0.5)
    assert c['specialty'] == pytest.approx(0.3)
    assert c['availability'] == pytest.approx(0.2)


# --- recommendation_reason: 최대 기여 요소를 문구로 매핑 ---
def test_reason_distance_dominant():
    # 0km → distance 성분(0.5)이 최대 → 거리 문구 + km 표기
    r = recommendation_reason(0, 20, 20, False)
    assert "가까워요" in r and "0.0km" in r


def test_reason_specialty_dominant():
    # distance 50(→0), 만석(avail 0), 특산물 → specialty(0.3)만 양수
    assert recommendation_reason(50, 20, 20, True) == "이 지역 대표 특산물이에요"


def test_reason_availability_dominant():
    # distance 50(→0), 특산물 아님, 빈자리 → availability(0.2)만 양수
    r = recommendation_reason(50, 20, 0, False)
    assert "넉넉해요" in r and "0/20" in r


def test_reason_priority_on_tie_prefers_distance():
    # 세 성분 모두 양수여도 가중치 최대인 distance가 우선
    assert "가까워요" in recommendation_reason(0, 20, 0, True)


def test_reason_all_zero_returns_generic():
    # distance>50(클램프 0), 만석(0), 특산물 아님 → 모든 성분 0 → 일반 문구
    assert recommendation_reason(60, 20, 20, False) == "회원님께 추천하는 농장이에요"
