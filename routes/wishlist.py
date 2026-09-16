# routes/wishlist.py — 찜 도메인 라우트(등록·해제·목록). 얇게 유지, 로직은 services 호출.
from flask import request, session

from common.response import success_response, error_response
from common.auth import api_login_required
from services import wishlist_service


@api_login_required
def create_wishlist():
    data = request.get_json(silent=True) or request.form
    try:
        experience_id = int(data.get('experience_id'))
    except (TypeError, ValueError):
        return error_response("INVALID_EXPERIENCE_ID", "experience_id가 올바르지 않습니다.", 400)

    wishlist, created = wishlist_service.add_wishlist(session['user_id'], experience_id)
    if wishlist is None:
        return error_response("EXPERIENCE_NOT_FOUND", "체험을 찾을 수 없습니다.", 404)
    return success_response(
        {"id": wishlist.id, "experience_id": experience_id, "created": created},
        status=201 if created else 200,
    )


@api_login_required
def delete_wishlist(wishlist_id):
    result = wishlist_service.remove_wishlist(session['user_id'], wishlist_id)
    if result == 'not_found':
        return error_response("WISHLIST_NOT_FOUND", "찜을 찾을 수 없습니다.", 404)
    if result == 'forbidden':
        return error_response("FORBIDDEN", "본인의 찜만 해제할 수 있습니다.", 403)
    return success_response({"removed": True})


@api_login_required
def list_my_wishlists():
    return success_response({"wishlists": wishlist_service.list_wishlists(session['user_id'])})


def register(app):
    app.add_url_rule('/api/wishlists', 'create_wishlist', create_wishlist, methods=['POST'])
    app.add_url_rule('/api/wishlists/<int:wishlist_id>', 'delete_wishlist', delete_wishlist, methods=['DELETE'])
    app.add_url_rule('/api/wishlists', 'list_my_wishlists', list_my_wishlists, methods=['GET'])
