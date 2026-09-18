"""services/surplus_service 테스트 — 과생산 수량 차감·복원.

핵심은 조건부 원자 UPDATE 다. 조회→검증→차감으로 쓰면 그 사이에
다른 요청이 끼어들어 재고를 넘길 수 있다.
"""
import os

os.environ.setdefault('SECRET_KEY', 'test-secret')
os.environ.setdefault('DB_USERNAME', 'x')
os.environ.setdefault('DB_PASSWORD', 'x')
os.environ.setdefault('DB_HOST', 'localhost')
os.environ.setdefault('DB_NAME', 'x')

from datetime import date, timedelta

import pytest
from sqlalchemy import create_engine
from sqlalchemy.pool import StaticPool

import app as app_module
from services import surplus_service

flask_app = app_module.app
db = app_module.db
Experience = app_module.Experience


@pytest.fixture
def ctx():
    flask_app.config['TESTING'] = True
    with flask_app.app_context():
        flask_app.extensions['sqlalchemy'].engines[None] = create_engine(
            'sqlite://', connect_args={'check_same_thread': False}, poolclass=StaticPool)
        db.create_all()
        yield
        db.session.remove()
        db.drop_all()


def make(qty_total=500, per_person=5, taken=0, is_surplus=True):
    exp = Experience(
        crop='과생산딸기', location='충남', address_detail='충남 논산시',
        cost=25000, farmer_id=1, status='recruiting',
        max_participants=100, current_participants=0,
        duration_start=date.today(), end_date=date.today() + timedelta(days=30),
        is_surplus=is_surplus, surplus_terms_agreed=is_surplus, list_price=50000,
        surplus_qty_total=qty_total, surplus_per_person=per_person,
        surplus_qty_taken=taken, surplus_unit='kg',
    )
    db.session.add(exp)
    db.session.commit()
    return exp


# ---- 판정 ----

def test_is_surplus_true(ctx):
    assert surplus_service.is_surplus(make()) is True


def test_is_surplus_false_for_normal(ctx):
    exp = make(is_surplus=False)
    exp.surplus_qty_total = None
    exp.surplus_per_person = None
    db.session.commit()
    assert surplus_service.is_surplus(exp) is False


def test_is_surplus_needs_all_values(ctx):
    """플래그만 켜고 수량이 없으면 수량 관리를 하지 않는다."""
    exp = make()
    exp.surplus_per_person = None
    db.session.commit()
    assert surplus_service.is_surplus(exp) is False


def test_is_surplus_handles_none(ctx):
    assert surplus_service.is_surplus(None) is False


# ---- 계산 ----

def test_required_qty(ctx):
    exp = make(per_person=5)
    assert surplus_service.required_qty(exp, 3) == 15


def test_required_qty_zero_for_normal(ctx):
    exp = make(is_surplus=False)
    exp.surplus_qty_total = None
    db.session.commit()
    assert surplus_service.required_qty(exp, 3) == 0


def test_remaining(ctx):
    assert surplus_service.remaining(make(qty_total=500, taken=15)) == 485


def test_remaining_none_for_normal(ctx):
    exp = make(is_surplus=False)
    exp.surplus_qty_total = None
    db.session.commit()
    assert surplus_service.remaining(exp) is None


# ---- 차감 ----

def test_take_deducts(ctx):
    """★3명 예약 → 5kg×3 = 15kg 차감 → 500 중 485 남음.★"""
    exp = make(qty_total=500, per_person=5)
    assert surplus_service.take(exp, 3) is True
    db.session.commit()
    assert exp.surplus_qty_taken == 15
    assert surplus_service.remaining(exp) == 485


def test_take_exact_last_portion(ctx):
    exp = make(qty_total=15, per_person=5)
    assert surplus_service.take(exp, 3) is True
    db.session.commit()
    assert surplus_service.remaining(exp) == 0


def test_take_over_stock_rejected(ctx):
    """재고를 넘으면 차감하지 않고 False."""
    exp = make(qty_total=10, per_person=5)
    assert surplus_service.take(exp, 3) is False
    db.session.commit()
    assert exp.surplus_qty_taken == 0, "실패했는데 차감되면 안 된다"


def test_take_passes_through_for_normal(ctx):
    exp = make(is_surplus=False)
    exp.surplus_qty_total = None
    db.session.commit()
    assert surplus_service.take(exp, 3) is True


def test_take_accumulates(ctx):
    exp = make(qty_total=100, per_person=5)
    surplus_service.take(exp, 2)   # 10
    surplus_service.take(exp, 3)   # 15
    db.session.commit()
    assert exp.surplus_qty_taken == 25 and surplus_service.remaining(exp) == 75


# ---- 동시성 (조건부 원자 UPDATE) ----

def test_concurrent_take_does_not_oversell(ctx):
    """★재고 15kg(3명분)에 3명씩 두 번 — 하나만 성공해야 한다.★

    조회→검증→차감 구조였다면 둘 다 통과해 재고를 넘겼을 것이다.
    조건을 UPDATE 에 실었으므로 두 번째는 rowcount 0 으로 막힌다.
    """
    exp = make(qty_total=15, per_person=5)
    first = surplus_service.take(exp, 3)
    second = surplus_service.take(exp, 3)
    db.session.commit()
    assert first is True
    assert second is False, "재고를 넘겨 팔렸다"
    assert exp.surplus_qty_taken == 15
    assert surplus_service.remaining(exp) == 0


def test_never_exceeds_total(ctx):
    exp = make(qty_total=100, per_person=5)
    ok = sum(1 for _ in range(30) if surplus_service.take(exp, 1))
    db.session.commit()
    assert ok == 20, "100 ÷ 5 = 20 번만 성공해야 한다"
    assert exp.surplus_qty_taken <= 100


# ---- 복원 ----

def test_restore_gives_back(ctx):
    """★복원을 빠뜨리면 재고가 샌다 — 취소해도 수량이 안 돌아온다.★"""
    exp = make(qty_total=500, per_person=5)
    surplus_service.take(exp, 3)
    db.session.commit()
    assert exp.surplus_qty_taken == 15

    surplus_service.restore(exp, 3)
    db.session.commit()
    assert exp.surplus_qty_taken == 0
    assert surplus_service.remaining(exp) == 500


def test_restore_partial(ctx):
    exp = make(qty_total=500, per_person=5, taken=50)
    surplus_service.restore(exp, 4)   # 20 되돌림
    db.session.commit()
    assert exp.surplus_qty_taken == 30


def test_restore_never_negative(ctx):
    """중복 복원이 와도 0 밑으로 내려가지 않는다."""
    exp = make(qty_total=500, per_person=5, taken=10)
    surplus_service.restore(exp, 5)   # 25 되돌리려 하지만 10 밖에 없다
    db.session.commit()
    assert exp.surplus_qty_taken == 0


def test_restore_noop_for_normal(ctx):
    exp = make(is_surplus=False)
    exp.surplus_qty_total = None
    db.session.commit()
    surplus_service.restore(exp, 3)   # 예외 없이 통과
    db.session.commit()


def test_take_then_restore_roundtrip(ctx):
    exp = make(qty_total=500, per_person=5)
    for _ in range(5):
        surplus_service.take(exp, 2)
    db.session.commit()
    assert exp.surplus_qty_taken == 50
    for _ in range(5):
        surplus_service.restore(exp, 2)
    db.session.commit()
    assert exp.surplus_qty_taken == 0
