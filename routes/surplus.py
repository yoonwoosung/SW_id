# routes/surplus.py — 과생산 수확 체험 전용 섹션. 얇게 유지, 로직은 services 호출.
#
# 기존 추천 알고리즘(rank_recommendations·rank_personalized)은 건드리지 않는다.
# 과생산은 별도 섹션으로만 노출한다.
from datetime import date

from flask import request

from models import Experience
from sqlalchemy.orm import joinedload

from common.response import success_response
from services import surplus_service
from services.experience_validator import discount_rate
from services.thumbnail_service import experience_thumbnail_url

DEFAULT_LIMIT = 12
MAX_LIMIT = 50


def _to_card(experience):
    rate = discount_rate(experience.list_price, experience.cost)
    left = surplus_service.remaining(experience)
    return {
        "id": experience.id,
        "crop": experience.crop,
        "address": experience.address_detail or experience.location or "",
        "cost": experience.cost,                      # 할인가(실제 결제 금액)
        "list_price": experience.list_price,          # 정가(취소선 표시용)
        "discount_rate": round(rate * 100, 1) if rate is not None else None,
        "unit": experience.surplus_unit or "kg",
        "per_person": experience.surplus_per_person,
        "qty_total": experience.surplus_qty_total,
        "qty_left": left,
        "sold_out": left == 0,
        "origin": experience.surplus_origin,
        "d_day": experience.d_day,
        "thumbnail_url": experience_thumbnail_url(experience),
        # 현장 수확·수령만 가능하다. 프론트가 문구를 지어내지 않게 서버가 내려준다.
        "pickup_only": True,
    }


def surplus_experiences():
    """과생산 전용 섹션 목록. 할인율이 큰 순으로 준다."""
    try:
        limit = min(int(request.args.get('limit', DEFAULT_LIMIT)), MAX_LIMIT)
    except (TypeError, ValueError):
        limit = DEFAULT_LIMIT
    if limit < 1:
        limit = DEFAULT_LIMIT

    today = date.today()
    rows = (Experience.query
            .options(joinedload(Experience.farmer))   # 대표 사진 폴백에서 farmer 를 읽는다
            .filter(Experience.is_surplus.is_(True),
                    Experience.surplus_terms_agreed.is_(True),
                    Experience.status == 'recruiting',
                    Experience.end_date >= today)
            .all())

    cards = [_to_card(e) for e in rows]
    # 남은 수량이 없는 건 뒤로, 그다음 할인율이 큰 순.
    cards.sort(key=lambda c: (c['sold_out'], -(c['discount_rate'] or 0)))
    return success_response({"count": len(cards), "results": cards[:limit]})


def register(app):
    app.add_url_rule('/api/experiences/surplus', 'surplus_experiences', surplus_experiences)
