# services/farm_service.py — 농장(Farm) 등록·수정·삭제·목록 + 기존 데이터 백필.
# 주소→좌표는 external.kakao_map 재사용. 남의 농장 접근은 라우트에서 소유 확인.
from models import db, Farm, Experience
from external.kakao_map import get_coords_from_address


def _geocode(address):
    """주소 → (lat, lng). 실패해도 kakao_map이 기본 좌표를 돌려주므로 그대로 사용."""
    try:
        return get_coords_from_address(address)
    except Exception:
        return None, None


def list_farms(user_id):
    return Farm.query.filter_by(user_id=user_id).order_by(Farm.created_at.desc()).all()


def get_owned_farm(user_id, farm_id):
    """(status, farm). status: 'ok' | 'not_found' | 'forbidden'."""
    farm = Farm.query.get(farm_id)
    if farm is None:
        return 'not_found', None
    if farm.user_id != user_id:
        return 'forbidden', None
    return 'ok', farm


def create_farm(user_id, name, address, certificate_pdf=None):
    lat, lng = _geocode(address)
    farm = Farm(user_id=user_id, name=name, address=address, lat=lat, lng=lng,
                certificate_pdf=certificate_pdf)
    db.session.add(farm)
    db.session.commit()
    return farm


def update_farm(user_id, farm_id, name, address, certificate_pdf=None):
    """농장 수정. 주소가 바뀌면 증빙 PDF 재제출 필수.
    반환 status: 'ok' | 'not_found' | 'forbidden' | 'cert_required'."""
    status, farm = get_owned_farm(user_id, farm_id)
    if status != 'ok':
        return status, None

    address_changed = bool(address) and address != farm.address
    if address_changed and not certificate_pdf:
        return 'cert_required', None

    if name:
        farm.name = name
    if address_changed:
        farm.address = address
        farm.lat, farm.lng = _geocode(address)
    if certificate_pdf:
        farm.certificate_pdf = certificate_pdf
    db.session.commit()
    return 'ok', farm


def delete_farm(user_id, farm_id):
    """농장 삭제. 소속 체험의 farm_id는 NULL로 되돌린다(체험 자체는 유지)."""
    status, farm = get_owned_farm(user_id, farm_id)
    if status != 'ok':
        return status
    Experience.query.filter_by(farm_id=farm.id).update({'farm_id': None})
    db.session.delete(farm)
    db.session.commit()
    return 'ok'


def default_farm_for(user_id):
    """농장주의 기본(가장 먼저 등록한) 농장. 없으면 None."""
    return Farm.query.filter_by(user_id=user_id).order_by(Farm.created_at.asc()).first()


def backfill_default_farms():
    """기존 데이터 이관: 농장이 없는 농장주의 체험을, 그 체험 주소로 만든 '기본 농장'에 연결한다.
    이미 farm_id가 있는 체험/농장이 있는 농장주는 건드리지 않는다(멱등)."""
    linked = 0
    orphan_farmer_ids = {
        exp.farmer_id for exp in Experience.query.filter(Experience.farm_id.is_(None)).all()
    }
    for farmer_id in orphan_farmer_ids:
        farm = default_farm_for(farmer_id)
        if farm is None:
            exps = Experience.query.filter_by(farmer_id=farmer_id).all()
            address = next((e.address_detail for e in exps if e.address_detail), '주소 미등록')
            lat, lng = (exps[0].lat, exps[0].lng) if exps else (None, None)
            farm = Farm(user_id=farmer_id, name='기본 농장', address=address, lat=lat, lng=lng)
            db.session.add(farm)
            db.session.flush()  # farm.id 확보
        for exp in Experience.query.filter_by(farmer_id=farmer_id, farm_id=None).all():
            exp.farm_id = farm.id
            linked += 1
    db.session.commit()
    return linked
