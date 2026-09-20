# routes/course.py — AI 추천 코스 라우트(체험 주변 장소를 시간순 코스로 구성). 얇게 유지, 로직은 services 호출.
from flask import request

from models import Experience
from common.response import success_response, error_response
from common.constants import (COURSE_SEARCH_RADIUS_M, MAX_SEARCH_RADIUS_M, COURSE_SLOTS,
                              TOUR_CSV_RADIUS_M)
from common.search_categories import LEAF_CODES
from external import tour_api
from external import chungnam_api
from external import tour_csv
from external import barrier_free_api
from external import pet_travel_api
from services import course_builder
from services import place_merge
from services import place_score
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
            if code and code in LEAF_CODES and code not in seen:
                seen.add(code)
                codes.append(code)
    return codes


def _build_scorer(experience, codes):
    """조건 코드로 장소 점수 함수를 만든다. 못 만들면 None(기존 거리순).

    전용 API 는 조건에 그 항목이 있을 때만 부른다 — 쓰지도 않을 호출로
    일일 한도를 태우지 않기 위해서다. 실패하면 빈 리스트가 되고,
    place_score 가 그 조건을 판정 불가로 빼 남은 조건끼리 가중치를 다시 나눈다.
    """
    if not codes:
        return None

    barrier_free, pet = [], []
    try:
        if place_score.COURSE_RULE_BARRIER_FREE in codes:
            barrier_free = barrier_free_api.find_barrier_free_places(
                experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M)
    except Exception:
        barrier_free = []
    try:
        if any(code in place_score.COURSE_RULE_PET for code in codes):
            pet = pet_travel_api.find_pet_facilities(
                experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M)
    except Exception:
        pet = []

    try:
        api_sets = place_score.build_api_sets(barrier_free, pet)
        return place_score.build_scorer(codes, api_sets)
    except Exception:
        return None      # 점수 계산이 어떤 이유로든 실패하면 기존 코스 생성을 지킨다


def experience_course(item_id):
    item = Experience.query.get(item_id)
    if item is None:
        return error_response("EXPERIENCE_NOT_FOUND", "체험을 찾을 수 없습니다.", 404)

    codes = _selected_codes()
    scorer = _build_scorer(item, codes)
    places_by_type = _collect_places(item)
    items = course_builder.build_course(item, places_by_type, scorer=scorer)
    summary = course_builder.build_course_summary(item)

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
    })


def register(app):
    app.add_url_rule('/api/experiences/<int:item_id>/course', 'experience_course', experience_course)
