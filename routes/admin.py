# routes/admin.py
from datetime import datetime
from functools import wraps
from flask import render_template, request, redirect, url_for, flash, session, jsonify
from models import db, Farm, User, Notification

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session or session.get('role') != 'admin':
            flash("관리자 전용 페이지입니다. 관리자 계정으로 로그인해 주세요.", "danger")
            return redirect(url_for('login_page'))
        return f(*args, **kwargs)
    return decorated_function

@admin_required
def farm_audit_list():
    status_filter = request.args.get('status', 'PENDING')
    farms = Farm.query.filter_by(status=status_filter).order_by(Farm.created_at.desc()).all()
    
    counts = {
        'PENDING': Farm.query.filter_by(status='PENDING').count(),
        'APPROVED': Farm.query.filter_by(status='APPROVED').count(),
        'REJECTED': Farm.query.filter_by(status='REJECTED').count(),
    }
    return render_template('admin/farm_audit_list.html', farms=farms, current_status=status_filter, counts=counts)

@admin_required
def farm_audit_detail(farm_id):
    farm = Farm.query.get_or_404(farm_id)
    return render_template('admin/farm_audit_detail.html', farm=farm)

@admin_required
def farm_approve(farm_id):
    farm = Farm.query.get_or_404(farm_id)
    farm.status = 'APPROVED'
    farm.reject_reason = None
    farm.updated_at = datetime.utcnow()

    notif = Notification(
        user_id=farm.user_id,
        message=f"[{farm.name or farm.address}] 농장 입점 심사가 승인되었습니다. 이제 체험을 등록할 수 있습니다."
    )
    db.session.add(notif)
    db.session.commit()
    flash("농장 입점이 승인되었습니다.", "success")

    # 친환경 신청 농장이면 바로 친환경 인증 심사 페이지로 이동
    if farm.is_organic and farm.organic_cert_status == 'PENDING':
        flash("친환경 인증 서류를 이어서 심사해 주세요.", "info")
        return redirect(url_for('admin_organic_cert_detail', farm_id=farm.id))

    return redirect(url_for('admin_farm_audit_list', status='PENDING'))

@admin_required
def farm_reject(farm_id):
    farm = Farm.query.get_or_404(farm_id)
    reason = request.form.get('reject_reason', '').strip()
    if not reason:
        flash("반려 사유를 반드시 입력해야 합니다.", "danger")
        return redirect(url_for('admin_farm_audit_detail', farm_id=farm.id))
        
    farm.status = 'REJECTED'
    farm.reject_reason = reason
    farm.updated_at = datetime.utcnow()
    
    notif = Notification(
        user_id=farm.user_id,
        message=f"[{farm.name or farm.address}] 농장 심사가 반려되었습니다. 사유: {reason}"
    )
    db.session.add(notif)
    db.session.commit()
    flash("농장 심사가 반려 처리되었습니다.", "warning")
    return redirect(url_for('admin_farm_audit_list', status='PENDING'))

@admin_required
def organic_cert_list():
    farms = Farm.query.filter(
        Farm.is_organic == True,
        Farm.organic_cert_status != None
    ).order_by(Farm.created_at.desc()).all()
    counts = {
        'PENDING': Farm.query.filter_by(is_organic=True, organic_cert_status='PENDING').count(),
        'APPROVED': Farm.query.filter_by(is_organic=True, organic_cert_status='APPROVED').count(),
        'REJECTED': Farm.query.filter_by(is_organic=True, organic_cert_status='REJECTED').count(),
    }
    status_filter = request.args.get('status', 'PENDING')
    farms = Farm.query.filter_by(is_organic=True, organic_cert_status=status_filter).order_by(Farm.created_at.desc()).all()
    return render_template('admin/organic_cert_list.html', farms=farms, current_status=status_filter, counts=counts)


@admin_required
def organic_cert_approve(farm_id):
    farm = Farm.query.get_or_404(farm_id)
    farm.organic_cert_status = 'APPROVED'
    farm.organic_cert_reject_reason = None
    farm.updated_at = datetime.utcnow()
    notif = Notification(
        user_id=farm.user_id,
        message=f"[{farm.name or farm.address}] 농장의 친환경 인증이 승인되었습니다. 체험 목록에 친환경 표시가 노출됩니다."
    )
    db.session.add(notif)
    db.session.commit()
    flash("친환경 인증이 승인되었습니다.", "success")
    return redirect(url_for('admin_organic_cert_list', status='PENDING'))


@admin_required
def organic_cert_reject(farm_id):
    farm = Farm.query.get_or_404(farm_id)
    reason = request.form.get('reject_reason', '').strip()
    if not reason:
        flash("반려 사유를 입력해야 합니다.", "danger")
        return redirect(url_for('admin_organic_cert_detail', farm_id=farm_id))
    farm.organic_cert_status = 'REJECTED'
    farm.organic_cert_reject_reason = reason
    farm.updated_at = datetime.utcnow()
    notif = Notification(
        user_id=farm.user_id,
        message=f"[{farm.name or farm.address}] 농장의 친환경 인증 심사가 반려되었습니다. 사유: {reason}"
    )
    db.session.add(notif)
    db.session.commit()
    flash("친환경 인증이 반려 처리되었습니다.", "warning")
    return redirect(url_for('admin_organic_cert_list', status='PENDING'))


@admin_required
def organic_cert_detail(farm_id):
    farm = Farm.query.get_or_404(farm_id)
    return render_template('admin/organic_cert_detail.html', farm=farm)


def register(app):
    app.add_url_rule('/admin/farms/audit', 'admin_farm_audit_list', farm_audit_list)
    app.add_url_rule('/admin/farms/audit/<int:farm_id>', 'admin_farm_audit_detail', farm_audit_detail)
    app.add_url_rule('/admin/farms/<int:farm_id>/approve', 'admin_farm_approve', farm_approve, methods=['POST'])
    app.add_url_rule('/admin/farms/<int:farm_id>/reject', 'admin_farm_reject', farm_reject, methods=['POST'])
    app.add_url_rule('/admin/organic-cert', 'admin_organic_cert_list', organic_cert_list)
    app.add_url_rule('/admin/organic-cert/<int:farm_id>', 'admin_organic_cert_detail', organic_cert_detail)
    app.add_url_rule('/admin/organic-cert/<int:farm_id>/approve', 'admin_organic_cert_approve', organic_cert_approve, methods=['POST'])
    app.add_url_rule('/admin/organic-cert/<int:farm_id>/reject', 'admin_organic_cert_reject', organic_cert_reject, methods=['POST'])