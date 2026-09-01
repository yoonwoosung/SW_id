# routes/volunteer.py — 봉사 도메인 라우트(봉사 신청).
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


def volunteer_apply():
    # e-sibal의 검색/필터 기능을 farmer의 status 필터와 결합
    page = request.args.get('page', 1, type=int)
    sort_by = request.args.get('sort', 'deadline', type=str)
    region = request.args.get('region', type=str)
    crop_query = request.args.get('crop_query', type=str)

    query = Experience.approved_only().filter(
        Experience.volunteer_needed > 0, Experience.status == 'recruiting')

    if region:
        query = query.filter(Experience.address_detail.like(f"%{region}%"))
    if crop_query:
        query = query.filter(Experience.crop.like(f"%{crop_query}%"))

    if sort_by == 'reviews':
        query = query.outerjoin(Review).group_by(Experience.id).order_by(func.count(Review.id).desc(), Experience.duration_start.asc())
    else: # 'deadline' 또는 기본값
        query = query.order_by(Experience.duration_start.asc())

    pagination = query.paginate(page=page, per_page=15, error_out=False)
    items_on_page = pagination.items

    return render_template('volunteer_apply.html',
                           items=items_on_page,
                           pagination=pagination,
                           sort_by=sort_by)


def register(app):
    app.add_url_rule('/volunteer', 'volunteer_apply', volunteer_apply)
