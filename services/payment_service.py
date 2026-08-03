# services/payment_service.py — 더미 '간편결제' 로직. 실제 PG 연동 없이 예약 상태만 전이한다.
from models import db, Application, Experience
from common.constants import APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID
from services import point_service


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
