"""지역 필터에 추가한 광역시 7개 — 목록·매칭·오매칭 방지.

핵심: '광주'는 경기도 시군('광주(경기)')과 이름이 같다.
주소 매칭이 부분 문자열이라 키워드를 잘못 두면 서로 섞인다.
"""
import pytest

from common.search_categories import (
    _REGIONS, _METRO_REGIONS, REGION_ADDRESS_KEYWORDS,
    LEAF_CODES, LABEL_BY_CODE, SEARCH_CATEGORIES,
)
from services.category_match import _has_region

METRO_CODES = ('seoul', 'busan', 'daegu', 'incheon', 'gwangju', 'daejeon', 'ulsan')
PROVINCE_CODES = ('gyeonggi', 'gangwon', 'chungbuk', 'chungnam',
                  'jeonbuk', 'jeonnam', 'gyeongbuk', 'gyeongnam', 'jeju')


class FakeExperience:
    def __init__(self, address_detail=""):
        self.address_detail = address_detail


# ───────────────────── 목록 ─────────────────────

def test_seven_metro_cities_added():
    assert len(_METRO_REGIONS) == 7
    assert tuple(code for code, _l, _a, _c in _METRO_REGIONS) == METRO_CODES


def test_sejong_is_not_included():
    """세종은 제외한다(요구 사항)."""
    assert 'sejong' not in REGION_ADDRESS_KEYWORDS


def test_existing_provinces_unchanged():
    """★기존 9개 도와 시군은 그대로 유지한다.★"""
    codes = [code for code, _l, _a, _c in _REGIONS]
    assert codes[7:] == list(PROVINCE_CODES)
    assert REGION_ADDRESS_KEYWORDS['chungnam'] == ['충남', '충청남도']
    assert REGION_ADDRESS_KEYWORDS['nonsan'] == ['논산']
    assert REGION_ADDRESS_KEYWORDS['jeju'] == ['제주']


def test_metro_has_no_district_children():
    """자치구는 넣지 않는다.

    '북구'·'중구'·'동구'·'서구'가 여러 광역시에 겹쳐 부분 문자열 매칭이 섞인다.
    """
    region = next(c for c in SEARCH_CATEGORIES if c['code'] == 'region')
    metro_nodes = [n for n in region['children'] if n['code'] in METRO_CODES]
    assert len(metro_nodes) == 7
    for node in metro_nodes:
        assert not node.get('children'), node['code']


def test_metro_nodes_are_leaves():
    """하위가 없으므로 잎이어야 한다(프론트가 체크박스 그리드로 그린다)."""
    for code in METRO_CODES:
        assert code in LEAF_CODES, code


def test_metro_labels():
    for code, label in zip(METRO_CODES, ('서울', '부산', '대구', '인천', '광주', '대전', '울산')):
        assert LABEL_BY_CODE[code] == label


def test_metro_comes_before_provinces():
    """잎이 아코디언보다 먼저 그려지므로 목록 맨 위에 모인다."""
    region = next(c for c in SEARCH_CATEGORIES if c['code'] == 'region')
    codes = [n['code'] for n in region['children']]
    assert codes[:7] == list(METRO_CODES)


# ───────────────────── 주소 매칭 ─────────────────────

@pytest.mark.parametrize('code,address', [
    ('seoul', '서울특별시 강남구 테헤란로 1'),
    ('seoul', '서울 서초구 반포대로'),
    ('busan', '부산광역시 기장군 일광읍'),
    ('busan', '부산 해운대구'),
    ('daegu', '대구광역시 달성군 가창면'),
    ('incheon', '인천광역시 강화군 길상면'),
    ('daejeon', '대전광역시 유성구'),
    ('ulsan', '울산광역시 울주군 상북면'),
])
def test_metro_matches_both_full_and_short_form(code, address):
    """동명 시군이 없는 6개는 정식·축약 표기 둘 다 잡는다."""
    assert _has_region([code], FakeExperience(address)) is True


# ───────────────────── 광주 오매칭 방지 ─────────────────────

def test_gwangju_metro_matches_full_form():
    assert _has_region(['gwangju'], FakeExperience('광주광역시 북구 운암동')) is True


def test_gwangju_metro_does_not_match_gyeonggi_gwangju():
    """★핵심: 광주광역시를 골랐는데 경기도 광주시 체험이 나오면 안 된다.★"""
    exp = FakeExperience('경기도 광주시 초월읍')
    assert _has_region(['gwangju'], exp) is False


def test_gyeonggi_gwangju_still_matches_its_own_address():
    """경기 광주시 필터는 그대로 동작한다(기존 동작 유지)."""
    assert _has_region(['gwangju_gg'], FakeExperience('경기도 광주시 초월읍')) is True


def test_gwangju_short_form_is_a_known_miss():
    """★알고 받아들인 한계.★ '광주 북구' 축약 표기는 잡지 못한다.

    '광주'를 키워드로 쓰면 잡히지만 "경기도 광주시"까지 끌려온다.
    틀린 결과를 보여주는 것보다 덜 나오는 쪽을 택했다.
    데이터가 쌓이면 재검토한다.
    """
    assert _has_region(['gwangju'], FakeExperience('광주 북구 운암동')) is False


def test_metro_does_not_match_unrelated_address():
    for code in METRO_CODES:
        assert _has_region([code], FakeExperience('충남 논산시 연무읍')) is False, code


def test_province_selection_unaffected_by_metro():
    """광역시를 추가해도 도 필터 결과가 달라지지 않는다."""
    exp = FakeExperience('경기도 광주시 초월읍')
    assert _has_region(['gyeonggi'], exp) is True
    assert _has_region(['chungnam'], exp) is False


# ───────────────────── 코드 충돌 ─────────────────────

def test_no_duplicate_region_codes():
    codes = [code for code, _l, _a, _c in _REGIONS]
    for _c, _l, _a, cities in _REGIONS:
        codes.extend(city_code for city_code, _cl in cities)
    assert len(codes) == len(set(codes)), "지역 코드가 중복됐다"
