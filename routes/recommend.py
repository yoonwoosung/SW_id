# routes/recommend.py — 추천 도메인 라우트(맞춤 체험 추천 JSON API). 얇게 유지, 로직은 services 호출.
from datetime import date

from flask import request

from models import Experience
from common.response import success_response, error_response
from services.recommend_service import rank_recommendations


def recommend_experiences():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if lat is None or lon is None:
        return error_response("COORDS_REQUIRED", "위치(lat, lon)가 필요합니다.", 400)

    today = date.today()
    experiences = Experience.query.filter(
        Experience.status == 'recruiting', Experience.end_date >= today
    ).all()
    ranked = rank_recommendations(experiences, lat, lon)
    results = [{
        "id": exp.id, "crop": exp.crop, "address": exp.address_detail,
        "distance_km": distance, "score": round(score, 3),
    } for exp, distance, score in ranked]
    return success_response({"count": len(results), "results": results})


def register(app):
    app.add_url_rule('/api/experiences/recommendations', 'recommend_experiences', recommend_experiences)
