"""농장주 승인 단계 테스트 — 결제 성공은 '확정'이 아니라 '결제완료'(승인 대기)다.

핵심: 농장주가 수락하지 않았는데 예약이 확정되면 안 된다.
'결제완료'는 이미 있던 상태값이고(activity_service 가 '수락 대기중'으로 판정),
토스 승인 경로만 '확정'으로 건너뛰고 있었다.
"""
from datetime import date, timedelta

import pytest
from werkzeug.security import generate_password_hash

import app as farmlink
from models import db, User, Experience, Application
from common.constants import (APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID,
                              APPLICATION_STATUS_CONFIRMED, APPLICATION_STATUS_CANCELLED)

PASSWORD = "pw12345678"
COST = 20000
HEADCOUNT = 2


def _user(email, role='experiencer'):
    u = User(nickname="n", email=email, name="이름", role=role,
             password=generate_password_hash(PASSWORD, method='pbkdf2:sha256'))
    db.session.add(u)
    db.session.commit()
    return u


def _experience(farmer, max_participants=20):
    exp = Experience(crop="딸기", location="충남", address_detail="충남 논산시",
                     cost=COST, farmer_id=farmer.id, status='recruiting',
                     max_participants=max_participants, current_participants=HEADCOUNT,
                     end_date=date.today() + timedelta(days=30), lat=36.2, lng=127.1)
    db.session.add(exp)
    db.session.commit()
    return exp


def _application(user, exp, status=APPLICATION_STATUS_PAID):
    row = Application(applicant_name="홍길동", phone_number="010-0000-0000",
                      participants_count=HEADCOUNT,
                      apply_date=date.today() + timedelta(days=7),
                      apply_time="10:00", user_id=user.id, experience_id=exp.id,
                      status=status)
    db.session.add(row)
    db.session.commit()
    return row


@pytest.fixture
def client(db_session):
    farmlink.app.secret_key = 'test-secret'
    with farmlink.app.test_client() as c:
        yield c


def _login(client, email):
    return client.post('/login', data={'email': email, 'password': PASSWORD})


# ───────────────────── 농장주 '수락 대기' 목록 ─────────────────────

def test_paid_reservation_appears_in_pending_list(client):
    """★결제를 마친 예약이 농장주의 수락 대기 목록에 떠야 한다.★

    예전에는 이 목록이 '예정'(결제 전)을 봐서, 결제 성공을 '결제완료'로
    바꾸면 돈을 낸 예약이 농장주 화면에서 사라졌다.
    """
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)

    _login(client, "f@x.com")
    html = client.get('/easy_mode').get_data(as_text=True)

    assert f'/application/confirm/{row.id}' in html
    assert f'/application/reject/{row.id}' in html


def test_unpaid_reservation_not_in_pending_list(client):
    """결제 전('예정') 건은 수락 대기 목록에 뜨지 않는다."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PENDING)

    _login(client, "f@x.com")
    html = client.get('/easy_mode').get_data(as_text=True)

    assert f'/application/confirm/{row.id}' not in html


def test_confirmed_reservation_not_in_pending_list(client):
    """이미 확정된 건도 수락 대기 목록에 남지 않는다."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_CONFIRMED)

    _login(client, "f@x.com")
    html = client.get('/easy_mode').get_data(as_text=True)

    assert f'/application/confirm/{row.id}' not in html


# ───────────────────── 수락 ─────────────────────

def test_farmer_accept_moves_paid_to_confirmed(client):
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)

    _login(client, "f@x.com")
    client.post(f'/application/confirm/{row.id}', follow_redirects=True)

    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_CONFIRMED


def test_other_farmer_cannot_accept(client):
    """남의 체험 예약은 수락할 수 없다."""
    owner = _user("f@x.com", 'farmer')
    stranger = _user("f2@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(owner), APPLICATION_STATUS_PAID)

    _login(client, "f2@x.com")
    client.post(f'/application/confirm/{row.id}', follow_redirects=True)

    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_PAID


def test_already_confirmed_is_not_reprocessed(client):
    """기존 '확정' 예약은 그대로 둔다(재처리 금지)."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_CONFIRMED)

    _login(client, "f@x.com")
    client.post(f'/application/confirm/{row.id}', follow_redirects=True)

    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_CONFIRMED


def test_cancelled_cannot_be_accepted(client):
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_CANCELLED)

    _login(client, "f@x.com")
    client.post(f'/application/confirm/{row.id}', follow_redirects=True)

    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_CANCELLED


# ═════════════════════ 거절 → 포인트 환급 ═════════════════════
#
# 토스 결제 취소 API 는 쓰지 않는다. 실제 결제한 금액을 포인트로 돌려준다.
# 한 건의 거절에서 두 가지가 따로 일어난다:
#   ① 환급 — 카드로 낸 금액(payment.amount)
#   ② 원복 — 결제에 썼던 포인트(payment.used_points)

from models import Payment, PointLog, Notification
from common.constants import (POINT_REASON_REJECT_REFUND, POINT_REASON_REFUND,
                              POINT_REASON_PAYMENT, POINT_REASON_LABELS)
from services import point_service

ORDER_TOTAL = COST * HEADCOUNT      # 40,000원


def _paid_via_toss(buyer, row, used_points=0):
    """토스로 승인까지 끝난 결제를 만든다(prepare→confirm 이 남기는 상태와 동일)."""
    if used_points:
        db.session.add(PointLog(user_id=buyer.id, amount=used_points,
                                reason='grant'))                      # 보유 포인트 지급
        db.session.add(PointLog(user_id=buyer.id, amount=-used_points,
                                reason='use', application_id=row.id))  # 결제 시 차감
    charged = ORDER_TOTAL - used_points
    payment = Payment(order_id=f"farmlink-{row.id}-test", payment_key='pk',
                      amount=charged, order_total=ORDER_TOTAL, used_points=used_points,
                      status=Payment.STATUS_DONE,
                      application_id=row.id, user_id=buyer.id)
    db.session.add(payment)
    db.session.commit()
    return payment


def _reject(client, row_id):
    return client.post(f'/application/reject/{row_id}', follow_redirects=True)


def test_reject_refunds_charged_amount_as_points(client):
    """★현금으로 낸 금액이 포인트로 돌아온다.★"""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)
    _paid_via_toss(buyer, row)

    _login(client, "f@x.com")
    _reject(client, row.id)

    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_CANCELLED
    assert point_service.get_balance(buyer.id) == ORDER_TOTAL
    log = PointLog.query.filter_by(application_id=row.id,
                                   reason=POINT_REASON_REJECT_REFUND).one()
    assert log.amount == ORDER_TOTAL


def test_reject_refunds_cash_and_restores_used_points_separately(client):
    """★환급(현금분)과 원복(쓴 포인트)은 다른 건이다. 둘 다 들어와야 한다.★

    40,000원 주문 / 포인트 10,000P 사용 → 카드 30,000원.
    거절하면 30,000P(환급) + 10,000P(원복) = 잔액 40,000P.
    """
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)
    _paid_via_toss(buyer, row, used_points=10000)

    _login(client, "f@x.com")
    _reject(client, row.id)

    refund = PointLog.query.filter_by(application_id=row.id,
                                      reason=POINT_REASON_REJECT_REFUND).one()
    restore = PointLog.query.filter_by(application_id=row.id,
                                       reason=POINT_REASON_REFUND).one()
    assert refund.amount == 30000, "카드로 낸 금액"
    assert restore.amount == 10000, "결제에 썼던 포인트"
    # 지급 10,000 − 사용 10,000 + 환급 30,000 + 원복 10,000
    assert point_service.get_balance(buyer.id) == 40000


def test_reject_twice_does_not_double_refund(client):
    """★같은 예약을 두 번 거절해도 포인트가 두 번 들어가지 않는다.★"""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)
    _paid_via_toss(buyer, row, used_points=10000)

    _login(client, "f@x.com")
    _reject(client, row.id)
    balance_once = point_service.get_balance(buyer.id)
    _reject(client, row.id)          # 두 번째 — 이미 '취소'라 막힌다
    _reject(client, row.id)          # 세 번째

    assert point_service.get_balance(buyer.id) == balance_once == 40000
    assert PointLog.query.filter_by(application_id=row.id,
                                    reason=POINT_REASON_REJECT_REFUND).count() == 1
    assert PointLog.query.filter_by(application_id=row.id,
                                    reason=POINT_REASON_REFUND).count() == 1


def test_refund_is_idempotent_even_if_called_directly(client):
    """상태 검사를 우회해 환급 함수를 직접 두 번 불러도 한 번만 적립된다."""
    from routes.reservation import refund_rejected_application
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)
    _paid_via_toss(buyer, row, used_points=10000)

    assert refund_rejected_application(row) == (30000, 10000)
    assert refund_rejected_application(row) == (0, 0)      # 두 번째는 0
    assert point_service.get_balance(buyer.id) == 40000


def test_reject_without_payment_refunds_nothing(client):
    """결제 전('예정') 거절은 환급할 돈이 없다. 오류 없이 취소만 된다."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PENDING)

    _login(client, "f@x.com")
    _reject(client, row.id)

    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_CANCELLED
    assert point_service.get_balance(buyer.id) == 0


def test_reject_keeps_payment_status_done(client):
    """payment.status 는 'done' 그대로 둔다. 토스에서 실제 승인된 결제가 맞다."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)
    payment = _paid_via_toss(buyer, row)

    _login(client, "f@x.com")
    _reject(client, row.id)

    assert db.session.get(Payment, payment.id).status == Payment.STATUS_DONE


def test_reject_keeps_earned_points(client):
    """적립(3%)은 회수하지 않는다. 거절은 사용자 잘못이 아니다."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)
    _paid_via_toss(buyer, row)
    point_service.earn_points_for_payment(buyer.id, row.id, ORDER_TOTAL)   # 1,200P

    _login(client, "f@x.com")
    _reject(client, row.id)

    assert PointLog.query.filter_by(application_id=row.id,
                                    reason=POINT_REASON_PAYMENT).one().amount == 1200
    assert point_service.get_balance(buyer.id) == ORDER_TOTAL + 1200


def test_reject_notifies_user_about_refund(client):
    """★사용자에게 '포인트로 환급되었습니다' 알림이 가야 한다.★"""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)
    _paid_via_toss(buyer, row)

    _login(client, "f@x.com")
    _reject(client, row.id)

    notif = Notification.query.filter_by(user_id=buyer.id).order_by(
        Notification.id.desc()).first()
    assert notif is not None
    assert '거절' in notif.message and '포인트로 환급' in notif.message
    assert '40,000P' in notif.message
    assert notif.notif_type == 'reservation_rejected'


def test_reject_restores_seats(client):
    """거절하면 모집 인원이 돌아온다(기존 동작 유지)."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    exp = _experience(farmer)
    row = _application(buyer, exp, APPLICATION_STATUS_PAID)
    _paid_via_toss(buyer, row)

    _login(client, "f@x.com")
    _reject(client, row.id)

    assert db.session.get(Experience, exp.id).current_participants == 0


def test_reject_restores_surplus_quantity(client):
    """과생산 체험은 차감했던 수량도 돌아온다(기존 동작 유지)."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    exp = _experience(farmer)
    exp.is_surplus = True
    exp.surplus_qty_total = 500
    exp.surplus_per_person = 5
    exp.surplus_qty_taken = 5 * HEADCOUNT      # 예약 때 차감된 만큼
    db.session.commit()
    row = _application(buyer, exp, APPLICATION_STATUS_PAID)
    _paid_via_toss(buyer, row)

    _login(client, "f@x.com")
    _reject(client, row.id)

    assert db.session.get(Experience, exp.id).surplus_qty_taken == 0


def test_confirmed_reservation_is_not_refunded(client):
    """이미 확정된 예약은 거절 대상이 아니다. 환급도 일어나지 않는다."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_CONFIRMED)
    _paid_via_toss(buyer, row)

    _login(client, "f@x.com")
    _reject(client, row.id)

    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_CONFIRMED
    assert point_service.get_balance(buyer.id) == 0


def test_other_farmer_cannot_reject(client):
    owner = _user("f@x.com", 'farmer')
    _user("f2@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(owner), APPLICATION_STATUS_PAID)
    _paid_via_toss(buyer, row)

    _login(client, "f2@x.com")
    res = _reject(client, row.id)

    assert res.status_code == 403
    assert db.session.get(Application, row.id).status == APPLICATION_STATUS_PAID
    assert point_service.get_balance(buyer.id) == 0


# ───────────────────── 포인트 내역 한글 라벨 ─────────────────────

def test_point_log_exposes_korean_label(client):
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)
    _paid_via_toss(buyer, row, used_points=10000)

    _login(client, "f@x.com")
    _reject(client, row.id)

    labels = {l['reason']: l['reason_label']
              for l in point_service.get_point_summary(buyer.id)['logs']}
    assert labels[POINT_REASON_REJECT_REFUND] == '예약 거절 환급'
    assert labels[POINT_REASON_REFUND] == '포인트 환불'
    assert labels['use'] == '포인트 사용'


def test_unknown_reason_falls_back_to_code(client):
    """매핑에 없는 사유는 코드를 그대로 보여준다(내역이 비지 않게)."""
    buyer = _user("u@x.com")
    db.session.add(PointLog(user_id=buyer.id, amount=100, reason='mystery'))
    db.session.commit()

    log = point_service.get_point_summary(buyer.id)['logs'][0]
    assert log['reason_label'] == 'mystery'


def test_every_reason_constant_has_a_label():
    """사유코드를 추가하고 라벨을 빠뜨리면 영어가 노출된다."""
    for code in ('payment', 'use', 'refund', POINT_REASON_REJECT_REFUND):
        assert code in POINT_REASON_LABELS


# ═════════════════════ 화면 ═════════════════════

def test_user_sees_waiting_for_approval_message(client):
    """★사용자 '내 활동'에 '농장주 승인을 기다리는 중입니다'가 보인다.★"""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)

    _login(client, "u@x.com")
    for path in ('/my_info', '/mypage'):
        html = client.get(path, follow_redirects=True).get_data(as_text=True)
        assert '수락 대기중' in html, path
        assert '농장주 승인을 기다리는 중입니다' in html, path


def test_user_sees_refund_notice_after_reject(client):
    """★거절당한 예약 카드에 환급 안내가 보인다.★"""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)
    _paid_via_toss(buyer, row)

    _login(client, "f@x.com")
    _reject(client, row.id)

    _login(client, "u@x.com")
    for path in ('/my_info', '/mypage'):
        html = client.get(path, follow_redirects=True).get_data(as_text=True)
        assert '결제 금액이 포인트로 환급되었습니다' in html, path


def test_self_cancelled_shows_no_refund_notice(client):
    """사용자가 스스로 취소한 건에는 환급 안내가 뜨면 안 된다.

    둘 다 status 는 '취소'라 환급 로그로 구분한다.
    """
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    row = _application(buyer, _experience(farmer), APPLICATION_STATUS_PAID)

    _login(client, "u@x.com")
    client.post(f'/application/delete/{row.id}', follow_redirects=True)

    for path in ('/my_info', '/mypage'):
        html = client.get(path, follow_redirects=True).get_data(as_text=True)
        assert '포인트로 환급되었습니다' not in html, path


def test_farmer_easy_reservations_shows_accept_and_reject(client):
    """농장주 예약 목록에서 결제 완료 건에만 수락·거절이 뜬다."""
    farmer = _user("f@x.com", 'farmer')
    buyer = _user("u@x.com")
    exp = _experience(farmer)
    paid = _application(buyer, exp, APPLICATION_STATUS_PAID)
    unpaid = _application(buyer, exp, APPLICATION_STATUS_PENDING)

    _login(client, "f@x.com")
    html = client.get('/easy_mode/reservations').get_data(as_text=True)

    assert f'/application/confirm/{paid.id}' in html
    assert f'/application/reject/{paid.id}' in html
    assert f'/application/confirm/{unpaid.id}' not in html
    assert '수락 대기' in html
