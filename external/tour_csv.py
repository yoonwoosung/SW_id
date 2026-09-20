# external/tour_csv.py — 관광지정보 표준데이터(CSV)에서 좌표 주변 장소를 찾는다.
#
# 충남 올담 API(external/chungnam_api.py)가 9/18 부터 복구되지 않아 같은 성격의
# 공공데이터를 파일로 대신 쓴다. 올담이 열리면 그 모듈을 그대로 살리면 된다.
#
# ★한국관광공사 API 를 대체하지 않는다.★ 대회 필수 요건이라 관광공사는 계속 호출하고,
# 여기서 나온 장소는 그 결과에 '보강'으로만 더한다(services/place_merge).
#
# 파일 이름이 tour_standard 인 이유: 충남 43건만 있는 게 아니라 ★전국 840건★이다.
# (전남 205 · 경남 121 · 부산 68 · 서울 65 … 충남 43)
# chungnam 으로 부르면 다음 사람이 충남 전용으로 오해한다.
import csv
import math
import os
import threading

from common.constants import (
    TOUR_CSV_PATH,
    TOUR_CSV_CONTENT_TYPE,
    TOUR_CSV_SOURCE,
    NEARBY_RESULT_LIMIT,
)

# 한 번 읽어 메모리에 둔다. 840행이라 크지 않고, 요청마다 파일을 파싱할 이유가 없다.
# 앱 시작 시 읽지 않고 처음 필요할 때 읽는다 — 파일이 없거나 깨져도 앱은 떠야 한다.
_places = None
_lock = threading.Lock()

_EARTH_RADIUS_KM = 6371.0


def _csv_path():
    # 작업 디렉터리가 어디든 저장소 기준으로 찾는다(배포 서버는 홈에서 실행된다).
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(root, TOUR_CSV_PATH)


def _to_float(value):
    try:
        return float(str(value).strip())
    except (TypeError, ValueError):
        return None


def _to_int(value):
    try:
        return int(float(str(value).strip()))
    except (TypeError, ValueError):
        return None


def _to_place(row):
    """CSV 한 행을 코스에서 쓰는 형태로. 좌표가 없거나 이름이 없으면 None.

    반환 형식은 external/tour_api._to_place 와 같아야 한다.
    course_builder 와 place_merge 가 두 출처를 구분 없이 다루기 때문이다.
    """
    lat = _to_float(row.get("위도"))
    lng = _to_float(row.get("경도"))
    name = (row.get("관광지명") or "").strip()
    if lat is None or lng is None or not name:
        return None
    # 도로명이 비면 지번으로 넘어간다.
    address = (row.get("소재지도로명주소") or "").strip() or (row.get("소재지지번주소") or "").strip()
    return {
        "name": name,
        "address": address,
        "lat": lat,
        "lng": lng,
        "tel": (row.get("관리기관전화번호") or "").strip() or None,
        # ★관광공사의 cat3(A01010900 같은 코드)와 성격이 다르다.★ 여기는 '관광지'·'관광단지'
        # 두 값뿐인 한글 문자열이라 cat1·cat2 접두사 판정(services/place_score)에 걸리지 않는다.
        # 억지로 코드로 바꾸면 틀린 판정이 되므로 원문을 그대로 둔다 — 조건 점수는 0 이고
        # 거리순 폴백으로 처리된다.
        "category": (row.get("관광지구분") or "").strip() or None,
        "image": None,
        "content_type_id": TOUR_CSV_CONTENT_TYPE,
        "source": TOUR_CSV_SOURCE,
        # 편의시설 판정용으로 실어만 둔다(지금은 아무 데서도 쓰지 않는다).
        # 화장실 651건·주차 498건이 채워져 있어 나중에 연결할 수 있다. docs/AUDIT.md 참고.
        "facilities": (row.get("공공편익시설정보") or "").strip() or None,
        "parking_count": _to_int(row.get("주차가능수")),
    }


def _load():
    """CSV 를 읽어 장소 리스트를 만든다. 어떤 실패에도 빈 리스트를 준다."""
    path = _csv_path()
    try:
        # ★utf-8-sig★ — BOM 이 있든 없든 안전하다. 지금 파일에는 BOM 이 없지만
        # 공공데이터포털 CSV 는 붙어 오는 경우가 흔하고, 그때 utf-8 로 읽으면
        # 첫 컬럼명이 BOM+'시스템키' 가 되어 행 전체를 못 읽는다.
        # 파일을 다시 받아 교체해도 깨지지 않게 해 둔다.
        with open(path, encoding="utf-8-sig", newline="") as handle:
            rows = csv.DictReader(handle)
            return [place for place in (_to_place(row) for row in rows) if place]
    except Exception:
        return []      # 파일 없음·권한·인코딩·형식 오류 — 코스 생성은 그대로 돌아가야 한다


def all_places():
    """로드된 전체 장소. 처음 호출할 때 한 번만 읽는다."""
    global _places
    if _places is None:
        with _lock:
            if _places is None:      # 락 안에서 다시 확인(동시 요청 대비)
                _places = _load()
    return _places


def _distance_km(lat1, lng1, lat2, lng2):
    radians = math.radians
    a = (math.sin(radians(lat2 - lat1) / 2) ** 2
         + math.cos(radians(lat1)) * math.cos(radians(lat2))
         * math.sin(radians(lng2 - lng1) / 2) ** 2)
    return 2 * _EARTH_RADIUS_KM * math.asin(math.sqrt(a))


def find_nearby_places(lat, lng, radius_m, content_type_id=None):
    """좌표+반경 안의 장소를 가까운 순으로. 실패하면 빈 리스트.

    시그니처를 tour_api.find_nearby_places 와 맞춰 호출부가 두 출처를 같은 방식으로
    다룰 수 있게 했다. CSV 는 전부 관광지라, 다른 content_type 을 요구하면
    빈 리스트를 준다(맛집·카페 슬롯에 관광지가 섞이면 안 된다).
    """
    if content_type_id is not None and int(content_type_id) != TOUR_CSV_CONTENT_TYPE:
        return []
    origin_lat, origin_lng = _to_float(lat), _to_float(lng)
    if origin_lat is None or origin_lng is None:
        return []
    try:
        radius_km = float(radius_m) / 1000.0
    except (TypeError, ValueError):
        return []

    near = []
    for place in all_places():
        distance = _distance_km(origin_lat, origin_lng, place["lat"], place["lng"])
        if distance <= radius_km:
            near.append((distance, place))
    near.sort(key=lambda pair: pair[0])
    return [place for _distance, place in near[:NEARBY_RESULT_LIMIT]]
