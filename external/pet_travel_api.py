# external/pet_travel_api.py — 한국관광공사 반려동물 동반여행 API 클라이언트(HTTP 호출·필드 정리만).
import os

import requests

from common.constants import HTTP_TIMEOUT_SEC, NEARBY_RESULT_LIMIT

# ⚠️ 현재 활성 키로는 403 Forbidden = 이 계정이 '반려동물 동반여행' 서비스에 활용신청 안 됨.
#   → data.go.kr에서 해당 서비스 활용신청 후, 샘플 URL로 엔드포인트 확정 필요. (그전까지 실패 시 빈 리스트)
PET_TRAVEL_URL = "https://apis.data.go.kr/B551011/KorPetTourService2/locationBasedList2"


def find_pet_facilities(lat, lng, radius_m):
    """좌표+반경 주변의 반려동물 동반 가능 시설 목록을 반환한다.
    실패 시(키 없음·네트워크·파싱 오류) 예외를 던지지 않고 빈 리스트를 반환한다."""
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
        return [_to_facility(it) for it in items]
    except Exception:
        return []


def _to_facility(item):
    # API 원본 전체가 아니라 화면에 필요한 필드만 정리한다.
    return {
        "name": item.get("title"),
        "category": item.get("cat3"),
        "address": item.get("addr1"),
        "tel": item.get("tel"),
        "lat": item.get("mapy"),
        "lng": item.get("mapx"),
    }
