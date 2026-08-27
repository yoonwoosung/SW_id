# routes/farms.py
import os
import uuid
from flask import render_template, request, session, redirect, url_for, flash, current_app
from common.response import success_response, error_response
from common.auth import api_login_required
from common.validators import allowed_file
from external.kakao_map import get_coords_from_address
from models import db, Farm
from services import farm_service

def _save_certificate():
    file = request.files.get('certificate_pdf') or request.files.get('farmer_certificate_pdf')
    if not file or not file.filename or not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"farm_cert_{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
    return filename

def _farm_dict(farm):
    return {
        "id": farm.id, "name": farm.name, "address": farm.address,
        "address_detail": farm.address_detail, "status": farm.status,
        "lat": farm.lat, "lng": farm.lng, "certificate_pdf": farm.certificate_pdf,
    }

def farm_manage_page():
    if 'user_id' not in session:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))
    if session.get('role') != 'farmer':
        flash("농장주만 접근할 수 있습니다.", "warning")
        return redirect(url_for('index'))
    farms = farm_service.list_farms(session['user_id'])
    return render_template('farm_manage.html', farms=farms)

def add_farm():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
        
    farmer_id = session['user_id']
    name = (request.form.get('farm_name') or '').strip()
    address = (request.form.get('farm_address') or '').strip()
    address_detail = (request.form.get('farm_address_detail') or '').strip()
    size = (request.form.get('farm_size') or '').strip()
    
    if not address:
        flash("농장 주소는 필수입니다.", "warning")
        return redirect(url_for('farmer_easy_mode', tab='account'))
        
    pdf_filename = _save_certificate()
    lat, lng = get_coords_from_address(address)
    
    new_farm = Farm(
        user_id=farmer_id,
        name=name or None,
        address=address,
        address_detail=address_detail,
        size=size or None,
        certificate_pdf=pdf_filename,
        lat=lat,
        lng=lng,
        status='PENDING',
        is_organic='is_organic' in request.form,
        organic_cert_type=request.form.get('organic_cert_type')
    )
    
    db.session.add(new_farm)
    db.session.commit()
    flash("농장 등록 및 서류 제출이 완료되었습니다. 관리자 심사 후 활성화됩니다.", "success")
    return redirect(url_for('farmer_easy_mode', tab='account'))

def delete_farm(farm_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    
    farm = Farm.query.get_or_404(farm_id)
    if farm.user_id != session['user_id']:
        flash("본인의 농장만 삭제할 수 있습니다.", "danger")
        return redirect(url_for('farmer_easy_mode', tab='account'))
        
    db.session.delete(farm)
    db.session.commit()
    flash("농장이 삭제되었습니다.", "info")
    return redirect(url_for('farmer_easy_mode', tab='account'))

@api_login_required
def create_farm_api():
    name = (request.form.get('name') or '').strip()
    address = (request.form.get('address') or '').strip()
    if not name or not address:
        return error_response("INVALID_FARM", "농장명과 주소는 필수입니다.", 400)
    farm = farm_service.create_farm(session['user_id'], name, address, _save_certificate())
    return success_response(_farm_dict(farm), status=201)

@api_login_required
def update_farm_api(farm_id):
    name = (request.form.get('name') or '').strip()
    address = (request.form.get('address') or '').strip()
    status, farm = farm_service.update_farm(session['user_id'], farm_id, name, address, _save_certificate())
    if status == 'not_found':
        return error_response("FARM_NOT_FOUND", "농장을 찾을 수 없습니다.", 404)
    if status == 'forbidden':
        return error_response("FORBIDDEN", "본인 농장만 수정할 수 있습니다.", 403)
    if status == 'cert_required':
        return error_response("CERTIFICATE_REQUIRED", "주소를 변경하면 증빙 PDF를 다시 제출해야 합니다.", 400)
    return success_response(_farm_dict(farm))

@api_login_required
def delete_farm_api(farm_id):
    status = farm_service.delete_farm(session['user_id'], farm_id)
    if status == 'not_found':
        return error_response("FARM_NOT_FOUND", "농장을 찾을 수 없습니다.", 404)
    if status == 'forbidden':
        return error_response("FORBIDDEN", "본인 농장만 삭제할 수 있습니다.", 403)
    return success_response({"deleted": True})

def register(app):
    app.add_url_rule('/farms/manage', 'farm_manage_page', farm_manage_page)
    # 엔드포인트 명칭을 고유하게 변경하여 충돌 방지
    app.add_url_rule('/farms/add', 'farmer_add_farm', add_farm, methods=['POST'])
    app.add_url_rule('/farms/delete/<int:farm_id>', 'farmer_delete_farm', delete_farm, methods=['POST'])
    app.add_url_rule('/api/farms', 'api_create_farm', create_farm_api, methods=['POST'])
    app.add_url_rule('/api/farms/<int:farm_id>', 'api_update_farm', update_farm_api, methods=['PUT'])
    app.add_url_rule('/api/farms/<int:farm_id>', 'api_delete_farm', delete_farm_api, methods=['DELETE'])