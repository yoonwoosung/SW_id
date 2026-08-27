# routes/farm.py — 농장주 대시보드(상세 모드) 라우트(대시보드·모드전환·만료체험)
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


def _get_reservations_by_date(experience_ids):
    """체험 ID 목록을 기반으로 날짜별 예약 목록을 그룹화하는 헬퍼 함수"""
    if not experience_ids:
        return defaultdict(list)

    applications = (
        Application.query.filter(
            Application.experience_id.in_(experience_ids),
            Application.status != '취소'
        )
        .options(joinedload(Application.experience))
        .all()
    )

    reservations_by_date = defaultdict(list)
    for app in applications:
        reservations_by_date[app.apply_date.strftime('%Y-%m-%d')].append({
            "id": app.id,
            "name": app.applicant_name,
            "phone": app.phone_number,
            "adult": app.count_adult,
            "teen": app.count_teen,
            "child": app.count_child,
            "time": app.apply_time,
            "crop": app.experience.crop if app.experience else "",
            "status": app.status
        })
    return reservations_by_date


def toggle_view_mode():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('index'))

    if session.get('view_mode') == 'easy':
        session['view_mode'] = 'detailed'
        return redirect(url_for('detailed_farmer_dashboard'))
    else:
        session['view_mode'] = 'easy'
        return redirect(url_for('farmer_easy_mode'))


@farmer_required
def detailed_farmer_dashboard():
    farmer_id = session.get('user_id')
    user = User.query.get(farmer_id)
    if not user:
        session.clear()
        flash("세션 정보가 유효하지 않습니다.", "warning")
        return redirect(url_for('login_page'))

    # 1. 알림 조회 (단일 쿼리 후 슬라이싱)
    all_notifications = (
        Notification.query.filter_by(user_id=farmer_id)
        .order_by(Notification.timestamp.desc())
        .all()
    )
    notifications = all_notifications[:3]
    notifications_json = [
        {"id": n.id, "message": n.message, "timestamp": n.timestamp.isoformat()}
        for n in all_notifications
    ]

    # 2. 내 체험 목록 조회 (리뷰 eager load 결합)
    my_listings = (
        Experience.query.filter(
            Experience.farmer_id == farmer_id,
            Experience.status.in_(['recruiting', 'hidden'])
        )
        .options(joinedload(Experience.reviews))
        .all()
    )
    experiences_json = [exp.to_dict() for exp in my_listings]
    experience_ids = [exp.id for exp in my_listings]

    # 3. 예약 현황 데이터
    reservations_by_date = _get_reservations_by_date(experience_ids)

    # 4. 평점 및 문의 내역
    avg_rating = 0
    latest_inquiries = []
    if experience_ids:
        avg_result = (
            db.session.query(func.avg(Review.rating))
            .filter(Review.experience_id.in_(experience_ids))
            .scalar()
        )
        if avg_result is not None:
            avg_rating = round(avg_result, 1)

        latest_inquiries = (
            Inquiry.query.filter(Inquiry.experience_id.in_(experience_ids))
            .order_by(Inquiry.timestamp.desc())
            .limit(5)
            .all()
        )

    # 5. 통계 정보
    total_visitors = sum(exp.current_participants for exp in my_listings)
    stats = {
        'total_experiences': len(my_listings),
        'average_rating': avg_rating if avg_rating > 0 else "N/A",
        'total_visitors': total_visitors
    }

    # 6. 리뷰 피드백 키워드 분석
    feedback_by_experience = {}
    for exp in my_listings:
        if not exp.reviews:
            continue
        strength_keywords = defaultdict(int)
        improvement_keywords = defaultdict(int)
        for review in exp.reviews:
            if review.analysis_result:
                try:
                    data = json.loads(review.analysis_result)
                    for keyword in data.get('strengths', []):
                        if keyword:
                            strength_keywords[keyword] += 1
                    for keyword in data.get('improvements', []):
                        if keyword:
                            improvement_keywords[keyword] += 1
                except (json.JSONDecodeError, TypeError):
                    continue

        if strength_keywords or improvement_keywords:
            feedback_by_experience[exp.id] = {
                'name': exp.crop,
                'strengths': sorted(strength_keywords.items(), key=lambda item: item[1], reverse=True),
                'improvements': sorted(improvement_keywords.items(), key=lambda item: item[1], reverse=True)
            }

    return render_template(
        'my_farm.html',
        user=user,
        experiences=my_listings,
        experiences_json=experiences_json,
        stats=stats,
        inquiries=latest_inquiries,
        reservations_data=reservations_by_date,
        notifications=notifications,
        notifications_json=notifications_json,
        feedback_report=feedback_by_experience
    )


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
    app.add_url_rule('/my_farm_detailed', 'detailed_farmer_dashboard', detailed_farmer_dashboard)
    app.add_url_rule('/my_farm/expired', 'expired_experiences', expired_experiences)
    app.add_url_rule('/my_farm/calendar', 'farmer_calendar', farmer_calendar)