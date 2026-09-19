# routes/course.py — AI 추천 코스 라우트(체험 주변 장소를 시간순 코스로 구성). 얇게 유지, 로직은 services 호출.
from models import Experience
from common.response import success_response, error_response
from common.constants import COURSE_SEARCH_RADIUS_M, MAX_SEARCH_RADIUS_M, COURSE_SLOTS
from external import tour_api
from external import chungnam_api
from services import course_builder
from services import place_merge
from services.course_reason import build_course_reason
from services.thumbnail_service import experience_thumbnail_url


def _fetch_places(experience, content_type, add_chungnam=False):
    """관광공사에서 주변 장소를 가져오고, 충남 체험이면 도 데이터로 보강한다.

    관광공사 호출은 그대로 유지한다(대회 필수 요건이라 호출 기록이 남아야 한다).
    충남 호출이 실패하면 빈 리스트가 와서 관광공사 결과만 남으므로,
    기존 코스 생성은 어느 경우에도 그대로 동작한다.
    """
    # 기본 반경으로 조회하고, 비면 최대 반경으로 한 번 더 시도(시골 농장 대응).
    places = tour_api.find_nearby_places(experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M, content_type)
    if not places:
        places = tour_api.find_nearby_places(experience.lat, experience.lng, MAX_SEARCH_RADIUS_M, content_type)

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


def experience_course(item_id):
    item = Experience.query.get(item_id)
    if item is None:
        return error_response("EXPERIENCE_NOT_FOUND", "체험을 찾을 수 없습니다.", 404)

    places_by_type = _collect_places(item)
    items = course_builder.build_course(item, places_by_type)
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
