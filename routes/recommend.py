# routes/recommend.py — 추천 도메인 라우트(AI 맞춤 추천 페이지 + JSON API). 얇게 유지, 로직은 services 호출.
from datetime import date

from flask import request, session, render_template
from sqlalchemy.orm import joinedload

from models import Experience, User
from common.response import success_response, error_response
from common.constants import (RECOMMEND_LIMIT, RECOMMEND_MAX_DISTANCE_KM,
                              RECOMMEND_CONDITION_MAX_DISTANCE_KM)
from common.search_categories import CATEGORY_CODES, LABEL_BY_CODE
from services.recommend_service import rank_recommendations
from services.personalize_service import rank_personalized
from services.profile_service import has_recommendation_profile
from services.trend_service import record_click, trending_experience_counts, trend_keywords
from services import segment_service
from services.esg_service import compute_esg
from services.thumbnail_service import experience_thumbnail_url, first_image_name
from services import eco_filter
from services import segment_score


def _recruiting_experiences():
    # 카드 대표 사진 폴백에서 farmer.farm_image 를 읽는다. 지연 로딩이면
    # 직렬화하는 체험 1건당 쿼리 1번(N+1)이 붙으므로 farmer 를 함께 가져온다.
    # rank_personalized 가 limit=15 로 자르므로 최대 15쿼리였다.
    today = date.today()
    return Experience.query.options(joinedload(Experience.farmer)).filter(
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
        "thumbnail_url": experience_thumbnail_url(exp),
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
    #
    # ★섹션마다 집계 기준이 다르다.★ 예전에는 세 섹션 모두 '성별 AND 나이대'
    # 교집합을 썼는데, 그 조합에 해당하는 사용자가 없으면 집계가 0건이 되어
    # 가점이 아예 붙지 않았다. 그래서 나이·성별 섹션이 '가볍게'와 같은 결과였다.
    # 나이 섹션은 나이만, 성별 섹션은 성별만 본다.
    trend_counts = {}
    if has_recommendation_profile(user):
        if segment == segment_score.SEGMENT_PEERS_AGE:
            trend_counts = trending_experience_counts(None, user.age_group)
        elif segment == segment_score.SEGMENT_PEERS_GENDER:
            trend_counts = trending_experience_counts(user.gender, None)
        else:
            trend_counts = trending_experience_counts(user.gender, user.age_group)
    trending = set(trend_counts)

    # ★조건 필터를 자르기 전에 건다.★ 예전에는 rank_personalized 가 상위 15건을
    # 자른 뒤에 걸렀다. 그래서 16위 이하는 조건이 맞아도 검사조차 되지 않았다
    # (실측: 모집 21건 중 6건이 사각지대. '울산 배'가 그중 하나였다).
    #
    # 조건에 맞으면 점수 가점을 받아 상위로 끌려 올라오긴 했는데, 가점이
    # 순위를 뒤집기에 부족하면 누락됐다. ★조건을 몇 개 걸었는지에 따라 결과가
    # 달라지는 불안정한 상태★였다 — 주차만 걸면 12건, 주차+자가용이면 13건.
    experiences = [exp for exp in _recruiting_experiences()
                   if eco_filter.passes_conditions(conditions, exp)]

    # ★조건으로 목록을 좁혔으면 거리 제한을 걸지 않는다.★
    # 예전에는 위치를 허용한 사용자에게 150km 밖 체험을 순위 계산 전에 버렸다.
    # 그래서 서울·천안에서 '지역>울산'을 골라도 0건이었다(실측 232~297km).
    # 조건을 안 걸었으면 예전 그대로 가까운 곳 우선이다.
    #
    # 판단 기준은 ★목록을 실제로 좁히는 조건★이 걸렸는지다. 분위기·계절처럼
    # 코스 장소에만 쓰이는 조건은 목록을 좁히지 않으므로 제한을 유지한다.
    narrowed = bool(eco_filter.selected_categories(conditions))
    max_distance = (RECOMMEND_CONDITION_MAX_DISTANCE_KM if narrowed
                    else RECOMMEND_MAX_DISTANCE_KM)

    # limit 은 여기서 주지 않는다. 세그먼트 보너스까지 반영한 뒤 잘라야
    # 섹션 기준이 순서에 실제로 반영된다(아래 RECOMMEND_LIMIT).
    ranked = rank_personalized(experiences, user, lat, lon, conditions,
                               trending_ids=trending, limit=None,
                               max_distance_km=max_distance)

    if segment == 'esg':
        # '친환경 인증 농장' 섹션: 정렬만 하면 친환경이 아닌 체험도 남는다.
        # 친환경 항목(E축)이 있고 ESG 등급 B 이상인 것만 남기고, 그 안에서 점수순.
        ranked = [item for item in ranked if eco_filter.passes_eco_section(item[0])]
        ranked.sort(key=lambda item: compute_esg(item[0])["score"], reverse=True)
    else:
        # 세그먼트마다 기준이 달라야 한다. 기본 점수는 그대로 두고 보너스만 더해
        # 순서를 바꾼다. 해당 없는 세그먼트(nearby)는 보너스가 0 이라 기본 점수순.
        #   peers        저렴 + 가까움
        #   group        잔여석 + 주차
        #   peers_age    같은 나이대 클릭 수      ← 이전에는 apply('peers') 였다
        #   peers_gender 같은 성별 클릭 수        ← 이전에는 apply('peers') 였다
        ranked = segment_score.apply(segment, ranked, trend_counts=trend_counts)

    # ★자르는 것은 맨 마지막이다.★ 조건 필터와 세그먼트 보너스를 모두 거친
    # 뒤에 자른다. 예전에는 자르기가 맨 앞이라 섹션 보너스로도 16위 이하를
    # 끌어올릴 수 없었고, 6개 섹션이 전부 같은 15건 풀을 돌려 썼다(실측).
    ranked = ranked[:RECOMMEND_LIMIT]

    results = [{
        "id": exp.id, "crop": exp.crop, "address": exp.address_detail, "cost": exp.cost,
        "barrier_free": bool(exp.barrier_free),
        "eco": bool(exp.pesticide_free or exp.organic_certification_type),
        "esg_grade": compute_esg(exp)["grade"],   # ESG 코스 카드 등급 배지(A~D)용
        "d_day": exp.d_day,
        "distance_km": distance, "score": round(score, 3), "reasons": reasons,
        "first_image": first_image_name(exp),   # 기존 프론트 호환용(파일명만)
        "thumbnail_url": experience_thumbnail_url(exp),
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
        # 또래·성별 섹션을 그릴 근거가 있는지. 없으면 프론트가 섹션을 숨긴다.
        "peer_segments": segment_service.peer_segment_availability(user),
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
