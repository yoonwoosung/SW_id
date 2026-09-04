#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""배포 서버 초기화·진단 스크립트.

배포 후 문제가 나면 대개 아래 셋 중 하나다. 순서대로 확인하고 고친다.
    1) SECRET_KEY 가 비어 로그인·flash 가 전부 500 난다
    2) .env 값이 틀려 DB에 못 붙는다
    3) 테이블이 없다                → db.create_all()
    4) 테이블은 있는데 컬럼이 없다     → ALTER TABLE ADD COLUMN (아래 sync_missing_columns)
       db.create_all() 은 "없는 테이블"만 만들고 기존 테이블에 컬럼을 더하지 않는다.
       팀원이 모델에 컬럼을 추가하면 배포 DB에는 반영되지 않아
       Unknown column '...' in 'field list' 로 터진다.
    5) 관리자 계정이 없다           → seed_admin.py

실행:
    cd ~/SW_id
    python3 deploy_setup.py            # 진단 + 자동 수리 (반복 실행 안전)
    python3 deploy_setup.py --seed     # + 관리자 계정까지 생성
    python3 deploy_setup.py --check    # 진단만, 아무것도 바꾸지 않음
    python3 deploy_setup.py --check-toss  # 토스 키 형식·인증만 점검(네트워크 사용)

끝나면 PythonAnywhere Web 탭에서 반드시 Reload 를 누를 것.

참고: 농장 승인은 Farm.status(PENDING/APPROVED/REJECTED)로 동작하며
      관리자 화면은 /admin/farms/audit 이다(routes/admin.py).
"""
import os
import sys

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import app, db

# 앱이 동작하는 데 반드시 있어야 하는 테이블.
CORE_TABLES = ('user', 'experience', 'farm', 'application')


def _column_ddl(column):
    """모델 컬럼 하나를 ADD COLUMN DDL 조각으로 만든다.

    기존 행이 이미 있으므로 NOT NULL 은 위험하다. 상수 기본값이 있을 때만
    NOT NULL DEFAULT 로 붙이고, 그 외에는 NULL 허용으로 추가한다.
    (모델 쪽 nullable=False 는 애플리케이션이 값을 채워주므로 실사용에 문제없다.)
    """
    type_sql = column.type.compile(db.engine.dialect)

    default = None
    if column.default is not None and not getattr(column.default, 'is_callable', False):
        arg = getattr(column.default, 'arg', None)
        if isinstance(arg, bool):
            default = '1' if arg else '0'
        elif isinstance(arg, (int, float)):
            default = str(arg)
        elif isinstance(arg, str):
            default = "'%s'" % arg.replace("'", "''")

    if not column.nullable and default is not None:
        return "%s NOT NULL DEFAULT %s" % (type_sql, default), None
    if not column.nullable:
        # 기본값을 만들 수 없는 NOT NULL — 기존 행 때문에 그대로는 못 넣는다.
        return "%s NULL" % type_sql, 'NOT NULL 이지만 기본값이 없어 NULL 허용으로 추가함'
    if default is not None:
        return "%s NULL DEFAULT %s" % (type_sql, default), None
    return "%s NULL" % type_sql, None


def sync_missing_columns():
    """모델에는 있고 DB 테이블에는 없는 컬럼을 ADD COLUMN 한다. 삭제·변경은 절대 하지 않는다."""
    inspector = db.inspect(db.engine)
    existing_tables = set(inspector.get_table_names())
    added, notes = [], []

    for table_name, table in db.metadata.tables.items():
        if table_name not in existing_tables:
            continue                                  # 테이블 자체가 없으면 create_all 담당
        db_columns = {c['name'] for c in inspector.get_columns(table_name)}

        for column in table.columns:
            if column.name in db_columns:
                continue
            ddl, note = _column_ddl(column)
            quoted = db.engine.dialect.identifier_preparer.quote(column.name)
            try:
                with db.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE %s ADD COLUMN %s %s"
                                      % (table_name, quoted, ddl)))
            except SQLAlchemyError as exc:
                notes.append("  !! %s.%s 추가 실패: %s"
                             % (table_name, column.name, str(exc).splitlines()[0]))
                continue
            added.append("%s.%s" % (table_name, column.name))
            if note:
                notes.append("  -- %s.%s: %s" % (table_name, column.name, note))

    return added, notes


def check_toss_keys():
    """토스 키의 형식과 인증을 점검한다. 네트워크를 쓰므로 --check-toss 일 때만 호출.

    결제위젯 SDK 는 '결제위젯 연동 키'(test_gck_/test_gsk_)만 받는다.
    'API 개별 연동 키'(test_ck_/test_sk_)를 넣으면 결제창이 아예 열리지 않는다.
    두 키를 서로 다른 세트에서 가져오면 결제창은 열리지만 서버 승인이 401 로 실패한다.
    """
    import base64
    import requests

    client = os.environ.get('TOSS_CLIENT_KEY') or ''
    secret = os.environ.get('TOSS_SECRET_KEY') or ''

    line("TOSS_CLIENT_KEY", bool(client), client[:9] + "…" if client else "비어 있음")
    line("TOSS_SECRET_KEY", bool(secret), secret[:9] + "…" if secret else "비어 있음")
    if not client or not secret:
        print("\n  → 개발자센터 > API 키 > '결제위젯 연동 키' 의 테스트 키를 넣을 것.")
        return False

    # 접두사로 키 세트를 판별한다.
    client_widget = client.startswith(('test_gck_', 'gck_'))
    secret_widget = secret.startswith(('test_gsk_', 'gsk_'))

    line("클라이언트 키 종류", client_widget,
         "결제위젯 연동 키" if client_widget else "API 개별 연동 키 → 위젯이 안 열린다")
    line("시크릿 키 종류", secret_widget,
         "결제위젯 연동 키" if secret_widget else "API 개별 연동 키 → 승인이 401 로 실패한다")
    line("두 키가 같은 세트", client_widget == secret_widget,
         "일치" if client_widget == secret_widget else "★ 서로 다른 세트 — 반드시 같은 세트로 맞출 것")

    # 시크릿 키로 실제 인증만 확인한다(더미 주문이라 승인은 어차피 실패한다).
    # 401 이면 키가 틀린 것이고, 400/404 면 인증은 통과한 것이다.
    try:
        token = base64.b64encode(("%s:" % secret).encode()).decode()
        res = requests.post('https://api.tosspayments.com/v1/payments/confirm',
                            json={'paymentKey': 'diagnostic', 'orderId': 'diagnostic', 'amount': 1},
                            headers={'Authorization': 'Basic %s' % token,
                                     'Content-Type': 'application/json'},
                            timeout=10)
    except Exception as exc:
        line("시크릿 키 인증", False, "토스 연결 실패: %s" % exc)
        return False

    authed = res.status_code != 401
    detail = "인증 통과 (HTTP %d — 더미 주문이라 승인 자체는 실패가 정상)" % res.status_code
    if not authed:
        try:
            detail = "401 인증 실패: %s" % (res.json().get('message') or '')
        except ValueError:
            detail = "401 인증 실패"
    line("시크릿 키 인증", authed, detail)
    return authed and client_widget and secret_widget


def line(label, ok, detail=''):
    print("  [%s] %-30s %s" % ('OK' if ok else '!!', label, detail))
    return ok


def diagnose():
    """DB 상태를 조사해 문제 목록을 돌려준다. 아무것도 바꾸지 않는다."""
    problems = []

    # SECRET_KEY 는 DB보다 먼저 본다. 비어 있으면 세션이 아예 동작하지 않아
    # 로그인·flash 가 전부 500 나는데, 증상만으로는 원인을 찾기 어렵다.
    secret_ok = bool(app.secret_key)
    line("SECRET_KEY", secret_ok,
         "설정됨(%d자)" % len(app.secret_key) if secret_ok
         else ".env 의 SECRET_KEY 가 비어 있다 → 로그인이 전부 500")
    if not secret_ok:
        problems.append('secret')

    try:
        inspector = db.inspect(db.engine)
        tables = set(inspector.get_table_names())
    except SQLAlchemyError as exc:
        line("DB 접속", False, str(exc).splitlines()[0])
        print("\n  → .env 의 DB_USERNAME/DB_PASSWORD/DB_HOST/DB_NAME 을 확인할 것.")
        print("    PythonAnywhere Databases 탭의 값과 정확히 일치해야 한다.")
        sys.exit(1)

    line("DB 접속", True, db.engine.url.render_as_string(hide_password=True))

    missing = [t for t in CORE_TABLES if t not in tables]
    line("핵심 테이블", not missing,
         "없음: %s" % ", ".join(missing) if missing else "%d개 존재" % len(tables))
    if missing:
        problems.append('tables')
        return problems

    # 모델 대비 빠진 컬럼 점검 — 이게 있으면 조회할 때 Unknown column 으로 터진다.
    missing = []
    for table_name, table in db.metadata.tables.items():
        if table_name not in tables:
            continue
        db_cols = {c['name'] for c in inspector.get_columns(table_name)}
        missing += ["%s.%s" % (table_name, c.name) for c in table.columns if c.name not in db_cols]
    line("모델 대비 컬럼", not missing,
         "누락 %d개: %s" % (len(missing), ", ".join(missing[:4]) + ("…" if len(missing) > 4 else ""))
         if missing else "누락 없음")
    if missing:
        problems.append('columns')
        return problems          # 컬럼이 없으면 아래 모델 조회가 반드시 실패한다

    from models import User, Farm
    try:
        admin_count = User.query.filter_by(role='admin').count()
        pending = Farm.query.filter_by(status='PENDING').count()
    except SQLAlchemyError as exc:
        line("모델 조회", False, str(exc).splitlines()[0])
        problems.append('schema')
        return problems

    line("관리자 계정", admin_count > 0, "%d개" % admin_count)
    if admin_count == 0:
        problems.append('admin')

    line("승인 대기 농장", True, "%d건 (/admin/farms/audit 에서 처리)" % pending)
    return problems


def main():
    check_only = '--check' in sys.argv
    do_seed = '--seed' in sys.argv

    if '--check-toss' in sys.argv:
        print("\n── 토스 키 점검 ──")
        ok = check_toss_keys()
        print("\n  결과: %s" % ("정상" if ok else "문제 있음 — 위 항목 확인"))
        sys.exit(0 if ok else 1)

    with app.app_context():
        print("\n── 진단 ──")
        problems = diagnose()

        if check_only:
            print("\n  --check 모드라 아무것도 바꾸지 않았다.")
            print("  발견된 문제: %s" % (", ".join(problems) or "없음"))
            # 진단 전용 모드도 문제가 있으면 0이 아닌 코드로 끝낸다(스크립트에서 쓰기 위함).
            sys.exit(1 if problems else 0)

        if 'tables' in problems:
            print("\n── 테이블 생성 ──")
            db.create_all()
            print("  db.create_all() 완료")

        print("\n── 컬럼 동기화 ──")
        added, notes = sync_missing_columns()
        if added:
            for name in added:
                print("  추가  %s" % name)
        else:
            print("  추가할 컬럼 없음")
        for note in notes:
            print(note)

        if do_seed:
            print("\n── 관리자 계정 ──")
            import seed_admin
            seed_admin.main()
        elif 'admin' in problems:
            print("\n  관리자 계정이 없다. 만들려면: python3 deploy_setup.py --seed")

        print("\n── 최종 확인 ──")
        remaining = diagnose()

    if 'secret' in remaining:
        print("\n  ★ .env 의 SECRET_KEY 를 채울 것. 이게 비면 로그인이 동작하지 않는다.")
        print("    python3 -c \"import secrets; print(secrets.token_hex(32))\"")

    blocking = [p for p in remaining if p != 'admin']
    if blocking:
        print("\n  아직 문제가 남았다: %s" % ", ".join(blocking))
        sys.exit(1)

    print("\n  ★ 마지막으로 PythonAnywhere Web 탭에서 Reload 를 누를 것.")
    print("    Reload 하지 않으면 이전 코드가 계속 돌아 증상이 그대로다.\n")


if __name__ == '__main__':
    main()
