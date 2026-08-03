# routes/reservation.py — 예약/신청 도메인 라우트(신청·확정·취소).
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
from common.constants import (APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID,
                              APPLICATION_STATUS_CONFIRMED)


def experience_apply(item_id):
    if 'user_id' not in session:
        flash("체험을 신청하려면 로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))

    item = Experience.query.get_or_404(item_id)
    if item.status != 'recruiting':
        flash("현재 모집 중인 체험이 아닙니다.", "warning")
        return redirect(url_for('experience_detail', item_id=item.id))

    if request.method == 'POST':
        apply_date_str = request.form.get('apply_date')
        apply_time_str = request.form.get('apply_time')

        if not apply_date_str or not apply_time_str:
            flash("신청 날짜와 시간을 모두 선택해주세요.", "danger")
            return redirect(url_for('experience_apply', item_id=item.id))
        count_adult = int(request.form.get('count_adult', 0))
        count_teen = int(request.form.get('count_teen', 0))
        count_child = int(request.form.get('count_child', 0))
        total_participants = count_adult + count_teen + count_child

        if total_participants == 0:
            flash("참가 인원을 1명 이상 선택해주세요.", "danger")
            return redirect(url_for('experience_apply', item_id=item.id))

        if item.current_participants + total_participants > item.max_participants:
            flash(f"죄송합니다. 남은 자리가 부족합니다. (현재 {item.max_participants - item.current_participants}명 신청 가능)", "danger")
            return redirect(url_for('experience_detail', item_id=item.id))

        new_application = Application(
            applicant_name=request.form.get('applicant_name'),
            phone_number=request.form.get('phone_number'),
            participants_count=total_participants,
            count_adult=count_adult,
            count_teen=count_teen,
            count_child=count_child,
            apply_date=datetime.strptime(request.form.get('apply_date'), '%Y-%m-%d').date(),
            apply_time=request.form.get('apply_time'),
            user_id=session['user_id'],
            experience_id=item.id
        )

        item.current_participants += total_participants
        db.session.add(new_application)

        # 알림 추가
        notification_message = f"'{new_application.applicant_name}'님이 '{item.crop}' 체험을 신청했습니다."
        new_notification = Notification(user_id=item.farmer_id, message=notification_message)
        db.session.add(new_notification)

        db.session.commit()

        return render_template('apply_complete.html', item=item, name=new_application.applicant_name, application=new_application)

    return render_template('experience_apply.html', item=item)


def confirm_application(app_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        flash("권한이 없습니다.", "danger")
        return redirect(url_for('login_page'))

    application = Application.query.get_or_404(app_id)
    experience = Experience.query.get_or_404(application.experience_id)

    if experience.farmer_id != session.get('user_id'):
        flash("자신의 체험에 대한 예약만 확정할 수 있습니다.", "danger")
        return redirect(url_for('index'))

    if application.status in (APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID):
        application.status = APPLICATION_STATUS_CONFIRMED
        db.session.commit()
        flash(f"{application.applicant_name}님의 예약을 확정했습니다.", "success")
    else:
        flash("이미 처리된 예약입니다.", "warning")

    if request.args.get('easy_mode') == 'true':
        return redirect(url_for('easy_reservations'))
    else:
        return redirect(url_for('detailed_farmer_dashboard'))


def delete_application(app_id):
    if 'user_id' not in session: abort(403)
    application = Application.query.get_or_404(app_id)
    if application.user_id != session['user_id']: abort(403)

    experience = Experience.query.get(application.experience_id)
    if experience and application.status != '취소': # 이미 취소된 건은 인원수 복구 안함
        experience.current_participants = max(0, experience.current_participants - application.participants_count)

    application.status = '취소'

    # 알림 추가
    notification_message = f"'{application.applicant_name}'님이 '{experience.crop}' 체험 신청을 취소했습니다."
    new_notification = Notification(user_id=experience.farmer_id, message=notification_message)
    db.session.add(new_notification)

    # Delete the associated review
    existing_review = Review.query.filter_by(
        user_id=application.user_id,
        experience_id=application.experience_id
    ).first()
    if existing_review:
        db.session.delete(existing_review)

    db.session.commit()

    flash("체험 신청이 취소되었습니다.", "success")
    return redirect(url_for('my_info'))


def register(app):
    app.add_url_rule('/experience/apply/<int:item_id>', 'experience_apply', experience_apply, methods=['GET', 'POST'])
    app.add_url_rule('/application/confirm/<int:app_id>', 'confirm_application', confirm_application, methods=['POST'])
    app.add_url_rule('/application/delete/<int:app_id>', 'delete_application', delete_application, methods=['POST'])
