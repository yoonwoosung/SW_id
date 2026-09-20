# external/barrier_free_api.py — 한국관광공사 무장애 여행 API 클라이언트(HTTP 호출·필드 정리만).
#
# ★URL 을 v1 에서 v2 로 고쳤다.★
# 기존 KorWithService/locationBasedList 는 HTTP 400 "NO_OPENAPI_SERVICE_ERROR
# (해당 오픈API 서비스가 없거나 폐기됨)" 을 돌려준다. 예외를 삼키는 구조라
# 오류가 드러나지 않고 늘 빈 리스트만 나왔다 — 즉 이 API 는 죽어 있었다.
# KorWithService2/locationBasedList2 로 부르면 정상 응답한다(실측 확인).
import os

import requests

from common.constants import HTTP_TIMEOUT_SEC, NEARBY_RESULT_LIMIT
from services import tour_cache

BARRIER_FREE_URL = "https://apis.data.go.kr/B551011/KorWithService2/locationBasedList2"

# 캐시 키 접두사. 관광공사 본 서비스와 좌표가 같아도 결과가 다르므로 구분한다.
CACHE_PREFIX = "bf"


def find_barrier_free_places(lat, lng, radius_m):
    """좌표+반경 주변의 무장애(휠체어·유모차 접근 등) 여행지 목록.

    실패 시 예외를 던지지 않고 빈 리스트를 반환한다(코스 생성이 멈추면 안 된다).
    관광공사 본 서비스와 같은 파일 캐시를 쓴다 — 코스 1건마다 새로 부르면
    일일 한도를 금방 태운다.
    """
    cache_key = tour_cache.make_key(lat, lng, f"{CACHE_PREFIX}:{radius_m}", None)
    cached = tour_cache.get(cache_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("BARRIER_FREE_API_KEY", "DUMMY_BARRIER_FREE_KEY")
    params = {
        "serviceKey": api_key,
        "mapX": lng,
        "mapY": lat,
        "radius": radius_m,
        "MobileOS": "ETC",
        "MobileApp": "FarmLink",
        "_type": "json",
        "numOfRows": NEARBY_RESULT_LIMIT,
        "arrange": "E",       # 거리순
    }
    try:
        resp = requests.get(BARRIER_FREE_URL, params=params, timeout=HTTP_TIMEOUT_SEC)
        resp.raise_for_status()
        items = resp.json()["response"]["body"]["items"]["item"]
        places = [_to_place(it) for it in items]
    except Exception:
        places = []

    tour_cache.set(cache_key, places)
    return places


def _to_place(item):
    """목록 응답 한 건을 정리한다.

    ★휠체어·유모차 같은 세부 플래그는 목록 응답에 없다.★ 상세(detailWithTour2)
    에만 있어 장소마다 한 번씩 더 불러야 하는데, 일일 한도를 생각하면
    코스 생성 경로에서 쓸 수 없다. 대신 ★이 목록에 들어 있다는 것 자체가
    무장애 시설이라는 뜻★ 이므로 그것만으로 판정한다.
    """
    return {
        "name": item.get("title"),
        "address": item.get("addr1"),
        "lat": item.get("mapy"),
        "lng": item.get("mapx"),
        "tel": item.get("tel"),
        "category": item.get("cat3"),
        "image": item.get("firstimage"),
        "content_type_id": item.get("contenttypeid"),
        "barrier_free": True,      # 이 API 가 돌려준 장소는 모두 무장애 정보 등록 시설
    }
