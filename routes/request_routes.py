# routes/request_routes.py — 역제안 라우트. 사용자: 요청글 작성·조회 / 농장주: 나에게 맞는 요청 조회.
import json
from datetime import datetime

from flask import request, session

from models import db, UserRequest, Proposal, Experience
from common.response import success_response, error_response
from services import match_service


def _login_user_id():
    return session.get('user_id')


def _parse_date(value):
    if not value:
        return None
    try:
        return datetime.strptime(value, '%Y-%m-%d').date()
    except (ValueError, TypeError):
        return None


def _request_to_dict(req):
    return {
        "id": req.id,
        "user_id": req.user_id,
        "title": req.title,
        "conditions": json.loads(req.conditions) if req.conditions else {},
        "desired_date_start": req.desired_date_start.isoformat() if req.desired_date_start else None,
        "desired_date_end": req.desired_date_end.isoformat() if req.desired_date_end else None,
        "participants": req.participants,
        "status": req.status,
        "created_at": req.created_at.isoformat() if req.created_at else None,
    }


def _proposal_to_dict(proposal):
    return {
        "id": proposal.id,
        "request_id": proposal.request_id,
        "farmer_id": proposal.farmer_id,
        "experience_id": proposal.experience_id,
        "message": proposal.message,
        "proposed_price": proposal.proposed_price,
        "proposed_date": proposal.proposed_date.isoformat() if proposal.proposed_date else None,
        "status": proposal.status,
        "created_at": proposal.created_at.isoformat() if proposal.created_at else None,
    }


def create_user_request():
    user_id = _login_user_id()
    if not user_id:
        return error_response("LOGIN_REQUIRED", "로그인이 필요합니다.", 403)

    body = request.get_json(silent=True) or {}
    title = body.get("title")
    if not title:
        return error_response("TITLE_REQUIRED", "요청 제목은 필수입니다.", 400)

    conditions = body.get("conditions") or {}
    if not isinstance(conditions, dict):
        return error_response("INVALID_CONDITIONS", "조건 형식이 올바르지 않습니다.", 400)

    new_request = UserRequest(
        user_id=user_id,
        title=title,
        conditions=json.dumps(conditions, ensure_ascii=False),
        desired_date_start=_parse_date(body.get("desired_date_start")),
        desired_date_end=_parse_date(body.get("desired_date_end")),
        participants=body.get("participants"),
    )
    db.session.add(new_request)
    db.session.commit()
    return success_response(_request_to_dict(new_request), 201)


def list_user_requests():
    requests_ = UserRequest.query.filter_by(status='open').order_by(UserRequest.created_at.desc()).all()
    return success_response([_request_to_dict(r) for r in requests_])


def get_user_request(request_id):
    req = UserRequest.query.get(request_id)
    if req is None:
        return error_response("REQUEST_NOT_FOUND", "요청글을 찾을 수 없습니다.", 404)
    data = _request_to_dict(req)
    data["proposals"] = [_proposal_to_dict(p) for p in req.proposals]
    return success_response(data)


def create_proposal(request_id):
    user_id = _login_user_id()
    if not user_id:
        return error_response("LOGIN_REQUIRED", "로그인이 필요합니다.", 403)
    if session.get('role') != 'farmer':
        return error_response("FARMER_ONLY", "농장주만 제안할 수 있습니다.", 403)

    req = UserRequest.query.get(request_id)
    if req is None:
        return error_response("REQUEST_NOT_FOUND", "요청글을 찾을 수 없습니다.", 404)

    body = request.get_json(silent=True) or {}
    message = body.get("message")
    if not message:
        return error_response("MESSAGE_REQUIRED", "제안 내용은 필수입니다.", 400)

    new_proposal = Proposal(
        request_id=req.id,
        farmer_id=user_id,
        experience_id=body.get("experience_id"),
        message=message,
        proposed_price=body.get("proposed_price"),
        proposed_date=_parse_date(body.get("proposed_date")),
    )
    db.session.add(new_proposal)
    db.session.commit()
    return success_response(_proposal_to_dict(new_proposal), 201)


def matching_requests_for_farmer():
    user_id = _login_user_id()
    if not user_id:
        return error_response("LOGIN_REQUIRED", "로그인이 필요합니다.", 403)
    if session.get('role') != 'farmer':
        return error_response("FARMER_ONLY", "농장주만 조회할 수 있습니다.", 403)

    my_experiences = Experience.query.filter_by(farmer_id=user_id).all()
    open_requests = UserRequest.query.filter_by(status='open').all()

    ranked = []
    for req in open_requests:
        score = match_service.best_match_for_experiences(req, my_experiences)
        item = _request_to_dict(req)
        item["match_score"] = score
        ranked.append(item)
    ranked.sort(key=lambda x: x["match_score"], reverse=True)
    return success_response(ranked)


def register(app):
    app.add_url_rule('/api/user-requests', 'create_user_request', create_user_request, methods=['POST'])
    app.add_url_rule('/api/user-requests', 'list_user_requests', list_user_requests, methods=['GET'])
    app.add_url_rule('/api/user-requests/<int:request_id>', 'get_user_request', get_user_request, methods=['GET'])
    app.add_url_rule('/api/user-requests/<int:request_id>/proposals', 'create_proposal', create_proposal, methods=['POST'])
    app.add_url_rule('/api/farmers/me/matching-requests', 'matching_requests_for_farmer', matching_requests_for_farmer, methods=['GET'])
