# services/activity_service.py — '내 활동' 예약 카드용 상태 분류·뷰 모델(순수 로직, 테스트 가능).
# 실제 Application.status(예정/결제완료/확정/취소) + 예정일을 목업 뱃지 상태로 매핑한다(엄격: 농장주 수락 구분).
from datetime import date

from common.constants import (
    APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID,
    APPLICATION_STATUS_CONFIRMED, APPLICATION_STATUS_CANCELLED,
)

# 카드 상태 코드(템플릿 뱃지·버튼 분기 키).
STATE_PAY_PENDING = 'pay_pending'     # 결제 대기 → [결제하기][예약 취소]
STATE_AWAIT_ACCEPT = 'await_accept'   # 수락 대기중(결제O, 농장주 확정 전) → [예약 취소][상세]
STATE_CONFIRMED = 'confirmed'         # 예약 확정(농장주 확정, 예정일 이후) → [코스 보기][상세]
STATE_COMPLETED = 'completed'         # 체험 완료(확정 + 예정일 지남) → [후기 남기기][상세]
STATE_CANCELLED = 'cancelled'         # 취소됨 → [상세]

_BADGE_LABEL = {
    STATE_PAY_PENDING: '결제 대기',
    STATE_AWAIT_ACCEPT: '수락 대기중',
    STATE_CONFIRMED: '예약 확정',
    STATE_COMPLETED: '체험 완료',
    STATE_CANCELLED: '취소됨',
}


def reservation_state(application, today=None):
    """예약 1건의 카드 상태 코드를 반환한다(엄격 매핑).
    확정된 예약의 예정일이 지나면 '체험 완료'. 취소가 최우선."""
    today = today or date.today()
    status = application.status
    if status == APPLICATION_STATUS_CANCELLED:
        return STATE_CANCELLED
    is_past = application.apply_date is not None and application.apply_date < today
    if status == APPLICATION_STATUS_CONFIRMED:
        return STATE_COMPLETED if is_past else STATE_CONFIRMED
    if status == APPLICATION_STATUS_PAID:
        return STATE_AWAIT_ACCEPT
    if status == APPLICATION_STATUS_PENDING:
        return STATE_PAY_PENDING
    return STATE_AWAIT_ACCEPT   # 알 수 없는 값은 안전하게 진행 중으로 취급


def badge_label(state):
    return _BADGE_LABEL.get(state, '')


def reservation_cards(applications, today=None):
    """예약 목록을 카드 렌더용 뷰 딕셔너리 리스트로 변환한다."""
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
        })
    return cards


def experienced_count(applications, today=None):
    """'FarmLink와 함께한 체험 횟수' = 결제 이상 진행된(취소·미결제 제외) 예약 수."""
    return sum(1 for app in applications
               if app.status in (APPLICATION_STATUS_PAID, APPLICATION_STATUS_CONFIRMED))
