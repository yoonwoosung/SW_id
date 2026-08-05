# routes/recommend.py — 추천 도메인 라우트(AI 맞춤 추천 페이지 + JSON API). 얇게 유지, 로직은 services 호출.
from datetime import date

from flask import request, session, render_template

from models import Experience, User
from common.response import success_response, error_response
from common.search_categories import CATEGORY_CODES, LABEL_BY_CODE
from services.recommend_service import rank_recommendations
from services.personalize_service import rank_personalized
from services.profile_service import has_recommendation_profile
from services.trend_service import record_click, trending_experience_ids, trend_keywords
from services import segment_service
from services.esg_service import compute_esg


def _recruiting_experiences():
    today = date.today()
    return Experience.query.filter(
        Experience.status == 'recruiting', Experience.end_date >= today
    ).all()


def ai_recommend_page():
    # AI 맞춤 추천 전용 페이지(상세조건 + 개인화 추천 + 코스). 데이터는 JS가 API로 불러온다.
    return render_template('ai_recommend.html')


def recommend_experiences():
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)
    if lat is None or lon is None:
        return error_response("COORDS_REQUIRED", "위치(lat, lon)가 필요합니다.", 400)
    ranked = rank_recommendations(_recruiting_experiences(), lat, lon)
    results = [{
        "id": exp.id, "crop": exp.crop, "address": exp.address_detail,
        "distance_km": distance, "score": round(score, 3),
    } for exp, distance, score in ranked]
    return success_response({"count": len(results), "results": results})


def personalized_recommendations():
    # 좌표는 선택. 없으면 거리 요소를 빼고 회원정보(이력·특산물·조건) 기반 '기본 추천'을 준다.
    lat = request.args.get('lat', type=float)
    lon = request.args.get('lon', type=float)

    conditions = {code: request.args.getlist('cond_' + code) for code in CATEGORY_CODES}
    segment = request.args.get('segment')  # 세그먼트 카드(peers/active/esg)
    user = User.query.get(session['user_id']) if 'user_id' in session else None

    # 프로필이 있으면 같은 세그먼트 인기 체험을 가점, 없으면 규칙 기반으로 폴백(빈 집합).
    trending = trending_experience_ids(user.gender, user.age_group) if has_recommendation_profile(user) else set()

    ranked = rank_personalized(_recruiting_experiences(), user, lat, lon, conditions, trending_ids=trending)
    if segment == 'esg':  # ESG 세그먼트: 친환경 점수 높은 순으로 재정렬
        ranked.sort(key=lambda item: compute_esg(item[0])["score"], reverse=True)

    results = [{
        "id": exp.id, "crop": exp.crop, "address": exp.address_detail, "cost": exp.cost,
        "barrier_free": bool(exp.barrier_free),
        "eco": bool(exp.pesticide_free or exp.organic_certification_type),
        "esg_grade": compute_esg(exp)["grade"],   # ESG 코스 카드 등급 배지(A~D)용
        "d_day": exp.d_day,
        "distance_km": distance, "score": round(score, 3), "reasons": reasons,
    } for exp, distance, score, reasons in ranked]
    return success_response({
        "personalized": user is not None,
        "segment_applied": bool(trending),
        "segment": segment,
        "count": len(results), "results": results,
    })


def recommendation_segments():
    # 진입 즉시 보여줄 회원정보 기반 자동 추천 세그먼트 카드.
    user = User.query.get(session['user_id']) if 'user_id' in session else None
    return success_response({
        "segment_label": segment_service.user_segment_label(user),
        "segments": segment_service.auto_segments(user),
    })


def segment_buttons_route():
    # 인적사항(성별·나이대) 기반 단축 추천 버튼 2개. 프론트는 이 응답으로 버튼을 그린다(하드코딩 금지).
    user = User.query.get(session['user_id']) if 'user_id' in session else None
    return success_response({"buttons": segment_service.segment_buttons(user)})


def create_click_log():
    data = request.get_json(silent=True) or request.form
    target_type = (data.get('target_type') or '').strip()
    target_id = (data.get('target_id') or '').strip()
    if target_type not in ('experience', 'category') or not target_id:
        return error_response("INVALID_CLICK", "target_type·target_id가 올바르지 않습니다.", 400)
    record_click(session.get('user_id'), target_type, target_id)
    return success_response({"recorded": True}, status=201)


def trend_keywords_route():
    results = [
        {"code": code, "label": LABEL_BY_CODE.get(code, code), "count": count}
        for code, count in trend_keywords()
    ]
    return success_response({"keywords": results})


def register(app):
    app.add_url_rule('/ai-recommend', 'ai_recommend_page', ai_recommend_page)
    app.add_url_rule('/api/experiences/recommendations', 'recommend_experiences', recommend_experiences)
    app.add_url_rule('/api/recommendations/personalized', 'personalized_recommendations', personalized_recommendations)
    app.add_url_rule('/api/recommendations/segments', 'recommendation_segments', recommendation_segments)
    app.add_url_rule('/api/recommend/segment-buttons', 'segment_buttons', segment_buttons_route)
    app.add_url_rule('/api/click-logs', 'create_click_log', create_click_log, methods=['POST'])
    app.add_url_rule('/api/trend-keywords', 'trend_keywords', trend_keywords_route)
