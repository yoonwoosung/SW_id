# routes/course.py — AI 추천 코스 라우트(체험 주변 장소를 시간순 코스로 구성). 얇게 유지, 로직은 services 호출.
from flask import request

from models import Experience
from common.response import success_response, error_response
from common.constants import (COURSE_SEARCH_RADIUS_M, MAX_SEARCH_RADIUS_M, COURSE_SLOTS,
                              TOUR_CSV_RADIUS_M)
from common.search_categories import (ALL_CODES, BUDGET_RANGES, CATEGORY_OF_CODE,
                                      LABEL_BY_CODE)
from services.eco_filter import JUDGEABLE_CATEGORIES
from external import tour_api
from external import chungnam_api
from external import tour_csv
from external import kakao_place
from common.constants import (COURSE_ACTIVITY_KAKAO, COURSE_COMPANION_KAKAO,
                              COURSE_COMPANION_CAFE_HINT, COURSE_LEISURE_CODE,
                              COURSE_CONDITION_RETRY_RADIUS_M,
                              COURSE_DURATION_SLOTS,
                              COURSE_SCHEDULE_RADIUS_M, COURSE_ROWS_PER_RADIUS,
                              COURSE_MAX_ROWS, NEARBY_RESULT_LIMIT,
                              COURSE_FACILITY_NEARBY, COURSE_PARTY_RULES,
                              COURSE_PET_KAKAO, TOUR_CONTENT_TYPE_ATTRACTION,
                              TOUR_CONTENT_TYPE_RESTAURANT,
                              TOUR_CAT_CAFE, TOUR_CONTENT_TYPE_LEISURE)
from services.distance import haversine

# 코스 장소 출처 표기(화면 배지). CSV 는 'standard', 충남 올담은 'chungnam'.
KAKAO_SOURCE = 'kakao'
from external import barrier_free_api
from external import pet_travel_api
from services import course_builder
from services import place_merge
from services import place_score
from services import course_estimate
from services.course_reason import build_course_reason
from services.thumbnail_service import experience_thumbnail_url


def _rows_for(radius_m):
    """반경에 맞춘 조회 건수.

    ★반경만 넓히면 결과가 그대로다.★ 관광공사는 거리순으로 numOfRows 만큼 주므로
    건수를 고정하면 반경을 늘려도 '가장 가까운 30건'이 똑같이 온다(실측).
    """
    scale = max(1, int(radius_m) // COURSE_SEARCH_RADIUS_M)
    return min(COURSE_MAX_ROWS, NEARBY_RESULT_LIMIT * min(scale, COURSE_ROWS_PER_RADIUS))


def _max_slots(codes):
    """고른 소요시간에 맞는 슬롯 수. 안 골랐으면 None(전부).

    여러 개를 골랐으면 ★가장 긴 쪽★을 쓴다 — 대분류 안은 OR 이라
    "2~4시간 또는 종일"이면 종일 기준으로 넉넉히 만든다.
    """
    picked = [COURSE_DURATION_SLOTS[c] for c in (codes or [])
              if c in COURSE_DURATION_SLOTS]
    return max(picked) if picked else None


def _search_radius(codes):
    """고른 일정에 맞는 탐색 반경(m). 안 골랐으면 기본값.

    여러 개를 골랐으면 ★가장 넓은 쪽★을 쓴다 — 대분류 안은 OR 이라
    "당일 또는 1박2일"이면 1박2일 기준으로 후보를 넓게 본다.
    """
    picked = [COURSE_SCHEDULE_RADIUS_M[c] for c in (codes or [])
              if c in COURSE_SCHEDULE_RADIUS_M]
    return max(picked) if picked else COURSE_SEARCH_RADIUS_M


def _fetch_places(experience, content_type, add_chungnam=False, radius_m=None):
    """관광공사에서 주변 장소를 가져오고, 공공데이터로 보강한다.

    관광공사 호출은 그대로 유지한다(대회 필수 요건이라 호출 기록이 남아야 한다).
    보강이 실패하면 빈 리스트가 와서 관광공사 결과만 남으므로,
    기존 코스 생성은 어느 경우에도 그대로 동작한다.

    보강 소스 두 가지
      1. 관광지정보 표준데이터 CSV — ★전국★. 관광 슬롯(관광지)에만 더한다.
      2. 충남 올담 API — 충남 체험에만. 서버 점검 중이라 지금은 늘 빈 리스트다.
    """
    # 기본(또는 일정이 요구한) 반경으로 조회하고, 비면 더 넓혀 한 번 더 시도(시골 농장 대응).
    radius_m = radius_m or COURSE_SEARCH_RADIUS_M
    rows = _rows_for(radius_m)
    places = tour_api.find_nearby_places(
        experience.lat, experience.lng, radius_m, content_type, rows)
    if not places:
        wider = max(radius_m, MAX_SEARCH_RADIUS_M)
        places = tour_api.find_nearby_places(
            experience.lat, experience.lng, wider, content_type, _rows_for(wider))

    # CSV 보강: 전국 데이터라 지역을 가리지 않는다. 충남으로 묶으면 오히려
    # 커버리지가 가장 낮은 지역만 쓰게 된다(충남 43건 vs 전남 205건).
    # CSV 는 전부 관광지라 content_type 이 다르면 알아서 빈 리스트를 준다.
    try:
        from_csv = tour_csv.find_nearby_places(
            experience.lat, experience.lng, max(radius_m or 0, TOUR_CSV_RADIUS_M), content_type)
        if from_csv:
            places = place_merge.merge(places, from_csv)
    except Exception:
        pass      # 보강은 '있으면 좋은 것'이다. 실패해도 관광공사 결과로 코스를 만든다

    if not add_chungnam:
        return places

    # chungnam_api 는 내부에서 예외를 삼키지만, 여기서도 한 번 더 막는다.
    # 보강은 '있으면 좋은 것'이라 어떤 이유로든 실패하면 관광공사 결과만 쓴다.
    # 이 보호가 없으면 충남 쪽 버그 하나가 코스 생성 전체를 500 으로 만든다.
    try:
        chungnam = chungnam_api.find_nearby_places(
            experience.lat, experience.lng, radius_m, content_type)
    except Exception:
        return places
    if not chungnam:
        return places
    # 겹치는 장소는 도 데이터를 남긴다(도가 직접 관리해 더 정확하다).
    try:
        return place_merge.merge(places, chungnam)
    except Exception:
        return places


def _collect_places(experience, radius_m=None):
    # 슬롯에 필요한 contentType별로 주변 장소를 수집(중복 조회 방지). 외부 실패 시 빈 리스트.
    places_by_content = {}
    places_by_type = {}
    # 충남 체험일 때만 도 데이터를 더한다. 다른 지역은 기존대로 관광공사만 쓴다.
    add_chungnam = place_merge.is_chungnam(experience)
    for slot in COURSE_SLOTS:
        content_type = slot["content_type"]
        if content_type is None:
            continue
        if content_type not in places_by_content:
            places_by_content[content_type] = _fetch_places(
                experience, content_type, add_chungnam, radius_m)
        places_by_type[slot["type"]] = places_by_content[content_type]
    places_by_type["cafe"] = _cafes_only(places_by_type.get("cafe"))
    return places_by_type


def _cafes_only(places):
    """카페 슬롯 후보를 ★진짜 카페★로 좁힌다. 없으면 원래 목록 그대로.

    카페 슬롯은 맛집과 같은 contentType(39)을 쓴다 — KTO 에 카페 타입이 없다.
    그래서 지금까지 '가까운 음식점 중 두 번째'가 카페 자리에 들어가
    김밥집·순대집이 17:00 에 놓였다(실측).

    분류 코드에는 카페가 있다(A05020900). 안산 반경 10km 음식점 30건 중
    7건이 카페였다. ★한 곳도 없으면 좁히지 않는다★ — 빈 슬롯보다 낫다.
    """
    places = places or []
    cafes = [p for p in places
             if str(p.get("category") or "").startswith(TOUR_CAT_CAFE)]
    return cafes or places


def _selected_codes():
    """사용자가 고른 조건 코드를 ★고른 순서대로★ 읽는다.

    cond_order 는 프론트가 클릭 순서를 그대로 이어 붙인 값이다.
    쿼리스트링의 cond_* 만으로는 대분류별로 묶여 있어 순서를 알 수 없다.
    cond_order 가 없으면(옛 링크·직접 호출) 조건을 무시하고 기존 거리순을 쓴다.
    """
    raw = request.args.getlist("cond_order")
    codes, seen = [], set()
    for chunk in raw:
        for code in str(chunk).split(","):
            code = code.strip()
            # 트리에 없는 코드는 버린다(오타·조작 방지). 중복은 첫 순서만 남긴다.
            # ★잎이 아니라 전체 노드로 검증한다★ — 도(chungnam)·광역시 그룹(metro)·
            # 반려견 '전체'(pet_allowed)는 잎이 아니지만 고를 수 있고 판정도 된다.
            if code and code in ALL_CODES and code not in seen:
                seen.add(code)
                codes.append(code)
    return codes


def _activity_places(experience, codes):
    """고른 액티비티에 해당하는 카카오 장소를 찾는다. 반환: (장소 리스트, {코드: 이름집합})

    ★판정만으로는 부족하다.★ 승마장·낚시터는 관광공사 관광지 목록에 없어서
    후보 풀에 없으면 아무리 점수를 매겨도 코스에 들어올 수 없다.
    그래서 후보로 '더하고'(관광 슬롯) 동시에 판정용 이름 집합도 만든다.
    관광공사 결과는 그대로 남는다 — 대체가 아니라 보강이다.

    고른 항목만 부른다(안 고른 조건으로 호출을 태우지 않게). 결과는 1시간 캐싱된다.
    """
    places, names = [], {}
    for code in codes or []:
        rule = COURSE_ACTIVITY_KAKAO.get(code)
        if not rule:
            continue
        keyword, hint = rule
        try:
            found = [p for p in kakao_place.search(
                        keyword, experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M)
                     if hint in (p.get("category") or "")]
        except Exception:
            found = []
        names[code] = {"".join(str(p["name"]).split()) for p in found}
        for place in found:
            places.append(dict(place, content_type_id=TOUR_CONTENT_TYPE_ATTRACTION,
                               source=KAKAO_SOURCE))
    return places, names


def _nothing_matches(scorer, places_by_type):
    """고른 조건에 맞는 장소가 후보에 하나도 없는지."""
    if scorer is None:
        return False
    for places in (places_by_type or {}).values():
        for place in places or []:
            try:
                if scorer(place) > 0:
                    return False
            except Exception:
                continue      # 점수 계산 실패는 '안 맞음'으로 본다
    return True


def _widen_attraction(experience, codes, places_by_type):
    """조건에 맞는 장소가 0건이면 ★관광 후보만★ 더 멀리까지 다시 찾는다.

    천안 병천은 반경 10km 안에 체험마을(수확)이 0건이지만 20km 부터 5건이
    있다(실측). 지금까지는 그대로 거리순으로 떨어져 "조건이 안 먹는다"로
    보였다.

    ★관광 슬롯만 다시 부른다.★ 조건 대부분이 관광지 분류 위에 세워져 있고,
    맛집·카페까지 다시 부르면 호출이 세 배가 된다.
    ★한 번만 넓힌다.★ 신규 호출이 0.3초라 단계를 반복하면 체감이 나빠진다.
    결과는 1시간 캐싱되므로 같은 체험을 다시 열 때는 비용이 없다.
    """
    radius_m = COURSE_CONDITION_RETRY_RADIUS_M
    try:
        wider = _fetch_places(experience, TOUR_CONTENT_TYPE_ATTRACTION,
                              place_merge.is_chungnam(experience), radius_m)
        wider += _leisure_places(experience, codes, radius_m)
    except Exception:
        return places_by_type     # ★넓히기 실패가 코스 생성을 막으면 안 된다.★
    if not wider:
        return places_by_type
    try:
        places_by_type["attraction"] = place_merge.merge(
            places_by_type.get("attraction") or [], wider)
    except Exception:
        pass          # 보강 실패는 코스 생성을 막지 않는다
    return places_by_type


def _leisure_places(experience, codes, radius_m=None):
    """액티브를 고른 경우에만 레포츠(28) 후보를 가져온다.

    ★A03(레포츠)은 관광지(12)에 한 건도 없다.★ 실측으로 확인했다 —
    천안 20km 기준 관광지 60건 중 A03 은 0건, 레포츠 26건은 전부 A03 이다.
    후보를 12·39 만 모아서 액티브 조건이 어느 지역에서도 0건이었다
    (천안·예산·논산·영월·남원·양평 모두 0건).

    ★고른 경우에만 부른다.★ 항상 더하면 조건 없이 볼 때 골프장·캠핑장이
    상위에 올라와 기본 코스가 나빠진다(반려견·주차에서 쓴 방식과 같다).
    """
    if COURSE_LEISURE_CODE not in (codes or []):
        return []
    radius_m = radius_m or COURSE_SEARCH_RADIUS_M
    try:
        return tour_api.find_nearby_places(
            experience.lat, experience.lng, radius_m,
            TOUR_CONTENT_TYPE_LEISURE, _rows_for(radius_m)) or []
    except Exception:
        return []      # 보강 실패는 코스 생성을 막지 않는다


def _companion_places(experience, codes):
    """동반구성에 맞는 장소를 찾는다. 반환: ({슬롯: 장소 리스트}, {코드: 이름집합})

    ★호출을 줄인다.★ 유형당 키워드가 2개이고, 유형 사이에 겹치는 검색어
    (공원·카페)는 한 번만 부른다. 7개를 다 골라도 검색어는 7개뿐이다.
    병렬로 돌려 체감 시간도 줄인다(실측 7종 0.14초).

    ★카페로 나온 곳은 카페 슬롯으로 보낸다.★ 예전에는 전부 관광 슬롯에
    넣었다 — 카페 슬롯이 아무 음식점이나 받던 때라 관광 자리가 카페로
    채워질까 봐 막아 둔 것이었다. 이제 카페 슬롯이 카페만 받으므로
    (_cafes_only) 제자리로 보낼 수 있고, 그래야 동반유형이 17:00 을 바꾼다.

    나머지(공원·문화재·전망대·박물관 등)는 그대로 관광 슬롯이다.
    """
    wanted = [code for code in (codes or []) if code in COURSE_COMPANION_KAKAO]
    if not wanted:
        return [], {}

    queries = [kw for code in wanted for kw, _hint in COURSE_COMPANION_KAKAO[code]]
    try:
        found = kakao_place.search_many(
            queries, experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M)
    except Exception:
        return [], {}

    places, names = [], {}
    for code in wanted:
        matched = []
        for keyword, hint in COURSE_COMPANION_KAKAO[code]:
            matched += [p for p in found.get(keyword, [])
                        if hint in (p.get("category") or "")]
        names[code] = {"".join(str(p["name"]).split()) for p in matched if p.get("name")}
        places += matched

    # 같은 장소가 여러 유형에 걸릴 수 있다(카페는 혼자·친구 모두). 한 번만 넣는다.
    seen, by_slot = set(), {"attraction": [], "cafe": []}
    for place in places:
        key = "".join(str(place.get("name") or "").split())
        if not key or key in seen:
            continue
        seen.add(key)
        is_cafe = COURSE_COMPANION_CAFE_HINT in (place.get("category") or "")
        extra = {"source": KAKAO_SOURCE}
        if is_cafe:
            # 카페 슬롯이 분류 코드로 후보를 거르므로(_cafes_only) 카카오 결과에도
            # 같은 코드를 달아 준다. 안 달면 제 슬롯에 넣자마자 다시 걸러진다.
            extra.update(content_type_id=TOUR_CONTENT_TYPE_RESTAURANT,
                         category=TOUR_CAT_CAFE)
        else:
            # 관광 슬롯으로 가는 곳은 카카오 분류 문자열을 그대로 둔다(정보 보존).
            extra.update(content_type_id=TOUR_CONTENT_TYPE_ATTRACTION)
        by_slot["cafe" if is_cafe else "attraction"].append(dict(place, **extra))
    return by_slot, names


def _pet_places(experience, codes):
    """반려견 조건을 고르면 동반 가능한 장소를 찾는다.

    반환: ({슬롯: 장소 리스트}, 이름 집합)

    ★반려동물 동반여행 API 를 우선한다.★ 키에 활용신청이 승인되면 그쪽이
    결과를 주고, 그때는 카카오를 부르지 않는다. 지금은 403 이라 빈 리스트다.

    카카오 '애견동반' 결과는 대부분 음식점·카페다(실측 199건 중 관광지 1건).
    ★종류에 맞는 슬롯으로 나눈다.★ 예전에는 맛집·카페 두 슬롯에 통째로
    넣어서, 애견동반 중식당이 17:00 카페 자리에 오고 애견동반 카페가
    12:30 점심 자리에 오는 일이 실제로 있었다(안산 컴포즈커피가 점심).

      음식점 > 카페 …        → 카페 슬롯
      음식점 > 중식/양식 …   → 맛집 슬롯
    """
    if not any(code in place_score.COURSE_RULE_PET for code in codes or []):
        return {}, set()

    try:
        official = pet_travel_api.find_pet_facilities(
            experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M)
    except Exception:
        official = []
    if official:
        return {}, {"".join(str(p.get("name") or "").split()) for p in official if p.get("name")}

    keyword, hint = COURSE_PET_KAKAO
    try:
        found = [p for p in kakao_place.search(
                    keyword, experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M)
                 if hint in (p.get("category") or "")]
    except Exception:
        found = []

    by_slot = {"restaurant": [], "cafe": []}
    for place in found:
        is_cafe = COURSE_COMPANION_CAFE_HINT in (place.get("category") or "")
        extra = {"content_type_id": TOUR_CONTENT_TYPE_RESTAURANT, "source": KAKAO_SOURCE}
        if is_cafe:
            # 카페 슬롯이 분류 코드로 거르므로(_cafes_only) 같은 코드를 달아 준다.
            extra["category"] = TOUR_CAT_CAFE
        by_slot["cafe" if is_cafe else "restaurant"].append(dict(place, **extra))
    return by_slot, {"".join(str(p["name"]).split()) for p in found}


def _facility_names(experience, codes, places_by_type):
    """편의시설을 좌표 근접으로 판정한다. 반환: {조건코드: {장소이름, ...}}

    ★주차장을 코스 후보로 넣지 않는다.★ 주차장이 코스 항목이 되면 이상하다.
    카카오에서 찾은 주차장 좌표와 후보 장소 좌표를 대어, 반경(기본 200m) 안에
    주차장이 있으면 그 장소를 '주차 가능'으로 본다. 호출은 조건당 1회다.
    """
    # 인원수 3~4명·5명 이상도 주차 조회가 필요하다. 같은 결과를 재사용한다
    # (조회는 한 번뿐이고 캐시도 공유한다).
    needs = set(codes or [])
    if any(COURSE_PARTY_RULES.get(c, {}).get("parking") for c in needs):
        needs.add("parking")

    result = {}
    for code in needs:
        rule = COURSE_FACILITY_NEARBY.get(code)
        if not rule:
            continue
        keyword, hint, radius_m = rule
        try:
            spots = [p for p in kakao_place.search(
                        keyword, experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M)
                     if hint in (p.get("category") or "")]
        except Exception:
            spots = []
        coords = []
        for spot in spots:
            lat, lng = _to_float(spot.get("lat")), _to_float(spot.get("lng"))
            if lat is not None and lng is not None:
                coords.append((lat, lng))
        if not coords:
            continue

        names = set()
        limit_km = radius_m / 1000.0
        for candidates in (places_by_type or {}).values():
            for place in candidates:
                lat, lng = _to_float(place.get("lat")), _to_float(place.get("lng"))
                if lat is None or lng is None:
                    continue
                if any(haversine(lat, lng, sy, sx) <= limit_km for sy, sx in coords):
                    names.add("".join(str(place.get("name") or "").split()))
        # CSV 장소는 자체 시설 정보가 있으면 그것도 인정한다(카카오보다 정확하다).
        for candidates in (places_by_type or {}).values():
            for place in candidates:
                facilities = place.get("facilities") or ""
                if "주차" in facilities or (place.get("parking_count") or 0) > 0:
                    names.add("".join(str(place.get("name") or "").split()))
        result[code] = names
    return result


def _to_float(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _build_scorer(experience, codes, activity_names=None, pet_names=None,
                  facility_names=None, companion_names=None):
    """조건 코드로 장소 점수 함수를 만든다. 못 만들면 None(기존 거리순).

    전용 API 는 조건에 그 항목이 있을 때만 부른다 — 쓰지도 않을 호출로
    일일 한도를 태우지 않기 위해서다. 실패하면 빈 리스트가 되고,
    place_score 가 그 조건을 판정 불가로 빼 남은 조건끼리 가중치를 다시 나눈다.
    """
    if not codes:
        return None, {}

    barrier_free = []
    try:
        if place_score.COURSE_RULE_BARRIER_FREE in codes:
            barrier_free = barrier_free_api.find_barrier_free_places(
                experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M)
    except Exception:
        barrier_free = []

    # 반려견은 이름 집합을 이미 만들어 받는다(_pet_places).
    pet_sets = {code: set(pet_names or ()) for code in place_score.COURSE_RULE_PET}

    try:
        api_sets = place_score.build_api_sets(
            barrier_free, None, activity_names, facility_names)
        for code, names in (companion_names or {}).items():
            if names:
                api_sets[code] = names
        for code, names in pet_sets.items():
            if names:
                api_sets[code] = names
        return place_score.build_scorer(codes, api_sets), api_sets
    except Exception:
        return None, {}   # 점수 계산이 어떤 이유로든 실패하면 기존 코스 생성을 지킨다


# 코스 장소에는 반영되지 않는 조건을 왜 그런지 설명한다.
# ★조용히 무시하면 "조건을 걸었는데 안 바뀐다"로만 보인다.★
_IGNORED_CODE_REASON = {
    "party_2": "제한 없이 모든 장소가 대상입니다",
}
_IGNORED_REASON = {
    "companion_type": "아직 코스 장소에 반영되지 않습니다",
    # 소요시간 대분류는 슬롯 수로 반영되지만, 슬롯 수를 정할 수 없는
    # 선택지('1시간 이내'·'기타')만 여기로 떨어진다. 둘 다 화면에선 감춰져 있다.
    "duration_hours": "코스 길이를 정할 수 없어 반영하지 않습니다",
}

# ★점수가 아니라 '필터'로 반영되는 조건.★ 가중치를 주면 아무것도 맞히지
# 못하면서 다른 조건의 몫만 줄인다. 대신 후보를 거르거나 넓혀 코스를 바꾼다.
# 반영은 되므로 목록에 넣되 비율 대신 역할을 적는다.
# 근거가 추정인 조건. 화면에 '예상'이라고 밝힌다.
_ESTIMATED_CODES = {"restroom", "nursing_room"}

_FILTER_ROLE = {
    "budget_range": "예산 안에 드는 장소를 고릅니다",
    "schedule": "더 먼 곳까지 후보로 봅니다",
    "duration_hours": "코스에 넣을 장소 수를 맞춥니다",
    # ★교통수단은 점수가 아니라 추정 기준으로 반영된다.★ 이걸 빼 두면
    # "근처에 해당하는 장소 정보를 찾지 못했습니다"로 떠서, 실제로는
    # 이동시간·교통비에 반영되는데 안 되는 것처럼 보인다.
    "transport": "이동시간과 교통비를 이 기준으로 계산합니다",
}

# ★코스 장소가 아니라 '체험 목록'을 거르는 조건.★ (_COURSE_ONLY 의 반대)
# Experience 컬럼으로 실제 판정되지만 코스 장소에는 쓰이지 않는다. 이걸
# 밝히지 않으면 "근처에 해당하는 장소 정보를 찾지 못했습니다"로 떠서,
# 실제로는 반영되는데 안 되는 것처럼 보인다.
_LIST_ONLY_ROLE = "체험 목록을 거릅니다 (코스 장소에는 반영되지 않습니다)"
_LIST_ONLY_CODES = frozenset({"wifi", "pesticide_free", "organic", "pet_not_allowed"})


def _filter_role(code):
    if code in _LIST_ONLY_CODES:
        return _LIST_ONLY_ROLE
    category = CATEGORY_OF_CODE.get(code)
    # 소요시간은 ★슬롯 수를 아는 선택지만★ 반영된다. 나머지는 반영 목록에
    # 넣으면 "반영했다"는 거짓말이 되므로 미반영으로 보낸다.
    if category == "duration_hours" and code not in COURSE_DURATION_SLOTS:
        return None
    return _FILTER_ROLE.get(category)
# 코스 장소에만 반영되고 ★체험 목록은 거르지 못하는★ 대분류.
# (activity_type 컬럼을 저장하는 코드가 없어 체험은 전부 NULL 이다)
_COURSE_ONLY = {"activity", "experience_type", "mood", "season"}


def _budget_for_places(codes, experience):
    """고른 예산대에서 ★장소에 쓸 수 있는 금액★(1인). 안 골랐으면 None.

    예산대는 코스 총비용 기준이므로 체험비와 교통비 추정을 먼저 뺀다.
    여러 구간을 골랐으면 가장 넉넉한 쪽을 쓴다(대분류 안은 OR 이다).
    빼고 나면 음수가 될 수 있다 — 그때는 0 으로 두고, 그래도 가장 싼 장소는
    넣는다(빈 코스보다 낫다).
    """
    ranges = [BUDGET_RANGES[c] for c in (codes or []) if c in BUDGET_RANGES]
    if not ranges:
        return None
    # high 가 None(상한 없음)이면 사실상 제한이 없다.
    if any(high is None for _low, high in ranges):
        return None
    ceiling = max(high for _low, high in ranges)

    spent = int(getattr(experience, "cost", 0) or 0)
    # 교통비는 코스를 만들기 전이라 정확히 모른다. 대중교통 3구간으로 잡는다
    # (슬롯이 4개라 이동이 3번이다). 실제 값은 코스 완성 뒤 다시 계산된다.
    spent += course_estimate.travel_cost(0, 3, course_estimate.COURSE_DEFAULT_TRANSPORT)
    return max(0, ceiling - spent)


def _pet_cafe_missing(codes, pet_places, items):
    """반려견을 골랐는데 ★카페 슬롯만★ 동반 불가로 채워졌는지.

    슬롯 성격을 지키느라(카페 시간에 중식당을 넣지 않느라) 근처에 애견동반
    카페가 없으면 일반 카페로 떨어진다. 조용히 넘어가면 사용자가 강아지를
    데리고 갔다가 못 들어간다. 화면에 알린다.
    """
    if not any(code in place_score.COURSE_RULE_PET for code in codes or []):
        return False
    if (pet_places or {}).get("cafe"):
        return False      # 애견동반 카페를 후보로 넣었다 — 알릴 것이 없다
    return any(it.get("type") == "cafe" for it in items or [])


def _condition_report(codes, api_sets, items, budget_over=False,
                      pet_cafe_missing=False):
    """반영된 조건·반영되지 않은 조건·폴백 여부를 화면에 설명할 형태로 만든다."""
    weights = place_score.applied_weights(codes, api_sets)

    applied = [{
        "code": code,
        "label": LABEL_BY_CODE.get(code, code),
        "percent": weights[code],
        # 체험 목록은 못 거르고 코스 장소에만 쓰이는 조건은 그렇다고 밝힌다.
        "course_only": CATEGORY_OF_CODE.get(code) in _COURSE_ONLY,
        # 실제 데이터가 아니라 장소 종류로 추정한 조건임을 밝힌다.
        "estimated": code in _ESTIMATED_CODES,
    } for code in codes if code in weights]

    for code in codes:
        role = _filter_role(code)
        if role and code not in weights:
            applied.append({"code": code, "label": LABEL_BY_CODE.get(code, code),
                            "percent": None, "course_only": False, "role": role})

    ignored = []
    for code in codes:
        if code in weights or _filter_role(code):
            continue
        category = CATEGORY_OF_CODE.get(code)
        reason = _IGNORED_CODE_REASON.get(code) or _IGNORED_REASON.get(category)
        if reason is None:
            reason = ("근처에 해당하는 장소 정보를 찾지 못했습니다"
                      if category in JUDGEABLE_CATEGORIES or category in _COURSE_ONLY
                      else "아직 반영되지 않습니다")
        ignored.append({"code": code, "label": LABEL_BY_CODE.get(code, code),
                        "reason": reason})

    # 조건을 반영했는데 맞는 장소가 하나도 없으면 거리순으로 떨어진다.
    # 지금까지 조용히 일어나 사용자는 "조건이 무시됐다"고만 느꼈다.
    #
    # ★'점수로 반영되는 조건'이 있을 때만 폴백을 따진다.★ 예산대·일정·
    # 소요시간·교통수단은 장소에 점수를 매기지 않아 match_score 가 아예 없다.
    # 이걸 구분하지 않으면 그 조건만 골랐을 때 잘 동작하는데도
    # "조건에 맞는 장소가 근처에 없다"는 거짓 경고가 뜬다(배포 서버에서 재현).
    scored = [i for i in (items or []) if i.get("type") != "experience"]
    matched_any = any((i.get("match_score") or 0) > 0 for i in scored)
    has_scored_condition = any(a.get("percent") is not None for a in applied)

    return {
        "applied": applied,
        "ignored": ignored,
        "fell_back": has_scored_condition and not matched_any,
        # 예산 안에 드는 장소가 없어 넘겼을 때 화면이 안내한다.
        "budget_over": bool(budget_over),
        # 애견동반 카페가 근처에 없어 일반 카페로 채웠을 때 화면이 안내한다.
        "pet_cafe_missing": bool(pet_cafe_missing),
    }


def experience_course(item_id):
    item = Experience.query.get(item_id)
    if item is None:
        return error_response("EXPERIENCE_NOT_FOUND", "체험을 찾을 수 없습니다.", 404)

    codes = _selected_codes()
    activity_places, activity_names = _activity_places(item, codes)
    pet_places, pet_names = _pet_places(item, codes)
    companion_places, companion_names = _companion_places(item, codes)
    transport = course_estimate.normalize_transport(codes)
    radius_m = _search_radius(codes)
    places_by_type = _collect_places(item, radius_m)

    # 레포츠(28)는 액티브를 골랐을 때만 관광 슬롯에 더한다.
    leisure_places = _leisure_places(item, codes, radius_m)
    if leisure_places:
        try:
            places_by_type["attraction"] = place_merge.merge(
                places_by_type.get("attraction") or [], leisure_places)
        except Exception:
            pass
    # 액티비티 장소는 관광 슬롯 후보에 더한다(맛집·카페에 승마장이 섞이면 안 된다).
    if activity_places:
        try:
            places_by_type["attraction"] = place_merge.merge(
                places_by_type.get("attraction") or [], activity_places)
        except Exception:
            pass      # 보강 실패는 코스 생성을 막지 않는다
    # 동반구성 장소는 종류에 맞는 슬롯에 더한다(카페는 카페, 나머지는 관광).
    for slot, found in (companion_places or {}).items():
        if not found:
            continue
        try:
            places_by_type[slot] = place_merge.merge(
                places_by_type.get(slot) or [], found)
        except Exception:
            pass      # 보강 실패는 코스 생성을 막지 않는다
    # 반려견 동반 장소는 종류에 맞는 슬롯에 더한다(카페는 카페, 식당은 맛집).
    for slot, found in (pet_places or {}).items():
        if not found:
            continue
        try:
            places_by_type[slot] = place_merge.merge(
                places_by_type.get(slot) or [], found)
        except Exception:
            pass      # 보강 실패는 코스 생성을 막지 않는다

    # 편의시설은 후보를 모은 뒤에 판정한다(후보 좌표가 있어야 근접 판정이 된다).
    try:
        facility_names = _facility_names(item, codes, places_by_type)
    except Exception:
        facility_names = {}
    scorer, _last_api_sets = _build_scorer(
        item, codes, activity_names, pet_names, facility_names, companion_names)

    # 조건에 맞는 장소가 하나도 없으면 관광 후보를 더 멀리까지 찾아본다.
    if _nothing_matches(scorer, places_by_type):
        places_by_type = _widen_attraction(item, codes, places_by_type)
        try:
            facility_names = _facility_names(item, codes, places_by_type)
        except Exception:
            pass      # 넓힌 뒤 편의시설 재판정 실패는 무시하고 기존 값을 쓴다
        scorer, _last_api_sets = _build_scorer(
            item, codes, activity_names, pet_names, facility_names, companion_names)

    budget_left = _budget_for_places(codes, item)
    max_slots = _max_slots(codes)
    items = course_builder.build_course(item, places_by_type, scorer=scorer,
                                        budget_left=budget_left, max_slots=max_slots)
    budget_over = False
    if budget_left is not None:
        spent = sum(course_estimate.place_price(i) for i in items)
        budget_over = spent > budget_left

    try:
        conditions = _condition_report(
            codes, _last_api_sets, items, budget_over,
            _pet_cafe_missing(codes, pet_places, items))
    except Exception:
        conditions = None      # 설명 생성 실패가 코스를 막지 않는다
    # 시간·비용 추정이 실패해도 코스는 그대로 나와야 한다.
    try:
        estimate = course_estimate.estimate(items, getattr(item, "cost", 0) or 0, transport)
    except Exception:
        estimate = None
    summary = course_builder.build_course_summary(item, estimate)

    # ★'체험만' 코스는 실패가 아니다.★ 사용자가 소요시간을 짧게 골라 슬롯을
    # 하나로 줄인 경우라, 이때까지 실패 안내를 띄우면 안 된다.
    wants_places = max_slots is None or max_slots > 1
    has_places = any(it.get("type") != "experience" for it in items)
    if wants_places and not has_places:
        # 외부 장소를 못 가져와도 화면이 죽지 않게 200 + 안내 메시지로 응답.
        return success_response({
            "experience_id": item.id,
            "thumbnail_url": experience_thumbnail_url(item),
            "reason": None,
            "items": items,
            "summary": summary,
            "message": "코스를 생성할 수 없습니다. 주변 장소 정보를 불러오지 못했습니다.",
        })

    return success_response({
        "experience_id": item.id,
        "thumbnail_url": experience_thumbnail_url(item),
        "reason": build_course_reason(item, items),
        "items": items,
        "summary": summary,
        "conditions": conditions,
    })


def register(app):
    app.add_url_rule('/api/experiences/<int:item_id>/course', 'experience_course', experience_course)
