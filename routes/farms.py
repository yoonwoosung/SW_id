# routes/farms.py — 농장(Farm) 다중 등록 라우트(관리 페이지 + CRUD API).
import os
import uuid

from flask import render_template, request, session, redirect, url_for, flash, current_app

from common.response import success_response, error_response
from common.auth import api_login_required
from common.validators import allowed_file
from services import farm_service


def _save_certificate():
    """요청의 certificate_pdf 파일을 저장하고 파일명을 반환. 없거나 허용 안 되면 None."""
    file = request.files.get('certificate_pdf')
    if not file or not file.filename or not allowed_file(file.filename):
        return None
    ext = file.filename.rsplit('.', 1)[1].lower()
    filename = f"farm_cert_{uuid.uuid4().hex}.{ext}"
    file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], filename))
    return filename


def _farm_dict(farm):
    return {
        "id": farm.id, "name": farm.name, "address": farm.address,
        "lat": farm.lat, "lng": farm.lng, "certificate_pdf": farm.certificate_pdf,
    }


def farm_manage_page():
    # 농장 관리 페이지(농장주 전용).
    if 'user_id' not in session:
        flash("로그인이 필요합니다.", "warning")
        return redirect(url_for('login_page'))
    if session.get('role') != 'farmer':
        flash("농장주만 접근할 수 있습니다.", "warning")
        return redirect(url_for('index'))
    farms = farm_service.list_farms(session['user_id'])
    return render_template('farm_manage.html', farms=farms)


@api_login_required
def create_farm():
    name = (request.form.get('name') or '').strip()
    address = (request.form.get('address') or '').strip()
    if not name or not address:
        return error_response("INVALID_FARM", "농장명과 주소는 필수입니다.", 400)
    farm = farm_service.create_farm(session['user_id'], name, address, _save_certificate())
    return success_response(_farm_dict(farm), status=201)


@api_login_required
def update_farm(farm_id):
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
def delete_farm(farm_id):
    status = farm_service.delete_farm(session['user_id'], farm_id)
    if status == 'not_found':
        return error_response("FARM_NOT_FOUND", "농장을 찾을 수 없습니다.", 404)
    if status == 'forbidden':
        return error_response("FORBIDDEN", "본인 농장만 삭제할 수 있습니다.", 403)
    return success_response({"deleted": True})


def register(app):
    app.add_url_rule('/farms/manage', 'farm_manage_page', farm_manage_page)
    # [수정] 엔드포인트 명칭 중복을 피하기 위해 api_* 구문으로 지정
    app.add_url_rule('/api/farms', 'api_create_farm', create_farm, methods=['POST'])
    app.add_url_rule('/api/farms/<int:farm_id>', 'api_update_farm', update_farm, methods=['PUT'])
    app.add_url_rule('/api/farms/<int:farm_id>', 'api_delete_farm', delete_farm, methods=['DELETE'])