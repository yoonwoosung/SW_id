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
