# routes/experience.py — 체험 도메인 라우트(목록·상세·등록/수정·삭제·공개전환·JSON API).
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
from services.recommend_service import matches_specialty, score_components, calculate_score, category_bonus
from services.recommend_reason import recommendation_reason
from services.review_service import analyze_review_with_clova
from services.trend_service import record_click
from services import policy_service
from common.search_categories import SEARCH_CATEGORIES, CATEGORY_CODES, CATEGORY_GROUPS
from common.response import success_response
from external.kakao_map import get_coords_from_address
from common.validators import allowed_file
from services import farm_service


def index():
    is_farmer = 'user_id' in session and session.get('role') == 'farmer'

    if is_farmer:
        session['view_mode'] = 'easy' 
        return redirect(url_for('detailed_farmer_dashboard')) #farmer_easy_mode에서 detailed_farmer_dashboard로 수정
    else: 
        page = request.args.get('page', 1, type=int)
        sort_by = request.args.get('sort', 'recommended', type=str)
        region = request.args.get('region', type=str)
        crop_query = request.args.get('crop_query', type=str)
        # 카테고리 조건은 cond_<카테고리> 파라미터로 받는다(기존 region 필터와 충돌 방지). 없으면 가점 0.
        selected_conditions = {code: request.args.getlist('cond_' + code) for code in CATEGORY_CODES}

        today = date.today()
        base_query = Experience.query.filter(Experience.status == 'recruiting', Experience.end_date >= today)

        if region:
            base_query = base_query.filter(Experience.address_detail.like(f"%{region}%"))
        if crop_query:
            base_query = base_query.filter(Experience.crop.like(f"%{crop_query}%"))

        items_on_page = []
        pagination = None

        is_closed = case(
            (Experience.current_participants >= Experience.max_participants, 1),
            else_=0
        ).label("is_closed")

        if sort_by == 'recommended':
            user_lat = request.args.get('lat', type=float)
            user_lon = request.args.get('lon', type=float)

            if user_lat and user_lon:
                # Bounding box filter to reduce items before expensive calculation
                lat_range = 1.5
                lon_range = 1.5
                base_query = base_query.filter(
                    Experience.lat.between(user_lat - lat_range, user_lat + lat_range),
                    Experience.lng.between(user_lon - lon_range, user_lon + lon_range)
                )

                query = base_query.filter(Experience.current_participants < Experience.max_participants)
                all_experiences = query.all()

                # --- ▼ 여기가 생략되었던 추천순 정렬 로직입니다. ▼ ---
            
                ranked_experiences = []
                for exp in all_experiences:
                    distance = haversine(user_lat, user_lon, exp.lat, exp.lng)
                    if distance > 150: continue

                    is_specialty = matches_specialty(exp.address_detail, exp.crop)
                    recommendation_score = calculate_score(distance, exp.max_participants, exp.current_participants, is_specialty)
                    recommendation_score += category_bonus(selected_conditions, exp)

                    exp.recommendation_score = recommendation_score
                    exp.distance = distance
                    exp.recommendation_reason = recommendation_reason(
                        distance, exp.max_participants, exp.current_participants, is_specialty)
                    ranked_experiences.append(exp)

                sorted_items = sorted(ranked_experiences, key=lambda x: x.recommendation_score, reverse=True)

                start = (page - 1) * 15
                end = start + 15
                items_on_page = sorted_items[start:end]
                total_items = len(sorted_items)
            
                total_pages = math.ceil(total_items / 15) if total_items > 0 else 1
                pagination = SimpleNamespace(
                    items=items_on_page, page=page, per_page=15, total=total_items,
                    pages=total_pages, has_prev=(page > 1), has_next=(page < total_pages),
                    prev_num=page - 1, next_num=page + 1,
                    iter_pages=lambda **kwargs: range(1, total_pages + 1)
                )
                # --- ▲ 여기까지가 추천순 정렬 로직입니다. ▲ ---
            else:
                # 위치 정보가 없으면(첫 방문·위치 거부) 빈 화면 대신 마감임박순으로 폴백한다.
                query = base_query.order_by(is_closed.asc(), Experience.end_date.asc())
                pagination = query.paginate(page=page, per_page=15, error_out=False)
                items_on_page = pagination.items

        elif sort_by == 'reviews':
            review_count = func.count(Review.id).label('review_count')
            query = base_query.outerjoin(Review).group_by(Experience.id).order_by(is_closed.asc(), review_count.desc())
            pagination = query.paginate(page=page, per_page=15, error_out=False)
            items_on_page = pagination.items

        else: # 'deadline' (모집 임박순) 및 기타
            query = base_query.order_by(is_closed.asc(), Experience.end_date.asc())
            pagination = query.paginate(page=page, per_page=15, error_out=False)
            items_on_page = pagination.items

        if items_on_page:
            for item in items_on_page:
                item.is_specialty = False
                for r, specialties in REGIONAL_SPECIALTIES.items():
                    if r in item.address_detail and any(sc in item.crop for sc in specialties):
                        item.is_specialty = True
                        break

        # "이번 주 제철 체험" 레일용: 위치 정보 없이도 항상 채워지는 마감 임박 추천 목록
        featured = Experience.query.filter(
            Experience.status == 'recruiting', Experience.end_date >= today
        ).order_by(Experience.end_date.asc()).limit(8).all()

        return render_template('index.html',
                               items=items_on_page,
                               pagination=pagination,
                               featured=featured,
                               sort_by=sort_by)


def experience_detail(item_id):
    item = Experience.query.get_or_404(item_id)
    if item.status != 'recruiting' and session.get('user_id') != item.farmer_id:
        flash("현재 모집 중인 체험이 아닙니다.", "warning")
        return redirect(url_for('index'))

    # 클릭 로그 적재(개인화 추천 신호). 실패해도 상세 페이지는 정상 표시.
    try:
        record_click(session.get('user_id'), 'experience', item_id)
    except Exception:
        db.session.rollback()

    review_status = 'not_logged_in'
    if 'user_id' in session:
        user_id = session['user_id']
        existing_review = Review.query.filter_by(user_id=user_id, experience_id=item_id).first()
        if existing_review:
            review_status = 'already_reviewed'
        else:
            application = Application.query.filter(
                Application.user_id == user_id,
                Application.experience_id == item_id
            ).order_by(Application.id.desc()).first()

            if application:
                if application.status == '확정':
                    review_status = 'allowed'
                elif application.status == '예정':
                    review_status = 'pending_confirmation'
                else: # 취소 또는 다른 상태
                    review_status = 'not_applicable'
            else:
                review_status = 'not_applied'

    reviews = Review.query.filter_by(experience_id=item_id).order_by(Review.timestamp.desc()).all()
    inquiries = Inquiry.query.filter_by(experience_id=item_id).order_by(Inquiry.timestamp.desc()).all()
    item_data_for_js = {'lat': item.lat, 'lng': item.lng}
    booking_policies = policy_service.booking_policies()
    return render_template('detail_experience.html', item=item, item_data_for_js=item_data_for_js,
                           reviews=reviews, inquiries=inquiries, review_status=review_status,
                           booking_policies=booking_policies)


def farmer_register(item_id=None):
    if 'user_id' not in session or session['role'] != 'farmer':
        flash("농장주로 로그인해야만 접근할 수 있습니다.", "warning")
        return redirect(url_for('login_page'))
    item = Experience.query.get(item_id) if item_id else None
    if item and item.farmer_id != session['user_id']: abort(403)

    if request.method == 'POST':
        is_organic = 'is_organic' in request.form
        has_parking = 'has_parking' in request.form
        cert_filename = item.organic_certification_image if item and item.organic_certification_image else None
        cert_file = request.files.get('organic_certification_image')

        if cert_file and cert_file.filename != '':
            if allowed_file(cert_file.filename):
                ext = cert_file.filename.rsplit('.', 1)[1].lower()
                cert_filename = f"cert_{session['user_id']}_{uuid.uuid4().hex}.{ext}"
                cert_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], cert_filename))
        elif not is_organic:
            cert_filename = None

        if is_organic and not cert_filename:
            flash("친환경 인증을 선택한 경우, 인증 이미지를 반드시 업로드해야 합니다.", "danger")
            return render_template('farmer_register.html', item=item, form_data=request.form)

        end_date_str = request.form.get('duration_end')
        if datetime.strptime(end_date_str, '%Y-%m-%d').date() < date.today():
            flash("모집 마감일은 현재 날짜보다 이전일 수 없습니다.", "danger")
            return render_template('farmer_register.html', item=item, form_data=request.form)

        uploaded_files = request.files.getlist('images')
        filenames = item.images.split(',') if item and item.images else []
        if any(f.filename for f in uploaded_files):
            filenames = []
        for file in uploaded_files:
            if file and allowed_file(file.filename):
                ext = file.filename.rsplit('.', 1)[1].lower()
                filename = f"exp_{session['user_id']}_{uuid.uuid4().hex}.{ext}"
                filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
                img = Image.open(file.stream)
                img.thumbnail((800, 600))
                img.save(filepath)
                if filename not in filenames: filenames.append(filename)
        image_string = ",".join(filter(None, filenames))

        address_detail = request.form.get('address')
        lat, lng = get_coords_from_address(address_detail)

        volunteer_needed_str = request.form.get('volunteer_needed')
        volunteer_needed = int(volunteer_needed_str) if volunteer_needed_str else 0

        if item: # 수정
            item.crop = request.form.get('crop')
            item.phone = request.form.get('phone')
            item.address_detail = address_detail
            item.farm_size = request.form.get('farm_size')
            item.duration_start = datetime.strptime(request.form.get('duration_start'), '%Y-%m-%d').date()
            item.end_date = datetime.strptime(request.form.get('duration_end'), '%Y-%m-%d').date()
            item.max_participants = int(request.form.get('max_participants'))
            item.cost = int(request.form.get('price'))
            item.images = image_string
            item.notes = request.form.get('notes')
            item.includes = request.form.get('includes')
            item.excludes = request.form.get('excludes')
            item.timetable_data = request.form.get('timetable_data')
            item.pesticide_free = is_organic
            item.organic_certification_image = cert_filename
            item.organic_certification_type = request.form.get('organic_certification_type')
            item.lat = lat
            item.lng = lng
            item.volunteer_needed = volunteer_needed
            item.volunteer_duties = request.form.get('volunteer_duties')
            item.has_parking = has_parking
            flash("체험 정보가 성공적으로 수정되었습니다!", "success")
        else: # 생성
            farmer = User.query.get(session['user_id'])
            default_farm = farm_service.default_farm_for(session['user_id'])  # B안: 기본 농장에 연결
            new_experience = Experience(
                farm_id=default_farm.id if default_farm else None,
                crop=request.form.get('crop'),
                phone=request.form.get('phone'),
                location=farmer.farm_address,
                address_detail=address_detail,
                farm_size=request.form.get('farm_size'),
                duration_start=datetime.strptime(request.form.get('duration_start'), '%Y-%m-%d').date(),
                end_date=datetime.strptime(request.form.get('duration_end'), '%Y-%m-%d').date(),
                max_participants=int(request.form.get('max_participants')),
                cost=int(request.form.get('price')),
                images=image_string,
                notes=request.form.get('notes'),
                includes=request.form.get('includes'),
                excludes=request.form.get('excludes'),
                timetable_data=request.form.get('timetable_data'),
                pesticide_free=is_organic,
                organic_certification_image=cert_filename,
                organic_certification_type=request.form.get('organic_certification_type'),
                lat=lat,
                lng=lng,
                farmer_id=session['user_id'],
                volunteer_needed=volunteer_needed,
                has_parking=has_parking,
                volunteer_duties=request.form.get('volunteer_duties'),
                status='recruiting'
            )
            db.session.add(new_experience)
            flash("새로운 체험이 성공적으로 등록되었습니다!", "success")

        db.session.commit()
        return redirect(url_for('index'))

    return render_template('farmer_register.html', item=item, form_data={})


def delete_experience(item_id):
    if 'user_id' not in session or session['role'] != 'farmer': abort(403)
    item = Experience.query.get_or_404(item_id)
    if item.farmer_id != session.get('user_id'): abort(403)
    db.session.delete(item)
    db.session.commit()
    flash("체험이 삭제되었습니다.", "info")
    return redirect(url_for('index'))


def toggle_visibility(item_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403

    item = Experience.query.get_or_404(item_id)
    if item.farmer_id != session.get('user_id'):
        return jsonify({'success': False, 'message': '자신이 등록한 체험만 변경할 수 있습니다.'}), 403

    if item.status == 'recruiting':
        item.status = 'hidden'
        message = '체험을 비공개로 전환했습니다.'
    elif item.status == 'hidden':
        item.status = 'recruiting'
        message = '체험을 공개로 전환했습니다.'
    else:
        return jsonify({'success': False, 'message': '상태를 변경할 수 없는 체험입니다.'}), 400

    db.session.commit()
    return jsonify({'success': True, 'message': message, 'new_status': item.status})


def get_experiences_json():
    experiences = Experience.query.filter_by(status='recruiting').all()
    experience_list = [exp.to_dict() for exp in experiences]
    return jsonify(experience_list)


def search_categories():
    # 프론트 드롭박스용 조건 카테고리 트리(필터·역제안 요청글 공용). groups로 섹션 구분.
    return success_response({"categories": SEARCH_CATEGORIES, "groups": CATEGORY_GROUPS})


def register(app):
    app.add_url_rule('/', 'index', index)
    app.add_url_rule('/api/search-categories', 'search_categories', search_categories)
    app.add_url_rule('/experience/<int:item_id>', 'experience_detail', experience_detail)
    app.add_url_rule('/farmer/register', 'farmer_register', farmer_register, methods=['GET', 'POST'])
    app.add_url_rule('/farmer/modify/<int:item_id>', 'farmer_register', farmer_register, methods=['GET', 'POST'])
    app.add_url_rule('/experience/delete/<int:item_id>', 'delete_experience', delete_experience, methods=['POST'])
    app.add_url_rule('/api/experience/<int:item_id>/toggle_visibility', 'toggle_visibility', toggle_visibility, methods=['PATCH'])
    app.add_url_rule('/api/experiences', 'get_experiences_json', get_experiences_json)
