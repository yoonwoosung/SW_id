# routes/user_routes.py — 사용자 도메인 라우트(프로필·마이페이지·업로드·알림삭제·이용가이드 및 농장주 관리).
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

# Models
from models import db, User, Experience, Review, Inquiry, Application, Notification, Farm
from services.distance import haversine
from services.recommend_data import REGIONAL_SPECIALTIES
from services.recommend_service import matches_specialty, score_components, calculate_score
from services.recommend_reason import recommendation_reason
from services.review_service import analyze_review_with_clova
from external.kakao_map import get_coords_from_address
from common.validators import allowed_file
from common.response import success_response
from common.auth import api_login_required
from services.trend_service import recent_viewed_experiences
from services.point_service import get_point_summary
from services import activity_service


def recent_views():
    # 로그인 사용자의 '최근 본 체험'(click_log 기반). 비로그인은 빈 배열.
    views = recent_viewed_experiences(session.get('user_id'))
    return success_response({"recent_views": views})


@api_login_required
def my_points():
    # 내 포인트 잔액 + 적립·사용 내역. 로그인 필수(비로그인 403).
    return success_response(get_point_summary(session['user_id']))


def update_bio():
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401
    user = User.query.get(session['user_id'])
    if not user:
        return jsonify({'success': False, 'message': '사용자를 찾을 수 없습니다.'}), 404

    data = request.get_json()
    new_bio = data.get('profile_bio')

    if new_bio is None:
        return jsonify({'success': False, 'message': '소개 내용이 없습니다.'}), 400

    user.profile_bio = new_bio
    db.session.commit()

    return jsonify({'success': True, 'message': '한 줄 소개가 업데이트되었습니다.'})


def delete_notification(notification_id):
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    notification = Notification.query.get_or_404(notification_id)

    if notification.user_id != session.get('user_id'):
        return jsonify({'success': False, 'message': '권한이 없습니다.'}), 403

    db.session.delete(notification)
    db.session.commit()

    return jsonify({'success': True, 'message': '알림이 삭제되었습니다.'})


def upload_profile():
    if 'user_id' not in session: return redirect(url_for('login_page'))
    if 'profile_pic' not in request.files or request.files['profile_pic'].filename == '':
        flash('선택된 파일이 없습니다.', 'warning')
        return redirect(url_for('my_info'))
    file = request.files['profile_pic']
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"profile_{session['user_id']}_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)
        img = Image.open(file.stream)
        img.thumbnail((400, 400))
        img.save(filepath)

        user = User.query.get(session['user_id'])
        user.profile_image = filename
        db.session.commit()
        flash('프로필 사진이 변경되었습니다.', 'success')
    else:
        flash('허용되지 않는 파일 형식입니다.', 'danger')
    return redirect(url_for('my_info'))


def upload_farm_photo():
    if 'user_id' not in session or session['role'] != 'farmer': return redirect(url_for('login_page'))
    if 'farm_photo' not in request.files or request.files['farm_photo'].filename == '':
        flash('선택된 파일이 없습니다.', 'warning')
        return redirect(url_for('index'))
    file = request.files['farm_photo']
    if file and allowed_file(file.filename):
        ext = file.filename.rsplit('.', 1)[1].lower()
        filename = f"farm_{session['user_id']}_{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(current_app.config['UPLOAD_FOLDER'], filename)

        img = Image.open(file.stream)
        img.thumbnail((800, 600))
        img.save(filepath)

        user = User.query.get(session['user_id'])
        user.farm_image = filename
        db.session.commit()
        flash('농장 사진이 변경되었습니다.', 'success')
    else:
        flash('허용되지 않는 파일 형식입니다.', 'danger')
    return redirect(url_for('index'))


def my_info():
    if 'user_id' not in session:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))

    user = User.query.get_or_404(session['user_id'])

    if request.method == 'POST':
        nickname = (request.form.get('nickname') or '').strip()
        name = (request.form.get('name') or '').strip()
        phone = (request.form.get('phone') or '').strip()

        if not nickname or not name or not phone:
            flash("닉네임과 이름, 전화번호는 필수 입력 항목입니다.", "danger")
            return redirect(url_for('my_info'))

        user.nickname = nickname
        user.name = name
        user.phone = phone

        if user.role == 'farmer':
            user.farm_address = (request.form.get('farm_address') or '').strip()
            user.farm_size = (request.form.get('farm_size') or '').strip()
            user.profile_bio = (request.form.get('profile_bio') or '').strip()

        db.session.commit()
        flash("회원 정보가 성공적으로 수정되었습니다.", "success")
        session['nickname'] = user.nickname
        if user.role == 'farmer':
            return redirect(url_for('farmer_easy_mode', tab='account'))
        return redirect(url_for('my_info'))

    applications = Application.query.filter_by(user_id=user.id).order_by(Application.apply_date.desc()).all()
    return render_template('my_info.html', user=user, applications=applications)


def mypage():
    if 'user_id' not in session:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))  
    user_id = session['user_id']
    user = User.query.get_or_404(user_id)
    newly_completed_crops = activity_service.sync_user_completed_reservations(user_id)

    if newly_completed_crops:
        for crop in newly_completed_crops:
            flash(f"🎉 '{crop}' 체험은 어떠셨나요? 소중한 후기를 남겨주세요.", "info")

    applications = Application.query.filter_by(user_id=user.id).order_by(Application.apply_date.desc()).all()
    reservation_cards = activity_service.reservation_cards(applications)
    experienced_count = activity_service.experienced_count(applications)

    return render_template('mypage.html', user=user, applications=applications,
                           reservation_cards=reservation_cards, experienced_count=experienced_count)


def guide_page():
    return render_template('guide.html')


def farmer_guide():
    return render_template('farmer_guide.html')


def album_create():
    if 'user_id' not in session:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))

    user = User.query.get_or_404(session['user_id'])
    applications = Application.query.filter_by(user_id=user.id).order_by(Application.apply_date.desc()).all()
    return render_template('album_create.html', user=user, applications=applications)


def verify_password():
    if 'user_id' not in session:
        return jsonify({'ok': False})
    user = User.query.get(session['user_id'])
    password = (request.json or {}).get('password', '')
    return jsonify({'ok': check_password_hash(user.password, password)})


def farmer_update_info():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    user = User.query.get_or_404(session['user_id'])
    user.nickname = (request.form.get('nickname') or user.nickname).strip()
    user.name = (request.form.get('name') or '').strip()
    user.birthdate = (request.form.get('birthdate') or '').strip()
    user.gender = request.form.get('gender') or None
    user.profile_bio = (request.form.get('profile_bio') or '').strip()
    db.session.commit()
    session['nickname'] = user.nickname
    flash("기본 정보가 저장되었습니다.", "success")
    return redirect(url_for('farmer_easy_mode', tab='account'))


def add_farm():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    address = (request.form.get('farm_address') or '').strip()
    if not address:
        flash('농장 주소를 입력해주세요.', 'warning')
        return redirect(url_for('farmer_easy_mode', tab='account'))
    size = (request.form.get('farm_size') or '').strip()
    is_organic = 'is_organic' in request.form

    cert_pdf_name = None
    cert_file = request.files.get('farmer_certificate_pdf')
    if cert_file and cert_file.filename and cert_file.filename.lower().endswith('.pdf'):
        cert_pdf_name = f"farm_cert_{session['user_id']}_{uuid.uuid4().hex}.pdf"
        cert_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], cert_pdf_name))

    organic_img_name = None
    organic_cert_type = None
    if is_organic:
        organic_cert_type = (request.form.get('organic_cert_type') or '').strip()
        org_file = request.files.get('organic_cert_image')
        if org_file and org_file.filename and allowed_file(org_file.filename):
            ext = org_file.filename.rsplit('.', 1)[1].lower()
            organic_img_name = f"organic_{session['user_id']}_{uuid.uuid4().hex}.{ext}"
            org_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], organic_img_name))

    # [수정] models/farm.py 모델 매핑 (farmer_id -> user_id)
    farm = Farm(
        user_id=session['user_id'],
        address=address,
        size=size,
        certificate_pdf=cert_pdf_name,
        is_organic=is_organic,
        organic_cert_image=organic_img_name,
        organic_cert_type=organic_cert_type,
    )
    db.session.add(farm)

    # 첫 번째 농장이면 user.farm_address 업데이트
    user = User.query.get(session['user_id'])
    if not user.farm_address:
        user.farm_address = address
        user.farm_size = size

    db.session.commit()
    flash('농장이 등록되었습니다.', 'success')
    return redirect(url_for('farmer_easy_mode', tab='account'))


def delete_farm(farm_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    farm = Farm.query.get_or_404(farm_id)
    
    # [수정] models/farm.py 모델 매핑 (farmer_id -> user_id)
    if farm.user_id != session['user_id']:
        abort(403)
    db.session.delete(farm)
    
    # 남은 농장 중 첫 번째로 user.farm_address 갱신
    user = User.query.get(session['user_id'])
    remaining = Farm.query.filter_by(user_id=user.id).order_by(Farm.created_at.asc()).first()
    user.farm_address = remaining.address if remaining else None
    user.farm_size = remaining.size if remaining else None
    db.session.commit()
    flash('농장이 삭제되었습니다.', 'success')
    return redirect(url_for('farmer_easy_mode', tab='account'))


def register(app):
    app.add_url_rule('/update_bio', 'update_bio', update_bio, methods=['POST'])
    app.add_url_rule('/notifications/delete/<int:notification_id>', 'delete_notification', delete_notification, methods=['POST'])
    app.add_url_rule('/upload_profile', 'upload_profile', upload_profile, methods=['POST'])
    app.add_url_rule('/upload_farm_photo', 'upload_farm_photo', upload_farm_photo, methods=['POST'])
    app.add_url_rule('/my_info', 'my_info', my_info, methods=['GET', 'POST'])
    app.add_url_rule('/mypage', 'mypage', mypage)
    app.add_url_rule('/api/users/me/recent-views', 'recent_views', recent_views)
    app.add_url_rule('/api/users/me/points', 'my_points', my_points)
    app.add_url_rule('/guide', 'guide_page', guide_page)
    app.add_url_rule('/farmer_guide', 'farmer_guide', farmer_guide)
    app.add_url_rule('/album/create', 'album_create', album_create, methods=['GET', 'POST'])
    
    # FE 신규 기능 라우트 등록
    app.add_url_rule('/verify_password', 'verify_password', verify_password, methods=['POST'])
    app.add_url_rule('/farmer/update_info', 'farmer_update_info', farmer_update_info, methods=['POST'])
    app.add_url_rule('/farmer/farm/add', 'add_farm', add_farm, methods=['POST'])
    app.add_url_rule('/farmer/farm/<int:farm_id>/delete', 'delete_farm', delete_farm, methods=['POST'])