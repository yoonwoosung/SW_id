# services/point_service.py — 포인트 적립·잔액·내역 로직. 잔액은 PointLog의 SUM(amount).
from sqlalchemy import func

from models import db, PointLog
from common.constants import (POINT_EARN_RATE, POINT_REASON_PAYMENT,
                             POINT_REASON_USE, POINT_REASON_REFUND)


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


# ────────────────────────── 결제 시 포인트 사용/원복 ──────────────────────────
#
# 잔액은 PointLog 의 SUM(amount) 이므로, 차감도 원복도 "행을 추가"해서 표현한다.
# 이렇게 하면 내역과 잔액이 구조적으로 어긋날 수 없다.

def validate_use(user_id, requested, order_total):
    """사용하려는 포인트가 유효한지 검사한다. 반환: (ok, 사유코드, 사용가능액).

    - 음수·숫자 아님 → 거부
    - 보유 잔액 초과 → 거부
    - 결제 총액 초과 → 거부 (포인트로 결제액보다 많이 깎을 수 없다)
    """
    try:
        amount = int(requested or 0)
    except (TypeError, ValueError):
        return False, 'INVALID_POINT_AMOUNT', 0
    if amount < 0:
        return False, 'INVALID_POINT_AMOUNT', 0
    if amount == 0:
        return True, None, 0

    balance = get_balance(user_id)
    if amount > balance:
        return False, 'INSUFFICIENT_POINTS', balance
    if amount > order_total:
        return False, 'POINT_EXCEEDS_TOTAL', order_total
    return True, None, amount


def use_points(user_id, application_id, amount):
    """포인트를 차감한다(음수 로그 1행). 호출 전 validate_use 로 검증할 것.

    커밋은 호출부(payment_service)가 결제 레코드와 함께 한 트랜잭션으로 처리한다.
    """
    if amount <= 0:
        return 0
    db.session.add(PointLog(
        user_id=user_id, amount=-amount,
        reason=POINT_REASON_USE, application_id=application_id,
    ))
    return amount


def refund_points(user_id, application_id, amount):
    """결제 실패·취소 시 차감분을 되돌린다(양수 로그 1행).

    같은 예약에 이미 원복 기록이 있으면 중복 원복하지 않는다(멱등).
    """
    if amount <= 0:
        return 0
    already = PointLog.query.filter_by(
        user_id=user_id, application_id=application_id, reason=POINT_REASON_REFUND
    ).first()
    if already is not None:
        return 0
    db.session.add(PointLog(
        user_id=user_id, amount=amount,
        reason=POINT_REASON_REFUND, application_id=application_id,
    ))
    db.session.commit()
    return amount
