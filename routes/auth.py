# routes/auth.py — 인증 도메인 라우트(회원가입·이메일확인·로그인·로그아웃).
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
from services.profile_service import clean_profile
from common.profile_options import AGE_GROUPS, GENDERS, FAMILY_TYPES, ACTIVITY_LABELS, TRANSPORT_LABELS


def register_page():
    if request.method == 'POST':
        role = request.form.get('role')
        nickname = request.form.get('nickname')
        email = request.form.get('email')
        password = request.form.get('password')
        name = request.form.get('name')
        phone = request.form.get('phone')
        birthdate = request.form.get('birthdate')
        gender = request.form.get('gender')
        password_confirm = request.form.get('password_confirm')
        required_fields = [role, nickname, email, password, name, phone]

        if password != password_confirm:
            flash("비밀번호가 일치하지 않습니다.", "danger")
            return render_template('register.html', form_data=request.form)
        if not all(required_fields):
            flash("모든 필수 항목을 올바르게 입력해주세요.", "danger")
            return render_template('register.html', form_data=request.form)
        if User.query.filter_by(email=email).first():
            flash("이미 가입된 이메일입니다.", "danger")
            return render_template('register.html', form_data=request.form)

        cert_pdf_filename = None
        hashed_password = generate_password_hash(password, method='pbkdf2:sha256')

        # [백 기능] clean_profile 활용 및 [프 기능] birthdate, gender 반영
        profile = clean_profile(request.form.get, request.form.getlist)
        profile.setdefault('birthdate', birthdate)
        if gender:
            profile['gender'] = gender

        new_user = User(
            email=email, nickname=nickname, password=hashed_password,
            role=role, name=name, phone=phone,
            farm_address=request.form.get('farm_address'),
            farm_size=request.form.get('farm_size'),
            profile_bio=request.form.get('profile_bio'),
            farmer_certificate_pdf=cert_pdf_filename,
            **profile
        )
        
        if role == 'farmer':
            cert_pdf_file = request.files.get('farmer_certificate_pdf')
            if not cert_pdf_file or cert_pdf_file.filename == '':
                flash("농장주 회원은 농업인 확인서 PDF 파일을 반드시 제출해야 합니다.", "danger")
                return render_template('register.html', form_data=request.form)

            if allowed_file(cert_pdf_file.filename):
                ext = cert_pdf_file.filename.rsplit('.', 1)[1].lower()
                cert_pdf_filename = f"farmer_cert_{email}_{uuid.uuid4().hex}.{ext}"
                cert_pdf_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], cert_pdf_filename))

                new_user.farmer_certificate_pdf = cert_pdf_filename
                new_user.verification_status = 'pending'
            else:
                flash("허용되지 않는 파일 형식입니다. PDF 파일만 업로드 가능합니다.", "danger")
                return render_template('register.html', form_data=request.form)
        
        db.session.add(new_user)
        start_time = datetime.now()
        db.session.commit()

        if role == 'farmer':
            flash("농장주 가입 신청이 완료되었습니다. 서류 검토는 1~2일 소요될 수 있습니다.", "success")
        else:
            flash("회원가입이 완료되었습니다! 로그인해주세요.", "success")

        print(f"[{datetime.now()}] USER REGISTRATION: DB commit took {datetime.now() - start_time}")
        return redirect(url_for('login_page'))
    return render_template('register.html', form_data={})


def check_email():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    return jsonify({'exists': user is not None})


def login_page():
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        if user and check_password_hash(user.password, password):
            session['user_id'] = user.id
            session['nickname'] = user.nickname
            session['role'] = user.role
            session['just_logged_in'] = True
            flash(f"{user.nickname}님, 환영합니다!", "success")
            
            # 역할별 시작 페이지 분기
            if user.role == 'admin':
                return redirect(url_for('admin_farm_audit_list'))
            elif user.role == 'farmer':
                return redirect(url_for('farmer_easy_mode'))
            else:
                return redirect(url_for('index'))
        else:
            flash("이메일 또는 비밀번호가 올바르지 않습니다.", "danger")
            return redirect(url_for('login_page'))

    return render_template('login.html')


def logout():
    session.clear()
    flash("로그아웃되었습니다.", "info")
    return redirect(url_for('index'))


def register(app):
    # [백 기능] 가입폼 프로필 선택지 전역 주입 유지
    @app.context_processor
    def _inject_register_options():
        return {"reg_options": {
            "age_groups": AGE_GROUPS, "genders": GENDERS, "family_types": FAMILY_TYPES,
            "activities": ACTIVITY_LABELS, "transports": TRANSPORT_LABELS,
        }}

    app.add_url_rule('/register', 'register_page', register_page, methods=['GET', 'POST'])
    app.add_url_rule('/check_email', 'check_email', check_email, methods=['POST'])
    app.add_url_rule('/login', 'login_page', login_page, methods=['GET', 'POST'])
    app.add_url_rule('/logout', 'logout', logout)