# routes/review.py — 후기·문의 도메인 라우트(후기 등록·문의 등록 및 농장주 답변 관리).
import os
import json
import math
import re
import uuid
import platform
from collections import defaultdict
from datetime import date, timedelta, datetime

from flask import (render_template, request, redirect, url_for, flash,
                   session, abort, jsonify, current_app)
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from sqlalchemy.sql import func
from sqlalchemy import or_, case
from types import SimpleNamespace
from PIL import Image

# [수정] models import 목록에 InquiryReply 추가
from models import db, User, Experience, Review, Inquiry, InquiryReply, Application, Notification
from services.distance import haversine
from services.recommend_data import REGIONAL_SPECIALTIES
from services.recommend_service import matches_specialty, score_components, calculate_score
from services.recommend_reason import recommendation_reason
from services.review_service import analyze_review_with_clova
from external.kakao_map import get_coords_from_address
from common.validators import allowed_file


def add_review(item_id):
    if 'user_id' not in session: return redirect(url_for('login_page'))

    user_id = session['user_id']
    has_confirmed_app = Application.query.filter(
        Application.user_id == user_id,
        Application.experience_id == item_id,
        Application.status == '확정'
    ).first()

    if not has_confirmed_app:
        flash("후기를 작성할 권한이 없습니다. 예약이 확정된 체험에만 후기를 남길 수 있습니다.", "warning")
        return redirect(url_for('experience_detail', item_id=item_id))

    existing_review = Review.query.filter_by(user_id=user_id, experience_id=item_id).first()
    if existing_review:
        flash("이미 이 체험에 대한 후기를 작성하셨습니다.", "warning")
        return redirect(url_for('experience_detail', item_id=item_id))

    review_content = request.form.get('content')
    analysis_json = None
    try:
        # [백 기능 유지] Clova AI 분석
        analysis_json = analyze_review_with_clova(review_content)
        if analysis_json is None:
            flash("AI 후기 분석에 실패했습니다. (API 응답 없음)", "warning")
    except Exception as e:
        print(f"CLOVA API 호출 중 에러 발생: {e}")
        flash(f"AI 후기 분석 중 오류가 발생했습니다. 관리자에게 문의하세요.", "danger")

    new_review = Review(
        rating=int(request.form.get('rating')),
        content=review_content,
        user_id=session['user_id'],
        experience_id=item_id,
        analysis_result=json.dumps(analysis_json) if analysis_json else None
    )
    db.session.add(new_review)

    experience = Experience.query.get_or_404(item_id)
    notification_message = f"'{new_review.user.nickname}'님이 '{experience.crop}' 체험에 새로운 후기를 작성했습니다."
    new_notification = Notification(user_id=experience.farmer_id, message=notification_message)
    db.session.add(new_notification)

    db.session.commit()
    flash("후기가 등록되었습니다.", "success")
    return redirect(url_for('experience_detail', item_id=item_id))


def add_inquiry(item_id):
    if 'user_id' not in session:
        flash("문의를 작성하려면 로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))
    new_inquiry = Inquiry(
        content=request.form.get('content'), user_id=session['user_id'], experience_id=item_id
    )
    db.session.add(new_inquiry)

    experience = Experience.query.get_or_404(item_id)
    notification_message = f"'{new_inquiry.user.nickname}'님이 '{experience.crop}' 체험에 새로운 문의를 남겼습니다."
    new_notification = Notification(user_id=experience.farmer_id, message=notification_message)
    db.session.add(new_notification)

    db.session.commit()
    flash("문의가 등록되었습니다.", "success")
    return redirect(url_for('experience_detail', item_id=item_id))


# =========================================================================
# [프 신규 기능] 농장주 문의 답변 CRUD 3개 함수
# =========================================================================

def reply_inquiry(inquiry_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        abort(403)
    inquiry = Inquiry.query.get_or_404(inquiry_id)
    experience = Experience.query.get_or_404(inquiry.experience_id)
    if experience.farmer_id != session['user_id']:
        abort(403)
    content = (request.form.get('content') or '').strip()
    if not content:
        flash('답변 내용을 입력해주세요.', 'warning')
        return redirect(url_for('easy_communication'))
    reply = InquiryReply(inquiry_id=inquiry_id, content=content)
    db.session.add(reply)
    db.session.commit()
    flash('답변이 등록되었습니다.', 'success')
    return redirect(url_for('easy_communication'))


def edit_inquiry_reply(reply_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        abort(403)
    reply = InquiryReply.query.get_or_404(reply_id)
    experience = Experience.query.get_or_404(reply.inquiry.experience_id)
    if experience.farmer_id != session['user_id']:
        abort(403)
    content = (request.form.get('content') or '').strip()
    if not content:
        flash('수정할 내용을 입력해주세요.', 'warning')
        return redirect(url_for('easy_communication'))
    reply.content = content
    reply.timestamp = datetime.utcnow()
    db.session.commit()
    flash('답변이 수정되었습니다.', 'success')
    return redirect(url_for('easy_communication'))


def delete_inquiry_reply(reply_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        abort(403)
    reply = InquiryReply.query.get_or_404(reply_id)
    experience = Experience.query.get_or_404(reply.inquiry.experience_id)
    if experience.farmer_id != session['user_id']:
        abort(403)
    db.session.delete(reply)
    db.session.commit()
    flash('답변이 삭제되었습니다.', 'success')
    return redirect(url_for('easy_communication'))


def register(app):
    app.add_url_rule('/experience/<int:item_id>/review', 'add_review', add_review, methods=['POST'])
    app.add_url_rule('/experience/<int:item_id>/inquiry', 'add_inquiry', add_inquiry, methods=['POST'])
    
    # [프 신규 라우트 등록] 답변 등록/수정/삭제
    app.add_url_rule('/inquiry/<int:inquiry_id>/reply', 'reply_inquiry', reply_inquiry, methods=['POST'])
    app.add_url_rule('/inquiry/reply/<int:reply_id>/edit', 'edit_inquiry_reply', edit_inquiry_reply, methods=['POST'])
    app.add_url_rule('/inquiry/reply/<int:reply_id>/delete', 'delete_inquiry_reply', delete_inquiry_reply, methods=['POST'])