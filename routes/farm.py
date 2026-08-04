# routes/farm.py — 농장주 대시보드(상세 모드) 라우트(대시보드·모드전환·만료체험).
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


def toggle_view_mode():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('index'))

    if session.get('view_mode') == 'easy':
        session['view_mode'] = 'detailed'
        return redirect(url_for('detailed_farmer_dashboard'))
    else:
        session['view_mode'] = 'easy'
        return redirect(url_for('farmer_easy_mode'))


def detailed_farmer_dashboard():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    
    farmer_id = session.get('user_id')
    user = User.query.get(farmer_id)
    if not user:
        session.clear()
        flash("세션 정보가 유효하지 않습니다.", "warning")
        return redirect(url_for('login_page'))

    notifications = Notification.query.filter_by(user_id=farmer_id).order_by(Notification.timestamp.desc()).limit(3).all()
    all_notifications = Notification.query.filter_by(user_id=farmer_id).order_by(Notification.timestamp.desc()).all()
    notifications_json = [{"id": n.id, "message": n.message, "timestamp": n.timestamp.isoformat()} for n in all_notifications]

    my_listings = Experience.query.filter(
        Experience.farmer_id == farmer_id,
        Experience.status.in_(['recruiting', 'hidden'])
    ).all()

    experiences_json = [exp.to_dict() for exp in my_listings]
    experience_ids = [exp.id for exp in my_listings]
    applications = Application.query.filter(Application.experience_id.in_(experience_ids), Application.status != '취소').all()
    
    reservations_by_date = defaultdict(list)
    for app in applications:
        reservations_by_date[app.apply_date.strftime('%Y-%m-%d')].append({
            "id": app.id, "name": app.applicant_name, "phone": app.phone_number,
            "adult": app.count_adult, "teen": app.count_teen, "child": app.count_child,
            "time": app.apply_time, "crop": app.experience.crop, "status": app.status
        })

    avg_rating = 0
    if experience_ids:
        avg_result = db.session.query(func.avg(Review.rating)).filter(Review.experience_id.in_(experience_ids)).scalar()
        if avg_result is not None:
            avg_rating = round(avg_result, 1)

    latest_inquiries = []
    if experience_ids:
        latest_inquiries = Inquiry.query.filter(Inquiry.experience_id.in_(experience_ids)).order_by(Inquiry.timestamp.desc()).limit(5).all()

    total_visitors = sum(exp.current_participants for exp in my_listings)
    stats = {
        'total_experiences': len(my_listings),
        'average_rating': avg_rating if avg_rating > 0 else "N/A",
        'total_visitors': total_visitors
    }

    feedback_by_experience = {}
    my_listings_with_reviews = Experience.query.filter(
        Experience.farmer_id == farmer_id
    ).options(db.joinedload(Experience.reviews)).all()

    for exp in my_listings_with_reviews:
        if not exp.reviews:
            continue
        strength_keywords = defaultdict(int)
        improvement_keywords = defaultdict(int)
        for review in exp.reviews:
            if review.analysis_result:
                try:
                    data = json.loads(review.analysis_result)
                    for keyword in data.get('strengths', []):
                        if keyword: strength_keywords[keyword] += 1
                    for keyword in data.get('improvements', []):
                        if keyword: improvement_keywords[keyword] += 1
                except (json.JSONDecodeError, TypeError):
                    continue
        if strength_keywords or improvement_keywords:
            feedback_by_experience[exp.id] = {
                'name': exp.crop,
                'strengths': sorted(strength_keywords.items(), key=lambda item: item[1], reverse=True),
                'improvements': sorted(improvement_keywords.items(), key=lambda item: item[1], reverse=True)
            }

    return render_template('my_farm.html',
                           user=user, experiences=my_listings, experiences_json=experiences_json,
                           stats=stats,
                           inquiries=latest_inquiries,
                           reservations_data=reservations_by_date, notifications=notifications, notifications_json=notifications_json,
                           feedback_report=feedback_by_experience)


def expired_experiences():
    if session.get('role') != 'farmer':
        flash("농장주만 접근 가능합니다.", "warning")
        return redirect(url_for('index'))

    farmer_id = session.get('user_id')
    user = User.query.get(farmer_id)
    expired_list = Experience.query.filter_by(farmer_id=farmer_id, status='expired').order_by(Experience.end_date.desc()).all()

    return render_template('expired_experiences.html', user=user, experiences=expired_list)

def farmer_calendar():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))

    farmer_id = session.get('user_id')
    user = User.query.get(farmer_id)
    if not user:
        session.clear()
        return redirect(url_for('login_page'))

    my_listings = Experience.query.filter(
        Experience.farmer_id == farmer_id,
        Experience.status.in_(['recruiting', 'hidden'])
    ).all()
    experience_ids = [exp.id for exp in my_listings]
    
    applications = Application.query.filter(
        Application.experience_id.in_(experience_ids),
        Application.status != '취소'
    ).all()

    reservations_by_date = defaultdict(list)
    for app in applications:
        reservations_by_date[app.apply_date.strftime('%Y-%m-%d')].append({
            "id": app.id, "name": app.applicant_name, "phone": app.phone_number,
            "adult": app.count_adult, "teen": app.count_teen, "child": app.count_child,
            "time": app.apply_time, "crop": app.experience.crop, "status": app.status
        })

    return render_template('farmer_calendar.html', user=user, reservations_data=reservations_by_date)

def register(app):
    app.add_url_rule('/toggle_view_mode', 'toggle_view_mode', toggle_view_mode)
    app.add_url_rule('/my_farm_detailed', 'detailed_farmer_dashboard', detailed_farmer_dashboard)
    app.add_url_rule('/my_farm/expired', 'expired_experiences', expired_experiences)
    app.add_url_rule('/my_farm/calendar', 'farmer_calendar', farmer_calendar)
