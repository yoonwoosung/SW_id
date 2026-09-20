"""external/kakao_place — 카카오 로컬 키워드 검색.

관광공사 분류 코드로 구분할 수 없는 조건을 채운다.
승마·등산·자전거가 관광공사에서는 전부 육상 레포츠(A0303) 한 코드라
서로 나눌 수 없는데, 카카오는 category_name 이 세분돼 있다.
"""
import pytest

from external import kakao_place
from common.constants import COURSE_ACTIVITY_KAKAO


@pytest.fixture(autouse=True)
def _no_cache(monkeypatch):
    """파일 캐시를 타지 않게 해 호출부 로직만 본다."""
    monkeypatch.setattr(kakao_place.tour_cache, 'get', lambda key: None)
    monkeypatch.setattr(kakao_place.tour_cache, 'set', lambda key, value: None)


def _fake_response(documents):
    class R:
        def raise_for_status(self): pass
        def json(self): return {'documents': documents}
    return R()


def test_search_maps_fields(monkeypatch):
    monkeypatch.setenv('KAKAO_API_KEY', 'k')
    monkeypatch.setattr(kakao_place.requests, 'get', lambda *a, **kw: _fake_response([
        {'place_name': '화랑승마목장', 'category_name': '스포츠,레저 > 승마 > 승마장',
         'road_address_name': '충남 천안시 x', 'x': '127.3', 'y': '36.8'},
    ]))
    places = kakao_place.search('승마장', 36.8, 127.3)
    assert places[0]['name'] == '화랑승마목장'
    assert '승마' in places[0]['category']
    assert places[0]['address'] == '충남 천안시 x'


def test_category_hint_filters_wrong_matches(monkeypatch):
    """★키워드만 믿으면 엉뚱한 게 섞인다.★

    '낚시터'로 찾으면 횟집이, '등산로'로 찾으면 주차장이 걸린다.
    """
    monkeypatch.setenv('KAKAO_API_KEY', 'k')
    monkeypatch.setattr(kakao_place.requests, 'get', lambda *a, **kw: _fake_response([
        {'place_name': '행암낚시터', 'category_name': '스포츠,레저 > 낚시 > 낚시터',
         'road_address_name': 'a', 'x': '1', 'y': '2'},
        {'place_name': '바다횟집', 'category_name': '음식점 > 한식 > 해물,생선',
         'road_address_name': 'b', 'x': '1', 'y': '2'},
    ]))
    names = kakao_place.search_names('낚시터', 36.8, 127.3, category_hint='낚시')
    assert names == {'행암낚시터'}


def test_names_ignore_spacing(monkeypatch):
    monkeypatch.setenv('KAKAO_API_KEY', 'k')
    monkeypatch.setattr(kakao_place.requests, 'get', lambda *a, **kw: _fake_response([
        {'place_name': '독립기념관 천안시 승마연합회', 'category_name': '스포츠,레저 > 승마',
         'road_address_name': 'a', 'x': '1', 'y': '2'},
    ]))
    assert kakao_place.search_names('승마장', 36.8, 127.3) == {'독립기념관천안시승마연합회'}


def test_missing_key_returns_empty(monkeypatch):
    """★키가 없어도 코스 생성은 그대로 동작해야 한다.★"""
    monkeypatch.delenv('KAKAO_API_KEY', raising=False)
    monkeypatch.setattr(kakao_place, '_api_key', lambda: None)
    assert kakao_place.search('승마장', 36.8, 127.3) == []


def test_network_error_returns_empty(monkeypatch):
    monkeypatch.setenv('KAKAO_API_KEY', 'k')
    def boom(*a, **kw):
        raise RuntimeError('네트워크 장애')
    monkeypatch.setattr(kakao_place.requests, 'get', boom)
    assert kakao_place.search('승마장', 36.8, 127.3) == []


def test_radius_capped():
    """카카오 허용 최대 반경을 넘기지 않는다."""
    assert kakao_place.MAX_RADIUS_M == 20000


def test_every_activity_has_keyword_and_hint():
    """액티비티 5개 모두 검색어와 카테고리 힌트가 있어야 한다."""
    assert set(COURSE_ACTIVITY_KAKAO) == {
        'horse_riding', 'fishing', 'hiking', 'cycling', 'kayak'}
    for code, rule in COURSE_ACTIVITY_KAKAO.items():
        keyword, hint = rule
        assert keyword and hint, code


def test_activity_codes_are_judgeable_only_with_results():
    """★검색 결과가 없으면 판정 불가로 빠진다.★ 가중치를 들고 아무 일도 하면 안 된다."""
    from services.place_score import judgeable, build_api_sets
    assert judgeable('horse_riding') is False
    sets = build_api_sets(activity_names={'horse_riding': {'화랑승마목장'}})
    assert judgeable('horse_riding', sets) is True


def test_activity_matches_place_by_name():
    from services.place_score import matches, build_api_sets
    sets = build_api_sets(activity_names={'horse_riding': {'화랑승마목장'}})
    assert matches({'name': '화랑승마목장', 'category': ''}, 'horse_riding', sets) is True
    assert matches({'name': '박문수묘', 'category': 'A02'}, 'horse_riding', sets) is False


# ---- 반려견 · 편의시설 (2026-09-20) ----

def test_pet_keyword_and_hint_defined():
    from common.constants import COURSE_PET_KAKAO
    keyword, hint = COURSE_PET_KAKAO
    assert keyword and hint


def test_pet_codes_judgeable_only_with_results():
    from services.place_score import judgeable, build_api_sets
    assert judgeable('dog_medium') is False
    sets = build_api_sets(pet_places=[{'name': '도어커피'}])
    assert judgeable('dog_medium', sets) is True


def test_facility_nearby_rule_defined():
    """★주차장은 후보로 넣지 않고 판정에만 쓴다.★

    주차장이 코스 항목이 되면 이상하다. 좌표 근접(기본 200m)으로만 본다.
    화장실은 '공중화장실' 검색 결과에 세차장·공원이 섞여 부정확해 넣지 않았다.
    """
    from common.constants import COURSE_FACILITY_NEARBY
    assert set(COURSE_FACILITY_NEARBY) == {'parking'}
    keyword, hint, radius_m = COURSE_FACILITY_NEARBY['parking']
    assert keyword and hint and 0 < radius_m <= 1000


def test_facility_names_feed_api_sets():
    from services.place_score import build_api_sets, judgeable, matches
    sets = build_api_sets(facility_names={'parking': {'청화집'}})
    assert judgeable('parking', sets) is True
    assert matches({'name': '청화집', 'category': ''}, 'parking', sets) is True
    assert matches({'name': '맘앤쉐프', 'category': ''}, 'parking', sets) is False


def test_official_pet_api_takes_priority(monkeypatch):
    """★반려동물 API 가 살아나면 그쪽을 우선한다.★ 그때는 카카오를 부르지 않는다."""
    import routes.course as rc

    class Exp:
        lat, lng = 36.8, 127.3

    monkeypatch.setattr(rc.pet_travel_api, 'find_pet_facilities',
                        lambda *a, **kw: [{'name': '공식 애견카페'}])
    called = []
    monkeypatch.setattr(rc.kakao_place, 'search',
                        lambda *a, **kw: called.append(1) or [])
    places, names = rc._pet_places(Exp(), ['dog_medium'])
    assert names == {'공식애견카페'}
    assert called == [], "공식 API 결과가 있으면 카카오를 부르지 않는다"


def test_pet_not_called_without_pet_condition(monkeypatch):
    import routes.course as rc

    class Exp:
        lat, lng = 36.8, 127.3

    called = []
    monkeypatch.setattr(rc.pet_travel_api, 'find_pet_facilities',
                        lambda *a, **kw: called.append(1) or [])
    assert rc._pet_places(Exp(), ['nature']) == ([], set())
    assert called == [], "고르지 않은 조건으로 호출을 태우지 않는다"


# ---- 동반구성 (2026-09-20) ----

def test_companion_keywords_limited_and_hinted():
    """★유형당 2개까지.★ 힌트 없이 키워드만 믿으면 엉뚱한 게 섞인다."""
    from common.constants import COURSE_COMPANION_KAKAO
    assert set(COURSE_COMPANION_KAKAO) == {
        'solo', 'couple', 'family_child', 'parents', 'friends', 'adults_only'}
    for code, pairs in COURSE_COMPANION_KAKAO.items():
        assert 1 <= len(pairs) <= 2, code
        for keyword, hint in pairs:
            assert keyword and hint, code


def test_adults_only_uses_brewery_not_liquor():
    """★'전통주'로 검색하면 고깃집이 걸린다.★ 양조장만 쓴다."""
    from common.constants import COURSE_COMPANION_KAKAO
    keywords = [kw for kw, _ in COURSE_COMPANION_KAKAO['adults_only']]
    assert keywords == ['양조장']


def test_duplicate_keywords_collapse():
    """★겹치는 검색어는 한 번만 부른다.★ 6개를 다 골라도 검색어는 7개뿐이다."""
    from common.constants import COURSE_COMPANION_KAKAO
    all_keywords = [kw for pairs in COURSE_COMPANION_KAKAO.values() for kw, _ in pairs]
    assert len(all_keywords) == 11
    assert len(set(all_keywords)) == 7


def test_search_many_dedupes_and_returns_per_query(monkeypatch):
    monkeypatch.setenv('KAKAO_API_KEY', 'k')
    calls = []

    def fake_search(query, lat, lng, radius_m=None):
        calls.append(query)
        return [{'name': query + '장소', 'category': '여행 > 공원'}]

    monkeypatch.setattr(kakao_place, 'search', fake_search)
    result = kakao_place.search_many(['공원', '카페', '공원'], 36.8, 127.3)
    assert sorted(calls) == ['공원', '카페'], "중복 검색어는 한 번만"
    assert set(result) == {'공원', '카페'}


def test_search_many_survives_partial_failure(monkeypatch):
    """하나가 실패해도 나머지는 살아야 한다."""
    monkeypatch.setenv('KAKAO_API_KEY', 'k')

    def fake_search(query, lat, lng, radius_m=None):
        if query == '카페':
            raise RuntimeError('장애')
        return [{'name': 'ok', 'category': '여행 > 공원'}]

    monkeypatch.setattr(kakao_place, 'search', fake_search)
    result = kakao_place.search_many(['공원', '카페'], 36.8, 127.3)
    assert result['카페'] == []
    assert result['공원']


def test_search_many_empty_input():
    assert kakao_place.search_many([], 36.8, 127.3) == {}
    assert kakao_place.search_many(None, 36.8, 127.3) == {}


def test_companion_not_called_without_condition(monkeypatch):
    import routes.course as rc

    class Exp:
        lat, lng = 36.8, 127.3

    called = []
    monkeypatch.setattr(rc.kakao_place, 'search_many',
                        lambda *a, **kw: called.append(1) or {})
    assert rc._companion_places(Exp(), ['nature']) == ([], {})
    assert called == [], "고르지 않은 조건으로 호출을 태우지 않는다"
