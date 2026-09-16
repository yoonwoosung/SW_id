# models/click_log.py — 사용자 클릭 로그(파트3). 개인화 추천의 세그먼트 집계 원천.
# 개인정보 최소화: 성별·나이대는 여기 저장하지 않고, 집계 시 user_id로 User와 join해서 얻는다.
from datetime import datetime

from models.base import db


class ClickLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # 비로그인 클릭은 NULL(세그먼트 집계 제외)
    target_type = db.Column(db.String(20), nullable=False)  # 'experience' | 'category'
    target_id = db.Column(db.String(100), nullable=False)   # 체험 id(문자열) 또는 카테고리 코드
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)

    user = db.relationship('User', backref='click_logs')

    __table_args__ = (
        db.Index('ix_clicklog_target', 'target_type', 'target_id'),
    )
