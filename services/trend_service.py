# services/trend_service.py — 클릭 로그를 집계해 세그먼트(성별·나이대)별 인기 대상을 낸다.
# 세그먼트는 수동 정의하지 않고 로그에서 자동 도출한다. 비로그인·프로필 미기입 클릭은 세그먼트 집계에서 빠진다.
from sqlalchemy import func

from models import db, ClickLog, User, Experience
from common.constants import TREND_TOP_LIMIT, TREND_KEYWORD_LIMIT, RECENT_VIEWS_LIMIT


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


def recent_viewed_experiences(user_id, limit=RECENT_VIEWS_LIMIT):
    """로그인 사용자의 '체험 열람' 로그를 최신순으로 읽어 최근 본 체험 목록을 만든다.
    같은 체험은 가장 최근 열람 1건만 남기고(중복 제거), 상위 limit개만 반환한다.
    반환: [{id, name, image, cost, viewed_at(ISO)}]. user_id 없으면 빈 리스트."""
    if not user_id:
        return []

    logs = (
        ClickLog.query
        .filter(ClickLog.user_id == user_id, ClickLog.target_type == 'experience')
        .order_by(ClickLog.created_at.desc())
        .all()
    )

    results = []
    seen = set()
    for log in logs:
        if log.target_id in seen:
            continue
        seen.add(log.target_id)
        if not str(log.target_id).isdigit():
            continue
        experience = Experience.query.get(int(log.target_id))
        if experience is None:  # 삭제된 체험은 건너뛴다
            continue
        results.append({
            "id": experience.id,
            "name": f"{experience.crop} 체험",
            "image": experience.images.split(',')[0] if experience.images else None,
            "cost": experience.cost,
            "viewed_at": log.created_at.isoformat(),
        })
        if len(results) >= limit:
            break
    return results


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
