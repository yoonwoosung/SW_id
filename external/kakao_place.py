# external/kakao_place.py — 카카오 로컬 '키워드 검색'으로 주변 장소를 찾는다.
#
# 관광공사 분류 코드로는 구분할 수 없는 조건을 채우는 데 쓴다.
# 예: 승마·등산·자전거가 관광공사에서는 전부 육상 레포츠(A0303) 한 코드라
#     서로 구분되지 않는다. 카카오는 category_name 이
#     '스포츠,레저 > 승마 > 승마장' 처럼 세분돼 있어 나눌 수 있다.
#
# ★관광공사 API 를 대체하지 않는다.★ 코스 후보는 관광공사·CSV 에서 뽑고,
# 여기서는 '그 후보가 조건에 맞는가'를 판정할 이름 집합만 만든다.
#
# 호출량: 조건을 고를 때만 부르고 결과를 tour_cache(1시간)에 담는다.
# 카카오 로컬은 일일 10만 건이라 여유롭지만, 코스마다 새로 부를 이유가 없다.
import os
from concurrent.futures import ThreadPoolExecutor, as_completed

import requests

from common.constants import HTTP_TIMEOUT_SEC
from services import tour_cache

KAKAO_KEYWORD_URL = "https://dapi.kakao.com/v2/local/search/keyword.json"

CACHE_PREFIX = "kakao"
RESULT_SIZE = 15          # 카카오 한 페이지 최대 15건
MAX_RADIUS_M = 20000      # 카카오 허용 최대 반경


def _api_key():
    # 앱 컨텍스트 밖(스크립트·테스트)에서도 동작하도록 환경변수를 먼저 본다.
    key = os.environ.get("KAKAO_API_KEY")
    if key:
        return key
    try:
        from flask import current_app
        return current_app.config.get("KAKAO_API_KEY")
    except Exception:
        return None


def search(keyword, lat, lng, radius_m=MAX_RADIUS_M):
    """좌표 주변에서 키워드로 장소를 찾는다. 실패하면 언제나 빈 리스트.

    반환: [{"name", "category", "address", "lat", "lng"}, ...]
    """
    cache_key = tour_cache.make_key(lat, lng, f"{CACHE_PREFIX}:{radius_m}", keyword)
    cached = tour_cache.get(cache_key)
    if cached is not None:
        return cached

    key = _api_key()
    if not key:
        return []          # 키가 없으면 조용히 건너뛴다(코스 생성에 영향 없음)

    try:
        response = requests.get(
            KAKAO_KEYWORD_URL,
            params={"query": keyword, "x": lng, "y": lat,
                    "radius": min(int(radius_m), MAX_RADIUS_M), "size": RESULT_SIZE},
            headers={"Authorization": f"KakaoAK {key}"},
            timeout=HTTP_TIMEOUT_SEC,
        )
        response.raise_for_status()
        documents = response.json().get("documents") or []
        places = [{
            "name": doc.get("place_name"),
            "category": doc.get("category_name") or "",
            "address": doc.get("road_address_name") or doc.get("address_name") or "",
            "lat": doc.get("y"),
            "lng": doc.get("x"),
        } for doc in documents if doc.get("place_name")]
    except Exception:
        places = []

    tour_cache.set(cache_key, places)
    return places


def search_names(keyword, lat, lng, radius_m=MAX_RADIUS_M, category_hint=None):
    """검색 결과의 장소 이름 집합(공백 제거). 조건 판정용.

    category_hint 를 주면 카카오 category_name 에 그 문자열이 들어간 것만 남긴다.
    ★키워드만 믿으면 엉뚱한 게 섞인다★ — '낚시터'로 찾으면 횟집('음식점 > 한식 >
    해물,생선')이 걸리고, '등산로'로 찾으면 주차장·입출구가 걸린다.
    """
    names = set()
    for place in search(keyword, lat, lng, radius_m):
        if category_hint and category_hint not in (place.get("category") or ""):
            continue
        names.add("".join(str(place["name"]).split()))
    return names


def search_many(queries, lat, lng, radius_m=MAX_RADIUS_M):
    """여러 검색어를 ★한 번에·병렬로★ 조회한다. 반환: {검색어: [장소, ...]}

    같은 검색어가 여러 조건에 겹쳐도 한 번만 부른다(호출부에서 중복을 제거해 넘긴다).
    병렬로 돌려 체감 시간을 줄인다 — 7개를 순차로 부르면 왕복이 7번 쌓인다.
    개별 실패는 빈 리스트가 되고 나머지에 영향을 주지 않는다.
    """
    unique = list(dict.fromkeys(q for q in (queries or []) if q))
    if not unique:
        return {}
    if len(unique) == 1:
        return {unique[0]: search(unique[0], lat, lng, radius_m)}

    results = {}
    with ThreadPoolExecutor(max_workers=min(8, len(unique))) as pool:
        futures = {pool.submit(search, q, lat, lng, radius_m): q for q in unique}
        for future in as_completed(futures):
            query = futures[future]
            try:
                results[query] = future.result()
            except Exception:
                results[query] = []
    return results
