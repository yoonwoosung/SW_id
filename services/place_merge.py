# services/place_merge.py — 관광공사 장소 목록에 충남 데이터를 보강한다(순수 함수).
#
# 관광공사 API 는 대체하지 않는다. 대회 필수 요건이라 호출 기록이 남아야 하고,
# 충남 밖 체험은 관광공사만으로 코스를 만든다.
# 충남 지역 체험일 때만 충남 데이터를 '더해서' 겹치는 장소는 도 데이터를 쓴다
# (도가 직접 관리하는 데이터가 더 정확하다).
import math
import re

from common.search_categories import REGION_ADDRESS_KEYWORDS

# 같은 장소로 볼 거리(m). 좌표가 이 안이면 이름이 달라도 같은 곳으로 본다
# (표기 차이: '○○사' vs '○○사(대웅전)').
DUPLICATE_DISTANCE_M = 50

# 충남 판정에 쓸 주소 키워드. search_categories 에 이미 있는 것을 재사용한다.
# 시도명('충남'·'충청남도')만 보면 '충남 논산시'처럼 시도가 빠진 주소를 놓치므로
# 시군명 15개도 함께 본다.
_CHUNGNAM_CITY_CODES = (
    'cheonan', 'gongju', 'boryeong', 'asan', 'seosan', 'nonsan', 'gyeryong',
    'dangjin', 'geumsan', 'buyeo', 'seocheon', 'cheongyang', 'hongseong',
    'yesan', 'taean',
)


def _chungnam_keywords():
    words = list(REGION_ADDRESS_KEYWORDS.get('chungnam', []))
    for code in _CHUNGNAM_CITY_CODES:
        words.extend(REGION_ADDRESS_KEYWORDS.get(code, []))
    return tuple(words)


CHUNGNAM_KEYWORDS = _chungnam_keywords()


def is_chungnam(experience):
    """충남 지역 체험인가. 주소 문자열로 판정한다.

    좌표 범위(위경도 사각형)로 하는 방법도 있지만 도 경계가 사각형이 아니라
    인접 시군을 잘못 포함한다. 주소는 농장주가 입력하고 지오코딩 원본이라
    더 정확하다. 다만 주소가 비어 있으면 판정할 수 없어 False 를 준다
    (충남 데이터를 안 부를 뿐 기존 코스 생성은 그대로 된다).
    """
    if experience is None:
        return False
    address = (getattr(experience, 'address_detail', None)
               or getattr(experience, 'location', None) or '')
    return any(word in address for word in CHUNGNAM_KEYWORDS)


def _normalize_name(name):
    """이름 비교용 정규화. 공백·괄호·특수문자를 털어낸다."""
    if not name:
        return ''
    return re.sub(r'[\s()\[\]{}·,.\-_/]', '', str(name)).lower()


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _distance_m(a, b):
    """두 장소 사이 거리(m). 좌표가 없으면 None."""
    a_lat, a_lng = _to_float(a.get('lat')), _to_float(a.get('lng'))
    b_lat, b_lng = _to_float(b.get('lat')), _to_float(b.get('lng'))
    if None in (a_lat, a_lng, b_lat, b_lng):
        return None
    # 50m 판정이라 하버사인까지 갈 필요 없이 평면 근사로 충분하다.
    lat_m = (a_lat - b_lat) * 111_320
    lng_m = (a_lng - b_lng) * 111_320 * math.cos(math.radians((a_lat + b_lat) / 2))
    return math.hypot(lat_m, lng_m)


def is_same_place(a, b):
    """같은 장소인가. 좌표가 50m 안이거나 정규화한 이름이 같으면 같다고 본다."""
    distance = _distance_m(a, b)
    if distance is not None and distance <= DUPLICATE_DISTANCE_M:
        return True
    name_a, name_b = _normalize_name(a.get('name')), _normalize_name(b.get('name'))
    return bool(name_a) and name_a == name_b


def merge(tour_places, chungnam_places):
    """관광공사 목록에 충남 목록을 더한다. 겹치면 충남 쪽을 남긴다.

    충남 데이터를 앞에 두는 이유는 도가 직접 관리해 더 정확하다고 봤기 때문이다.
    관광공사 결과는 사라지지 않고, 겹치지 않는 것은 그대로 뒤에 붙는다.
    """
    merged = list(chungnam_places or [])
    for place in (tour_places or []):
        if not any(is_same_place(place, kept) for kept in merged):
            merged.append(place)
    return merged
