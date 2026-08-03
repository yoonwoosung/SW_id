# routes/payment.py — 더미 '간편결제' 라우트(팝업 결제 페이지 + 결제 처리 API). 얇게 유지.
from flask import render_template, request, session, abort

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
    return render_template('payment.html', application=application, experience=experience, amount=amount)


@api_login_required
def create_payment():
    data = request.get_json(silent=True) or request.form
    try:
        application_id = int(data.get('application_id'))
    except (TypeError, ValueError):
        return error_response("INVALID_APPLICATION_ID", "application_id가 올바르지 않습니다.", 400)

    status, payload = payment_service.pay(session['user_id'], application_id)
    if status == 'not_found':
        return error_response("APPLICATION_NOT_FOUND", "예약을 찾을 수 없습니다.", 404)
    if status == 'forbidden':
        return error_response("FORBIDDEN", "본인의 예약만 결제할 수 있습니다.", 403)
    if status == 'invalid_state':
        return error_response("ALREADY_PROCESSED", "이미 결제되었거나 결제할 수 없는 예약입니다.", 400)
    return success_response(payload, status=201)


def register(app):
    app.add_url_rule('/payments/<int:app_id>', 'payment_page', payment_page)
    app.add_url_rule('/api/payments', 'create_payment', create_payment, methods=['POST'])
