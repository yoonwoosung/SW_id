"""공모전 심사 계정 시드가 ★심사위원이 볼 것★을 모두 준비하는지.

이 스크립트는 배포 서버에서 한 번 돌려 계정·농장·체험·후기를 만든다.
반복 실행해도 안전해야 한다 — 중복 후기가 쌓이면 화면이 이상해진다.
"""
from datetime import date

import pytest

import app as farmlink
from models import db, User, Experience, Application, Review
from models.farm import Farm

PASSWORD = '2026openapi!'


@pytest.fixture
def seeded(db_session, monkeypatch):
    monkeypatch.setenv('OPENAPI_PASSWORD', PASSWORD)
    monkeypatch.setattr('sys.argv', ['seed_openapi.py'])
    import seed_openapi
    seed_openapi.main()
    return seed_openapi


def _main_user():
    return User.query.filter_by(email='openapi@farmlink.com').first()


def _main_experience():
    import seed_openapi
    return Experience.query.filter_by(farmer_id=_main_user().id,
                                      crop=seed_openapi.EXPERIENCE['crop']).first()


def test_accounts_created(seeded):
    for email, role in (('openapi@farmlink.com', 'experiencer'),
                        ('openapi.farmer@farmlink.com', 'farmer'),
                        ('openapi.admin@farmlink.com', 'admin')):
        user = User.query.filter_by(email=email).first()
        assert user is not None, email
        assert user.role == role


def test_main_account_owns_an_approved_farm(seeded):
    """★농장주로 전환했을 때 빈 화면이면 기능 확인이 안 된다.★"""
    farms = Farm.query.filter_by(user_id=_main_user().id).all()
    assert len(farms) == 1
    assert farms[0].status == 'APPROVED'


def test_main_account_has_a_recipe_and_a_surplus_experience(seeded):
    exps = Experience.query.filter_by(farmer_id=_main_user().id).all()
    assert len(exps) == 2
    assert any(e.has_recipe and e.recipe_steps for e in exps), "레시피 체험이 없다"
    assert any(e.is_surplus and e.list_price for e in exps), "과생산 체험이 없다"
    assert all(e.status == 'recruiting' for e in exps)
    assert all(e.end_date > date.today() for e in exps), "심사 중 마감되면 안 된다"


def test_reviews_exist_with_varied_ratings(seeded):
    """★후기가 0건이면 AI 요약 API 가 400 을 돌려준다.★"""
    reviews = Review.query.filter_by(experience_id=_main_experience().id).all()
    assert len(reviews) >= 3
    assert len({r.rating for r in reviews}) >= 2, "별점이 다양해야 한다"
    assert all(r.content.strip() for r in reviews)


def test_main_account_has_a_completed_reservation_but_no_review(seeded):
    """★심사위원이 후기를 직접 써 볼 수 있어야 한다.★

    대표 계정이 이미 후기를 썼으면 "이미 작성하셨습니다"가 되어 작성 화면을
    볼 수 없다. 완료된 예약만 만들어 둔다(레시피 버튼 확인용).
    """
    user = _main_user()
    app_row = Application.query.filter_by(user_id=user.id,
                                          experience_id=_main_experience().id).first()
    assert app_row is not None
    assert app_row.status == '완료'
    assert app_row.can_review is True
    assert app_row.apply_date < date.today(), "지난 날짜여야 체험이 끝난 것으로 본다"
    assert Review.query.filter_by(user_id=user.id).count() == 0


def test_running_twice_does_not_duplicate(seeded):
    """★반복 실행해도 안전해야 한다.★ 중복 후기가 쌓이면 화면이 이상해진다."""
    before = (Review.query.count(), Application.query.count(),
              Experience.query.count(), Farm.query.count(), User.query.count())
    seeded.main()
    assert (Review.query.count(), Application.query.count(),
            Experience.query.count(), Farm.query.count(), User.query.count()) == before


def test_review_page_shows_the_reviews(seeded):
    """체험 상세에 후기 목록이 실제로 그려지는가."""
    farmlink.app.secret_key = 'test-secret'
    with farmlink.app.test_client() as client:
        html = client.get(f'/experience/{_main_experience().id}').get_data(as_text=True)
    assert '후기 4개' in html


def test_completed_card_appears_in_my_activity(seeded):
    """내 활동에 완료 카드가 떠야 레시피 버튼이 붙는다(③④와 연결)."""
    from services.activity_service import STATE_COMPLETED
    farmlink.app.secret_key = 'test-secret'
    with farmlink.app.test_client() as client:
        client.post('/login', data={'email': 'openapi@farmlink.com', 'password': PASSWORD})
        html = client.get('/my_info').get_data(as_text=True)
    assert f'class="mi-res-card" data-state="{STATE_COMPLETED}"' in html
