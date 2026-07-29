# external/medical_tour_api.py — 한국관광공사 의료관광 API 클라이언트(HTTP 호출·필드 정리만).
import os

import requests

from common.constants import HTTP_TIMEOUT_SEC, NEARBY_RESULT_LIMIT

# ⚠️ 확인 필요(미검증): 이 URL은 임시 placeholder다. KTO에 'MedicalTourService'가 실재하는지 불확실.
#   MEDICAL_API_KEY가 어떤 data.go.kr 서비스(의료관광/응급의료/병원정보 등)용인지 확인 후,
#   해당 서비스의 샘플 요청 URL·파라미터·응답 필드로 맞춰야 한다. (다른 제공기관일 수 있음)
MEDICAL_TOUR_URL = "https://apis.data.go.kr/B551011/MedicalTourService/locationBasedList"


def find_medical_facilities(lat, lng, radius_m):
    """좌표+반경 주변의 병원·응급센터 등 의료 시설 목록을 반환한다.
    실패 시 예외를 던지지 않고 빈 리스트를 반환한다."""
    api_key = os.environ.get("MEDICAL_API_KEY", "DUMMY_MEDICAL_KEY")
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
        resp = requests.get(MEDICAL_TOUR_URL, params=params, timeout=HTTP_TIMEOUT_SEC)
        resp.raise_for_status()
        items = resp.json()["response"]["body"]["items"]["item"]
        return [_to_facility(it) for it in items]
    except Exception:
        return []


def _to_facility(item):
    return {
        "name": item.get("title"),
        "category": item.get("cat3"),
        "address": item.get("addr1"),
        "tel": item.get("tel"),
        "lat": item.get("mapy"),
        "lng": item.get("mapx"),
    }
