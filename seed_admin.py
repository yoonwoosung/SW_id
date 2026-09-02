#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""배포 DB(PythonAnywhere MySQL)에 시드 계정을 생성한다.

실행:
    cd ~/SW_id
    python3 seed_admin.py                      # 비밀번호를 입력 프롬프트로 받음
    ADMIN_PASSWORD='...' python3 seed_admin.py # 비대화식(스크립트/CI)

특징:
    - 비밀번호를 소스에 남기지 않는다. 이 저장소는 public 이므로 하드코딩 금지.
    - 이메일(User.email 은 unique)로 존재 여부를 먼저 확인해 중복 생성하지 않는다.
    - 모든 작업은 app.app_context() 안에서 수행하고, 실패하면 전체 롤백한다.

주의: app.py 의 db.create_all() 은 `if __name__ == '__main__':` 블록 안에 있어
      WSGI 구동 시 실행되지 않는다. 테이블이 없으면 이 스크립트가 안내 후 종료한다.
"""
import os
import sys
import getpass

# app.py 는 import 시점에 load_dotenv() 로 .env 를 읽고 db.init_app(app) 까지 끝낸다.
# 따라서 app 을 먼저 import 해야 db 세션이 앱에 바인딩된 상태가 된다.
# db / User 는 app.py:48 의 `from models import db, User, ...` 로 이미 재노출되어 있다.
from app import app, db, User
from werkzeug.security import generate_password_hash
from sqlalchemy.exc import SQLAlchemyError

# routes/auth.py:55 와 반드시 동일해야 한다.
# 로그인 검증(routes/auth.py:119 check_password_hash)이 이 해시를 읽는다.
HASH_METHOD = 'pbkdf2:sha256'

MIN_PASSWORD_LENGTH = 8

# 생성할 계정 목록.
# User 모델(models/user.py)에서 nullable=False 인 컬럼은 nickname/email/password/name 뿐이고
# 나머지(profile_image='shd.png', verification_status='verified' 등)는 모델 기본값을 쓴다.
SEED_ACCOUNTS = [
    {
        'email': 'admin@farmlink.com',
        'nickname': '관리자',
        'name': '관리자',
        # 참고: 현재 코드베이스에는 role == 'admin' 분기나 관리자 전용 라우트가 없다.
        # 로그인은 정상 동작하지만 화면상 권한은 일반 체험자와 동일하다.
        # 관리자 기능을 붙일 때를 대비한 자리표시 역할이다.
        'role': 'admin',
        'phone': '010-0000-0000',
        'password_env': 'ADMIN_PASSWORD',
        'prompt': '관리자(admin@farmlink.com) 비밀번호',
    },
    {
        'email': 'farmer@farmlink.com',
        'nickname': '관리농장',
        'name': '관리자농장주',
        # role='farmer' 는 이 코드베이스에서 실제로 추가 권한이 있는 유일한 역할이다.
        # (routes/auth.py:136 → 로그인 시 농장주 대시보드로 이동)
        'role': 'farmer',
        'phone': '010-0000-0000',
        'password_env': 'FARMER_PASSWORD',
        'prompt': '농장주(farmer@farmlink.com) 비밀번호',
    },
]


def fail(message):
    """오류 메시지를 출력하고 종료 코드 1로 끝낸다."""
    print("[seed] 오류: %s" % message, file=sys.stderr)
    sys.exit(1)


def read_password(env_key, prompt, fallback=None):
    """비밀번호를 환경변수 → 입력 프롬프트 → fallback 순으로 확보한다.

    소스에 비밀번호를 남기지 않기 위한 함수다. 반환값은 (평문, 출처설명).
    """
    value = os.environ.get(env_key)
    if value:
        if len(value) < MIN_PASSWORD_LENGTH:
            fail("환경변수 %s 가 너무 짧다 (최소 %d자)" % (env_key, MIN_PASSWORD_LENGTH))
        return value, "환경변수 %s" % env_key

    if fallback is not None:
        return fallback, "관리자 비밀번호와 동일"

    if not sys.stdin.isatty():
        fail(
            "환경변수 %s 가 없고 입력을 받을 터미널도 없다.\n"
            "        해결: %s='원하는비밀번호' python3 seed_admin.py" % (env_key, env_key)
        )

    while True:
        first = getpass.getpass("%s 입력: " % prompt)
        if len(first) < MIN_PASSWORD_LENGTH:
            print("  최소 %d자 이상이어야 한다. 다시 입력." % MIN_PASSWORD_LENGTH)
            continue
        second = getpass.getpass("  확인을 위해 다시 입력: ")
        if first != second:
            print("  두 입력이 다르다. 다시 입력.")
            continue
        return first, "직접 입력"


def ensure_tables_exist():
    """DB에 접속해 테이블 존재를 확인한다. 접속 실패/테이블 없음이면 원인을 알려주고 종료한다."""
    try:
        table_names = db.inspect(db.engine).get_table_names()
    except SQLAlchemyError as exc:
        # 서버에서 가장 흔한 실패: .env 의 DB_* 값이 비었거나 틀린 경우.
        # 원시 traceback 대신 확인할 지점을 알려준다.
        fail(
            "DB 접속 실패. .env 의 DB_USERNAME/DB_PASSWORD/DB_HOST/DB_NAME 을 확인할 것.\n"
            "        PythonAnywhere Databases 탭의 호스트/DB이름과 정확히 일치해야 한다.\n"
            "        원인: %s" % str(exc).splitlines()[0]
        )
    if 'user' not in table_names:
        fail(
            "DB에 'user' 테이블이 없다. 먼저 테이블을 생성할 것.\n"
            "        python3 -c \"from app import app, db; \\\n"
            "                     app.app_context().push(); db.create_all()\""
        )
    return table_names


def main():
    with app.app_context():
        # 접속 대상을 먼저 보여준다. 실수로 로컬 DB에 시드하는 것을 막기 위함.
        # hide_password=True 로 비밀번호가 로그/터미널에 남지 않게 한다.
        print("[seed] 대상 DB: %s" % db.engine.url.render_as_string(hide_password=True))

        ensure_tables_exist()

        admin_password = None
        created, skipped = [], []

        for spec in SEED_ACCOUNTS:
            email = spec['email']

            # User.email 은 unique=True (models/user.py:8) 이므로 이메일로 중복을 판정한다.
            existing = User.query.filter_by(email=email).first()
            if existing:
                skipped.append((email, existing.id, existing.role))
                continue

            # 농장주 비밀번호는 별도 환경변수가 없으면 관리자 것을 재사용한다(입력 1회로 끝내기 위함).
            fallback = admin_password if spec['role'] != 'admin' else None
            plain, source = read_password(spec['password_env'], spec['prompt'], fallback)
            if spec['role'] == 'admin':
                admin_password = plain

            db.session.add(User(
                email=email,
                nickname=spec['nickname'],
                name=spec['name'],
                role=spec['role'],
                phone=spec['phone'],
                password=generate_password_hash(plain, method=HASH_METHOD),
            ))
            created.append((email, spec['role'], source))

        if not created:
            print("[seed] 새로 만들 계정이 없다.")
        else:
            try:
                db.session.commit()
            except Exception as exc:
                db.session.rollback()
                fail("커밋 실패, 전체 롤백함: %s" % exc)

        for email, role, source in created:
            user = User.query.filter_by(email=email).first()
            print("[seed] 생성  %-22s role=%-11s id=%-4s (비밀번호 출처: %s)" % (email, role, user.id, source))
        for email, user_id, role in skipped:
            print("[seed] 건너뜀 %-22s role=%-11s id=%-4s (이미 존재)" % (email, role, user_id))

        print("[seed] 완료. 생성 %d건 / 건너뜀 %d건" % (len(created), len(skipped)))


if __name__ == '__main__':
    main()
