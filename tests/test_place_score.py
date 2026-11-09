"""services/place_score — 여행 조건으로 코스 장소에 점수를 매긴다.

지금까지 조건은 체험 목록만 걸렀고 코스 장소 선정에는 쓰이지 않아,
조건을 바꿔도 코스가 똑같았다.
"""
import pytest

from services import place_score
from services.place_score import (
    ordered_weights, build_scorer, build_api_sets, matches, judgeable, score_place,
)
from common.constants import COURSE_CONDITION_WEIGHTS, COURSE_CONDITION_TAIL_WEIGHT

NATURE = {'name': '천안북면계곡', 'category': 'A01010900', 'content_type_id': 12}
HISTORY = {'name': '박문수묘', 'category': 'A02010700', 'content_type_id': 12}
FOOD = {'name': '박순자 아우내순대', 'category': 'A05020100', 'content_type_id': 39}
SPORTS = {'name': '천안카약장', 'category': 'A03020200', 'content_type_id': 28}


# ---- 순서 가중치 ----

def test_first_choice_dominates():
    """★1순위가 지배적이어야 '내가 고른 게 반영됐다'고 느껴진다.★"""
    w = ordered_weights(['a', 'b', 'c', 'd'])
    assert w['a'] > w['b'] > w['c'] > w['d']
    assert w['a'] > 0.4


def test_weights_sum_to_one():
    for n in (1, 2, 3, 4, 5, 8):
        w = ordered_weights([str(i) for i in range(n)])
        assert sum(w.values()) == pytest.approx(1.0), n


def test_single_condition_takes_everything():
    assert ordered_weights(['only']) == {'only': 1.0}


def test_fifth_and_beyond_share_the_tail():
    """5순위 이하는 남은 몫을 균등하게 나눈다."""
    w = ordered_weights(list('abcdef'))
    assert w['e'] == pytest.approx(w['f'])
    assert w['e'] < w['d']
    # 정규화 전 비율이 상수 그대로인지
    assert w['a'] == pytest.approx(COURSE_CONDITION_WEIGHTS[0])
    assert w['e'] == pytest.approx(COURSE_CONDITION_TAIL_WEIGHT / 2)


def test_empty_selection():
    assert ordered_weights([]) == {}


def test_order_changes_weight():
    """★같은 조건이라도 고른 순서가 다르면 가중치가 다르다.★"""
    first = ordered_weights(['tradition', 'nature'])
    second = ordered_weights(['nature', 'tradition'])
    assert first['tradition'] > first['nature']
    assert second['nature'] > second['tradition']


# ---- 분류 코드 판정 ----

# 2026-09-20 재매핑: 힐링·수확·자연생태가 전부 cat1=A01 이던 것을
# cat2·cat3 로 내려 겹치지 않게 나눴다.
@pytest.mark.parametrize('place,code,expected', [
    (NATURE, 'nature', True), (NATURE, 'healing', False), (NATURE, 'tradition', False),
    (HISTORY, 'tradition', True), (HISTORY, 'craft', False), (HISTORY, 'nature', False),
    (FOOD, 'food', True), (FOOD, 'nature', False),
    (SPORTS, 'active', True),
    # 액티비티는 cat 규칙을 두지 않는다(카카오 전용) — 분류 코드로는 안 걸린다
    (SPORTS, 'kayak', False), (SPORTS, 'horse_riding', False),
])
def test_category_rules(place, code, expected):
    assert matches(place, code) is expected


def test_food_matched_by_content_type():
    """먹거리는 cat 이 아니라 contenttypeid=39 로 본다."""
    assert matches({'name': '무명식당', 'category': '', 'content_type_id': 39}, 'food') is True


def test_season_matched_by_name_keyword():
    """계절·제철은 분류 코드가 없어 장소 이름으로 본다."""
    assert matches({'name': '딸기체험농원', 'category': 'A01'}, 'spring_strawberry') is True
    assert matches({'name': '박문수묘', 'category': 'A02'}, 'spring_strawberry') is False


def test_unknown_code_never_matches():
    assert matches(NATURE, 'solo') is False
    assert matches(NATURE, 'party_1') is False


# ---- 전용 API 조건 ----

def test_barrier_free_needs_api_result():
    """API 결과가 없으면 판정 불가 — 가중치를 차지한 채 아무 일도 하면 안 된다."""
    assert judgeable('barrier_free') is False
    sets = build_api_sets(barrier_free_places=[{'name': '박순자 아우내순대'}])
    assert judgeable('barrier_free', sets) is True
    assert matches(FOOD, 'barrier_free', sets) is True
    assert matches(NATURE, 'barrier_free', sets) is False


def test_pet_conditions_share_one_api_result():
    sets = build_api_sets(pet_places=[{'name': '천안북면계곡'}])
    for code in ('pet_allowed', 'dog_small', 'dog_medium', 'dog_large'):
        assert judgeable(code, sets) is True
        assert matches(NATURE, code, sets) is True


def test_empty_api_result_is_not_judgeable():
    """★반려동물 API 가 죽어 있으면 반려견 조건은 빠진다.★"""
    sets = build_api_sets(barrier_free_places=[], pet_places=[])
    assert judgeable('dog_medium', sets) is False
    assert judgeable('barrier_free', sets) is False


def test_name_spacing_ignored_when_matching_api():
    sets = build_api_sets(barrier_free_places=[{'name': '박순자아우내순대'}])
    assert matches(FOOD, 'barrier_free', sets) is True    # 원본은 '박순자 아우내순대'


# ---- 점수·재분배 ----

def test_unjudgeable_condition_redistributes_weight():
    """★판정 불가 조건은 빠지고 남은 조건끼리 비중을 다시 나눈다.★

    반려견을 1순위로 골라도 API 가 죽어 있으면 그 40% 가 다음 조건으로 간다.
    """
    scorer = build_scorer(['dog_medium', 'tradition'], build_api_sets())
    assert scorer(HISTORY) == pytest.approx(1.0)   # 전통이 유일한 판정 조건 → 전부 차지


def test_scorer_is_none_without_usable_conditions():
    """쓸 조건이 하나도 없으면 None — 호출부가 기존 거리순을 쓴다."""
    assert build_scorer([]) is None
    # party_1 은 2026-09-20 부터 판정 가능해졌다(역사관광지 기준).
    assert build_scorer(['solo', 'day_trip']) is None
    assert build_scorer(['dog_medium'], build_api_sets()) is None


def test_score_adds_up_matched_weights():
    """여러 조건을 충족하면 가중치가 더해진다."""
    park = {'name': '태조산 공원', 'category': 'A02020700', 'content_type_id': 12}
    scorer = build_scorer(['healing', 'tradition'])
    assert scorer(park) == pytest.approx(ordered_weights(['healing', 'tradition'])['healing'])
    assert scorer(HISTORY) == pytest.approx(ordered_weights(['healing', 'tradition'])['tradition'])
    assert scorer(NATURE) == pytest.approx(0.0)


def test_score_is_zero_without_weights():
    assert score_place(NATURE, {}) == 0.0


# ---- 분류 코드 재매핑 (2026-09-20) ----

def test_no_duplicate_rules_among_core_conditions():
    """★한 코드를 두 조건이 함께 쓰면 안 된다.★

    예전에는 힐링·수확·자연생태가 전부 cat1=A01 이라 서로 다른 조건인데
    같은 결과가 나왔다. "조건을 바꿔도 코스가 안 바뀐다"의 직접 원인이었다.
    액티비티 5개는 관광공사 코드로 구분이 불가능해 제외한다(감춘 상태).
    """
    from common.constants import COURSE_PLACE_RULES
    activity = {'horse_riding', 'hiking', 'cycling', 'kayak', 'fishing'}
    core = {k: str(v) for k, v in COURSE_PLACE_RULES.items() if k not in activity}
    assert len(set(core.values())) == len(core), core


@pytest.mark.parametrize('place,expected', [
    ({'name': '천안북면계곡', 'category': 'A01010900'}, 'nature'),
    ({'name': '박문수묘', 'category': 'A02010700'}, 'tradition'),
    ({'name': '태조산 공원', 'category': 'A02020700'}, 'healing'),
    ({'name': '보련마을', 'category': 'A02030100'}, 'harvest'),
    ({'name': '충남안전체험관', 'category': 'A02030400'}, 'educational'),
    ({'name': '흔들전망대', 'category': 'A02050600'}, 'photo'),
    ({'name': '영산강문화관', 'category': 'A02040800'}, 'craft'),
    ({'name': '울주 구량리 은행나무', 'category': 'A01020100'}, 'animal'),
])
def test_each_place_matches_exactly_one_core_condition(place, expected):
    """실제 응답값으로 만든 장소가 의도한 조건 하나에만 걸린다."""
    core = ('nature', 'harvest', 'craft', 'animal',
            'healing', 'educational', 'tradition', 'photo')
    hit = [c for c in core if matches(place, c)]
    assert hit == [expected], (place['name'], hit)


def test_cat3_prefix_is_supported():
    """cat3 수준 규칙이 동작해야 한다(수확·교육적이 cat3 를 쓴다)."""
    assert matches({'name': 'x', 'category': 'A02030100'}, 'harvest') is True
    assert matches({'name': 'x', 'category': 'A02030400'}, 'harvest') is False


# ---- 지역: 장소 주소로 판정 (2026-09-20) ----

CHEONAN_PLACE = {'name': '천안북면계곡', 'address': '충청남도 천안시 동남구 북면',
                 'category': 'A01010900', 'content_type_id': 12}
NAJU_PLACE = {'name': '완사천', 'address': '전라남도 나주시 송월동',
              'category': 'A02010700', 'content_type_id': 12}


@pytest.mark.parametrize('code,expected', [
    ('cheonan', True), ('chungnam', True), ('naju', False), ('jeonnam', False),
])
def test_region_matched_by_place_address(code, expected):
    """★지역은 사용자가 가장 많이 만지는 조건인데 코스에 반영되지 않았다.★"""
    assert matches(CHEONAN_PLACE, code) is expected


def test_region_uses_same_keywords_as_experience_filter():
    """체험 목록 필터와 같은 키워드 표를 쓴다(정의가 두 벌이 되지 않게)."""
    from common.search_categories import REGION_ADDRESS_KEYWORDS
    from services.category_match import _has_region

    class FakeExp:
        address_detail = NAJU_PLACE['address']

    assert matches(NAJU_PLACE, 'naju') is True
    assert _has_region(['naju'], FakeExp()) is True
    assert 'naju' in REGION_ADDRESS_KEYWORDS


def test_region_is_judgeable_without_api():
    """추가 API 호출 없이 판정된다."""
    assert judgeable('chungnam') is True
    assert build_scorer(['chungnam']) is not None


def test_place_without_address_never_matches_region():
    assert matches({'name': 'x', 'address': '', 'category': 'A01'}, 'chungnam') is False
    assert matches({'name': 'x', 'category': 'A01'}, 'chungnam') is False


def test_metro_group_matches_any_metro_place():
    seoul = {'name': 'x', 'address': '서울특별시 강남구', 'category': 'A02'}
    assert matches(seoul, 'metro') is True
    assert matches(CHEONAN_PLACE, 'metro') is False


def test_region_scores_alongside_other_conditions():
    """지역과 분위기를 함께 고르면 둘 다 점수에 들어간다."""
    scorer = build_scorer(['chungnam', 'nature'])
    assert scorer(CHEONAN_PLACE) == pytest.approx(1.0)      # 충남 + 자연 둘 다
    assert scorer(NAJU_PLACE) == pytest.approx(0.0)


# ---- 반영 비율 (화면 표시용) ----

def test_applied_weights_match_actual_scoring():
    """★화면에 보이는 %와 실제 계산이 같아야 한다.★"""
    from services.place_score import applied_weights
    codes = ['healing', 'tradition']
    shown = applied_weights(codes)
    actual = ordered_weights(codes)
    for code, percent in shown.items():
        assert percent == pytest.approx(round(actual[code] * 100, 1))
    assert sum(shown.values()) == pytest.approx(100.0)


def test_applied_weights_drop_unjudgeable():
    """판정 불가 조건은 빠지고 남은 것끼리 다시 나눈다."""
    from services.place_score import applied_weights
    assert applied_weights(['course_under_30k', 'healing']) == {'healing': 100.0}
    assert applied_weights(['course_under_30k']) == {}


def test_usable_codes_preserve_order():
    from services.place_score import usable_codes
    assert usable_codes(['course_under_30k', 'healing', 'tradition']) == ['healing', 'tradition']


# ---- 인원수 (2026-09-20) ----

HISTORY_PLACE = {'name': '박문수묘', 'category': 'A02010700', 'content_type_id': 12}
RESORT_PLACE = {'name': '천안상록리조트', 'category': 'A02020200', 'content_type_id': 12}


def test_party_1_prefers_quiet_places():
    """혼자는 조용히 둘러보는 곳(역사관광지)."""
    assert matches(HISTORY_PLACE, 'party_1') is True
    assert matches(RESORT_PLACE, 'party_1') is False


def test_party_1_needs_no_parking_lookup():
    """주차 조회 없이도 판정된다(추가 호출 0회)."""
    assert judgeable('party_1') is True


def test_party_3_4_needs_parking_result():
    """주차가 있는 곳에 가점. 주차장 조회 결과가 없으면 판정 불가."""
    assert judgeable('party_3_4') is False
    sets = build_api_sets(facility_names={'parking': {'박문수묘'}})
    assert judgeable('party_3_4', sets) is True
    assert matches(HISTORY_PLACE, 'party_3_4', sets) is True
    assert matches(RESORT_PLACE, 'party_3_4', sets) is False


def test_party_5plus_requires_parking_and_space():
    """★5명 이상은 주차가 없으면 탈락한다.★ 넓은 곳(휴양·자연)이어야 한다."""
    with_parking = build_api_sets(facility_names={'parking': {'천안상록리조트', '박문수묘'}})
    assert matches(RESORT_PLACE, 'party_5plus', with_parking) is True    # 주차 O + 휴양지
    assert matches(HISTORY_PLACE, 'party_5plus', with_parking) is False  # 주차 O 이나 역사관광지
    no_parking = build_api_sets(facility_names={'parking': {'다른곳'}})
    assert matches(RESORT_PLACE, 'party_5plus', no_parking) is False     # 주차 X


def test_party_2_is_not_judged():
    """★'2명'은 제한이 없어 판정하지 않는다.★

    가중치를 차지한 채 모든 장소를 통과시키면 다른 조건의 몫만 줄인다.
    """
    assert judgeable('party_2') is False
    assert matches(HISTORY_PLACE, 'party_2') is False


# ---- 화장실·수유실 (2026-09-20) ----

def test_csv_facilities_take_priority():
    """★CSV 장소는 실제 데이터(화장실 651건)가 있어 그쪽을 먼저 본다.★"""
    have = {'name': 'x', 'category': '관광지', 'facilities': '주차장+화장실'}
    only_parking = {'name': 'y', 'category': '관광지', 'facilities': '주차장'}
    assert matches(have, 'restroom') is True
    assert matches(only_parking, 'restroom') is False


def test_amenity_defaults_by_place_kind():
    assert matches({'name': 'x', 'category': 'A01010900'}, 'restroom') is True    # 계곡
    assert matches({'name': 'x', 'category': 'A02030100'}, 'nursing_room') is True  # 체험관
    assert matches({'name': 'x', 'category': 'A05020100'}, 'restroom') is True    # 음식점


def test_uncertain_kinds_are_not_judged():
    """★확실하지 않은 종류는 판정하지 않는다.★ 억지로 붙이면 틀린 정보다."""
    for category in ('A02010700', 'A02050600'):   # 문화재 · 전망대
        assert matches({'name': 'x', 'category': category}, 'restroom') is False
        assert matches({'name': 'x', 'category': category}, 'nursing_room') is False


def test_nursing_room_rarer_than_restroom():
    """수유실은 화장실보다 드물다 — 체험관에만 있다고 본다."""
    park = {'name': 'x', 'category': 'A01010900'}
    assert matches(park, 'restroom') is True
    assert matches(park, 'nursing_room') is False


def test_amenity_needs_no_api_call():
    assert judgeable('restroom') is True
    assert judgeable('nursing_room') is True
