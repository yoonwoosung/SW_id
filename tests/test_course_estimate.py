"""services/course_estimate — 코스의 이동·체류 시간과 비용 추정.

★전부 추정이다.★ 실제 경로·요금 API 를 쓰지 않는다(대중교통 소요시간·
입장료를 주는 공개 API 가 없다). 화면에 '예상'임을 밝히고 내역을 함께 보여준다.

예전에는 '총 8시간'이 COURSE_SLOTS 첫·마지막 시각의 뺄셈이었다.
이동·체류와 무관한 상수라 실제(약 6시간)와 달랐다.
"""
import pytest

from services import course_estimate
from services.course_estimate import (
    estimate, legs, normalize_transport, travel_minutes, travel_cost, road_distance_km,
)
from common.constants import (
    COURSE_SPEED_KMH, COURSE_ROUTE_DETOUR, COURSE_STAY_MINUTES,
    COURSE_DEFAULT_TRANSPORT, COURSE_COST_MEAL,
)

ITEMS = [
    {'name': '딸기 체험', 'type': 'experience', 'lat': 36.80, 'lng': 127.30},
    {'name': '맘앤쉐프', 'type': 'restaurant', 'lat': 36.82, 'lng': 127.33},
    {'name': '박문수묘', 'type': 'attraction', 'lat': 36.85, 'lng': 127.28},
    {'name': '이도로에커피', 'type': 'cafe', 'lat': 36.79, 'lng': 127.31},
]


# ---- 이동수단 ----

def test_default_is_public_transit():
    """미설정이면 보수적으로 — 시간을 넉넉히 잡는다."""
    assert normalize_transport([]) == COURSE_DEFAULT_TRANSPORT
    assert normalize_transport(None) == 'public_transit'
    assert normalize_transport(['nature', 'chungnam']) == 'public_transit'


def test_picks_slowest_when_multiple():
    """★여러 개 고르면 가장 느린 것을 쓴다.★

    시간을 적게 잡아 놓고 실제로 더 걸리는 것보다 넉넉한 편이 덜 위험하다.
    """
    assert normalize_transport(['car', 'public_transit']) == 'public_transit'
    assert normalize_transport(['taxi', 'car']) == 'car'
    assert normalize_transport(['taxi']) == 'taxi'


# ---- 이동 시간 ----

def test_detour_correction_applied():
    """곧은 길이 없으므로 직선거리를 보정한다."""
    assert road_distance_km(10) == pytest.approx(10 * COURSE_ROUTE_DETOUR)


def test_slower_transport_takes_longer():
    assert (travel_minutes(10, 'public_transit')
            > travel_minutes(10, 'car')
            > travel_minutes(10, 'taxi'))


def test_travel_minutes_matches_speed_constant():
    expected = round(10 * COURSE_ROUTE_DETOUR / COURSE_SPEED_KMH['car'] * 60)
    assert travel_minutes(10, 'car') == expected


@pytest.mark.parametrize('bad', [None, '', '멀리', -5])
def test_bad_distance_does_not_crash(bad):
    assert travel_minutes(bad, 'car') == 0


def test_unknown_transport_gives_zero():
    assert travel_minutes(10, '헬리콥터') == 0


# ---- 구간 ----

def test_legs_are_between_consecutive_places():
    """★이전 장소 → 다음 장소 기준이다.★ 농장 기준 거리가 아니다."""
    route = legs(ITEMS)
    assert [(l['from'], l['to']) for l in route] == [
        ('딸기 체험', '맘앤쉐프'), ('맘앤쉐프', '박문수묘'), ('박문수묘', '이도로에커피')]
    assert all(l['distance_km'] > 0 for l in route)


def test_legs_skip_items_without_coords():
    items = [ITEMS[0], {'name': '좌표없음', 'type': 'restaurant'}, ITEMS[2]]
    assert legs(items) == []          # 좌표가 끊기면 구간을 잇지 않는다


def test_legs_empty_input():
    assert legs([]) == []
    assert legs(None) == []


# ---- 비용 ----

def test_transit_cost_counts_legs():
    assert travel_cost(10, 3, 'public_transit') == 1500 * 3


def test_car_cost_scales_with_distance():
    assert travel_cost(20, 3, 'car') > travel_cost(10, 3, 'car')


def test_taxi_has_base_fare():
    assert travel_cost(0, 1, 'taxi') > 0


# ---- 전체 ----

def test_estimate_sums_time_and_cost():
    result = estimate(ITEMS, 25000, 'car')
    assert result['total_minutes'] == result['move_minutes'] + result['stay_minutes']
    assert result['stay_minutes'] == sum(
        COURSE_STAY_MINUTES[i['type']] for i in ITEMS)
    assert result['total_cost'] == sum(c['amount'] for c in result['cost_breakdown'])


def test_breakdown_marks_what_is_estimated():
    """★체험비만 실제 값이고 나머지는 추정이다.★ 화면이 구분해 보여줄 수 있어야 한다."""
    result = estimate(ITEMS, 25000, 'car')
    by_label = {c['label']: c for c in result['cost_breakdown']}
    assert by_label['체험']['estimated'] is False
    assert by_label['식사']['estimated'] is True
    assert by_label['식사']['amount'] == COURSE_COST_MEAL


def test_experience_stay_flagged_as_default():
    """체험 소요시간은 컬럼이 없어 기본값이다. 화면에 밝힌다."""
    assert estimate(ITEMS, 25000, 'car')['experience_stay_is_default'] is True


def test_transport_changes_time_not_stay():
    slow = estimate(ITEMS, 25000, 'public_transit')
    fast = estimate(ITEMS, 25000, 'taxi')
    assert slow['move_minutes'] > fast['move_minutes']
    assert slow['stay_minutes'] == fast['stay_minutes']


def test_empty_items_does_not_crash():
    result = estimate([], 0, 'car')
    assert result['total_minutes'] == 0 and result['legs'] == []


# ---- 장소 종류별 단가 (2026-09-20) ----

def test_free_places_cost_nothing():
    """★공원·계곡·전망대는 0원이다.★

    예전에는 슬롯 고정값이라 공원이든 유원지든 똑같이 5,000원이었다.
    """
    from services.course_estimate import place_price
    assert place_price({'category': 'A01010900', 'type': 'attraction'}) == 0   # 계곡
    assert place_price({'category': 'A02050600', 'type': 'attraction'}) == 0   # 전망대


def test_price_scales_with_place_kind():
    from services.course_estimate import place_price
    nature = place_price({'category': 'A0101', 'type': 'attraction'})
    history = place_price({'category': 'A0201', 'type': 'attraction'})
    hands_on = place_price({'category': 'A02030100', 'type': 'attraction'})
    assert nature < history < hands_on


def test_cafe_slot_overrides_category():
    """★관광공사에 카페 분류가 없어 카페도 음식점(A05)으로 온다.★

    cat 으로만 매기면 카페가 식사값(12,000원)이 된다.
    """
    from services.course_estimate import place_price
    from common.constants import COURSE_PRICE_SLOT_FIRST
    assert place_price({'category': 'A05020100', 'type': 'cafe'}) == COURSE_PRICE_SLOT_FIRST['cafe']
    assert place_price({'category': 'A05020100', 'type': 'restaurant'}) == 12000


def test_experience_priced_separately():
    """체험비는 Experience.cost 로 따로 더한다(중복 계산 방지)."""
    from services.course_estimate import place_price
    assert place_price({'category': 'A01', 'type': 'experience'}) == 0


def test_unknown_category_falls_back():
    """CSV 는 '관광지' 한글, 카카오는 자체 분류라 cat 코드가 없다."""
    from services.course_estimate import place_price
    from common.constants import COURSE_PRICE_BY_SLOT, COURSE_PRICE_DEFAULT
    assert place_price({'category': '관광지', 'type': 'attraction'}) == COURSE_PRICE_BY_SLOT['attraction']
    assert place_price({'category': None, 'type': None}) == COURSE_PRICE_DEFAULT


# ---- 일정 → 탐색 반경 (2026-09-20) ----

def test_schedule_widens_search_radius():
    import routes.course as rc
    from common.constants import COURSE_SEARCH_RADIUS_M
    assert rc._search_radius([]) == COURSE_SEARCH_RADIUS_M
    assert rc._search_radius(['day_trip']) == 20000
    assert rc._search_radius(['one_night']) == 40000
    assert rc._search_radius(['two_night']) == 60000


def test_schedule_picks_widest_when_multiple():
    """대분류 안은 OR — 여러 개면 가장 넓게 본다."""
    import routes.course as rc
    assert rc._search_radius(['day_trip', 'two_night']) == 60000


def test_rows_scale_with_radius():
    """★반경만 넓히면 소용이 없다.★

    관광공사는 거리순으로 numOfRows 만큼 주므로, 건수를 고정하면
    반경을 60km 로 해도 '가장 가까운 30건'이 그대로 온다(실측 확인).
    """
    import routes.course as rc
    from common.constants import COURSE_MAX_ROWS
    assert rc._rows_for(10000) == 30
    assert rc._rows_for(20000) == 60
    assert rc._rows_for(40000) > rc._rows_for(20000)
    assert rc._rows_for(200000) <= COURSE_MAX_ROWS


# ---- 소요시간 → 슬롯 수 (2026-09-20) ----

def test_duration_sets_slot_count():
    import routes.course as rc
    from common.constants import COURSE_SLOTS
    assert rc._max_slots([]) is None                 # 안 고르면 기존 그대로 전부
    assert rc._max_slots(['hours_2']) == 1           # 체험만
    assert rc._max_slots(['half_day']) == 3
    assert rc._max_slots(['full_day']) == len(COURSE_SLOTS)


def test_duration_picks_longest_when_multiple():
    """대분류 안은 OR — 여러 개면 가장 긴 쪽으로 넉넉히 만든다."""
    import routes.course as rc
    assert rc._max_slots(['hours_2', 'full_day']) == rc._max_slots(['full_day'])


def test_hidden_duration_codes_are_not_claimed_as_applied():
    """★슬롯 수를 못 정하는 선택지를 '반영했다'고 하면 거짓말이다.★

    '1시간 이내'·'기타'는 화면에서 감췄지만 직접 호출은 막을 수 없다.
    """
    import routes.course as rc
    assert rc._max_slots(['under_2h']) is None
    assert rc._filter_role('under_2h') is None
    assert rc._filter_role('duration_hours_other') is None
    assert rc._filter_role('half_day') is not None


# ---- 조건 반영 표기 (2026-09-20) ----

def test_transport_is_reported_as_applied():
    """★"찾지 못했습니다"는 사실과 다르다.★

    자가용·대중교통·택시는 이동시간·교통비 추정에 실제로 쓰인다.
    """
    import routes.course as rc
    items = [{'type': 'attraction', 'name': 'A', 'match_score': 0.4}]
    report = rc._condition_report(['car', 'public_transit', 'taxi'], {}, items)
    assert report['ignored'] == []
    roles = {a['label']: a.get('role') for a in report['applied']}
    assert roles == {'자가용': rc._FILTER_ROLE['transport'],
                     '대중교통': rc._FILTER_ROLE['transport'],
                     '택시': rc._FILTER_ROLE['transport']}


def test_list_only_conditions_say_so():
    """체험 목록만 거르는 조건은 그렇다고 밝힌다.

    와이파이·무농약·유기농인증·노펫존은 Experience 컬럼으로 실제 판정되지만
    코스 장소에는 쓰이지 않는다. 밝히지 않으면 '반영 안 됨'으로 보인다.
    """
    import routes.course as rc
    items = [{'type': 'attraction', 'name': 'A', 'match_score': 0.4}]
    codes = ['wifi', 'pesticide_free', 'organic', 'pet_not_allowed']
    report = rc._condition_report(codes, {}, items)
    assert report['ignored'] == []
    for entry in report['applied']:
        assert entry['role'] == rc._LIST_ONLY_ROLE, entry


def test_scored_conditions_keep_percent_not_role():
    """★기존 동작 유지.★ 점수로 반영되는 조건은 비율 그대로 보여준다."""
    import routes.course as rc
    items = [{'type': 'attraction', 'name': 'A', 'match_score': 0.4}]
    report = rc._condition_report(['nature'], {}, items)
    entry = next(a for a in report['applied'] if a['code'] == 'nature')
    assert entry['percent'] == 100.0
    assert 'role' not in entry


def test_no_visible_condition_is_silently_ignored():
    """★전수 확인.★ 고른 조건이 조용히 무시되면 "조건이 안 먹는다"로만 보인다.

    반영되지 않는 조건은 반드시 ★이유★를 달고 나와야 한다.
    """
    import routes.course as rc
    from common.search_categories import visible_categories
    from services import place_score

    def leaves(nodes):
        for node in nodes:
            if node.get('children'):
                yield from leaves(node['children'])
            else:
                yield node['code']

    codes = list(leaves(visible_categories()))
    report = rc._condition_report(codes, {}, [{'type': 'attraction', 'name': 'A'}])
    reported = ({a['code'] for a in report['applied']}
                | {i['code'] for i in report['ignored']})
    assert set(codes) - reported == set()
    assert all(i['reason'] for i in report['ignored'])


def test_filter_only_conditions_do_not_warn_fallback():
    """★거짓 경고를 막는다.★ (배포 서버에서 재현한 버그)

    예산대·일정·소요시간·교통수단은 장소에 점수를 매기지 않아 match_score 가
    없다. 이걸 폴백으로 세면 잘 동작하는데도 "조건에 맞는 장소가 근처에
    없어 가까운 순으로 구성했습니다"가 뜬다.
    """
    import routes.course as rc
    items = [{'type': 'attraction', 'name': 'A'}]      # 점수 없음
    for codes in (['taxi'], ['half_day'], ['day_trip'], ['course_under_30k']):
        assert rc._condition_report(codes, {}, items)['fell_back'] is False, codes


def test_scored_condition_with_no_match_still_warns():
    """★기존 동작 유지.★ 점수 조건이 하나도 안 맞으면 폴백 경고는 그대로다."""
    import routes.course as rc
    items = [{'type': 'attraction', 'name': 'A', 'match_score': 0.0}]
    assert rc._condition_report(['healing'], {}, items)['fell_back'] is True
    # 필터 조건을 같이 골라도 점수 조건이 안 맞았으면 경고는 유지된다.
    assert rc._condition_report(['healing', 'taxi'], {}, items)['fell_back'] is True


def test_matched_scored_condition_does_not_warn():
    import routes.course as rc
    items = [{'type': 'attraction', 'name': 'A', 'match_score': 0.4}]
    assert rc._condition_report(['healing'], {}, items)['fell_back'] is False


# ---- 카페 슬롯 정상화 (2026-09-20) ----

def _food(name, cat):
    return {'name': name, 'category': cat, 'lat': 37.3, 'lng': 126.8}


def test_cafe_slot_keeps_only_cafes():
    """★카페 자리에 김밥집이 오면 안 된다.★

    카페 슬롯은 맛집과 같은 contentType(39)이라 지금까지 '가까운 음식점
    두 번째'를 집었다(실측: 안산 좋은날 김밥, 천안 신은수참병천순대집).
    """
    import routes.course as rc
    from common.constants import TOUR_CAT_CAFE
    places = [_food('좋은날 김밥', 'A05020100'), _food('데미안', TOUR_CAT_CAFE),
              _food('오복당', 'A05020400'), _food('묵커피바', TOUR_CAT_CAFE)]
    assert [p['name'] for p in rc._cafes_only(places)] == ['데미안', '묵커피바']


def test_cafe_slot_falls_back_when_no_cafe():
    """★한 곳도 없으면 좁히지 않는다.★ 빈 슬롯보다 음식점이라도 낫다."""
    import routes.course as rc
    places = [_food('좋은날 김밥', 'A05020100'), _food('오복당', 'A05020400')]
    assert rc._cafes_only(places) == places


def test_cafe_slot_handles_empty_and_missing_category():
    import routes.course as rc
    assert rc._cafes_only([]) == []
    assert rc._cafes_only(None) == []
    no_cat = [{'name': '카카오카페', 'lat': 37.3, 'lng': 126.8}]
    assert rc._cafes_only(no_cat) == no_cat      # 분류가 없으면 거르지 않는다


# ---- 동반구성 카페를 카페 슬롯으로 (2026-09-20) ----

class _Exp:
    lat, lng = 37.3261, 126.8


def test_companion_cafes_go_to_the_cafe_slot(monkeypatch):
    """★동반유형이 17:00 을 바꾸게 한다.★

    예전에는 카페까지 전부 관광 슬롯에 넣었다 — 카페 슬롯이 아무 음식점이나
    받던 때라 관광 자리가 카페로 채워질까 봐 막아 둔 것이었다.
    """
    import routes.course as rc
    from common.constants import TOUR_CAT_CAFE, TOUR_CONTENT_TYPE_RESTAURANT

    def fake_search_many(queries, lat, lng, radius):
        return {
            '카페': [{'name': '데미안', 'category': '음식점 > 카페 > 커피전문점',
                     'lat': 37.33, 'lng': 126.81}],
            '박물관': [{'name': '안산시립박물관', 'category': '문화,예술 > 박물관',
                       'lat': 37.34, 'lng': 126.82}],
        }
    monkeypatch.setattr(rc.kakao_place, 'search_many', fake_search_many)

    by_slot, names = rc._companion_places(_Exp(), ['solo'])
    assert [p['name'] for p in by_slot['cafe']] == ['데미안']
    assert [p['name'] for p in by_slot['attraction']] == ['안산시립박물관']
    # 카페 슬롯이 분류 코드로 거르므로 같은 코드를 달아 줘야 살아남는다.
    assert by_slot['cafe'][0]['category'] == TOUR_CAT_CAFE
    assert by_slot['cafe'][0]['content_type_id'] == TOUR_CONTENT_TYPE_RESTAURANT
    assert rc._cafes_only(by_slot['cafe']) == by_slot['cafe']
    # 관광 슬롯으로 가는 곳은 카카오 분류를 그대로 둔다.
    assert by_slot['attraction'][0]['category'] == '문화,예술 > 박물관'
    assert '데미안' in names['solo']


def test_companion_places_empty_when_not_selected():
    """★기존 동작 유지.★ 안 고르면 카카오를 부르지 않는다."""
    import routes.course as rc
    by_slot, names = rc._companion_places(_Exp(), ['healing'])
    assert by_slot == [] or by_slot == {} or not any(by_slot.values())
    assert names == {}


# ---- 레포츠(28) 후보: 액티브를 고른 경우에만 (2026-09-20) ----

def test_leisure_places_only_when_active_selected(monkeypatch):
    """★항상 더하면 기본 코스가 나빠진다.★

    조건 없이 볼 때 골프장·캠핑장이 관광 슬롯 상위에 올라온다.
    반려견·주차와 같게 '고른 경우에만' 부른다.
    """
    import routes.course as rc
    calls = []

    def fake_fetch(lat, lng, radius, content_type, rows):
        calls.append(content_type)
        return [{'name': '천안 상록골프장', 'category': 'A03020200',
                 'lat': 36.8, 'lng': 127.2}]
    monkeypatch.setattr(rc.tour_api, 'find_nearby_places', fake_fetch)

    assert rc._leisure_places(_Exp(), ['healing']) == []
    assert rc._leisure_places(_Exp(), []) == []
    assert calls == []                      # 안 고르면 아예 부르지 않는다

    found = rc._leisure_places(_Exp(), ['active'])
    assert [p['name'] for p in found] == ['천안 상록골프장']
    from common.constants import TOUR_CONTENT_TYPE_LEISURE
    assert calls == [TOUR_CONTENT_TYPE_LEISURE]


def test_leisure_failure_does_not_break_course(monkeypatch):
    """★보강 실패가 코스 생성을 막으면 안 된다.★"""
    import routes.course as rc

    def boom(*a, **kw):
        raise RuntimeError('관광공사 장애')
    monkeypatch.setattr(rc.tour_api, 'find_nearby_places', boom)
    assert rc._leisure_places(_Exp(), ['active']) == []


def test_leisure_uses_the_requested_radius(monkeypatch):
    """일정 조건으로 넓힌 반경을 그대로 쓴다(조회 건수도 함께 늘어난다)."""
    import routes.course as rc
    seen = {}

    def fake_fetch(lat, lng, radius, content_type, rows):
        seen['radius'], seen['rows'] = radius, rows
        return []
    monkeypatch.setattr(rc.tour_api, 'find_nearby_places', fake_fetch)
    rc._leisure_places(_Exp(), ['active'], 40000)
    assert seen['radius'] == 40000
    assert seen['rows'] == rc._rows_for(40000)


# ---- 조건 0건이면 반경 자동 확대 (2026-09-20) ----

def test_nothing_matches_detects_zero_hits():
    import routes.course as rc
    scorer = lambda p: 1.0 if p.get('category', '').startswith('A0202') else 0.0
    miss = {'attraction': [{'category': 'A0101'}, {'category': 'A0201'}]}
    hit = {'attraction': [{'category': 'A0101'}, {'category': 'A02020700'}]}
    assert rc._nothing_matches(scorer, miss) is True
    assert rc._nothing_matches(scorer, hit) is False
    # 조건을 안 골랐으면(scorer 없음) 넓히지 않는다 — 기존 거리순 그대로.
    assert rc._nothing_matches(None, miss) is False


def test_nothing_matches_survives_broken_scorer():
    """★점수 계산이 터져도 코스는 만들어져야 한다.★"""
    import routes.course as rc

    def boom(place):
        raise RuntimeError('점수 계산 실패')
    assert rc._nothing_matches(boom, {'attraction': [{'category': 'A01'}]}) is True


def test_widen_uses_retry_radius_and_more_rows(monkeypatch):
    """★반경만 넓히면 소용없다.★ 조회 건수도 함께 늘어나야 한다."""
    import routes.course as rc
    from common.constants import COURSE_CONDITION_RETRY_RADIUS_M
    seen = {}

    def fake_fetch(experience, content_type, add_chungnam=False, radius_m=None):
        seen['radius'] = radius_m
        return [{'name': '보련마을', 'category': 'A02030100', 'lat': 36.9, 'lng': 127.4}]
    monkeypatch.setattr(rc, '_fetch_places', fake_fetch)
    monkeypatch.setattr(rc, '_leisure_places', lambda *a, **kw: [])

    out = rc._widen_attraction(_Exp(), ['harvest'], {'attraction': []})
    assert seen['radius'] == COURSE_CONDITION_RETRY_RADIUS_M
    assert rc._rows_for(COURSE_CONDITION_RETRY_RADIUS_M) > rc._rows_for(10000)
    assert [p['name'] for p in out['attraction']] == ['보련마을']


def test_widen_keeps_existing_candidates(monkeypatch):
    """★기존 후보가 사라지면 안 된다.★ 넓힌 결과는 더하는 것이다."""
    import routes.course as rc
    monkeypatch.setattr(rc, '_fetch_places',
                        lambda *a, **kw: [{'name': '새 장소', 'category': 'A02030100',
                                           'lat': 36.9, 'lng': 127.4}])
    monkeypatch.setattr(rc, '_leisure_places', lambda *a, **kw: [])
    before = [{'name': '기존 장소', 'category': 'A0201', 'lat': 36.8, 'lng': 127.3}]
    out = rc._widen_attraction(_Exp(), [], {'attraction': list(before)})
    names = [p['name'] for p in out['attraction']]
    assert '기존 장소' in names and '새 장소' in names


def test_widen_survives_fetch_failure(monkeypatch):
    """★넓히기 실패가 코스 생성을 막으면 안 된다.★ 원래 후보를 그대로 돌려준다."""
    import routes.course as rc

    def boom(*a, **kw):
        raise RuntimeError('관광공사 장애')
    monkeypatch.setattr(rc, '_fetch_places', boom)
    before = {'attraction': [{'name': '기존 장소', 'category': 'A0201'}]}
    assert rc._widen_attraction(_Exp(), [], before) == before


# ---- 반려견 후보를 슬롯 종류에 맞게 나눈다 (2026-09-20) ----

def test_pet_places_split_by_slot(monkeypatch):
    """★카페 시간에 중식당이 오면 안 된다.★

    예전에는 애견동반 결과를 맛집·카페 두 슬롯에 통째로 넣어, 안산에서
    애견동반 카페(컴포즈커피)가 12:30 점심 자리에 오고 중식당이 17:00
    카페 자리에 올 수 있었다.
    """
    import routes.course as rc
    from common.constants import TOUR_CAT_CAFE

    monkeypatch.setattr(rc.pet_travel_api, 'find_pet_facilities', lambda *a, **kw: [])
    monkeypatch.setattr(rc.kakao_place, 'search', lambda *a, **kw: [
        {'name': '컴포즈커피 안산원곡동점', 'category': '음식점 > 카페 > 커피전문점'},
        {'name': '오복당 고잔점', 'category': '음식점 > 중식 > 중국요리'},
        {'name': '뽁식당 고잔점', 'category': '음식점 > 양식'},
    ])
    by_slot, names = rc._pet_places(_Exp(), ['pet_allowed'])
    assert [p['name'] for p in by_slot['cafe']] == ['컴포즈커피 안산원곡동점']
    assert [p['name'] for p in by_slot['restaurant']] == ['오복당 고잔점', '뽁식당 고잔점']
    # 카페 슬롯이 분류 코드로 거르므로 살아남아야 한다.
    assert by_slot['cafe'][0]['category'] == TOUR_CAT_CAFE
    assert rc._cafes_only(by_slot['cafe']) == by_slot['cafe']
    # 판정용 이름 집합은 슬롯과 무관하게 전부 담는다.
    assert len(names) == 3


def test_pet_places_skipped_without_pet_condition():
    """★기존 동작 유지.★ 안 고르면 빈 묶음."""
    import routes.course as rc
    assert rc._pet_places(_Exp(), ['healing']) == ({}, set())


def test_pet_cafe_missing_is_reported():
    """★조용히 넘어가면 강아지를 데리고 갔다가 못 들어간다.★"""
    import routes.course as rc
    items = [{'type': 'experience'}, {'type': 'cafe', 'name': '데미안'}]

    # 애견동반 카페를 못 찾았다 → 알린다
    assert rc._pet_cafe_missing(['pet_allowed'], {'restaurant': [{'name': '오복당'}]}, items) is True
    assert rc._pet_cafe_missing(['pet_allowed'], {}, items) is True
    # 찾았다 → 알릴 것이 없다
    assert rc._pet_cafe_missing(['pet_allowed'], {'cafe': [{'name': '컴포즈커피'}]}, items) is False
    # 반려견을 안 골랐다 → 해당 없음
    assert rc._pet_cafe_missing(['healing'], {}, items) is False
    # 카페 슬롯 자체가 없다(소요시간을 짧게 골랐다) → 알릴 것이 없다
    assert rc._pet_cafe_missing(['pet_allowed'], {}, [{'type': 'experience'}]) is False


def test_pet_cafe_missing_flows_into_the_report():
    import routes.course as rc
    items = [{'type': 'cafe', 'name': '데미안'}]
    assert rc._condition_report(['pet_allowed'], {}, items,
                                pet_cafe_missing=True)['pet_cafe_missing'] is True
    assert rc._condition_report(['pet_allowed'], {}, items)['pet_cafe_missing'] is False
