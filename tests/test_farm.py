"""services/farm_service 통합 테스트 — 농장 CRUD·소유확인·주소변경 증빙·백필(B안)."""
from models import db, User, Experience, Farm
from services import farm_service


def _user(email="f@x.com", role="farmer"):
    u = User(nickname="n", email=email, password="x", role=role, name="농부")
    db.session.add(u)
    db.session.commit()
    return u


def _experience(farmer_id, addr="경기도 안성시 서운면"):
    exp = Experience(crop="포도", location="loc", cost=25000, address_detail=addr,
                     farmer_id=farmer_id, lat=37.0, lng=127.2)
    db.session.add(exp)
    db.session.commit()
    return exp


def test_create_and_list(db_session):
    u = _user()
    farm_service.create_farm(u.id, "행복농장", "경기도 안성시 서운면")
    farms = farm_service.list_farms(u.id)
    assert len(farms) == 1 and farms[0].name == "행복농장"


def test_owner_only(db_session):
    owner = _user("o@x.com")
    other = _user("x@x.com")
    farm = farm_service.create_farm(owner.id, "내농장", "경기 안성")
    assert farm_service.update_farm(other.id, farm.id, "해킹", "", None)[0] == 'forbidden'
    assert farm_service.delete_farm(other.id, farm.id) == 'forbidden'


def test_address_change_requires_certificate(db_session):
    u = _user()
    farm = farm_service.create_farm(u.id, "농장", "경기 안성", certificate_pdf="c1.pdf")
    # 이름만 바꾸면 증빙 불필요
    assert farm_service.update_farm(u.id, farm.id, "새이름", "", None)[0] == 'ok'
    # 주소 변경엔 증빙 필수
    assert farm_service.update_farm(u.id, farm.id, "", "충남 논산시", None)[0] == 'cert_required'
    assert farm_service.update_farm(u.id, farm.id, "", "충남 논산시", "c2.pdf")[0] == 'ok'


def test_delete_unlinks_experiences(db_session):
    u = _user()
    farm = farm_service.create_farm(u.id, "농장", "경기 안성")
    exp = _experience(u.id)
    exp.farm_id = farm.id
    db.session.commit()
    assert farm_service.delete_farm(u.id, farm.id) == 'ok'
    assert Experience.query.get(exp.id).farm_id is None   # 체험은 유지, 연결만 해제


def test_backfill_creates_default_farm(db_session):
    u = _user()
    _experience(u.id)
    _experience(u.id, addr="경기도 이천시")
    linked = farm_service.backfill_default_farms()
    assert linked == 2
    farms = farm_service.list_farms(u.id)
    assert len(farms) == 1 and farms[0].name == "기본 농장"
    # 재실행해도 중복 생성/연결 없음(멱등)
    assert farm_service.backfill_default_farms() == 0
