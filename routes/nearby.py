# routes/nearby.py — 주변 탐색 도메인 라우트(체험 주변 반려동물/무장애/의료 시설 조회).
from flask import request

from models import Experience
from common.response import success_response, error_response
from common.constants import DEFAULT_SEARCH_RADIUS_M, MAX_SEARCH_RADIUS_M
from services import nearby_service


def _radius_from_request():
    # ?radius=미터 (없거나 잘못된 값이면 기본값), 최대 반경으로 상한 제한.
    raw = request.args.get("radius", DEFAULT_SEARCH_RADIUS_M, type=int)
    if raw is None:
        raw = DEFAULT_SEARCH_RADIUS_M
    return max(1, min(raw, MAX_SEARCH_RADIUS_M))


def _get_experience_or_error(item_id):
    item = Experience.query.get(item_id)
    if item is None:
        return None, error_response("EXPERIENCE_NOT_FOUND", "체험을 찾을 수 없습니다.", 404)
    return item, None


def register(app):
    @app.route("/api/experiences/<int:item_id>/pet-facilities")
    def experience_pet_facilities(item_id):
        item, err = _get_experience_or_error(item_id)
        if err:
            return err
        data = nearby_service.get_pet_facilities(item, _radius_from_request())
        return success_response(data)

    @app.route("/api/experiences/<int:item_id>/barrier-free")
    def experience_barrier_free(item_id):
        item, err = _get_experience_or_error(item_id)
        if err:
            return err
        data = nearby_service.get_barrier_free_places(item, _radius_from_request())
        return success_response(data)

    @app.route("/api/experiences/<int:item_id>/medical")
    def experience_medical(item_id):
        item, err = _get_experience_or_error(item_id)
        if err:
            return err
        data = nearby_service.get_medical_facilities(item, _radius_from_request())
        return success_response(data)
