#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""배포 서버 초기화·진단 한 방 스크립트.

배포 후 500이 나면 대개 아래 셋 중 하나다. 이 스크립트가 순서대로 확인하고 고친다.
    1) .env 값이 틀려 DB에 못 붙는다
    2) 테이블이 없다                      → db.create_all()
    3) approval_status 컬럼이 없다        → migrate_approval.py 미실행
       (증상: 메인/관리자 페이지가 전부 500,
        로그에 Unknown column 'experience.approval_status')

실행:
    cd ~/SW_id
    python3 deploy_setup.py            # 진단 + 자동 수리 (반복 실행 안전)
    python3 deploy_setup.py --seed     # + 관리자 계정까지 생성
    python3 deploy_setup.py --check    # 진단만, 아무것도 바꾸지 않음

끝나면 PythonAnywhere Web 탭에서 반드시 Reload 를 누를 것.
"""
import sys

from sqlalchemy.exc import SQLAlchemyError

from app import app, db

REQUIRED_COLUMNS = ('approval_status', 'approval_note', 'approved_at')


def line(label, ok, detail=''):
    print("  [%s] %-34s %s" % ('OK' if ok else '!!', label, detail))
    return ok


def diagnose():
    """현재 DB 상태를 조사해 (문제요약, 상세) 를 돌려준다. 아무것도 바꾸지 않는다."""
    problems = []

    try:
        inspector = db.inspect(db.engine)
        tables = inspector.get_table_names()
    except SQLAlchemyError as exc:
        line("DB 접속", False, str(exc).splitlines()[0])
        print("\n  → .env 의 DB_USERNAME/DB_PASSWORD/DB_HOST/DB_NAME 을 확인할 것.")
        print("    PythonAnywhere Databases 탭의 값과 정확히 일치해야 한다.")
        sys.exit(1)

    line("DB 접속", True, db.engine.url.render_as_string(hide_password=True))

    has_experience = 'experience' in tables
    line("테이블 존재", has_experience, "총 %d개" % len(tables))
    if not has_experience:
        problems.append('tables')
        return problems, set()

    columns = {c['name'] for c in inspector.get_columns('experience')}
    missing = set(REQUIRED_COLUMNS) - columns
    line("승인 컬럼", not missing,
         "없음: %s" % ", ".join(sorted(missing)) if missing else "3개 모두 존재")
    if missing:
        problems.append('columns')

    from models import User
    try:
        admin_count = User.query.filter_by(role='admin').count()
    except SQLAlchemyError:
        admin_count = 0
    line("관리자 계정", admin_count > 0, "%d개" % admin_count)
    if admin_count == 0:
        problems.append('admin')

    return problems, missing


def main():
    check_only = '--check' in sys.argv
    do_seed = '--seed' in sys.argv

    with app.app_context():
        print("\n── 진단 ──")
        problems, _ = diagnose()

        if check_only:
            print("\n  --check 모드라 아무것도 바꾸지 않았다.")
            print("  발견된 문제: %s" % (", ".join(problems) or "없음"))
            return

        if 'tables' in problems:
            print("\n── 테이블 생성 ──")
            db.create_all()
            print("  db.create_all() 완료")

        # 컬럼 추가·백필은 migrate_approval 에 위임한다(로직 중복 방지).
        print("\n── 마이그레이션 ──")
        import migrate_approval
        migrate_approval.main()

        if do_seed:
            print("\n── 관리자 계정 ──")
            import seed_admin
            seed_admin.main()
        elif 'admin' in problems:
            print("\n  관리자 계정이 없다. 만들려면: python3 deploy_setup.py --seed")

        print("\n── 최종 확인 ──")
        remaining, _ = diagnose()

    if remaining and remaining != ['admin']:
        print("\n  아직 문제가 남았다: %s" % ", ".join(remaining))
        sys.exit(1)

    print("\n  ★ 마지막으로 PythonAnywhere Web 탭에서 Reload 를 누를 것.")
    print("    Reload 하지 않으면 이전 코드가 계속 돌아 증상이 그대로다.\n")


if __name__ == '__main__':
    main()
