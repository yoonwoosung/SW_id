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


def experience_nearby_summary(item_id):
    """상세 페이지 우측 '주변 시설' 요약 — 맛집·관광 각 2곳만.

    코스 API와 같은 _collect_places 를 재사용한다(수집 로직 중복 방지).
    외부 API가 실패해도 빈 리스트로 200 을 주어 화면이 '정보 없음'으로 뜨게 한다.
    """
    item = Experience.query.get(item_id)
    if item is None:
        return error_response("EXPERIENCE_NOT_FOUND", "체험을 찾을 수 없습니다.", 404)

    places_by_type = _collect_places(item)

    def top(kind, limit=2):
        places = places_by_type.get(kind) or []
        ranked = sorted(
            (p for p in places if p.get("name")),
            key=lambda p: p.get("distance_km") if p.get("distance_km") is not None else 9999,
        )
        return [{"name": p["name"], "distance_km": p.get("distance_km")} for p in ranked[:limit]]

    return success_response({
        "experience_id": item.id,
        "restaurants": top("restaurant"),
        "attractions": top("attraction"),
    })


def register(app):
    app.add_url_rule('/api/experiences/<int:item_id>/course', 'experience_course', experience_course)
    app.add_url_rule('/api/experiences/<int:item_id>/nearby-summary',
                     'experience_nearby_summary', experience_nearby_summary)
