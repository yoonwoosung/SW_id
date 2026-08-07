# routes/esg.py — ESG 도메인 라우트(체험/농장 ESG 점수 조회). 얇게 유지, 로직은 services 호출.
from models import Experience
from common.response import success_response, error_response
from services.esg_service import compute_esg


def experience_esg(item_id):
    item = Experience.query.get(item_id)
    if item is None:
        return error_response("EXPERIENCE_NOT_FOUND", "체험을 찾을 수 없습니다.", 404)
    return success_response({"experience_id": item.id, **compute_esg(item)})


def register(app):
    app.add_url_rule('/api/experiences/<int:item_id>/esg', 'experience_esg', experience_esg)
