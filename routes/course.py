# routes/course.py — AI 추천 코스 라우트(체험 주변 장소를 시간순 코스로 구성). 얇게 유지, 로직은 services 호출.
from models import Experience
from common.response import success_response, error_response
from common.constants import COURSE_SEARCH_RADIUS_M, MAX_SEARCH_RADIUS_M, COURSE_SLOTS
from external import tour_api
from services import course_builder
from services.course_reason import build_course_reason


def _fetch_places(experience, content_type):
    # 기본 반경으로 조회하고, 비면 최대 반경으로 한 번 더 시도(시골 농장 대응).
    places = tour_api.find_nearby_places(experience.lat, experience.lng, COURSE_SEARCH_RADIUS_M, content_type)
    if not places:
        places = tour_api.find_nearby_places(experience.lat, experience.lng, MAX_SEARCH_RADIUS_M, content_type)
    return places


def _collect_places(experience):
    # 슬롯에 필요한 contentType별로 주변 장소를 수집(중복 조회 방지). 외부 실패 시 빈 리스트.
    places_by_content = {}
    places_by_type = {}
    for slot in COURSE_SLOTS:
        content_type = slot["content_type"]
        if content_type is None:
            continue
        if content_type not in places_by_content:
            places_by_content[content_type] = _fetch_places(experience, content_type)
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
            "reason": None,
            "items": items,
            "summary": summary,
            "message": "코스를 생성할 수 없습니다. 주변 장소 정보를 불러오지 못했습니다.",
        })

    return success_response({
        "experience_id": item.id,
        "reason": build_course_reason(item, items),
        "items": items,
        "summary": summary,
    })


def register(app):
    app.add_url_rule('/api/experiences/<int:item_id>/course', 'experience_course', experience_course)
