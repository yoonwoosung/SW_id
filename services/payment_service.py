# services/payment_service.py — 결제 로직.
# 토스페이먼츠 테스트 결제 연동: 주문 생성(prepare) → 결제창 → 서버 승인(confirm).
import uuid
from datetime import datetime

from models import db, Application, Experience, Payment
from common.constants import APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID
from services import point_service, toss_service
from services.toss_service import TossError


def calculate_amount(application, experience):
    """결제 금액 = 참가 인원수 × 체험 1인 가격."""
    if experience is None or experience.cost is None:
        return 0
    return application.participants_count * experience.cost


def get_owned_application(user_id, application_id):
    """본인 소유 예약을 (application, experience)로 반환. 반환: (status, application, experience).
    status: 'ok' | 'not_found' | 'forbidden'."""
    application = Application.query.get(application_id)
    if application is None:
        return 'not_found', None, None
    if application.user_id != user_id:
        return 'forbidden', None, None
    experience = Experience.query.get(application.experience_id)
    return 'ok', application, experience


def pay(user_id, application_id):
    """더미 결제 성공 처리: 본인 소유 + '예정' 상태만 '결제완료'로 전이한다.
    반환: (status, data). status: 'ok' | 'not_found' | 'forbidden' | 'invalid_state'."""
    status, application, experience = get_owned_application(user_id, application_id)
    if status != 'ok':
        return status, None
    if application.status != APPLICATION_STATUS_PENDING:
        return 'invalid_state', None

    amount = calculate_amount(application, experience)
    application.status = APPLICATION_STATUS_PAID
    db.session.commit()

    earned = point_service.earn_points_for_payment(user_id, application.id, amount)
    return 'ok', {
        "application_id": application.id,
        "status": APPLICATION_STATUS_PAID,
        "amount": amount,
        "earned_points": earned,
    }


# ────────────────────────────── 토스페이먼츠 연동 ──────────────────────────────

def _new_order_id(application_id):
    """토스 주문번호. 영문/숫자/하이픈, 6~64자 규격을 지키고 재시도마다 새로 발급한다."""
    return f"farmlink-{application_id}-{uuid.uuid4().hex[:16]}"


def prepare(user_id, application_id):
    """결제창을 띄우기 직전 호출. 결제할 금액을 서버가 확정해 Payment(ready)로 남긴다.

    금액을 여기서 기록해 두는 것이 위변조 방지의 핵심이다.
    반환: (status, data) — status: 'ok' | 'not_found' | 'forbidden' | 'invalid_state'
    """
    status, application, experience = get_owned_application(user_id, application_id)
    if status != 'ok':
        return status, None
    if application.status != APPLICATION_STATUS_PENDING:
        return 'invalid_state', None

    amount = calculate_amount(application, experience)
    if amount <= 0:
        return 'invalid_state', None

    payment = Payment(
        order_id=_new_order_id(application.id),
        amount=amount,
        status=Payment.STATUS_READY,
        application_id=application.id,
        user_id=user_id,
    )
    db.session.add(payment)
    db.session.commit()

    return 'ok', {
        "order_id": payment.order_id,
        "amount": amount,
        "order_name": f"{experience.crop} 체험" if experience else "체험 예약",
    }


def confirm(user_id, payment_key, order_id, client_amount):
    """토스 결제 승인. 성공하면 예약을 '결제완료'로 전이한다.

    반환: (status, data) — status: 'ok' | 'not_found' | 'forbidden'
          | 'already_done' | 'amount_mismatch' | 'toss_error'
    """
    payment = Payment.query.filter_by(order_id=order_id).first()
    if payment is None:
        return 'not_found', None
    if payment.user_id != user_id:
        return 'forbidden', None

    # 이미 승인된 주문을 다시 승인하지 않는다(새로고침·중복 콜백 방어).
    if payment.status == Payment.STATUS_DONE:
        return 'already_done', {
            "application_id": payment.application_id,
            "order_id": payment.order_id,
            "amount": payment.amount,
        }

    # ★ 클라이언트가 보낸 금액이 아니라 서버가 저장해 둔 금액을 신뢰한다.
    try:
        if int(client_amount) != payment.amount:
            payment.status = Payment.STATUS_FAILED
            payment.fail_code = 'AMOUNT_MISMATCH'
            payment.fail_reason = f'요청 금액({client_amount})이 주문 금액({payment.amount})과 다릅니다.'
            db.session.commit()
            return 'amount_mismatch', None
    except (TypeError, ValueError):
        return 'amount_mismatch', None

    try:
        body = toss_service.confirm_payment(payment.payment_key or payment_key,
                                            order_id, payment.amount)
    except TossError as exc:
        payment.status = Payment.STATUS_FAILED
        payment.fail_code = exc.code
        payment.fail_reason = exc.message[:255]
        db.session.commit()
        return 'toss_error', exc

    payment.payment_key = body.get('paymentKey') or payment_key
    payment.method = body.get('method')
    payment.status = Payment.STATUS_DONE
    payment.approved_at = datetime.utcnow()

    application = Application.query.get(payment.application_id)
    earned = 0
    # 승인은 됐는데 예약이 이미 다른 상태로 갔다면 상태는 건드리지 않는다(중복 적립 방지).
    if application is not None and application.status == APPLICATION_STATUS_PENDING:
        application.status = APPLICATION_STATUS_PAID
        db.session.commit()
        earned = point_service.earn_points_for_payment(user_id, application.id, payment.amount)
    else:
        db.session.commit()

    return 'ok', {
        "application_id": payment.application_id,
        "order_id": payment.order_id,
        "amount": payment.amount,
        "method": payment.method,
        "status": APPLICATION_STATUS_PAID,
        "earned_points": earned,
    }


def mark_failed(user_id, order_id, code, message):
    """결제창에서 실패·취소했을 때 Payment 만 실패로 남긴다. 예약 상태는 그대로 둔다."""
    payment = Payment.query.filter_by(order_id=order_id).first()
    if payment is None or payment.user_id != user_id:
        return None
    if payment.status == Payment.STATUS_DONE:
        return payment
    payment.status = Payment.STATUS_FAILED
    payment.fail_code = (code or 'UNKNOWN')[:100]
    payment.fail_reason = (message or '')[:255]
    db.session.commit()
    return payment
