#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공모전 제출용 심사 계정을 만든다(2026 관광데이터 활용 공모전).

공모전 제출 요건이 계정 형식을 지정한다: openapi@<도메인>. 심사위원이 이
계정으로 접속해 서비스를 확인하므로, 체험자·농장주·관리자 세 역할을 모두
준비한다. 농장주는 ★승인된 농장과 모집 중인 체험★이 있어야 기능이 보인다.

실행(비밀번호는 소스에 남기지 않는다 — 이 저장소는 public 이다):
    cd ~/SW_id
    OPENAPI_PASSWORD='공모전지정비밀번호' python3 seed_openapi.py
    OPENAPI_PASSWORD='...' python3 seed_openapi.py --check   # 진단만, 변경 없음

반복 실행해도 안전하다.
    - 계정이 없으면 만들고, 있으면 ★비밀번호만 갱신★한다(역할·닉네임은 유지).
    - 농장·체험은 이름으로 찾아 없을 때만 만든다.

기존 admin@farmlink.com 등 팀 계정은 건드리지 않는다. 추가일 뿐 교체가 아니다.

끝나면 PythonAnywhere Web 탭에서 Reload 를 누를 것.
"""
import os
import sys
from datetime import date, timedelta

from werkzeug.security import generate_password_hash

# app.py 가 import 시점에 .env 를 읽고 db.init_app(app) 까지 끝낸다.
from app import app, db, User
from models import Experience
from models.farm import Farm

# routes/auth.py 의 로그인 검증(check_password_hash)이 읽는 해시 방식.
# seed_admin.py 와 같은 값이어야 한다.
HASH_METHOD = 'pbkdf2:sha256'

PASSWORD_ENV = 'OPENAPI_PASSWORD'

ACCOUNTS = [
    {'email': 'openapi@farmlink.com',
     'nickname': '심사위원', 'name': '심사위원', 'role': 'experiencer'},
    {'email': 'openapi.farmer@farmlink.com',
     'nickname': '심사농장', 'name': '심사농장주', 'role': 'farmer'},
    {'email': 'openapi.admin@farmlink.com',
     'nickname': '심사관리자', 'name': '심사관리자', 'role': 'admin'},
]

FARMER_EMAIL = 'openapi.farmer@farmlink.com'

# 농장주 화면을 보려면 ★승인된 농장★이 있어야 한다(Farm.status = 'APPROVED').
# Farm 은 (user_id, name) 이 unique 라 이름으로 중복을 판정한다.
FARM = {
    'name': '심사용 체험농장',
    'address': '충남 천안시 동남구 병천면 충절로 1600',
    'address_detail': '심사용 시연 농장',
    'lat': 36.7651, 'lng': 127.281,
    'size': '3000',
    'status': 'APPROVED',
}

# 모집 중인 체험이 하나는 있어야 목록·상세·코스 추천이 전부 보인다.
EXPERIENCE = {
    'crop': '심사용 딸기 따기 체험',
    'location': '충남',
    'address_detail': FARM['address'],
    'cost': 20000,
    'max_participants': 20,
    'current_participants': 0,
    'lat': FARM['lat'], 'lng': FARM['lng'],
    'status': 'recruiting',
    'has_parking': True,
    'pet_allowed': True,
    'pet_max_weight_kg': 15.0,
    'barrier_free': True,
    'pesticide_free': True,
    'notes': '공모전 심사용 시연 체험입니다.',
}


def fail(message):
    print("[openapi] 오류: %s" % message, file=sys.stderr)
    sys.exit(1)


def upsert_accounts(password, dry_run):
    """계정을 만들거나 ★비밀번호만★ 갱신한다. 반환: {email: User}"""
    users, report = {}, []
    for spec in ACCOUNTS:
        user = User.query.filter_by(email=spec['email']).first()
        if user is None:
            user = User(email=spec['email'], nickname=spec['nickname'],
                        name=spec['name'], role=spec['role'],
                        password=generate_password_hash(password, method=HASH_METHOD))
            if not dry_run:
                db.session.add(user)
            report.append(('생성', spec['email'], spec['role']))
        else:
            # 역할·닉네임은 건드리지 않는다. 사람이 바꿔 둔 값일 수 있다.
            if not dry_run:
                user.password = generate_password_hash(password, method=HASH_METHOD)
            note = '비밀번호 갱신'
            if user.role != spec['role']:
                note += ' (★역할이 %s 다 — 요건은 %s★)' % (user.role, spec['role'])
            report.append((note, spec['email'], user.role))
        users[spec['email']] = user
    return users, report


def ensure_farm_and_experience(farmer, dry_run):
    """농장주에게 ★승인된 농장★과 ★모집 중인 체험★이 있게 한다."""
    notes = []
    farm = Farm.query.filter_by(user_id=farmer.id, name=FARM['name']).first() if farmer.id else None
    if farm is None:
        farm = Farm(user=farmer, **FARM)
        if not dry_run:
            db.session.add(farm)
        notes.append('농장 생성: %s (status=APPROVED)' % FARM['name'])
    else:
        if farm.status != 'APPROVED':
            if not dry_run:
                farm.status = 'APPROVED'
            notes.append('농장 상태를 APPROVED 로 변경')
        else:
            notes.append('농장 이미 있음 (status=APPROVED)')

    exp = (Experience.query.filter_by(farmer_id=farmer.id, crop=EXPERIENCE['crop']).first()
           if farmer.id else None)
    today = date.today()
    if exp is None:
        exp = Experience(farmer=farmer, farm=farm,
                         duration_start=today,
                         end_date=today + timedelta(days=180),
                         **EXPERIENCE)
        if not dry_run:
            db.session.add(exp)
        notes.append('체험 생성: %s (모집중, 마감 %s)'
                     % (EXPERIENCE['crop'], today + timedelta(days=180)))
    else:
        # 심사 기간에 마감되어 목록에서 사라지지 않게 기한을 밀어 둔다.
        if exp.end_date is None or exp.end_date < today + timedelta(days=90):
            if not dry_run:
                exp.end_date = today + timedelta(days=180)
            notes.append('체험 마감일을 %s 로 연장' % (today + timedelta(days=180)))
        if exp.status != 'recruiting':
            if not dry_run:
                exp.status = 'recruiting'
            notes.append('체험 상태를 recruiting 으로 변경')
        if len(notes) == 1:
            notes.append('체험 이미 있음 (모집중)')
    return notes


def main():
    dry_run = '--check' in sys.argv
    password = os.environ.get(PASSWORD_ENV)
    if not password:
        fail("환경변수 %s 가 없다.\n"
             "        실행: %s='비밀번호' python3 seed_openapi.py" % (PASSWORD_ENV, PASSWORD_ENV))

    with app.app_context():
        print("[openapi] 대상 DB: %s" % db.engine.url.render_as_string(hide_password=True))
        if dry_run:
            print("[openapi] --check: 아무것도 바꾸지 않는다.")

        users, report = upsert_accounts(password, dry_run)
        if not dry_run:
            db.session.flush()      # farmer.id 를 얻어야 농장·체험을 붙일 수 있다

        farmer = users[FARMER_EMAIL]
        farm_notes = ensure_farm_and_experience(farmer, dry_run)

        if dry_run:
            db.session.rollback()
        else:
            try:
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                fail("커밋 실패, 전체 롤백함: %s" % exc)

        print()
        for action, email, role in report:
            print("[openapi] %-28s %-30s role=%s" % (action, email, role))
        print()
        for note in farm_notes:
            print("[openapi] 농장주 준비: %s" % note)

        # 실제로 로그인되는지 여기서 바로 확인한다(해시 방식이 어긋나면 여기서 잡힌다).
        if not dry_run:
            from werkzeug.security import check_password_hash
            print()
            for spec in ACCOUNTS:
                user = User.query.filter_by(email=spec['email']).first()
                ok = check_password_hash(user.password, password)
                print("[openapi] 로그인 검증 %-30s %s" % (spec['email'], 'OK' if ok else '★실패★'))

        print("\n[openapi] 완료. PythonAnywhere Web 탭에서 Reload 를 누를 것.")


if __name__ == '__main__':
    main()
