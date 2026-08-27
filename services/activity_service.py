# services/activity_service.py — '내 활동' 예약 카드 상태 분류 및 체험 완료 자동 동기화
from datetime import date, datetime, time

from common.constants import (
    APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID,
    APPLICATION_STATUS_CONFIRMED, APPLICATION_STATUS_CANCELLED,
)
from models import db, Application, Notification

# 카드 상태 코드
STATE_PAY_PENDING = 'pay_pending'     # 결제 대기
STATE_AWAIT_ACCEPT = 'await_accept'   # 수락 대기중
STATE_CONFIRMED = 'confirmed'         # 예약 확정 (체험 전)
STATE_COMPLETED = 'completed'         # 체험 완료 (체험 종료 후 -> 후기 가능)
STATE_CANCELLED = 'cancelled'         # 취소됨

_BADGE_LABEL = {
    STATE_PAY_PENDING: '결제 대기',
    STATE_AWAIT_ACCEPT: '수락 대기중',
    STATE_CONFIRMED: '예약 확정',
    STATE_COMPLETED: '체험 완료',
    STATE_CANCELLED: '취소됨',
}


def is_experience_ended(application):
    # 체험 날짜와 시작 시간을 기준으로 체험 종료 여부를 판별한다 (시작 시간 + 1시간).
    if not application.apply_date:
        return False
    
    exp_time = time(18, 0) # 시간 정보가 없을 경우 당일 18시 기준
    if application.apply_time:
        try:
            parts = application.apply_time.strip().split(':')
            if len(parts) == 2:
                # 시작 시간 기준 1시간 뒤를 체험 종료 시점으로 설정
                exp_time = time(min(23, int(parts[0]) + 1), int(parts[1]))
        except Exception:
            pass

    exp_datetime = datetime.combine(application.apply_date, exp_time)
    return datetime.now() >= exp_datetime


def sync_user_completed_reservations(user_id):
    if not user_id:
        return []

    confirmed_apps = Application.query.filter(
        Application.user_id == user_id,
        Application.status.in_([APPLICATION_STATUS_CONFIRMED, '확정', '완료'])
    ).all()

    updated = False
    newly_completed = []

    for app in confirmed_apps:
        if is_experience_ended(app):
            if app.status != '완료':
                app.status = '완료'
                updated = True

            if not app.can_review:
                app.can_review = True
                updated = True
                crop_name = app.experience.crop if app.experience else '농장'
                newly_completed.append(crop_name)

                notif = Notification(
                    user_id=user_id,
                    message=f"'{crop_name}' 체험은 어떠셨나요? 소중한 후기를 남겨주세요."
                )
                db.session.add(notif)

    if updated:
        db.session.commit()

    return newly_completed


def reservation_state(application, today=None):
    today = today or date.today()
    status = application.status
    if status in (APPLICATION_STATUS_CANCELLED, '취소'):
        return STATE_CANCELLED
    
    if status in (APPLICATION_STATUS_CONFIRMED, '확정', '완료'):
        if status == '완료' or application.can_review or is_experience_ended(application):
            return STATE_COMPLETED
        return STATE_CONFIRMED
        
    if status in (APPLICATION_STATUS_PAID, '예정'):
        return STATE_AWAIT_ACCEPT
    if status == APPLICATION_STATUS_PENDING:
        return STATE_PAY_PENDING
    return STATE_AWAIT_ACCEPT


def badge_label(state):
    return _BADGE_LABEL.get(state, '')


def reservation_cards(applications, today=None):
    today = today or date.today()
    cards = []
    for app in applications:
        exp = app.experience
        state = reservation_state(app, today)
        image = ''
        if exp is not None and exp.images:
            image = exp.images.split(',')[0]
        cards.append({
            'app_id': app.id,
            'exp_id': app.experience_id,
            'crop': (exp.crop if exp is not None else '체험'),
            'image': image,
            'date': app.apply_date,
            'time': app.apply_time,
            'participants': app.participants_count,
            'location': (exp.address_detail or exp.location) if exp is not None else '',
            'state': state,
            'badge': badge_label(state),
            'can_review': app.can_review,
        })
    return cards


def experienced_count(applications, today=None):
    return sum(1 for app in applications
               if app.status in (APPLICATION_STATUS_CONFIRMED, '확정', '완료') and is_experience_ended(app))