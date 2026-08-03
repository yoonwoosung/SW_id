# services/point_service.py — 포인트 적립·잔액·내역 로직. 잔액은 PointLog의 SUM(amount).
from sqlalchemy import func

from models import db, PointLog
from common.constants import POINT_EARN_RATE, POINT_REASON_PAYMENT


def earn_points_for_payment(user_id, application_id, amount):
    """결제 금액의 POINT_EARN_RATE만큼 적립(정수 내림). 같은 예약에 이미 적립됐으면 중복 적립 안 함(멱등).
    반환: 이번에 적립된 포인트(이미 적립돼 있으면 0)."""
    already = PointLog.query.filter_by(
        application_id=application_id, reason=POINT_REASON_PAYMENT
    ).first()
    if already is not None:
        return 0

    earned = int(amount * POINT_EARN_RATE)
    if earned <= 0:
        return 0

    db.session.add(PointLog(
        user_id=user_id, amount=earned,
        reason=POINT_REASON_PAYMENT, application_id=application_id,
    ))
    db.session.commit()
    return earned


def get_balance(user_id):
    """현재 포인트 잔액 = 내역 합계."""
    total = db.session.query(func.coalesce(func.sum(PointLog.amount), 0)).filter(
        PointLog.user_id == user_id
    ).scalar()
    return int(total or 0)


def get_point_summary(user_id):
    """잔액 + 내역(최신순)."""
    logs = (
        PointLog.query.filter_by(user_id=user_id)
        .order_by(PointLog.created_at.desc())
        .all()
    )
    return {
        "balance": get_balance(user_id),
        "logs": [{
            "amount": log.amount,
            "reason": log.reason,
            "application_id": log.application_id,
            "created_at": log.created_at.isoformat(),
        } for log in logs],
    }
