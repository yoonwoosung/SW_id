# services/point_service.py — 포인트 적립·잔액·내역 로직. 잔액은 PointLog의 SUM(amount).
from sqlalchemy import func

from models import db, PointLog
from common.constants import (POINT_EARN_RATE, POINT_REASON_PAYMENT,
                             POINT_REASON_USE, POINT_REASON_REFUND,
                             POINT_REASON_REJECT_REFUND, POINT_REASON_LABELS)


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


def refunded_application_ids(user_id):
    """거절 환급을 받은 예약 id 집합.

    '취소'된 예약이 사용자가 직접 취소한 것인지 농장주가 거절한 것인지는
    Application 만 봐서는 알 수 없다(둘 다 '취소'로 간다).
    환급 로그가 있으면 농장주 거절이므로 이것으로 판정한다.
    """
    rows = db.session.query(PointLog.application_id).filter(
        PointLog.user_id == user_id,
        PointLog.reason == POINT_REASON_REJECT_REFUND,
        PointLog.application_id.isnot(None),
    ).all()
    return {row[0] for row in rows}


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
            # 화면에는 한글 라벨을 쓴다. 매핑에 없는 코드는 코드를 그대로 두어
            # 내역이 비거나 깨지지 않게 한다.
            "reason_label": POINT_REASON_LABELS.get(log.reason, log.reason),
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


def refund_payment_as_points(user_id, application_id, amount):
    """농장주 거절 시 ★실제 결제한 금액★만큼 포인트로 환급한다(양수 로그 1행).

    토스 결제 취소 API 는 쓰지 않는다. 카드 취소는 연동·정산 확인이 필요해
    이번 범위 밖이고, 포인트 환급이면 우리 DB 안에서 끝난다.

    사유코드를 refund_points 의 'refund' 와 나눈 이유:
    거절 한 건에서 '현금 결제분 환급'과 '사용 포인트 원복'이 둘 다 일어나는데,
    멱등 검사가 (user, application, reason) 단위라 같은 코드를 쓰면
    ★먼저 들어간 쪽이 뒤를 막아★ 환급이 절반만 되거나 원복이 누락된다.

    같은 예약을 두 번 거절해도 두 번 적립되지 않는다(멱등).
    """
    if amount <= 0:
        return 0
    already = PointLog.query.filter_by(
        user_id=user_id, application_id=application_id,
        reason=POINT_REASON_REJECT_REFUND
    ).first()
    if already is not None:
        return 0
    db.session.add(PointLog(
        user_id=user_id, amount=amount,
        reason=POINT_REASON_REJECT_REFUND, application_id=application_id,
    ))
    db.session.commit()
    return amount


def refund_points(user_id, application_id, amount):
    """결제 실패·취소 시 ★결제에 썼던 포인트★를 되돌린다(양수 로그 1행).

    거절 환급(refund_payment_as_points)과는 다른 건이다.
    이쪽은 원래 갖고 있던 포인트를 돌려주는 것이고, 저쪽은 현금 결제분이다.

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
