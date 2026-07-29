"""services/trend_service 통합 테스트 — 클릭 로그 세그먼트 집계(파트3)."""
from models import db, User, ClickLog
from services.trend_service import (
    record_click, top_targets_for_segment, trending_experience_ids, trend_keywords,
)


def _user(gender=None, age_group=None, email="u@example.com"):
    u = User(nickname="n", email=email, password="x", role="experiencer",
             name="이름", gender=gender, age_group=age_group)
    db.session.add(u)
    db.session.commit()
    return u


def test_record_click_persists(db_session):
    record_click(None, "experience", 5)
    assert ClickLog.query.count() == 1
    log = ClickLog.query.first()
    assert log.user_id is None and log.target_type == "experience" and log.target_id == "5"


def test_segment_aggregation_counts_same_group(db_session):
    # 20대 여성 둘이 체험 7을, 한 명은 8을 클릭 → 세그먼트 인기: 7 > 8
    f1 = _user("female", "20s", "f1@x.com")
    f2 = _user("female", "20s", "f2@x.com")
    male = _user("male", "20s", "m@x.com")
    for _ in range(2):
        record_click(f1.id, "experience", 7)
    record_click(f2.id, "experience", 7)
    record_click(f1.id, "experience", 8)
    record_click(male.id, "experience", 9)  # 다른 세그먼트 → 제외

    ranked = top_targets_for_segment("female", "20s", "experience")
    assert ranked[0] == ("7", 3)
    ids = {tid for tid, _ in ranked}
    assert "9" not in ids  # 남성 클릭은 여성 세그먼트에 안 섞임


def test_anonymous_clicks_excluded_from_segment(db_session):
    record_click(None, "experience", 7)  # 비로그인 → 세그먼트 집계 제외
    assert top_targets_for_segment("female", "20s") == []


def test_no_segment_returns_empty(db_session):
    _user("female", "20s")
    record_click(1, "experience", 7)
    assert top_targets_for_segment(None, None) == []  # 프로필 없으면 폴백(빈 리스트)


def test_trending_experience_ids_are_ints(db_session):
    f1 = _user("female", "30s")
    record_click(f1.id, "experience", 12)
    assert trending_experience_ids("female", "30s") == {12}


def test_trend_keywords_counts_categories(db_session):
    f1 = _user("female", "20s")
    record_click(f1.id, "category", "harvest")
    record_click(f1.id, "category", "harvest")
    record_click(None, "category", "kayak")
    kws = dict(trend_keywords())
    assert kws["harvest"] == 2 and kws["kayak"] == 1
