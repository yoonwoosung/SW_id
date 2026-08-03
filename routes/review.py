# routes/review.py — 후기·문의 도메인 라우트(후기 등록·문의 등록).
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

from models import db, User, Experience, Review, Inquiry, Application, Notification
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
    analysis_json = None  # 기본값을 None으로 설정
    try:
        # AI 분석 함수를 try-except 블록으로 감싸서 에러를 포착합니다.
        analysis_json = analyze_review_with_clova(review_content)
        if analysis_json is None:
            # API에서 정상 응답을 받았지만, 내용이 비어있는 경우
            flash("AI 후기 분석에 실패했습니다. (API 응답 없음)", "warning")
    except Exception as e:
        # API 호출 중 네트워크 오류 등 예외가 발생한 경우
        print(f"CLOVA API 호출 중 에러 발생: {e}") # 서버 로그에 에러 기록
        flash(f"AI 후기 분석 중 오류가 발생했습니다. 관리자에게 문의하세요.", "danger")

    new_review = Review(
        rating=int(request.form.get('rating')),
        content=review_content, # review_content 변수 사용
        user_id=session['user_id'],
        experience_id=item_id,
        # AI 분석 결과를 JSON 문자열 형태로 저장
        analysis_result=json.dumps(analysis_json) if analysis_json else None
    )
    db.session.add(new_review)

    # 알림 추가
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

    # 알림 추가
    experience = Experience.query.get_or_404(item_id)
    notification_message = f"'{new_inquiry.user.nickname}'님이 '{experience.crop}' 체험에 새로운 문의를 남겼습니다."
    new_notification = Notification(user_id=experience.farmer_id, message=notification_message)
    db.session.add(new_notification)

    db.session.commit()
    flash("문의가 등록되었습니다.", "success")
    return redirect(url_for('experience_detail', item_id=item_id))


def register(app):
    app.add_url_rule('/experience/<int:item_id>/review', 'add_review', add_review, methods=['POST'])
    app.add_url_rule('/experience/<int:item_id>/inquiry', 'add_inquiry', add_inquiry, methods=['POST'])
