# external/pet_travel_api.py — 한국관광공사 반려동물 동반여행 API 클라이언트(HTTP 호출·필드 정리만).
#
# ★URL 을 v1 에서 v2 로 고쳤다.★ 실측한 두 가지 오류가 서로 다르다.
#   v1 KorPetTourService  → HTTP 400 "NO_OPENAPI_SERVICE_ERROR"        (서비스 폐기됨)
#   v2 KorPetTourService2 → HTTP 403 "SERVICE_KEY_IS_NOT_REGISTERED_ERROR"
#
# 같은 키로 KorService2(관광정보)·KorWithService2(무장애)는 200 OK 라 ★키 자체는 정상★이고,
# 반려동물 서비스만 data.go.kr 활용신청이 안 돼 있다. 신청이 승인되면
# 이 파일은 그대로 두고 바로 동작한다(코드로 해결할 수 있는 문제가 아니다).
import os

import requests

from common.constants import HTTP_TIMEOUT_SEC, NEARBY_RESULT_LIMIT
from services import tour_cache

PET_TRAVEL_URL = "https://apis.data.go.kr/B551011/KorPetTourService2/locationBasedList2"

CACHE_PREFIX = "pet"


def find_pet_facilities(lat, lng, radius_m):
    """좌표+반경 주변의 반려동물 동반 가능 시설 목록.

    실패 시(키 미등록·네트워크·파싱 오류) 예외를 던지지 않고 빈 리스트를 반환한다.
    무장애와 같은 파일 캐시를 써서 일일 한도를 아낀다.
    """
    cache_key = tour_cache.make_key(lat, lng, f"{CACHE_PREFIX}:{radius_m}", None)
    cached = tour_cache.get(cache_key)
    if cached is not None:
        return cached

    api_key = os.environ.get("PET_API_KEY", "DUMMY_PET_KEY")
    params = {
        "serviceKey": api_key,
        "mapX": lng,
        "mapY": lat,
        "radius": radius_m,
        "MobileOS": "ETC",
        "MobileApp": "FarmLink",
        "_type": "json",
        "numOfRows": NEARBY_RESULT_LIMIT,
        "arrange": "E",  # 거리순
    }
    try:
        resp = requests.get(PET_TRAVEL_URL, params=params, timeout=HTTP_TIMEOUT_SEC)
        resp.raise_for_status()
        items = resp.json()["response"]["body"]["items"]["item"]
        facilities = [_to_facility(it) for it in items]
    except Exception:
        facilities = []

    tour_cache.set(cache_key, facilities)
    return facilities


def _to_facility(item):
    # API 원본 전체가 아니라 화면·코스 점수에 필요한 필드만 정리한다.
    return {
        "name": item.get("title"),
        "category": item.get("cat3"),
        "address": item.get("addr1"),
        "tel": item.get("tel"),
        "lat": item.get("mapy"),
        "lng": item.get("mapx"),
        "image": item.get("firstimage"),
        "content_type_id": item.get("contenttypeid"),
        "pet_allowed": True,       # 이 API 가 돌려준 장소는 모두 반려동물 동반 가능
    }
