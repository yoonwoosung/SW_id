"""services/trend_service.recent_viewed_experiences 통합 테스트 — 최근 본 체험(click_log 기반)."""
from datetime import datetime, timedelta

from models import db, User, Experience, ClickLog
from services.trend_service import recent_viewed_experiences
from common.constants import RECENT_VIEWS_LIMIT


def _experience(crop, cost=10000, images=None):
    farmer = User(nickname="f", email=f"{crop}@x.com", password="x", role="farmer", name="농부")
    db.session.add(farmer)
    db.session.commit()
    exp = Experience(crop=crop, location="loc", cost=cost, images=images, farmer_id=farmer.id, lat=36.8, lng=127.3)
    db.session.add(exp)
    db.session.commit()
    return exp


def _view(user_id, exp_id, when):
    db.session.add(ClickLog(user_id=user_id, target_type='experience', target_id=str(exp_id), created_at=when))
    db.session.commit()


def test_empty_when_not_logged_in(db_session):
    assert recent_viewed_experiences(None) == []


def test_returns_latest_first_and_dedupes(db_session):
    base = datetime(2026, 7, 29, 12, 0, 0)
    a = _experience("딸기", cost=15000, images="s1.jpg,s2.jpg")
    b = _experience("포도", cost=25000)
    # 딸기를 먼저, 포도를 나중에, 딸기를 또(가장 최근) 열람
    _view(1, a.id, base)
    _view(1, b.id, base + timedelta(minutes=5))
    _view(1, a.id, base + timedelta(minutes=10))

    out = recent_viewed_experiences(1)
    assert [v["id"] for v in out] == [a.id, b.id]  # 최신순 + 딸기 1건만
    top = out[0]
    assert top["name"] == "딸기 체험"
    assert top["image"] == "s1.jpg"          # 대표이미지 = 첫 파일명
    assert top["cost"] == 15000
    assert top["viewed_at"] == (base + timedelta(minutes=10)).isoformat()


def test_image_null_when_no_images(db_session):
    b = _experience("포도")
    _view(1, b.id, datetime(2026, 7, 29, 12, 0, 0))
    assert recent_viewed_experiences(1)[0]["image"] is None


def test_deleted_experience_is_skipped(db_session):
    _view(1, 999, datetime(2026, 7, 29, 12, 0, 0))  # 존재하지 않는 체험
    assert recent_viewed_experiences(1) == []


def test_limit_applied(db_session):
    base = datetime(2026, 7, 29, 12, 0, 0)
    for i in range(RECENT_VIEWS_LIMIT + 3):
        exp = _experience(f"작물{i}")
        _view(1, exp.id, base + timedelta(minutes=i))
    assert len(recent_viewed_experiences(1)) == RECENT_VIEWS_LIMIT
