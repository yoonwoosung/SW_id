# services/toss_service.py — 토스페이먼츠 결제 승인 API 호출.
#
# 이 모듈만 시크릿 키를 다룬다. 라우트·템플릿은 시크릿 키를 절대 만지지 않는다.
# 승인(confirm)은 "결제창에서 성공했다"를 서버가 최종 확정하는 단계다.
# 클라이언트가 보낸 값을 그대로 믿으면 금액을 바꿔치기당하므로,
# 반드시 서버가 저장해 둔 금액(Payment.amount)과 대조한 뒤 호출한다.
import base64
import os

import requests

CONFIRM_URL = 'https://api.tosspayments.com/v1/payments/confirm'

# 토스 승인은 결제 확정이라 짧은 타임아웃은 위험하다(승인됐는데 우리만 실패로 처리할 수 있음).
TIMEOUT_SECONDS = 15


class TossError(Exception):
    """토스 승인 실패. code/message 는 사용자에게 보여줄 수 있는 수준으로만 쓴다."""

    def __init__(self, code, message, status=400):
        super().__init__(message)
        self.code = code
        self.message = message
        self.status = status


def _secret_key():
    key = os.environ.get('TOSS_SECRET_KEY')
    if not key:
        raise TossError('TOSS_NOT_CONFIGURED',
                        '결제 설정이 완료되지 않았습니다. 관리자에게 문의해 주세요.', 500)
    return key


def _auth_header():
    # 토스 규격: Basic base64("<시크릿키>:")  — 콜론까지 포함하고 비밀번호는 빈 문자열.
    token = base64.b64encode(f"{_secret_key()}:".encode('utf-8')).decode('ascii')
    return f"Basic {token}"


def confirm_payment(payment_key, order_id, amount):
    """토스에 결제 승인을 요청한다. 성공 시 응답 dict, 실패 시 TossError.

    amount 는 서버가 계산해 저장해 둔 금액이어야 한다(클라이언트 값 그대로 넘기지 말 것).
    """
    try:
        res = requests.post(
            CONFIRM_URL,
            json={'paymentKey': payment_key, 'orderId': order_id, 'amount': amount},
            headers={'Authorization': _auth_header(), 'Content-Type': 'application/json'},
            timeout=TIMEOUT_SECONDS,
        )
    except requests.Timeout:
        # 승인 요청이 토스에 도달했을 수도 있다. 임의로 성공/실패 확정하지 않고 재조회를 유도한다.
        raise TossError('TOSS_TIMEOUT',
                        '결제 승인 응답이 지연되고 있습니다. 잠시 후 예약 내역에서 상태를 확인해 주세요.', 504)
    except requests.RequestException:
        raise TossError('TOSS_UNREACHABLE', '결제 서버에 연결하지 못했습니다.', 502)

    try:
        body = res.json()
    except ValueError:
        raise TossError('TOSS_BAD_RESPONSE', '결제 서버 응답을 해석할 수 없습니다.', 502)

    if res.status_code != 200:
        # 토스 에러 규격: {"code": "...", "message": "..."}
        raise TossError(body.get('code') or 'TOSS_CONFIRM_FAILED',
                        body.get('message') or '결제 승인에 실패했습니다.', 400)

    return body
