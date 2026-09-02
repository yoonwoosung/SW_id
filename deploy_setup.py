#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""배포 서버 초기화·진단 스크립트.

배포 후 문제가 나면 대개 아래 셋 중 하나다. 순서대로 확인하고 고친다.
    1) .env 값이 틀려 DB에 못 붙는다
    2) 테이블이 없다            → db.create_all()
    3) 관리자 계정이 없다        → seed_admin.py

실행:
    cd ~/SW_id
    python3 deploy_setup.py            # 진단 + 자동 수리 (반복 실행 안전)
    python3 deploy_setup.py --seed     # + 관리자 계정까지 생성
    python3 deploy_setup.py --check    # 진단만, 아무것도 바꾸지 않음

끝나면 PythonAnywhere Web 탭에서 반드시 Reload 를 누를 것.

참고: 농장 승인은 Farm.status(PENDING/APPROVED/REJECTED)로 동작하며
      관리자 화면은 /admin/farms/audit 이다(routes/admin.py).
"""
import sys

from sqlalchemy.exc import SQLAlchemyError

from app import app, db

# 앱이 동작하는 데 반드시 있어야 하는 테이블.
CORE_TABLES = ('user', 'experience', 'farm', 'application')


def line(label, ok, detail=''):
    print("  [%s] %-30s %s" % ('OK' if ok else '!!', label, detail))
    return ok


def diagnose():
    """DB 상태를 조사해 문제 목록을 돌려준다. 아무것도 바꾸지 않는다."""
    problems = []

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

    with app.app_context():
        print("\n── 진단 ──")
        problems = diagnose()

        if check_only:
            print("\n  --check 모드라 아무것도 바꾸지 않았다.")
            print("  발견된 문제: %s" % (", ".join(problems) or "없음"))
            return

        if 'tables' in problems:
            print("\n── 테이블 생성 ──")
            db.create_all()
            print("  db.create_all() 완료")

        if do_seed:
            print("\n── 관리자 계정 ──")
            import seed_admin
            seed_admin.main()
        elif 'admin' in problems:
            print("\n  관리자 계정이 없다. 만들려면: python3 deploy_setup.py --seed")

        print("\n── 최종 확인 ──")
        remaining = diagnose()

    blocking = [p for p in remaining if p != 'admin']
    if blocking:
        print("\n  아직 문제가 남았다: %s" % ", ".join(blocking))
        sys.exit(1)

    print("\n  ★ 마지막으로 PythonAnywhere Web 탭에서 Reload 를 누를 것.")
    print("    Reload 하지 않으면 이전 코드가 계속 돌아 증상이 그대로다.\n")


if __name__ == '__main__':
    main()
