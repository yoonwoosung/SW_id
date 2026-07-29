# services/personalize_service.py — 회원 정보(과거 신청 이력) 기반 개인화 추천 로직(순수 함수).
# 로그인 사용자의 지난 신청 작물을 선호로 보고, 같은 작물 체험에 가점한다.
# 파트3: 같은 성별·나이대가 많이 누른 체험(trending_ids)에도 가점한다.
from common.constants import PERSONALIZE_CROP_BOOST, SEGMENT_TREND_BOOST
from services.distance import haversine
from services.recommend_service import matches_specialty, calculate_score, category_bonus


def user_preferences(user):
    """사용자의 과거 신청 내역에서 선호 작물 집합을 추출한다. 비로그인/이력 없으면 빈 집합."""
    crops = set()
    if user is not None:
        for application in getattr(user, "applications", []) or []:
            experience = getattr(application, "experience", None)
            if experience is not None and experience.crop:
                crops.add(experience.crop)
    return {"crops": crops}


def personalize_boost(experience, prefs):
    """과거 신청 작물과 같으면 가점. 아니면 0."""
    if experience.crop and experience.crop in prefs["crops"]:
        return PERSONALIZE_CROP_BOOST
    return 0.0


def rank_personalized(experiences, user, user_lat, user_lon, conditions=None,
                      trending_ids=None, max_distance_km=150, limit=15):
    """거리·특산물(기본) + 회원 개인화 + 세그먼트 인기 + 카테고리 조건을 합산해 추천 순위를 매긴다.
    trending_ids: 같은 성별·나이대가 많이 누른 체험 id 집합(없으면 규칙 기반으로 폴백).
    반환: (experience, distance_km, score, reasons[]) 리스트."""
    prefs = user_preferences(user)
    conditions = conditions or {}
    trending_ids = trending_ids or set()
    ranked = []
    for exp in experiences:
        distance = haversine(user_lat, user_lon, exp.lat, exp.lng)
        if distance > max_distance_km:
            continue
        is_specialty = matches_specialty(exp.address_detail, exp.crop)
        score = calculate_score(distance, exp.max_participants, exp.current_participants, is_specialty)
        score += personalize_boost(exp, prefs)
        score += category_bonus(conditions, exp)
        if exp.id in trending_ids:
            score += SEGMENT_TREND_BOOST

        reasons = []
        if exp.id in trending_ids:
            reasons.append("나와 비슷한 분들이 많이 봤어요")
        if exp.crop in prefs["crops"]:
            reasons.append("이전에 신청한 작물이에요")
        if is_specialty:
            reasons.append("이 지역 대표 특산물이에요")
        if distance <= 20:
            reasons.append(f"가까워요(약 {round(distance, 1)}km)")
        ranked.append((exp, round(distance, 1), score, reasons))

    ranked.sort(key=lambda x: x[2], reverse=True)
    return ranked[:limit]
