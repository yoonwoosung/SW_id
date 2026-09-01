#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""experience 테이블에 관리자 승인 컬럼을 추가하는 마이그레이션.

실행:
    cd ~/SW_id
    python3 migrate_approval.py

이 프로젝트에는 alembic이 설정되어 있지 않아 수동 ALTER TABLE로 처리한다.

★ 핵심: 모델 기본값은 'pending'이지만, 기존 농장까지 pending이 되면
  이미 서비스 중인 농장이 전부 목록에서 사라진다.
  그래서 컬럼 추가 직후 기존 행을 전부 'approved'로 backfill한다.
  (이 스크립트 실행 이후 새로 등록되는 농장만 'pending'으로 들어간다.)

멱등: 이미 컬럼이 있으면 추가를 건너뛴다. 여러 번 실행해도 안전하다.
      단 backfill은 '컬럼을 이번에 새로 만든 경우'에만 수행하므로,
      나중에 관리자가 거절해 둔 농장을 되살리지 않는다.
"""
import sys

from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError

from app import app, db

TABLE = 'experience'

# (컬럼명, MySQL DDL 조각). SQLite에서도 동일 구문으로 동작한다.
NEW_COLUMNS = [
    ('approval_status', "VARCHAR(20) NOT NULL DEFAULT 'pending'"),
    ('approval_note', "VARCHAR(255) NULL"),
    ('approved_at', "DATETIME NULL"),
]


def fail(message):
    print("[migrate] 오류: %s" % message, file=sys.stderr)
    sys.exit(1)


def main():
    with app.app_context():
        print("[migrate] 대상 DB: %s" % db.engine.url.render_as_string(hide_password=True))

        try:
            inspector = db.inspect(db.engine)
            table_names = inspector.get_table_names()
        except SQLAlchemyError as exc:
            fail("DB 접속 실패. .env 의 DB_* 값을 확인할 것.\n        원인: %s"
                 % str(exc).splitlines()[0])

        if TABLE not in table_names:
            fail("'%s' 테이블이 없다. 먼저 db.create_all() 로 테이블을 만들 것." % TABLE)

        existing = {c['name'] for c in inspector.get_columns(TABLE)}
        added = []

        for name, ddl in NEW_COLUMNS:
            if name in existing:
                print("[migrate] 건너뜀 %-16s (이미 존재)" % name)
                continue
            try:
                with db.engine.begin() as conn:
                    conn.execute(text("ALTER TABLE %s ADD COLUMN %s %s" % (TABLE, name, ddl)))
            except SQLAlchemyError as exc:
                fail("컬럼 %s 추가 실패: %s" % (name, str(exc).splitlines()[0]))
            added.append(name)
            print("[migrate] 추가   %-16s %s" % (name, ddl))

        # ★ 기존 데이터 보호: approval_status를 이번에 새로 만들었을 때만 backfill.
        if 'approval_status' in added:
            with db.engine.begin() as conn:
                result = conn.execute(text(
                    "UPDATE %s SET approval_status = 'approved'" % TABLE))
            print("[migrate] backfill 기존 농장 %s건을 'approved'로 설정 (노출 유지)"
                  % result.rowcount)
        elif added:
            print("[migrate] approval_status는 이미 있었으므로 backfill하지 않음.")

        if not added:
            print("[migrate] 변경 사항 없음. 이미 마이그레이션된 DB다.")

        # 결과 확인
        with db.engine.begin() as conn:
            rows = conn.execute(text(
                "SELECT approval_status, COUNT(*) FROM %s GROUP BY approval_status" % TABLE)).all()
        print("[migrate] 현재 승인 상태 분포: %s"
              % (", ".join("%s=%s" % (r[0], r[1]) for r in rows) or "(농장 없음)"))
        print("[migrate] 완료.")


if __name__ == '__main__':
    main()
