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
                              COURSE_FACILITY_NEARBY, COURSE_PARTY_RULES,
                              COURSE_PET_KAKAO, TOUR_CONTENT_TYPE_ATTRACTION,
                              TOUR_CONTENT_TYPE_RESTAURANT)
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


def _fetch_places(experience, content_type, add_chungnam=False):
    """관광공사에서 주변 장소를 가져오고, 공공데이터로 보강한다.

    관광공사 호출은 그대로 유지한다(대회 필수 요건이라 호출 기록이 남아야 한다).
    보강이 실패하면 빈 리스트가 와서 관광공사 결과만 남으므로,
    기존 코스 생성은 어느 경우에도 그대로 동작한다.

    보강 소스 두 가지
      1. 관광지정보 표준데이터 CSV — ★전국★. 관광 슬롯(관광지)에만 더한다.
      2. 충남 올담 API — 충남 체험에만. 서버 점검 중이라 지금은 늘 빈 리스트다.
    """
    # 기본 반경으로 조회하고, 비면 최대 반경으로 한 번 더 시도(시골 농장 대응).
    places = tour_api.find_nearby_places(experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M, content_type)
    if not places:
        places = tour_api.find_nearby_places(experience.lat, experience.lng, MAX_SEARCH_RADIUS_M, content_type)

    # CSV 보강: 전국 데이터라 지역을 가리지 않는다. 충남으로 묶으면 오히려
    # 커버리지가 가장 낮은 지역만 쓰게 된다(충남 43건 vs 전남 205건).
    # CSV 는 전부 관광지라 content_type 이 다르면 알아서 빈 리스트를 준다.
    try:
        from_csv = tour_csv.find_nearby_places(
            experience.lat, experience.lng, TOUR_CSV_RADIUS_M, content_type)
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
            experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M, content_type)
    except Exception:
        return places
    if not chungnam:
        return places
    # 겹치는 장소는 도 데이터를 남긴다(도가 직접 관리해 더 정확하다).
    try:
        return place_merge.merge(places, chungnam)
    except Exception:
        return places


def _collect_places(experience):
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
            places_by_content[content_type] = _fetch_places(experience, content_type, add_chungnam)
        places_by_type[slot["type"]] = places_by_content[content_type]
    return places_by_type


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


def _companion_places(experience, codes):
    """동반구성에 맞는 장소를 찾는다. 반환: (장소 리스트, {코드: 이름집합})

    ★호출을 줄인다.★ 유형당 키워드가 2개이고, 유형 사이에 겹치는 검색어
    (공원·카페)는 한 번만 부른다. 7개를 다 골라도 검색어는 7개뿐이다.
    병렬로 돌려 체감 시간도 줄인다(실측 7종 0.14초).

    결과는 대부분 카페·공원·문화재라 ★관광 슬롯★ 후보로 더한다.
    카페 키워드로 나온 곳은 맛집·카페 슬롯에도 맞지만, 슬롯을 늘리면
    관광 자리가 카페로 채워질 수 있어 관광 슬롯만 보강한다.
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
    seen, unique = set(), []
    for place in places:
        key = "".join(str(place.get("name") or "").split())
        if key and key not in seen:
            seen.add(key)
            unique.append(dict(place, content_type_id=TOUR_CONTENT_TYPE_ATTRACTION,
                               source=KAKAO_SOURCE))
    return unique, names


def _pet_places(experience, codes):
    """반려견 조건을 고르면 동반 가능한 장소를 찾는다. 반환: (장소 리스트, 이름 집합)

    ★반려동물 동반여행 API 를 우선한다.★ 키에 활용신청이 승인되면 그쪽이
    결과를 주고, 그때는 카카오를 부르지 않는다. 지금은 403 이라 빈 리스트다.

    카카오 '애견동반' 결과는 대부분 음식점·카페다(실측 199건 중 관광지 1건).
    그래서 ★맛집·카페 슬롯★ 후보로 더한다 — 관광 슬롯에 넣으면 카페가
    관광지 자리에 들어간다.
    """
    if not any(code in place_score.COURSE_RULE_PET for code in codes or []):
        return [], set()

    try:
        official = pet_travel_api.find_pet_facilities(
            experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M)
    except Exception:
        official = []
    if official:
        return [], {"".join(str(p.get("name") or "").split()) for p in official if p.get("name")}

    keyword, hint = COURSE_PET_KAKAO
    try:
        found = [p for p in kakao_place.search(
                    keyword, experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M)
                 if hint in (p.get("category") or "")]
    except Exception:
        found = []
    places = [dict(p, content_type_id=TOUR_CONTENT_TYPE_RESTAURANT, source=KAKAO_SOURCE)
              for p in found]
    return places, {"".join(str(p["name"]).split()) for p in found}


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
    "budget_range": "체험 목록에만 적용됩니다",
    "companion_type": "아직 코스 장소에 반영되지 않습니다",
    "schedule": "아직 반영되지 않습니다",
    "duration_hours": "아직 반영되지 않습니다",
}
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


def _condition_report(codes, api_sets, items, budget_over=False):
    """반영된 조건·반영되지 않은 조건·폴백 여부를 화면에 설명할 형태로 만든다."""
    weights = place_score.applied_weights(codes, api_sets)

    applied = [{
        "code": code,
        "label": LABEL_BY_CODE.get(code, code),
        "percent": weights[code],
        # 체험 목록은 못 거르고 코스 장소에만 쓰이는 조건은 그렇다고 밝힌다.
        "course_only": CATEGORY_OF_CODE.get(code) in _COURSE_ONLY,
    } for code in codes if code in weights]

    # ★예산대는 점수가 아니라 '필터'다.★ 가중치를 주면 아무것도 맞히지 못하면서
    # 다른 조건의 몫만 줄인다. 대신 장소 단가로 후보를 걸러 코스를 바꾼다.
    # 반영은 되므로 목록에는 넣되 비율 대신 역할을 적는다.
    for code in codes:
        if code in BUDGET_RANGES:
            applied.append({"code": code, "label": LABEL_BY_CODE.get(code, code),
                            "percent": None, "course_only": False,
                            "role": "예산 안에 드는 장소를 고릅니다"})

    ignored = []
    for code in codes:
        if code in weights or code in BUDGET_RANGES:
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
    scored = [i for i in (items or []) if i.get("type") != "experience"]
    matched_any = any((i.get("match_score") or 0) > 0 for i in scored)

    return {
        "applied": applied,
        "ignored": ignored,
        "fell_back": bool(applied) and not matched_any,
        # 예산 안에 드는 장소가 없어 넘겼을 때 화면이 안내한다.
        "budget_over": bool(budget_over),
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
    places_by_type = _collect_places(item)

    # 액티비티 장소는 관광 슬롯 후보에 더한다(맛집·카페에 승마장이 섞이면 안 된다).
    if activity_places:
        try:
            places_by_type["attraction"] = place_merge.merge(
                places_by_type.get("attraction") or [], activity_places)
        except Exception:
            pass      # 보강 실패는 코스 생성을 막지 않는다
    # 동반구성 장소(카페·공원·문화재 등)는 관광 슬롯에 더한다.
    if companion_places:
        try:
            places_by_type["attraction"] = place_merge.merge(
                places_by_type.get("attraction") or [], companion_places)
        except Exception:
            pass
    # 반려견 동반 장소는 대부분 음식점·카페라 그 두 슬롯에 더한다.
    if pet_places:
        for slot in ("restaurant", "cafe"):
            try:
                places_by_type[slot] = place_merge.merge(
                    places_by_type.get(slot) or [], pet_places)
            except Exception:
                pass

    # 편의시설은 후보를 모은 뒤에 판정한다(후보 좌표가 있어야 근접 판정이 된다).
    try:
        facility_names = _facility_names(item, codes, places_by_type)
    except Exception:
        facility_names = {}
    scorer, _last_api_sets = _build_scorer(
        item, codes, activity_names, pet_names, facility_names, companion_names)
    budget_left = _budget_for_places(codes, item)
    items = course_builder.build_course(item, places_by_type, scorer=scorer,
                                        budget_left=budget_left)
    budget_over = False
    if budget_left is not None:
        spent = sum(course_estimate.place_price(i) for i in items)
        budget_over = spent > budget_left

    try:
        conditions = _condition_report(codes, _last_api_sets, items, budget_over)
    except Exception:
        conditions = None      # 설명 생성 실패가 코스를 막지 않는다
    # 시간·비용 추정이 실패해도 코스는 그대로 나와야 한다.
    try:
        estimate = course_estimate.estimate(items, getattr(item, "cost", 0) or 0, transport)
    except Exception:
        estimate = None
    summary = course_builder.build_course_summary(item, estimate)

    has_places = any(it.get("type") != "experience" for it in items)
    if not has_places:
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
