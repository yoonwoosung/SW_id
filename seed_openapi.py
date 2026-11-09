#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""공모전 제출용 심사 계정을 만든다(2026 관광데이터 활용 공모전).

공모전 제출 요건이 계정 형식을 지정한다: openapi@<도메인>. 제출 폼에 계정을
하나만 적을 수 있으므로 ★대표 계정 하나로 세 역할을 모두 볼 수 있게★ 한다.
로그인 후 프로필 메뉴의 역할 전환을 쓰면 된다(routes/auth.switch_role).

그 계정이 ★승인된 농장과 모집 중인 체험★을 직접 소유해야 농장주로 전환했을
때 빈 화면이 아니다. 과생산 체험도 하나 만들어 할인 기능까지 보이게 한다.

역할별 개별 계정도 함께 만든다 — 전환 기능이 심사 환경에서 헷갈릴 때의 대비다.

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
from datetime import date, datetime, timedelta

from werkzeug.security import generate_password_hash

# app.py 가 import 시점에 .env 를 읽고 db.init_app(app) 까지 끝낸다.
from app import app, db, User
from models import Experience, Application, Review
from models.farm import Farm

# routes/auth.py 의 로그인 검증(check_password_hash)이 읽는 해시 방식.
# seed_admin.py 와 같은 값이어야 한다.
HASH_METHOD = 'pbkdf2:sha256'

PASSWORD_ENV = 'OPENAPI_PASSWORD'

# ★대표 계정은 experiencer 로 시작한다.★ 역할 전환으로 농장주·관리자를 본다.
# (common/constants.ROLE_SWITCH_ALLOWED_EMAILS 에 이 이메일이 있어야 한다)
MAIN_EMAIL = 'openapi@farmlink.com'

ACCOUNTS = [
    {'email': MAIN_EMAIL,
     'nickname': '심사위원', 'name': '심사위원', 'role': 'experiencer'},
    # 폴백용 개별 계정. 전환 메뉴를 못 찾거나 헷갈릴 때 쓴다.
    {'email': 'openapi.farmer@farmlink.com',
     'nickname': '심사농장', 'name': '심사농장주', 'role': 'farmer'},
    {'email': 'openapi.admin@farmlink.com',
     'nickname': '심사관리자', 'name': '심사관리자', 'role': 'admin'},
]

# 농장·체험은 ★대표 계정★과 폴백 농장주 계정 양쪽에 만든다.
# 어느 쪽으로 들어가도 농장주 화면이 비어 있지 않아야 한다.
FARM_OWNER_EMAILS = (MAIN_EMAIL, 'openapi.farmer@farmlink.com')

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
    # 레시피 전수 — 완료된 예약의 '레시피 보기' 버튼을 확인할 수 있게 한다.
    # ★손글씨 사진은 넣지 않는다.★ 없는 사진을 만들어 '농부님의 손글씨'라고
    # 붙이면 거짓 표시가 된다. 사진 우선 표시는 농장주 화면에서 직접 올려 본다.
    'has_recipe': True,
    'recipe_name': '딸기 우유잼',
    'recipe_ingredients': '딸기 500g\n설탕 200g\n레몬즙 1큰술',
    'recipe_steps': '딸기를 씻어 꼭지를 떼고 반으로 자릅니다.\n'
                    '설탕을 뿌려 30분간 재웁니다.\n'
                    '중약불에서 저어가며 20분간 졸입니다.\n'
                    '레몬즙을 넣고 5분 더 졸인 뒤 식힙니다.',
    'recipe_tip': '딸기는 꼭지를 뗀 뒤에 씻으면 물이 배어 맛이 싱거워집니다.',
}

# 과생산(할인) 체험도 하나 둔다 — 심사위원이 할인 리본·수량 기능을 볼 수 있게.
# 할인율은 services/experience_validator 가 수량 구간으로 계산한다(여기서 정하지 않는다).
SURPLUS_EXPERIENCE = {
    'crop': '심사용 과생산 사과 수확',
    'location': '충남',
    'address_detail': FARM['address'],
    'cost': 14000,              # 할인가
    'list_price': 20000,        # 정가 — 리본이 이 둘의 차이로 할인율을 보여준다
    'max_participants': 20,
    'current_participants': 0,
    'lat': FARM['lat'], 'lng': FARM['lng'],
    'status': 'recruiting',
    'has_parking': True,
    'is_surplus': True,
    'surplus_terms_agreed': True,
    'surplus_qty_total': 300,
    'surplus_per_person': 3,
    'surplus_unit': 'kg',
    'surplus_reason': '작황호조',
    'notes': '공모전 심사용 과생산 할인 체험입니다.',
}


# 심사위원이 체험 상세에서 후기 목록을, 농장주 화면에서 AI 후기 요약을 볼 수
# 있어야 한다. 후기가 0건이면 AI 요약 API 가 400 을 돌려준다(routes/farms.py).
#
# ★대표 계정 본인은 후기를 쓰지 않는다.★ 쓰면 "이미 작성하셨습니다"가 되어
# 심사위원이 후기 작성 화면을 볼 수 없다. 완료된 예약만 만들어 둔다.
REVIEWERS = [
    ('review1@farmlink.com', '딸기러버', 5,
     '아이랑 같이 갔는데 농장주님이 하나하나 알려주셔서 좋았어요. '
     '딸기도 정말 달고 양도 넉넉했습니다. 주차장이 넓어서 편했어요.'),
    ('review2@farmlink.com', '주말농부', 4,
     '체험 자체는 만족스러웠습니다. 다만 화장실이 조금 멀어서 '
     '아이 데리고 다니기에는 불편했어요. 딸기 맛은 최고였습니다.'),
    ('review3@farmlink.com', '강아지랑여행', 5,
     '반려견 동반이 가능해서 선택했는데 정말 잘한 것 같아요. '
     '강아지도 뛰어놀고 저희도 딸기 따고 하루가 금방 갔습니다.'),
    ('review4@farmlink.com', '조용한여행자', 3,
     '주말이라 사람이 많아 조금 정신없었습니다. 체험 시간이 짧게 느껴졌어요. '
     '딸기 품질은 좋았고 농장주님도 친절하셨습니다.'),
]

# 후기를 달 때 쓰는 완료 예약의 기준일(오늘로부터 며칠 전).
REVIEW_DAYS_AGO = (14, 10, 7, 3)
# 대표 계정 본인의 완료 예약 — '내 활동'에서 레시피 버튼을 확인하는 용도.
MAIN_VISIT_DAYS_AGO = 5


def _completed_application(user, exp, days_ago, dry_run):
    """★지난 날짜로 완료된 예약★을 만든다. 없으면 후기를 쓸 수 없다.

    apply_date 를 과거로 두면 is_experience_ended 가 참이 되어 can_review 가
    자연스럽게 켜진다(services/activity_service). 상태도 '완료'로 둔다.
    """
    existing = (Application.query.filter_by(user_id=user.id, experience_id=exp.id).first()
                if user.id and exp.id else None)
    if existing:
        return existing, False
    row = Application(
        user_id=user.id, experience_id=exp.id,
        applicant_name=user.name or user.nickname,
        phone_number='010-0000-0000',
        participants_count=2,
        apply_date=date.today() - timedelta(days=days_ago),
        apply_time='10:00',
        status='완료', can_review=True,
    )
    if not dry_run:
        db.session.add(row)
    return row, True


def ensure_reviews(main_user, dry_run):
    """심사용 체험에 후기를 달고, 대표 계정에는 완료된 예약을 하나 만든다."""
    notes = []
    exp = Experience.query.filter_by(farmer_id=main_user.id,
                                     crop=EXPERIENCE['crop']).first()
    if exp is None:
        notes.append('체험을 찾지 못해 후기를 건너뛴다')
        return notes

    for (email, nickname, rating, content), days in zip(REVIEWERS, REVIEW_DAYS_AGO):
        user = User.query.filter_by(email=email).first()
        if user is None:
            user = User(email=email, nickname=nickname, name=nickname,
                        role='experiencer',
                        password=generate_password_hash(os.urandom(16).hex(),
                                                        method=HASH_METHOD))
            if not dry_run:
                db.session.add(user)
                db.session.flush()
            notes.append('후기 작성자 생성: %s' % nickname)
        _completed_application(user, exp, days, dry_run)

        if user.id and Review.query.filter_by(user_id=user.id,
                                              experience_id=exp.id).first():
            notes.append('후기 이미 있음: %s' % nickname)
            continue
        if not dry_run:
            db.session.add(Review(user_id=user.id, experience_id=exp.id,
                                  rating=rating, content=content,
                                  timestamp=datetime.now() - timedelta(days=days)))
        notes.append('후기 생성: %s (별점 %d)' % (nickname, rating))

    _row, created = _completed_application(main_user, exp, MAIN_VISIT_DAYS_AGO, dry_run)
    notes.append('대표 계정 완료 예약 %s (레시피 버튼 확인용, 후기는 직접 작성)'
                 % ('생성' if created else '이미 있음'))
    return notes


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


def _ensure_experience(farmer, farm, spec, dry_run, notes):
    """체험 하나를 만들거나, 심사 기간에 마감되지 않게 기한만 밀어 둔다."""
    today = date.today()
    deadline = today + timedelta(days=180)
    exp = (Experience.query.filter_by(farmer_id=farmer.id, crop=spec['crop']).first()
           if farmer.id else None)
    if exp is None:
        if not dry_run:
            db.session.add(Experience(farmer=farmer, farm=farm,
                                      duration_start=today, end_date=deadline, **spec))
        notes.append('체험 생성: %s (모집중, 마감 %s)' % (spec['crop'], deadline))
        return
    changed = False
    if exp.end_date is None or exp.end_date < today + timedelta(days=90):
        if not dry_run:
            exp.end_date = deadline
        notes.append('체험 마감일 연장: %s → %s' % (spec['crop'], deadline))
        changed = True
    if exp.status != 'recruiting':
        if not dry_run:
            exp.status = 'recruiting'
        notes.append('체험 상태를 recruiting 으로 변경: %s' % spec['crop'])
        changed = True
    if not changed:
        notes.append('체험 이미 있음: %s (모집중)' % spec['crop'])


def ensure_farm_and_experience(farmer, dry_run):
    """농장주에게 ★승인된 농장★과 ★모집 중인 체험★이 있게 한다.

    농장주로 전환했을 때 빈 화면이면 기능 확인이 안 된다.
    과생산 체험도 함께 둬서 할인 리본·수량 기능까지 보이게 한다.
    """
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

    _ensure_experience(farmer, farm, EXPERIENCE, dry_run, notes)
    _ensure_experience(farmer, farm, SURPLUS_EXPERIENCE, dry_run, notes)
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

        farm_notes = []
        for email in FARM_OWNER_EMAILS:
            farm_notes.append('--- %s ---' % email)
            farm_notes += ensure_farm_and_experience(users[email], dry_run)
        if not dry_run:
            db.session.flush()      # 체험 id 가 있어야 후기·예약을 붙일 수 있다
        farm_notes.append('--- 후기·완료 예약 ---')
        farm_notes += ensure_reviews(users[MAIN_EMAIL], dry_run)

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
