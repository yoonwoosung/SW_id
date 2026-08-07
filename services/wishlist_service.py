# services/wishlist_service.py — 찜 등록·해제·목록 로직(DB 처리). 라우트는 이 함수들을 호출만 한다.
from models import db, Wishlist, Experience


def add_wishlist(user_id, experience_id):
    """찜 등록(멱등). 반환: (wishlist, created).
    체험이 없으면 (None, False), 이미 찜했으면 기존 것과 (created=False)."""
    experience = Experience.query.get(experience_id)
    if experience is None:
        return None, False

    existing = Wishlist.query.filter_by(user_id=user_id, experience_id=experience_id).first()
    if existing is not None:
        return existing, False

    wishlist = Wishlist(user_id=user_id, experience_id=experience_id)
    db.session.add(wishlist)
    db.session.commit()
    return wishlist, True


def remove_wishlist(user_id, wishlist_id):
    """찜 해제. 반환: 'removed' | 'not_found' | 'forbidden'(본인 것이 아님)."""
    wishlist = Wishlist.query.get(wishlist_id)
    if wishlist is None:
        return 'not_found'
    if wishlist.user_id != user_id:
        return 'forbidden'
    db.session.delete(wishlist)
    db.session.commit()
    return 'removed'


def list_wishlists(user_id):
    """내 찜 목록(체험 정보 포함, 최신순). 삭제된 체험은 건너뛴다."""
    rows = (
        Wishlist.query
        .filter_by(user_id=user_id)
        .order_by(Wishlist.created_at.desc())
        .all()
    )
    result = []
    for wishlist in rows:
        experience = wishlist.experience
        if experience is None:
            continue
        result.append({
            "id": wishlist.id,
            "experience_id": experience.id,
            "name": f"{experience.crop} 체험",
            "image": experience.images.split(',')[0] if experience.images else None,
            "cost": experience.cost,
            "created_at": wishlist.created_at.isoformat(),
        })
    return result
