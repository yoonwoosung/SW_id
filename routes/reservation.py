# routes/reservation.py — 예약/신청 도메인 라우트(신청·확정·거절·취소).
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
from services import reservation_validator
from services import payment_service
from services import point_service
from services import surplus_service
from external.kakao_map import get_coords_from_address
from common.validators import allowed_file
from common.constants import (APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID,
                              APPLICATION_STATUS_CONFIRMED, APPLICATION_STATUS_CANCELLED)


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
        counts, total_participants, error = reservation_validator.parse_participants(request.form)
        if error:
            flash(error, "danger")
            return redirect(url_for('experience_apply', item_id=item.id))
        count_adult = counts['count_adult']
        count_teen = counts['count_teen']
        count_child = counts['count_child']

        apply_date, error = reservation_validator.parse_apply_date(apply_date_str)
        if error:
            flash(error, "danger")
            return redirect(url_for('experience_apply', item_id=item.id))

        # 폼의 min/max 는 브라우저 힌트일 뿐이라 직접 POST 하면 뚫린다.
        error = reservation_validator.validate_apply_date_range(apply_date, item)
        if error:
            flash(error, "danger")
            return redirect(url_for('experience_apply', item_id=item.id))

        if item.current_participants + total_participants > item.max_participants:
            flash(f"죄송합니다. 남은 자리가 부족합니다. (현재 {item.max_participants - item.current_participants}명 신청 가능)", "danger")
            return redirect(url_for('experience_detail', item_id=item.id))

        # 과생산은 수량도 본다. 정원과 별개로 재고가 모자랄 수 있다.
        if surplus_service.is_surplus(item):
            need = surplus_service.required_qty(item, total_participants)
            left = surplus_service.remaining(item)
            if need > left:
                flash(f"남은 수량이 부족합니다. (남은 양 {left}{item.surplus_unit or ''}, "
                      f"신청 {need}{item.surplus_unit or ''})", "danger")
                return redirect(url_for('experience_detail', item_id=item.id))

        new_application = Application(
            applicant_name=request.form.get('applicant_name'),
            phone_number=request.form.get('phone_number'),
            participants_count=total_participants,
            count_adult=count_adult,
            count_teen=count_teen,
            count_child=count_child,
            apply_date=apply_date,
            apply_time=request.form.get('apply_time'),
            user_id=session['user_id'],
            experience_id=item.id
        )

        # 조건을 UPDATE 에 실어 보내 동시 요청이 겹쳐도 총량을 넘지 않게 한다.
        if not surplus_service.take(item, total_participants):
            flash("방금 다른 분이 먼저 신청해 남은 수량이 부족해졌습니다. 다시 확인해 주세요.", "danger")
            return redirect(url_for('experience_detail', item_id=item.id))

        item.current_participants += total_participants
        db.session.add(new_application)

        notification_message = f"'{new_application.applicant_name}'님이 '{item.crop}' 체험을 신청했습니다."
        new_notification = Notification(user_id=item.farmer_id, message=notification_message)
        db.session.add(new_notification)

        db.session.commit()

        return redirect(url_for('payment_page', app_id=new_application.id))

    # 오늘 날짜·현재 시각을 서버 기준으로 넘긴다. 브라우저 시계가 틀린 기기에서
    # "UI 는 통과했는데 서버가 거부"하는 일이 없게 서버 검증과 같은 값을 쓴다.
    now = datetime.now()
    return render_template('experience_apply.html', item=item,
                           today_str=now.strftime('%Y-%m-%d'),
                           now_minutes=now.hour * 60 + now.minute)


def reservation_complete(app_id):
    if 'user_id' not in session:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))
    application = Application.query.get_or_404(app_id)
    if application.user_id != session['user_id']:
        abort(403)
    if application.status == APPLICATION_STATUS_PENDING:
        return redirect(url_for('payment_page', app_id=app_id))
    item = Experience.query.get(application.experience_id)
    return render_template('apply_complete.html', item=item,
                           name=application.applicant_name, application=application)


def confirm_application(app_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        flash("권한이 없습니다.", "danger")
        return redirect(url_for('login_page'))

    application = Application.query.get_or_404(app_id)
    experience = Experience.query.get_or_404(application.experience_id)

    if experience.farmer_id != session.get('user_id'):
        flash("자신의 체험에 대한 예약만 확정할 수 있습니다.", "danger")
        return redirect(url_for('index'))

    if application.status in (APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID, '예정'):
        application.status = APPLICATION_STATUS_CONFIRMED
        db.session.commit()
        flash(f"{application.applicant_name}님의 예약을 확정했습니다.", "success")
    else:
        flash("이미 처리된 예약입니다.", "warning")

    return redirect(url_for('farmer_easy_mode', tab='reservations'))


def refund_rejected_application(application):
    """농장주 거절 시 돈을 돌려준다. 반환: (환급 포인트, 원복 포인트).

    ★토스 결제 취소 API 는 부르지 않는다.★ 대신 실제 결제한 금액만큼
    포인트로 환급한다. 이때 두 건이 따로 일어난다 —

      ① 환급: 카드로 실제 낸 금액(payment.amount) → 포인트로 지급
      ② 원복: 결제에 썼던 포인트(payment.used_points) → 되돌림

    ①과 ②는 사유코드가 다르다. 같은 코드를 쓰면 멱등 검사가 서로를 막아
    한쪽만 처리된다(services/point_service 주석 참고).

    둘 다 멱등이라 같은 예약을 두 번 거절해도 포인트가 두 번 들어가지 않는다.
    더미 결제 경로는 Payment 가 없어 (0, 0) 이 나온다 — 청구된 돈이 없다.
    """
    payment = payment_service.done_payment_for(application.id)
    if payment is None:
        return 0, 0
    refunded = point_service.refund_payment_as_points(
        payment.user_id, application.id, payment.amount)
    restored = point_service.refund_points(
        payment.user_id, application.id, payment.used_points)
    return refunded, restored


def reject_application(app_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        abort(403)
    application = Application.query.get_or_404(app_id)
    experience = Experience.query.get_or_404(application.experience_id)
    if experience.farmer_id != session.get('user_id'):
        abort(403)
    if application.status not in (APPLICATION_STATUS_PENDING, APPLICATION_STATUS_PAID):
        flash("이미 처리된 예약입니다.", "warning")
        return redirect(url_for('farmer_easy_mode', tab='reservations'))

    experience.current_participants = max(0, experience.current_participants - application.participants_count)
    surplus_service.restore(experience, application.participants_count)
    application.status = APPLICATION_STATUS_CANCELLED
    db.session.commit()

    # 자리·수량을 먼저 돌려놓고 돈을 처리한다. 환급이 실패해도 좌석은 이미 풀렸다.
    refunded, restored = refund_rejected_application(application)

    message = f"'{experience.crop}' 체험 예약이 농장주 사정으로 거절되었습니다."
    if refunded or restored:
        message += f" 결제 금액이 포인트로 환급되었습니다. (+{refunded + restored:,}P)"
    db.session.add(Notification(
        user_id=application.user_id, message=message,
        notif_type='reservation_rejected',
    ))
    db.session.commit()

    flash(f"{application.applicant_name}님의 예약을 거절했습니다.", "success")
    return redirect(url_for('farmer_easy_mode', tab='reservations'))


def delete_application(app_id):
    if 'user_id' not in session: abort(403)
    application = Application.query.get_or_404(app_id)
    if application.user_id != session['user_id']: abort(403)

    experience = Experience.query.get(application.experience_id)
    if experience and application.status != '취소':
        experience.current_participants = max(0, experience.current_participants - application.participants_count)
        surplus_service.restore(experience, application.participants_count)

    application.status = '취소'

    notification_message = f"'{application.applicant_name}'님이 '{experience.crop}' 체험 신청을 취소했습니다."
    new_notification = Notification(user_id=experience.farmer_id, message=notification_message)
    db.session.add(new_notification)

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
    app.add_url_rule('/reservations/<int:app_id>/complete', 'reservation_complete', reservation_complete)
    app.add_url_rule('/application/confirm/<int:app_id>', 'confirm_application', confirm_application, methods=['POST'])
    app.add_url_rule('/application/reject/<int:app_id>', 'reject_application', reject_application, methods=['POST'])
    app.add_url_rule('/application/delete/<int:app_id>', 'delete_application', delete_application, methods=['POST'])