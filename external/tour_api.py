# external/tour_api.py — 한국관광공사 국문 관광정보 API(KorService2) 위치기반 조회.
# 엔드포인트는 data.go.kr 샘플 URL로 확인 완료: KorService2/locationBasedList2
import os

import requests

from common.constants import HTTP_TIMEOUT_SEC, NEARBY_RESULT_LIMIT

TOUR_API_URL = "https://apis.data.go.kr/B551011/KorService2/locationBasedList2"


def find_nearby_places(lat, lng, radius_m, content_type_id=None):
    """좌표+반경 주변의 관광지/음식점 등을 반환한다. content_type_id로 종류를 지정한다.
    실패 시(키 없음·네트워크·파싱 오류) 예외를 던지지 않고 빈 리스트를 반환한다."""
    api_key = os.environ.get("TOUR_API_KEY", "DUMMY_TOUR_KEY")
    params = {
        "serviceKey": api_key,
        "MobileOS": "ETC",
        "MobileApp": "FarmLink",
        "_type": "json",
        "numOfRows": NEARBY_RESULT_LIMIT,
        "mapX": lng,
        "mapY": lat,
        "radius": radius_m,
        "arrange": "E",  # 거리순
    }
    if content_type_id is not None:
        params["contentTypeId"] = content_type_id
    try:
        resp = requests.get(TOUR_API_URL, params=params, timeout=HTTP_TIMEOUT_SEC)
        resp.raise_for_status()
        items = resp.json()["response"]["body"]["items"]["item"]
        return [_to_place(it) for it in items]
    except Exception:
        return []


def _to_place(item):
    # API 원본 전체가 아니라 화면에 필요한 필드만 정리한다(KorService2 응답 기준).
    return {
        "name": item.get("title"),
        "address": item.get("addr1"),
        "lat": item.get("mapy"),
        "lng": item.get("mapx"),
        "tel": item.get("tel"),
        "category": item.get("cat3"),
        "image": item.get("firstimage"),
        "content_type_id": item.get("contenttypeid"),
    }
