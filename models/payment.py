# models/payment.py — 토스페이먼츠 결제 건(Payment) 엔티티.
#
# 예약(Application) 1건당 결제 시도가 여러 번 있을 수 있어(실패 후 재시도) 별도 테이블로 둔다.
# order_id 는 우리가 발급해 토스로 보내는 주문번호이고, 승인 응답으로 받은 payment_key 를 저장한다.
# amount 를 여기에 먼저 기록해 두는 것이 핵심이다 — 승인 직전 클라이언트가 보낸 금액과
# 이 값을 대조해야 금액 위변조를 막을 수 있다.
from datetime import datetime

from models.base import db


class Payment(db.Model):
    __tablename__ = 'payment'

    id = db.Column(db.Integer, primary_key=True)

    # 우리가 발급하는 주문번호. 토스가 멱등키처럼 다루므로 유일해야 한다.
    order_id = db.Column(db.String(64), nullable=False, unique=True, index=True)
    # 토스가 승인 시 돌려주는 결제 키. 승인 전에는 없다.
    payment_key = db.Column(db.String(200), nullable=True)

    # 결제 요청 시점에 서버가 계산한 금액(원). 승인 요청의 검증 기준값.
    amount = db.Column(db.Integer, nullable=False)

    # ready(결제창 띄움) → done(승인 완료) / failed(실패·취소)
    status = db.Column(db.String(20), nullable=False, default='ready')
    # 실패 시 토스가 준 코드·사유
    fail_code = db.Column(db.String(100), nullable=True)
    fail_reason = db.Column(db.String(255), nullable=True)
    # 승인 응답의 결제수단(카드/간편결제 등)
    method = db.Column(db.String(50), nullable=True)

    application_id = db.Column(db.Integer, db.ForeignKey('application.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    approved_at = db.Column(db.DateTime, nullable=True)

    application = db.relationship('Application', backref=db.backref('payments', lazy=True))

    STATUS_READY = 'ready'
    STATUS_DONE = 'done'
    STATUS_FAILED = 'failed'
