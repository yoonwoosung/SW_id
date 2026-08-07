# routes/product.py — 농산물 정보 도메인 라우트(지역별 특산물 조회). 기존 REGIONAL_SPECIALTIES 재사용.
from flask import request

from common.response import success_response
from services.recommend_data import REGIONAL_SPECIALTIES


def list_products():
    # ?region=<지역명> 이면 해당 지역(부분일치) 특산물만, 없으면 전체 지역 목록.
    region = request.args.get('region')
    if region:
        results = [
            {"region": name, "specialties": specialties}
            for name, specialties in REGIONAL_SPECIALTIES.items()
            if name in region or region in name
        ]
        return success_response({"region": region, "results": results})
    results = [{"region": name, "specialties": specialties}
               for name, specialties in REGIONAL_SPECIALTIES.items()]
    return success_response({"count": len(results), "results": results})


def register(app):
    app.add_url_rule('/api/products', 'list_products', list_products)
