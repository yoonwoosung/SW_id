# services/trend_service.py — 클릭 로그를 집계해 세그먼트(성별·나이대)별 인기 대상을 낸다.
# 세그먼트는 수동 정의하지 않고 로그에서 자동 도출한다. 비로그인·프로필 미기입 클릭은 세그먼트 집계에서 빠진다.
from sqlalchemy import func

from models import db, ClickLog, User
from common.constants import TREND_TOP_LIMIT, TREND_KEYWORD_LIMIT


def record_click(user_id, target_type, target_id):
    """클릭 1건 적재. user_id는 비로그인이면 None."""
    log = ClickLog(user_id=user_id, target_type=target_type, target_id=str(target_id))
    db.session.add(log)
    db.session.commit()
    return log


def top_targets_for_segment(gender, age_group, target_type='experience', limit=TREND_TOP_LIMIT):
    """같은 성별·나이대 사용자가 많이 누른 target_id 목록(많은 순). 세그먼트 정보가 없으면 빈 리스트."""
    if not gender and not age_group:
        return []
    query = (
        db.session.query(ClickLog.target_id, func.count().label('cnt'))
        .join(User, ClickLog.user_id == User.id)
        .filter(ClickLog.target_type == target_type)
    )
    if gender:
        query = query.filter(User.gender == gender)
    if age_group:
        query = query.filter(User.age_group == age_group)
    rows = (
        query.group_by(ClickLog.target_id)
        .order_by(func.count().desc())
        .limit(limit)
        .all()
    )
    return [(row.target_id, row.cnt) for row in rows]


def trending_experience_ids(gender, age_group):
    """세그먼트 인기 체험 id 집합(정수). 추천 가점용."""
    pairs = top_targets_for_segment(gender, age_group, target_type='experience')
    return {int(tid) for tid, _ in pairs if str(tid).isdigit()}


def trend_keywords(limit=TREND_KEYWORD_LIMIT):
    """전체에서 최근 많이 눌린 카테고리 코드 상위(검색창 하단 노출용). [(code, count), ...]"""
    rows = (
        db.session.query(ClickLog.target_id, func.count().label('cnt'))
        .filter(ClickLog.target_type == 'category')
        .group_by(ClickLog.target_id)
        .order_by(func.count().desc())
        .limit(limit)
        .all()
    )
    return [(row.target_id, row.cnt) for row in rows]
