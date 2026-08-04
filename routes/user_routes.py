# routes/user_routes.py — 사용자 도메인 라우트(프로필·마이페이지·업로드·알림삭제·이용가이드).
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
from common.response import success_response
from common.auth import api_login_required
from services.trend_service import recent_viewed_experiences
from services.point_service import get_point_summary


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
        # nickname·name은 NOT NULL이므로 폼에 값이 있을 때만 갱신(없으면 기존값 유지).
        nickname = request.form.get('nickname')
        if nickname:
            user.nickname = nickname
        name = request.form.get('name')
        if name:
            user.name = name
        user.phone = request.form.get('phone')
        if user.role == 'farmer':
            user.farm_address = request.form.get('farm_address')
            user.farm_size = request.form.get('farm_size')
            user.profile_bio = request.form.get('profile_bio')
        db.session.commit()
        flash("회원 정보가 성공적으로 수정되었습니다.", "success")
        session['nickname'] = user.nickname
        return redirect(url_for('my_info'))

    applications = Application.query.filter_by(user_id=user.id).order_by(Application.apply_date.desc()).all()
    return render_template('my_info.html', user=user, applications=applications)


def mypage():
    if 'user_id' not in session:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))
    user = User.query.get_or_404(session['user_id'])
    applications = Application.query.filter_by(user_id=user.id).order_by(Application.apply_date.desc()).all()
    return render_template('mypage.html', user=user, applications=applications)


def album_create():
    # park_back 기능: 다녀온 체험으로 추억 앨범 만들기.
    if 'user_id' not in session:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))
    user = User.query.get_or_404(session['user_id'])
    applications = Application.query.filter_by(user_id=user.id).order_by(Application.apply_date.desc()).all()
    return render_template('album_create.html', user=user, applications=applications)


def guide_page():
    return render_template('guide.html')


def farmer_guide():
    return render_template('farmer_guide.html')


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
