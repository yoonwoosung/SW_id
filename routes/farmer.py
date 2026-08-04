# routes/farmer.py — 농장주 간편모드(easy_mode) 라우트 모음.
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
from services import farm_service


def farmer_easy_mode():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    session['view_mode'] = 'easy'
    user = User.query.get_or_404(session['user_id'])
    listings = Experience.query.filter_by(farmer_id=user.id).order_by(Experience.end_date.desc()).all()
    return render_template('farmer_easy_mode.html', user=user, listings=listings)


def easy_edit_bio():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.profile_bio = request.form.get('profile_bio')
        db.session.commit()
        flash('소개 글이 성공적으로 저장되었습니다.', 'success')
        return redirect(url_for('farmer_easy_mode'))
        
    return render_template('easy_edit_bio.html', user=user)


def easy_create_experience():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))

    if request.method == 'POST':

        if 'terms' not in request.form:
            flash("서비스 이용 약관에 동의해야 합니다.", "warning")
            return render_template('easy_create_experience.html', item=None, form_data=request.form)
        
        required_fields = {
            'crop': '체험 이름', 'address': '상세 주소', 'phone': '농장 연락처',
            'price': '가격', 'max_participants': '하루 최대 인원',
            'duration_start': '체험 시작 날짜', 'duration_end': '체험 끝나는 날짜',
            'timetable_data': '체험 가능 시간', 'notes': '상세 설명',
            'includes': '포함 내역', 'excludes': '불포함 내역'
        }
        for field, name in required_fields.items():
            if not request.form.get(field):
                flash(f"'{name}' 항목을 입력해주세요. 모든 항목은 필수입니다.", "warning")
                return render_template('easy_create_experience.html', item=None, form_data=request.form)
            
        is_organic = 'is_organic' in request.form
        cert_filename = None
        cert_type = None

        if is_organic:
            cert_type = request.form.get('organic_certification_type')
            cert_file = request.files.get('organic_certification_image')
            if cert_file and cert_file.filename and allowed_file(cert_file.filename):
                ext = cert_file.filename.rsplit('.', 1)[1].lower()
                cert_filename = f"cert_{session['user_id']}_{uuid.uuid4().hex}.{ext}"
                cert_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], cert_filename))
            else:
                flash("친환경 농법 사용 시 인증서 이미지를 반드시 등록해야 합니다.", "warning")
                return render_template('easy_create_experience.html', item=None, form_data=request.form)

        address_detail = request.form.get('address')
        lat, lng = get_coords_from_address(address_detail)
        farmer = User.query.get(session['user_id'])
        default_farm = farm_service.default_farm_for(session['user_id'])  # B안: 기본 농장에 연결

        new_experience = Experience(
            farm_id=default_farm.id if default_farm else None,
            crop=request.form.get('crop'),
            cost=int(request.form.get('price')),
            max_participants=int(request.form.get('max_participants')),
            duration_start=datetime.strptime(request.form.get('duration_start'), '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.form.get('duration_end'), '%Y-%m-%d').date(),
            farmer_id=session['user_id'],
            location=farmer.farm_address,
            address_detail=address_detail,
            phone=request.form.get('phone'),
            notes=request.form.get('notes'),
            includes=request.form.get('includes'),
            excludes=request.form.get('excludes'),
            timetable_data=request.form.get('timetable_data'),
            has_parking='has_parking' in request.form,
            volunteer_needed=int(request.form.get('volunteer_needed', 0)),
            volunteer_duties=request.form.get('volunteer_duties'),
            pesticide_free=is_organic,
            organic_certification_type=cert_type,
            organic_certification_image=cert_filename,
            lat=lat,
            lng=lng,
            status='recruiting'
        )
        
        uploaded_files = request.files.getlist('images')
        filenames = []
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"exp_{session['user_id']}_{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                img = Image.open(file.stream)
                img.thumbnail((800, 600))
                img.save(filepath)
                filenames.append(filename)
        new_experience.images = ",".join(filenames)
        
        db.session.add(new_experience)
        db.session.commit()
        flash(f"'{new_experience.crop}' 체험이 성공적으로 만들어졌습니다.", 'success')
        return redirect(url_for('farmer_easy_mode'))
        
    return render_template('easy_create_experience.html', item=None, form_data={})


def easy_modify_experience_list():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    farmer_id = session.get('user_id')
    my_listings = Experience.query.filter(
        Experience.farmer_id == farmer_id,
        Experience.status.in_(['recruiting', 'hidden'])
    ).order_by(Experience.end_date.desc()).all()
    return render_template('easy_modify_list.html', experiences=my_listings)


def easy_modify_experience(item_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    
    item = Experience.query.get_or_404(item_id)
    if item.farmer_id != session.get('user_id'):
        abort(403)

    if request.method == 'POST':
        if 'terms' not in request.form:
            flash("서비스 이용 약관에 동의해야 합니다.", "warning")
            return render_template('easy_create_experience.html', item=item, form_data=request.form)
        
        required_fields = {
            'crop': '체험 이름', 'address': '상세 주소', 'phone': '농장 연락처',
            'price': '가격', 'max_participants': '하루 최대 인원',
            'duration_start': '체험 시작 날짜', 'duration_end': '체험 끝나는 날짜',
            'timetable_data': '체험 가능 시간', 'notes': '상세 설명',
            'includes': '포함 내역', 'excludes': '불포함 내역'
        }

        for field, name in required_fields.items():
            if not request.form.get(field):
                flash(f"'{name}' 항목을 입력해주세요. 모든 항목은 필수입니다.", "warning")
                return render_template('easy_create_experience.html', item=item, form_data=request.form)
        
        is_organic = 'is_organic' in request.form
        if is_organic:
            item.pesticide_free = True
            item.organic_certification_type = request.form.get('organic_certification_type')
            cert_file = request.files.get('organic_certification_image')

            if cert_file and cert_file.filename and allowed_file(cert_file.filename):
                ext = cert_file.filename.rsplit('.', 1)[1].lower()
                new_cert_filename = f"cert_{session['user_id']}_{uuid.uuid4().hex}.{ext}"
                cert_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], new_cert_filename))
                item.organic_certification_image = new_cert_filename
            elif not item.organic_certification_image:
                flash("친환경 농법 사용 시 인증서 이미지를 등록해야 합니다.", "warning")
                return render_template('easy_create_experience.html', item=item, form_data=request.form)
        else:
            item.pesticide_free = False
            item.organic_certification_type = None
            item.organic_certification_image = None

        item.crop = request.form.get('crop')
        item.cost = int(request.form.get('price'))
        item.max_participants = int(request.form.get('max_participants'))
        item.duration_start = datetime.strptime(request.form.get('duration_start'), '%Y-%m-%d').date()
        item.end_date = datetime.strptime(request.form.get('duration_end'), '%Y-%m-%d').date()
        item.address_detail = request.form.get('address')
        lat, lng = get_coords_from_address(item.address_detail)
        item.lat = lat
        item.lng = lng
        item.phone = request.form.get('phone')
        item.notes = request.form.get('notes')
        item.includes = request.form.get('includes')
        item.excludes = request.form.get('excludes')
        item.timetable_data = request.form.get('timetable_data')
        item.has_parking = 'has_parking' in request.form
        item.volunteer_needed = int(request.form.get('volunteer_needed', 0))
        item.volunteer_duties = request.form.get('volunteer_duties')

        uploaded_files = request.files.getlist('images')
        if uploaded_files and uploaded_files[0].filename:
            filenames = []
            for file in uploaded_files:
                if file and allowed_file(file.filename):
                    ext = file.filename.rsplit('.', 1)[1].lower()
                    filename = f"exp_{session['user_id']}_{uuid.uuid4().hex}.{ext}"
                    filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                    img = Image.open(file.stream)
                    img.thumbnail((800, 600))
                    img.save(filepath)
                    filenames.append(filename)
            item.images = ",".join(filenames)

        db.session.commit()
        flash(f"'{item.crop}' 체험이 성공적으로 수정되었습니다.", "success")
        return redirect(url_for('easy_modify_experience_list'))

    return render_template('easy_create_experience.html', item=item, form_data={})


def easy_reservations():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    
    farmer_id = session.get('user_id')
    experience_ids = [exp.id for exp in Experience.query.filter_by(farmer_id=farmer_id).all()]
    
    applications = Application.query.filter(
        Application.experience_id.in_(experience_ids),
        Application.status != '취소'
    ).order_by(Application.apply_date.desc(), Application.apply_time.asc()).all()
    
    reservations_by_date = defaultdict(list)
    for app in applications:
        reservations_by_date[app.apply_date.strftime('%Y년 %m월 %d일')].append(app)

    return render_template('easy_reservations.html', reservations_by_date=reservations_by_date)


def easy_communication():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
        
    farmer_id = session.get('user_id')
    experience_ids = [exp.id for exp in Experience.query.filter_by(farmer_id=farmer_id).all()]
    latest_inquiries = Inquiry.query.filter(Inquiry.experience_id.in_(experience_ids)).order_by(Inquiry.timestamp.desc()).limit(5).all()
    feedback_report = {}
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
            feedback_report[exp.id] = {
                'name': exp.crop,
                'strengths': sorted(strength_keywords.items(), key=lambda item: item[1], reverse=True),
                'improvements': sorted(improvement_keywords.items(), key=lambda item: item[1], reverse=True)
            }

    return render_template('easy_communication.html', inquiries=latest_inquiries, feedback_report=feedback_report)


def register(app):
    app.add_url_rule('/easy_mode', 'farmer_easy_mode', farmer_easy_mode)
    app.add_url_rule('/easy_mode/edit_bio', 'easy_edit_bio', easy_edit_bio, methods=['GET', 'POST'])
    app.add_url_rule('/easy_mode/create_experience', 'easy_create_experience', easy_create_experience, methods=['GET', 'POST'])
    app.add_url_rule('/easy_mode/modify_experience_list', 'easy_modify_experience_list', easy_modify_experience_list)
    app.add_url_rule('/easy_mode/modify_experience/<int:item_id>', 'easy_modify_experience', easy_modify_experience, methods=['GET', 'POST'])
    app.add_url_rule('/easy_mode/reservations', 'easy_reservations', easy_reservations)
    app.add_url_rule('/easy_mode/communication', 'easy_communication', easy_communication)
