# routes/farm.py — 농장주 라우트(모드전환·만료체험·캘린더)
import json
from collections import defaultdict
from functools import wraps

from flask import (render_template, redirect, url_for, flash, session)
from sqlalchemy.sql import func
from sqlalchemy.orm import joinedload

from models import db, User, Experience, Review, Inquiry, Application, Notification


def farmer_required(f):
    """농장주 권한 검증 데코레이터"""
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'farmer':
            flash("농장주만 접근 가능합니다.", "warning")
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function


def toggle_view_mode():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('index'))

    session['view_mode'] = 'easy'
    return redirect(url_for('farmer_easy_mode'))


@farmer_required
def expired_experiences():
    farmer_id = session.get('user_id')
    user = User.query.get(farmer_id)
    expired_list = (
        Experience.query.filter_by(farmer_id=farmer_id, status='expired')
        .order_by(Experience.end_date.desc())
        .all()
    )
    return render_template('expired_experiences.html', user=user, experiences=expired_list)


@farmer_required
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
    
    experiences_data = [
        {
            "id": exp.id,
            "title": f"{exp.crop} 체험",
            "crop": exp.crop,
            "start_date": exp.duration_start.strftime('%Y-%m-%d') if exp.duration_start else None,
            "end_date": exp.end_date.strftime('%Y-%m-%d') if exp.end_date else None,
            "price": exp.cost,
            "description": exp.notes or "체험 안내 사항이 없습니다."
        }
        for exp in my_listings if exp.duration_start and exp.end_date
    ]

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

    return render_template(
        'farmer_calendar.html',
        user=user,
        reservations_data=reservations_by_date,
        experiences_data=experiences_data
    )


def register(app):
    app.add_url_rule('/toggle_view_mode', 'toggle_view_mode', toggle_view_mode)
    app.add_url_rule('/my_farm/expired', 'expired_experiences', expired_experiences)
    app.add_url_rule('/my_farm/calendar', 'farmer_calendar', farmer_calendar)