# routes/farmer.py — 농장주 간편모드(easy_mode) 라우트 모음 (농장별 통합 AI 리포트 적용)
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

from models import db, User, Experience, Review, Inquiry, Application, Notification, Farm
from services.distance import haversine
from services.recommend_data import REGIONAL_SPECIALTIES
from services.recommend_service import matches_specialty, score_components, calculate_score
from services.recommend_reason import recommendation_reason
from services.review_service import analyze_review_with_clova
from external.kakao_map import get_coords_from_address
from common.validators import allowed_file
from services import farm_service


def farmer_easy_mode():
    if 'user_id' not in session or session.get('role') not in ['farmer', 'admin']:
        return redirect(url_for('login_page'))
    session['view_mode'] = 'easy'
    user = User.query.get_or_404(session['user_id'])
    show_pending_modal = session.pop('just_logged_in', False)
    
    listings = Experience.query.filter_by(farmer_id=user.id).order_by(Experience.end_date.desc()).all()
    experience_ids = [e.id for e in listings]
    today = date.today()
    
    today_reservations = Application.query.filter(
        Application.experience_id.in_(experience_ids),
        Application.apply_date == today,
        Application.status != '취소'
    ).count() if experience_ids else 0
    
    pending_inquiries = Inquiry.query.filter(
        Inquiry.experience_id.in_(experience_ids)
    ).count() if experience_ids else 0
    
    applications = Application.query.filter(
        Application.experience_id.in_(experience_ids),
        Application.status != '취소'
    ).all() if experience_ids else []
    
    reservations_by_date = defaultdict(list)
    for app in applications:
        reservations_by_date[app.apply_date.strftime('%Y-%m-%d')].append({
            "id": app.id, "name": app.applicant_name, "phone": app.phone_number,
            "adult": app.count_adult, "teen": app.count_teen, "child": app.count_child,
            "time": app.apply_time, "crop": app.experience.crop, "status": app.status
        })
        
    recent_inquiries = Inquiry.query.filter(
        Inquiry.experience_id.in_(experience_ids)
    ).order_by(Inquiry.timestamp.desc()).limit(5).all() if experience_ids else []
    
    pending_applications = Application.query.filter(
        Application.experience_id.in_(experience_ids),
        Application.status == '예정'
    ).order_by(Application.apply_date.asc(), Application.apply_time.asc()).all() if experience_ids else []

    # 농장 통계 기본값
    avg_rating = 0
    if experience_ids:
        avg_result = db.session.query(func.avg(Review.rating)).filter(Review.experience_id.in_(experience_ids)).scalar()
        if avg_result is not None:
            avg_rating = round(avg_result, 1)
    total_visitors = sum(exp.current_participants for exp in listings)
    stats = {
        'total_experiences': len(listings),
        'average_rating': avg_rating if avg_rating > 0 else 'N/A',
        'total_visitors': total_visitors
    }

    # ── AI 후기 요약 (농장별 통합 집계 + 작물 태그 바인딩) ─────────
    def _build_summary(kw_crop_list, is_strength):
        if not kw_crop_list:
            return None
        top = kw_crop_list[:3]
        items = []
        for kw, crop in top:
            tag = f"[{crop}] " if crop else ""
            items.append(f"{tag}{kw}")

        if len(items) == 1:
            joined = items[0]
        elif len(items) == 2:
            joined = f"{items[0]}와(과) {items[1]}"
        else:
            joined = f"{items[0]}, {items[1]}와(과) {items[2]}"

        if is_strength:
            return f"방문객들이 {joined}을(를) 특히 높이 평가했어요."
        return f"{joined}을(를) 개선하면 더 좋은 평가를 받을 수 있어요."

    feedback_report = {}
    farms = Farm.query.filter_by(user_id=user.id).order_by(Farm.created_at.asc()).all()

    for idx, farm in enumerate(farms):
        if idx == 0:
            farm_filter = or_(Experience.farm_id == farm.id, Experience.farm_id.is_(None))
        else:
            farm_filter = (Experience.farm_id == farm.id)

        farm_experiences = Experience.query.filter(
            Experience.farmer_id == user.id,
            farm_filter
        ).options(db.joinedload(Experience.reviews)).all()

        all_farm_reviews = []
        crops = set()
        for exp in farm_experiences:
            crops.add(exp.crop)
            for r in exp.reviews:
                all_farm_reviews.append((r, exp.crop))

        if not all_farm_reviews:
            continue

        strength_kw_total = defaultdict(int)
        strength_kw_crop_map = defaultdict(lambda: defaultdict(int))
        improvement_kw_total = defaultdict(int)
        improvement_kw_crop_map = defaultdict(lambda: defaultdict(int))

        pos_count = 0
        total_rating = 0

        for review, crop in all_farm_reviews:
            total_rating += review.rating
            if review.rating >= 4:
                pos_count += 1
            if review.analysis_result:
                try:
                    data = json.loads(review.analysis_result)
                    for kw in data.get('strengths', []):
                        if kw:
                            strength_kw_total[kw] += 1
                            strength_kw_crop_map[kw][crop] += 1
                    for kw in data.get('improvements', []):
                        if kw:
                            improvement_kw_total[kw] += 1
                            improvement_kw_crop_map[kw][crop] += 1
                except (json.JSONDecodeError, TypeError):
                    continue

        def _get_top_kw_with_crop(kw_total_dict, kw_crop_map):
            sorted_kws = sorted(kw_total_dict.items(), key=lambda x: x[1], reverse=True)
            result = []
            for kw, _ in sorted_kws:
                top_crop = max(kw_crop_map[kw].items(), key=lambda x: x[1])[0] if kw_crop_map[kw] else None
                result.append((kw, top_crop))
            return result

        s_list = _get_top_kw_with_crop(strength_kw_total, strength_kw_crop_map)
        i_list = _get_top_kw_with_crop(improvement_kw_total, improvement_kw_crop_map)

        satisfaction_rate = round(pos_count / len(all_farm_reviews) * 100) if all_farm_reviews else None
        avg_farm_rating = round(total_rating / len(all_farm_reviews), 1) if all_farm_reviews else 0
        farm_display_name = farm.name if farm.name else f"농장 ({farm.address.split(' ')[0]} {farm.address.split(' ')[1] if len(farm.address.split(' ')) > 1 else ''})"

        feedback_report[farm.id] = {
            'farm_name': farm_display_name,
            'farm_address': farm.address,
            'crops': list(crops),
            'total_reviews': len(all_farm_reviews),
            'avg_rating': avg_farm_rating,
            'strengths_summary': _build_summary(s_list, True),
            'improvements_summary': _build_summary(i_list, False),
            'satisfaction_rate': satisfaction_rate
        }

    return render_template('farmer_easy_mode.html', user=user, listings=listings,
                           today_reservations=today_reservations,
                           pending_inquiries=pending_inquiries,
                           today=today,
                           reservations_data=reservations_by_date,
                           stats=stats,
                           feedback_report=feedback_report,
                           recent_inquiries=recent_inquiries,
                           pending_applications=pending_applications,
                           farms=farms,
                           show_pending_modal=show_pending_modal)


def easy_edit_bio():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    
    user = User.query.get(session['user_id'])
    if request.method == 'POST':
        user.profile_bio = request.form.get('profile_bio')
        db.session.commit()
        flash('소개 글이 성공적으로 저장되었습니다.', 'success')
        return redirect(url_for('farmer_easy_mode', tab='account'))
        
    return render_template('easy_edit_bio.html', user=user)


def easy_create_experience():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))

    farmer_id = session['user_id']
    approved_farms = Farm.query.filter_by(user_id=farmer_id, status='APPROVED').order_by(Farm.created_at.asc()).all()

    if request.method == 'POST':
        if 'terms' not in request.form:
            flash("서비스 이용 약관에 동의해야 합니다.", "warning")
            return render_template('easy_create_experience.html', item=None, approved_farms=approved_farms, form_data=request.form)
        
        farm_id = request.form.get('farm_id')
        selected_farm = Farm.query.filter_by(id=farm_id, user_id=farmer_id, status='APPROVED').first()
        if not selected_farm:
            flash("체험을 진행할 승인된 농장을 선택해 주세요.", "warning")
            return render_template('easy_create_experience.html', item=None, approved_farms=approved_farms, form_data=request.form)

        required_fields = {
            'crop': '체험 이름', 'phone': '농장 연락처',
            'price': '가격', 'max_participants': '하루 최대 인원',
            'duration_start': '체험 시작 날짜', 'duration_end': '체험 끝나는 날짜',
            'timetable_data': '체험 가능 시간', 'notes': '상세 설명',
            'includes': '포함 내역', 'excludes': '불포함 내역'
        }
        for field, name in required_fields.items():
            if not request.form.get(field):
                flash(f"'{name}' 항목을 입력해주세요. 모든 항목은 필수입니다.", "warning")
                return render_template('easy_create_experience.html', item=None, approved_farms=approved_farms, form_data=request.form)
            
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
                return render_template('easy_create_experience.html', item=None, approved_farms=approved_farms, form_data=request.form)

        full_address = f"{selected_farm.address} {selected_farm.address_detail or ''}".strip()

        new_experience = Experience(
            farm_id=selected_farm.id,
            crop=request.form.get('crop'),
            cost=int(request.form.get('price')),
            max_participants=int(request.form.get('max_participants')),
            duration_start=datetime.strptime(request.form.get('duration_start'), '%Y-%m-%d').date(),
            end_date=datetime.strptime(request.form.get('duration_end'), '%Y-%m-%d').date(),
            farmer_id=session['user_id'],
            location=selected_farm.address,
            address_detail=full_address,
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
            lat=selected_farm.lat,
            lng=selected_farm.lng,
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
        return redirect(url_for('farmer_easy_mode', tab='operations'))
        
    return render_template('easy_create_experience.html', item=None, approved_farms=approved_farms, form_data={})


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
    
    farmer_id = session['user_id']
    item = Experience.query.get_or_404(item_id)
    if item.farmer_id != farmer_id:
        abort(403)

    approved_farms = Farm.query.filter_by(user_id=farmer_id, status='APPROVED').order_by(Farm.created_at.asc()).all()

    if request.method == 'POST':
        if 'terms' not in request.form:
            flash("서비스 이용 약관에 동의해야 합니다.", "warning")
            return render_template('easy_create_experience.html', item=item, approved_farms=approved_farms, form_data=request.form)
        
        farm_id = request.form.get('farm_id')
        selected_farm = Farm.query.filter_by(id=farm_id, user_id=farmer_id, status='APPROVED').first()
        if not selected_farm:
            flash("체험을 진행할 승인된 농장을 선택해 주세요.", "warning")
            return render_template('easy_create_experience.html', item=item, approved_farms=approved_farms, form_data=request.form)

        required_fields = {
            'crop': '체험 이름', 'phone': '농장 연락처',
            'price': '가격', 'max_participants': '하루 최대 인원',
            'duration_start': '체험 시작 날짜', 'duration_end': '체험 끝나는 날짜',
            'timetable_data': '체험 가능 시간', 'notes': '상세 설명',
            'includes': '포함 내역', 'excludes': '불포함 내역'
        }

        for field, name in required_fields.items():
            if not request.form.get(field):
                flash(f"'{name}' 항목을 입력해주세요. 모든 항목은 필수입니다.", "warning")
                return render_template('easy_create_experience.html', item=item, approved_farms=approved_farms, form_data=request.form)
        
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
                return render_template('easy_create_experience.html', item=item, approved_farms=approved_farms, form_data=request.form)
        else:
            item.pesticide_free = False
            item.organic_certification_type = None
            item.organic_certification_image = None

        full_address = f"{selected_farm.address} {selected_farm.address_detail or ''}".strip()
        item.farm_id = selected_farm.id
        item.location = selected_farm.address
        item.address_detail = full_address
        item.lat = selected_farm.lat
        item.lng = selected_farm.lng

        item.crop = request.form.get('crop')
        item.cost = int(request.form.get('price'))
        item.max_participants = int(request.form.get('max_participants'))
        item.duration_start = datetime.strptime(request.form.get('duration_start'), '%Y-%m-%d').date()
        item.end_date = datetime.strptime(request.form.get('duration_end'), '%Y-%m-%d').date()
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

    return render_template('easy_create_experience.html', item=item, approved_farms=approved_farms, form_data={})


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


def close_experience(item_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    item = Experience.query.get_or_404(item_id)
    if item.farmer_id != session.get('user_id'):
        abort(403)
    item.status = 'hidden'
    db.session.commit()
    flash(f"'{item.crop}' 체험이 숨김 처리되었습니다.", 'success')
    return redirect(url_for('farmer_easy_mode', tab='operations'))


def register(app):
    app.add_url_rule('/easy_mode', 'farmer_easy_mode', farmer_easy_mode)
    app.add_url_rule('/easy_mode/edit_bio', 'easy_edit_bio', easy_edit_bio, methods=['GET', 'POST'])
    app.add_url_rule('/easy_mode/create_experience', 'easy_create_experience', easy_create_experience, methods=['GET', 'POST'])
    app.add_url_rule('/easy_mode/modify_experience_list', 'easy_modify_experience_list', easy_modify_experience_list)
    app.add_url_rule('/easy_mode/modify_experience/<int:item_id>', 'easy_modify_experience', easy_modify_experience, methods=['GET', 'POST'])
    app.add_url_rule('/easy_mode/reservations', 'easy_reservations', easy_reservations)
    app.add_url_rule('/easy_mode/communication', 'easy_communication', easy_communication)
    app.add_url_rule('/easy_mode/close_experience/<int:item_id>', 'close_experience', close_experience, methods=['POST'])