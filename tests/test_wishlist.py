"""services/wishlist_service 통합 테스트 — 찜 등록(멱등)·해제(소유확인)·목록."""
from models import db, User, Experience, Wishlist
from services.wishlist_service import add_wishlist, remove_wishlist, list_wishlists


def _user(email):
    u = User(nickname="n", email=email, password="x", role="experiencer", name="이름")
    db.session.add(u)
    db.session.commit()
    return u


def _experience(crop="포도", cost=25000, images="g1.jpg,g2.jpg"):
    farmer = _user(f"farmer_{crop}@x.com")
    exp = Experience(crop=crop, location="loc", cost=cost, images=images, farmer_id=farmer.id, lat=36.8, lng=127.3)
    db.session.add(exp)
    db.session.commit()
    return exp


def test_add_is_idempotent(db_session):
    u = _user("a@x.com")
    exp = _experience()
    w1, created1 = add_wishlist(u.id, exp.id)
    w2, created2 = add_wishlist(u.id, exp.id)  # 같은 사용자·같은 체험 재요청
    assert created1 is True and created2 is False
    assert w1.id == w2.id
    assert Wishlist.query.count() == 1  # 중복 저장 안 됨


def test_add_missing_experience(db_session):
    u = _user("a@x.com")
    wishlist, created = add_wishlist(u.id, 9999)
    assert wishlist is None and created is False


def test_remove_owner_only(db_session):
    owner = _user("owner@x.com")
    other = _user("other@x.com")
    exp = _experience()
    w, _ = add_wishlist(owner.id, exp.id)
    assert remove_wishlist(other.id, w.id) == 'forbidden'   # 남의 찜
    assert Wishlist.query.count() == 1
    assert remove_wishlist(owner.id, w.id) == 'removed'      # 본인
    assert Wishlist.query.count() == 0


def test_remove_not_found(db_session):
    u = _user("a@x.com")
    assert remove_wishlist(u.id, 12345) == 'not_found'


def test_list_includes_experience_info(db_session):
    u = _user("a@x.com")
    exp = _experience(crop="딸기", cost=15000, images="s1.jpg,s2.jpg")
    add_wishlist(u.id, exp.id)
    items = list_wishlists(u.id)
    assert len(items) == 1
    v = items[0]
    assert v["experience_id"] == exp.id
    assert v["name"] == "딸기 체험"
    assert v["image"] == "s1.jpg"
    assert v["cost"] == 15000
    assert "created_at" in v
