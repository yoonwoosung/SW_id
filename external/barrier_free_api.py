# external/barrier_free_api.py — 한국관광공사 무장애 여행 API 클라이언트(HTTP 호출·필드 정리만).
import os

import requests

from common.constants import HTTP_TIMEOUT_SEC, NEARBY_RESULT_LIMIT

# ⚠️ 확인 필요(미검증): KorService2 이관에 맞춰 v2 형태로 추정 변경.
#   KorWithService(무장애)의 실제 v2 서비스명/오퍼레이션은 data.go.kr 샘플 URL로 확인해 확정할 것.
#   휠체어/유모차/장애인화장실 상세 플래그는 detail 계열 응답에 있으므로 실제 응답 확인 후 필드 매핑 확정.
BARRIER_FREE_URL = "https://apis.data.go.kr/B551011/KorWithService2/locationBasedList2"


def find_barrier_free_places(lat, lng, radius_m):
    """좌표+반경 주변의 무장애(휠체어·유모차 접근 등) 여행지 목록을 반환한다.
    실패 시 예외를 던지지 않고 빈 리스트를 반환한다."""
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
        "arrange": "E",
    }
    try:
        resp = requests.get(BARRIER_FREE_URL, params=params, timeout=HTTP_TIMEOUT_SEC)
        resp.raise_for_status()
        items = resp.json()["response"]["body"]["items"]["item"]
        return [_to_place(it) for it in items]
    except Exception:
        return []


def _to_place(item):
    return {
        "name": item.get("title"),
        "address": item.get("addr1"),
        "lat": item.get("mapy"),
        "lng": item.get("mapx"),
        # 상세 접근성 플래그(값이 있으면 True). 실제 필드명은 키 확보 후 확정(TODO).
        "wheelchair": bool(item.get("wheelchair")),
        "stroller": bool(item.get("stroller")),
        "disabled_toilet": bool(item.get("restroom")),
    }
