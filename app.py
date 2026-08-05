import os
from flask import Flask, render_template, request, redirect, url_for, flash, session, abort, jsonify
from dotenv import load_dotenv
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import requests
from sqlalchemy.sql import func
from collections import defaultdict
from datetime import date, timedelta, datetime
from sqlalchemy import or_
import json
import math
import re
import uuid
from sqlalchemy import case
from types import SimpleNamespace
import platform
from PIL import Image


project_folder = os.path.dirname(os.path.abspath(__file__))
load_dotenv(os.path.join(project_folder, '.env'))

# --- 1. 앱 및 DB 설정 ---
app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY')

# DB 접속 정보: farmer 기준 로컬 DB 사용.
db_username = os.environ.get('DB_USERNAME')
db_password = os.environ.get('DB_PASSWORD')
db_hostname = os.environ.get('DB_HOST')
db_name     = os.environ.get('DB_NAME')
DATABASE_URI = f"mysql+mysqlconnector://{db_username}:{db_password}@{db_hostname}/{db_name}"


app.config['SQLALCHEMY_DATABASE_URI'] = DATABASE_URI
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SQLALCHEMY_POOL_RECYCLE'] = 280
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 30

# --- 파일 업로드 설정 ---
app.config['UPLOAD_FOLDER'] = os.path.join(app.static_folder, 'uploads')
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg', 'gif', 'pdf'} # farmer 기준
app.config['KAKAO_API_KEY'] = os.environ.get('KAKAO_API_KEY') # farmer 기준
app.config['KAKAO_JS_KEY'] = os.environ.get('KAKAO_JS_KEY')   # 카카오맵 JS SDK 키(park_back)

# DB 모델과 db 객체는 models/ 패키지로 분리됨. 여기서는 앱에 바인딩만 한다.
from models import db, User, Experience, Review, Inquiry, Application, Notification
db.init_app(app)

# 공통 검증 유틸(파일 업로드 확장자 검사)
from common.validators import allowed_file


# 템플릿 전역 주입은 common/context.py로 분리됨.
from common.context import inject_globals
app.context_processor(inject_globals)




# 추천/거리 계산 로직은 services/ 패키지로 분리됨.
from services.distance import haversine
from services.recommend_data import REGIONAL_SPECIALTIES
from services.recommend_service import matches_specialty, score_components, calculate_score
from services.recommend_reason import recommendation_reason


# --- 2. DB 모델(테이블) 정의 → models/ 패키지로 분리됨 ---
# User / Experience / Review / Inquiry / Application(reservation.py) / Notification
# 은 위쪽 `from models import ...` 로 가져와 그대로 사용한다.

# 외부 API 호출/후기 분석은 external/, services/ 로 분리됨.
from external.kakao_map import get_coords_from_address
from services.review_service import analyze_review_with_clova


# 모든 라우트는 routes/ 패키지로 분리됨. register_routes(app)로 등록한다.
from routes import register_routes
register_routes(app)


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    debug_mode = os.environ.get('DEBUG', 'False').lower() in ('1', 'true', 'yes')
    app.run(debug=debug_mode, ssl_context='adhoc')
