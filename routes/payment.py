# routes/payment.py — 토스페이먼츠 테스트 결제 라우트(결제창 + 준비/승인/실패 API). 얇게 유지.
#
# 흐름:
#   예약 신청 → Application '예정'(결제 대기)
#     → /payments/<id>            결제창(토스 SDK, 클라이언트 키)
#     → POST /api/payments/prepare  서버가 주문번호·금액 확정 (Payment ready)
#     → 토스 결제창 → successUrl 로 복귀
#     → POST /api/payments/confirm  서버가 시크릿 키로 승인 + 금액 검증 → '결제완료'
#     → 완료 화면
# 실패·취소는 /payments/<id>/fail 로 돌아온다.
from flask import render_template, request, session, abort, url_for, current_app, redirect, flash

from common.response import success_response, error_response
from common.auth import api_login_required
from services import payment_service


def payment_page(app_id):
    # 팝업 결제 화면. 로그인 + 본인 소유 예약만 접근 가능.
    if 'user_id' not in session:
        abort(403)
    status, application, experience = payment_service.get_owned_application(session['user_id'], app_id)
    if status == 'not_found':
        abort(404)
    if status == 'forbidden':
        abort(403)
    amount = payment_service.calculate_amount(application, experience)
    return render_template(
        'payment.html',
        application=application,
        experience=experience,
        amount=amount,
        # 클라이언트 키만 내려보낸다. 시크릿 키는 서버 밖으로 나가지 않는다.
        toss_client_key=current_app.config.get('TOSS_CLIENT_KEY'),
        success_url=url_for('payment_success', app_id=app_id, _external=True),
        fail_url=url_for('payment_fail', app_id=app_id, _external=True),
    )


@api_login_required
def prepare_payment():
    """결제창을 열기 직전 주문번호·금액을 서버에서 확정한다."""
    data = request.get_json(silent=True) or request.form
    try:
        application_id = int(data.get('application_id'))
    except (TypeError, ValueError):
        return error_response("INVALID_APPLICATION_ID", "application_id가 올바르지 않습니다.", 400)

    status, payload = payment_service.prepare(session['user_id'], application_id)
    if status == 'not_found':
        return error_response("APPLICATION_NOT_FOUND", "예약을 찾을 수 없습니다.", 404)
    if status == 'forbidden':
        return error_response("FORBIDDEN", "본인의 예약만 결제할 수 있습니다.", 403)
    if status == 'invalid_state':
        return error_response("ALREADY_PROCESSED", "이미 결제되었거나 결제할 수 없는 예약입니다.", 400)
    return success_response(payload, status=201)


@api_login_required
def confirm_payment():
    """토스 결제창 성공 후 서버가 최종 승인한다(시크릿 키 + 금액 검증)."""
    data = request.get_json(silent=True) or request.form
    payment_key = data.get('paymentKey') or data.get('payment_key')
    order_id = data.get('orderId') or data.get('order_id')
    amount = data.get('amount')

    if not payment_key or not order_id or amount is None:
        return error_response("INVALID_PAYMENT_PARAMS",
                              "결제 정보(paymentKey/orderId/amount)가 누락되었습니다.", 400)

    status, payload = payment_service.confirm(session['user_id'], payment_key, order_id, amount)

    if status == 'not_found':
        return error_response("ORDER_NOT_FOUND", "주문을 찾을 수 없습니다.", 404)
    if status == 'forbidden':
        return error_response("FORBIDDEN", "본인의 주문만 결제할 수 있습니다.", 403)
    if status == 'amount_mismatch':
        return error_response("AMOUNT_MISMATCH", "결제 금액이 주문 금액과 일치하지 않습니다.", 400)
    if status == 'toss_error':
        # payload 는 TossError
        return error_response(payload.code, payload.message, payload.status)

    # 'ok' 와 'already_done' 모두 완료 화면으로 보낸다(새로고침 대비).
    payload = dict(payload)
    payload['redirect'] = url_for('reservation_complete', app_id=payload['application_id'])
    return success_response(payload, status=200)


def payment_success(app_id):
    """토스 successUrl. 실제 승인은 화면의 JS 가 /api/payments/confirm 으로 수행한다."""
    if 'user_id' not in session:
        abort(403)
    return render_template(
        'payment_result.html',
        app_id=app_id,
        payment_key=request.args.get('paymentKey'),
        order_id=request.args.get('orderId'),
        amount=request.args.get('amount'),
    )


def payment_fail(app_id):
    """토스 failUrl. 결제 실패·취소. 예약은 결제 대기 그대로 두고 재시도를 안내한다."""
    if 'user_id' not in session:
        abort(403)
    code = request.args.get('code')
    message = request.args.get('message')
    order_id = request.args.get('orderId')
    if order_id:
        payment_service.mark_failed(session['user_id'], order_id, code, message)

    # 사용자가 창을 닫은 것은 오류가 아니므로 문구를 구분한다.
    if code == 'USER_CANCEL':
        flash("결제를 취소했습니다. 예약은 결제 대기 상태로 남아 있어요.", "info")
    else:
        flash(f"결제에 실패했습니다. {message or ''}".strip(), "danger")
    return redirect(url_for('payment_page', app_id=app_id))


def register(app):
    app.add_url_rule('/payments/<int:app_id>', 'payment_page', payment_page)
    app.add_url_rule('/payments/<int:app_id>/success', 'payment_success', payment_success)
    app.add_url_rule('/payments/<int:app_id>/fail', 'payment_fail', payment_fail)
    app.add_url_rule('/api/payments/prepare', 'prepare_payment', prepare_payment, methods=['POST'])
    app.add_url_rule('/api/payments/confirm', 'confirm_payment', confirm_payment, methods=['POST'])
