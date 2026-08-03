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

        new_user = User(
            email=email, nickname=nickname, password=hashed_password,
            role=role, name=name, phone=phone,birthdate=birthdate, gender=gender,
            farm_address=request.form.get('farm_address'),
            farm_size=request.form.get('farm_size'),
            profile_bio=request.form.get('profile_bio'),
            farmer_certificate_pdf=cert_pdf_filename
        )
        
        if role == 'farmer':
            cert_pdf_file = request.files.get('farmer_certificate_pdf')
            if not cert_pdf_file or cert_pdf_file.filename == '':
                flash("농장주 회원은 농업인 확인서 PDF 파일을 반드시 제출해야 합니다.", "danger")
                return render_template('register.html', form_data=request.form)
            # highlight-start
            # OCR 실행 로직을 완전히 제거하고, 파일 저장 및 상태 변경으로 대체합니다.
            if allowed_file(cert_pdf_file.filename):
                ext = cert_pdf_file.filename.rsplit('.', 1)[1].lower()
                cert_pdf_filename = f"farmer_cert_{email}_{uuid.uuid4().hex}.{ext}"
                cert_pdf_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], cert_pdf_filename))

                new_user.farmer_certificate_pdf = cert_pdf_filename
                new_user.verification_status = 'pending' # 상태를 '인증 대기중'으로 설정
            else:
                flash("허용되지 않는 파일 형식입니다. PDF 파일만 업로드 가능합니다.", "danger")
                return render_template('register.html', form_data=request.form)
            # highlight-end
        
        db.session.add(new_user)
        start_time = datetime.now()
        db.session.commit()
        # highlight-start
        # 농장주에게는 다른 안내 메시지를 보여줍니다.
        if role == 'farmer':
            flash("농장주 가입 신청이 완료되었습니다. 서류 검토는 1~2일 소요될 수 있습니다.", "success")
        else:
            flash("회원가입이 완료되었습니다! 로그인해주세요.", "success")
        # highlight-end
        print(f"[{datetime.now()}] USER REGISTRATION: DB commit took {datetime.now() - start_time}")

        flash("회원가입이 완료되었습니다! 로그인해주세요.", "success")
        return redirect(url_for('login_page'))
    return render_template('register.html', form_data={})


def check_email():
    email = request.json.get('email')
    user = User.query.filter_by(email=email).first()
    return jsonify({'exists': user is not None})


def login_page():
    # 1. 사용자가 '로그인' 버튼을 눌렀을 때만 아래 코드를 실행합니다.
    if request.method == 'POST':
        email = request.form.get('email')
        password = request.form.get('password')
        user = User.query.filter_by(email=email).first()

        # 2. 사용자 정보 확인 및 로그인 처리 로직 전체를 POST 블록 안으로 옮깁니다.
        if user and check_password_hash(user.password, password):
            
            ## 인증서 인증 임시 비활성화(나중에 주석 지우기)
            # if user.role == 'farmer' and user.verification_status == 'pending':
            #     flash("가입 승인 대기 중인 계정입니다. 서류 검토 후 결과를 알려드리겠습니다.", "warning")
            #     return redirect(url_for('login_page'))
        
            # if user.role == 'farmer' and user.verification_status in ['rejected', 'error']:
            #     flash("가입이 거절되었거나 인증 중 오류가 발생했습니다. 관리자에게 문의하세요.", "danger")
            #     return redirect(url_for('login_page'))
            

            session['user_id'] = user.id
            session['nickname'] = user.nickname
            session['role'] = user.role
            flash(f"{user.nickname}님, 환영합니다!", "success")
            if user.role == 'farmer':
                return redirect(url_for('detailed_farmer_dashboard'))
            return redirect(url_for('index'))
        else:
            flash("이메일 또는 비밀번호가 올바르지 않습니다.", "danger")
            # POST 요청 실패 시에도 로그인 페이지를 다시 보여줍니다.
            return redirect(url_for('login_page'))

    # GET 요청일 경우 (그냥 페이지 방문)에는 아무 작업도 하지 않고 페이지만 보여줍니다.
    return render_template('login.html')


def logout():
    session.clear()
    flash("로그아웃되었습니다.", "info")
    return redirect(url_for('index'))


def register(app):
    app.add_url_rule('/register', 'register_page', register_page, methods=['GET', 'POST'])
    app.add_url_rule('/check_email', 'check_email', check_email, methods=['POST'])
    app.add_url_rule('/login', 'login_page', login_page, methods=['GET', 'POST'])
    app.add_url_rule('/logout', 'logout', logout)
