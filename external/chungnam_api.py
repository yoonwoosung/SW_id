# external/chungnam_api.py — 충청남도 올담 관광지정보표준데이터 조회.
#
# 한국관광공사(external/tour_api.py)를 대체하지 않는다. 충남 지역 체험의 코스를
# 만들 때 관광공사 결과에 '보강'으로 더한다. 도가 직접 관리하는 데이터라
# 겹치는 장소는 이쪽을 우선한다.
#
# ★이 API 는 tour_api 패턴을 그대로 복사하면 안 된다.★ 실제로 호출해 확인한 특성:
#
#   1) WAF 가 User-Agent 를 검사한다.
#      requests 기본 UA 로 부르면 404 + "Violated Web Attack Tool Prevention" 이 온다.
#      브라우저 UA 를 반드시 헤더에 넣어야 한다.
#
#   2) 오류 응답이 HTTP 200 + HTML 이다.
#      점검 중에는 200 에 text/html 로 안내 페이지가 온다.
#      raise_for_status() 로는 못 잡으므로 Content-Type 과 본문으로 판정한다.
#
#   3) 인코딩이 상황에 따라 다르다.
#      차단 페이지는 EUC-KR, 점검 페이지는 UTF-8 이었다. 고정하면 깨진다.
#      requests 의 apparent_encoding 에 맡기고 실패하면 대체 문자로 넘긴다.
import json
import os

import requests

from common.constants import HTTP_TIMEOUT_SEC, NEARBY_RESULT_LIMIT
from services import tour_cache

CHUNGNAM_API_URL = "https://alldam.chungnam.go.kr/api/getTrsmic/stdlist.do"

# WAF 가 막지 않는 UA. 값 자체에 의미는 없고 '도구가 아닌 브라우저'로 보이면 된다.
BROWSER_UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
              "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

# 캐시 키를 관광공사와 구분하는 접두사. 같은 좌표라도 출처가 다르다.
CACHE_PREFIX = 'cn'


def _decode(response):
    """응답 본문을 문자열로. 인코딩이 섞여 오므로 추정에 맡긴다."""
    if not response.encoding or response.encoding.lower() == 'iso-8859-1':
        response.encoding = response.apparent_encoding or 'utf-8'
    try:
        return response.text
    except Exception:
        return response.content.decode('utf-8', 'replace')


def _looks_like_data(response, body):
    """진짜 데이터 응답인지 판정한다.

    이 API 는 실패해도 200 을 주므로 상태 코드로는 알 수 없다.
    Content-Type 이 JSON/XML 이거나, 본문이 {·[·< 로 시작하되
    HTML 문서가 아니어야 데이터로 본다.
    """
    content_type = (response.headers.get('Content-Type') or '').lower()
    if 'html' in content_type:
        return False
    head = (body or '').lstrip()[:200].lower()
    if head.startswith('<!doctype html') or head.startswith('<html'):
        return False
    if 'json' in content_type or 'xml' in content_type:
        return True
    return head[:1] in ('{', '[', '<')


def _to_place(raw):
    """올담 응답의 항목 하나를 코스에서 쓰는 형태로 바꾼다.

    ★TODO: 서버 점검이 끝나면 실제 필드명을 확인해 채운다.★
    지금은 응답 구조를 볼 수 없어 비워 둔다(None 을 주면 호출부가 건너뛴다).

    반환 형식은 external/tour_api._to_place 와 같아야 한다.
    course_builder 가 두 출처를 구분 없이 다루기 때문이다.
        {
            "name": str, "address": str, "lat": str|float, "lng": str|float,
            "tel": str|None, "category": str|None, "image": str|None,
            "source": "chungnam",      # 화면에서 '충남도 제공' 표시에 쓴다
        }

    채울 때 주의: lat/lng 가 문자열로 와도 된다.
    course_builder._to_float 가 변환하고 실패하면 그 장소를 건너뛴다.
    """
    # TODO(chungnam): 실제 응답 필드에 맞춰 매핑
    return None


def _extract_items(body):
    """응답 본문에서 항목 리스트를 꺼낸다.

    ★TODO: 서버 점검이 끝나면 실제 구조를 확인해 채운다.★
    JSON 이면 보통 response.body.items.item 또는 data 같은 경로에 들어 있다.
    XML 이면 별도 파싱이 필요하다.
    """
    try:
        parsed = json.loads(body)
    except Exception:
        return []

    # TODO(chungnam): 실제 경로로 교체. 아래는 흔한 공공데이터 형태의 추정이라
    # 구조를 확인하기 전까지는 대부분 빈 리스트를 돌려준다.
    for path in (('response', 'body', 'items', 'item'), ('items',), ('data',), ('list',)):
        node = parsed
        for key in path:
            if not isinstance(node, dict):
                node = None
                break
            node = node.get(key)
        if isinstance(node, list):
            return node
        if isinstance(node, dict):
            return [node]
    return []


def find_nearby_places(lat, lng, radius_m, content_type_id=None):
    """충남 관광지 목록. 실패하면 언제나 빈 리스트.

    시그니처를 tour_api.find_nearby_places 와 맞춰 호출부가 두 출처를
    같은 방식으로 다룰 수 있게 했다. content_type_id 는 올담에 대응 개념이
    있는지 확인 전이라 지금은 캐시 키에만 쓴다.
    """
    api_key = os.environ.get('CHUNGNAM_API_KEY')
    if not api_key:
        return []      # 키가 없으면 조용히 건너뛴다(기존 코스 생성에 영향 없음)

    cache_key = tour_cache.make_key(lat, lng, f"{CACHE_PREFIX}:{radius_m}", content_type_id)
    cached = tour_cache.get(cache_key)
    if cached is not None:
        return cached

    params = {
        'serviceKey': api_key,
        'numOfRows': NEARBY_RESULT_LIMIT,
        'pageNo': 1,
        'type': 'json',
    }
    try:
        response = requests.get(
            CHUNGNAM_API_URL, params=params, timeout=HTTP_TIMEOUT_SEC,
            headers={'User-Agent': BROWSER_UA, 'Accept': 'application/json, */*'},
        )
        body = _decode(response)
        if not _looks_like_data(response, body):
            places = []           # 점검 페이지·차단 페이지
        else:
            places = [p for p in (_to_place(raw) for raw in _extract_items(body)) if p]
    except Exception:
        places = []

    # 빈 결과도 캐싱한다(짧은 TTL). 점검 중에 매 요청마다 부르지 않게.
    tour_cache.set(cache_key, places)
    return places
