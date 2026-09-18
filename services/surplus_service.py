# services/surplus_service.py — 과생산 체험의 수량 차감·복원.
#
# 왜 조건부 원자 UPDATE 인가:
# 조회 → 검증 → 차감 순서로 쓰면 그 사이에 다른 요청이 끼어들어 재고를 초과한다.
# 기존 정원(current_participants) 이 딱 그 구조라 초과 예약이 가능하다.
# 여기서는 같은 버그를 만들지 않으려고 UPDATE 문 하나에 조건을 함께 실어
# DB 가 원자적으로 판정하게 한다. 락도, 트랜잭션 경계 관리도 필요 없다.
#
#   UPDATE experience
#      SET surplus_qty_taken = surplus_qty_taken + :n
#    WHERE id = :id AND surplus_qty_taken + :n <= surplus_qty_total
#
# rowcount 가 0 이면 그 사이 누가 먼저 가져간 것이다.
from sqlalchemy import case

from models import db, Experience


def is_surplus(experience):
    """수량 관리를 해야 하는 체험인지. 필요한 값이 다 있어야 한다."""
    return bool(
        experience is not None
        and getattr(experience, 'is_surplus', False)
        and getattr(experience, 'surplus_qty_total', None)
        and getattr(experience, 'surplus_per_person', None)
    )


def required_qty(experience, participants_count):
    """참가 인원이 가져갈 수량. 과생산이 아니면 0."""
    if not is_surplus(experience) or not participants_count:
        return 0
    return experience.surplus_per_person * participants_count


def remaining(experience):
    """남은 수량. 컬럼으로 두지 않고 매번 계산한다(두 값이 어긋날 수 없게)."""
    if not is_surplus(experience):
        return None
    taken = experience.surplus_qty_taken or 0
    return max(0, experience.surplus_qty_total - taken)


def take(experience, participants_count):
    """수량을 차감한다. 성공하면 True, 재고가 모자라면 False.

    조건을 UPDATE 에 실어 보내므로 동시 요청이 겹쳐도 총량을 넘지 않는다.
    커밋은 호출부(라우트)가 한다 — 예약 생성과 같은 트랜잭션에 묶어야 하기 때문이다.
    """
    need = required_qty(experience, participants_count)
    if need <= 0:
        return True     # 과생산이 아니면 통과

    result = db.session.execute(
        Experience.__table__.update()
        .where(Experience.id == experience.id)
        .where(Experience.surplus_qty_taken + need <= Experience.surplus_qty_total)
        .values(surplus_qty_taken=Experience.surplus_qty_taken + need)
    )
    if result.rowcount == 0:
        return False

    # UPDATE 를 직접 실행했으므로 세션의 객체는 옛 값을 들고 있다. 다시 읽게 만든다.
    db.session.expire(experience, ['surplus_qty_taken'])
    return True


def restore(experience, participants_count):
    """취소·거절 시 수량을 되돌린다.

    복원을 빠뜨리면 재고가 샌다 — 취소해도 수량이 안 돌아와 실제보다 빨리 소진된다.
    0 밑으로는 내려가지 않게 막는다(중복 복원 방어).
    """
    need = required_qty(experience, participants_count)
    if need <= 0:
        return

    db.session.execute(
        Experience.__table__.update()
        .where(Experience.id == experience.id)
        # GREATEST 는 SQLite 에 없다. case 로 쓰면 MySQL·SQLite 둘 다 동작한다.
        .values(surplus_qty_taken=case(
            (Experience.surplus_qty_taken - need > 0, Experience.surplus_qty_taken - need),
            else_=0))
    )
    db.session.expire(experience, ['surplus_qty_taken'])
