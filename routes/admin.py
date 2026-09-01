# routes/admin.py — 관리자 도메인 라우트(농장 승인·회원/예약/농장 관리).
#
# 핵심은 '농장 승인'이다. 이 코드베이스에는 Farm 모델이 없고 농장주(User.role='farmer')가
# Experience를 직접 소유하므로, 승인 단위는 Experience 한 건이다.
# 승인되지 않은 농장은 Experience.approved_only() 게이트에 걸려 공개 노출·예약이 막힌다.
from datetime import datetime

from flask import render_template, request, redirect, url_for, flash
from sqlalchemy import func

from models import db, User, Experience, Application, Review, Inquiry
from common.auth import admin_required

# 목록 화면에서 한 번에 보여줄 최대 건수. 페이지네이션 대신 상한으로 단순화한다.
LIST_LIMIT = 200

# 관리자가 인라인으로 바꿀 수 있는 값들. 폼에서 넘어온 값을 이 목록으로 검증한다.
EXPERIENCE_STATUSES = ['recruiting', 'hidden', 'expired']
USER_ROLES = ['experiencer', 'farmer', 'admin']
VERIFICATION_STATUSES = ['pending', 'verified', 'rejected', 'error']


def _pending_farms():
    """승인 대기 농장. 대시보드와 농장 목록 양쪽에서 쓴다."""
    return (Experience.query
            .filter(Experience.approval_status == Experience.APPROVAL_PENDING)
            .order_by(Experience.id.desc())
            .all())


def admin_dashboard():
    """관리자 대시보드. 승인 대기 목록을 가장 위에 둔다."""
    pending = _pending_farms()

    # 상태별 농장 수를 한 번의 group by로 센다.
    approval_counts = dict(
        db.session.query(Experience.approval_status, func.count(Experience.id))
        .group_by(Experience.approval_status).all()
    )
    role_counts = dict(
        db.session.query(User.role, func.count(User.id)).group_by(User.role).all()
    )

    stats = {
        'users_total': sum(role_counts.values()),
        'users_farmer': role_counts.get('farmer', 0),
        'users_experiencer': role_counts.get('experiencer', 0),
        'users_admin': role_counts.get('admin', 0),
        'farms_total': sum(approval_counts.values()),
        'farms_pending': approval_counts.get(Experience.APPROVAL_PENDING, 0),
        'farms_approved': approval_counts.get(Experience.APPROVAL_APPROVED, 0),
        'farms_rejected': approval_counts.get(Experience.APPROVAL_REJECTED, 0),
        'reservations_total': Application.query.count(),
        'reviews_total': Review.query.count(),
        'inquiries_total': Inquiry.query.count(),
    }
    return render_template('admin/dashboard.html', pending=pending, stats=stats)


# ---------------------------------------------------------------- 농장(체험) 관리

def admin_farms():
    """농장 목록. ?approval= 로 승인 상태를 거른다(기본: 전체)."""
    approval = request.args.get('approval', '')
    query = Experience.query
    if approval in (Experience.APPROVAL_PENDING, Experience.APPROVAL_APPROVED,
                    Experience.APPROVAL_REJECTED):
        query = query.filter(Experience.approval_status == approval)

    farms = query.order_by(Experience.id.desc()).limit(LIST_LIMIT).all()
    return render_template('admin/farms.html', farms=farms, approval=approval,
                           statuses=EXPERIENCE_STATUSES,
                           pending_count=len(_pending_farms()))


def _set_approval(item_id, new_status, note=None):
    """승인 상태 변경 공통 처리. 처리 시각과 사유를 함께 기록한다."""
    item = Experience.query.get_or_404(item_id)
    item.approval_status = new_status
    item.approval_note = note
    item.approved_at = datetime.now()
    db.session.commit()
    return item


def admin_farm_approve(item_id):
    item = _set_approval(item_id, Experience.APPROVAL_APPROVED)
    flash(f"'{item.crop}' 농장을 승인했습니다. 이제 목록에 노출되고 예약을 받습니다.", "success")
    return redirect(request.form.get('next') or url_for('admin_farms'))


def admin_farm_reject(item_id):
    # 거절 사유는 선택 입력. 비워두면 사유 없이 거절 처리한다.
    note = (request.form.get('approval_note') or '').strip() or None
    item = _set_approval(item_id, Experience.APPROVAL_REJECTED, note)
    flash(f"'{item.crop}' 농장을 거절했습니다.", "warning")
    return redirect(request.form.get('next') or url_for('admin_farms'))


def admin_farm_update(item_id):
    """핵심 필드 인라인 수정(모집상태·가격·정원). 이미지·좌표 등은 농장주 폼에서 다룬다."""
    item = Experience.query.get_or_404(item_id)

    status = request.form.get('status')
    if status in EXPERIENCE_STATUSES:
        item.status = status

    # 숫자 필드는 비어있거나 형식이 틀리면 기존 값을 유지한다.
    for field in ('cost', 'max_participants'):
        raw = request.form.get(field)
        if raw is None or raw == '':
            continue
        try:
            setattr(item, field, int(raw))
        except ValueError:
            flash(f"'{field}' 값이 숫자가 아니라 무시했습니다.", "warning")

    db.session.commit()
    flash(f"'{item.crop}' 농장 정보를 수정했습니다.", "success")
    return redirect(request.form.get('next') or url_for('admin_farms'))


def admin_farm_delete(item_id):
    item = Experience.query.get_or_404(item_id)
    crop = item.crop
    # 리뷰·문의·예약은 Experience 관계에 cascade가 걸려 있어 함께 지워진다.
    db.session.delete(item)
    db.session.commit()
    flash(f"'{crop}' 농장을 삭제했습니다.", "info")
    return redirect(request.form.get('next') or url_for('admin_farms'))


# ---------------------------------------------------------------- 회원 관리

def admin_users():
    role = request.args.get('role', '')
    query = User.query
    if role in USER_ROLES:
        query = query.filter(User.role == role)

    users = query.order_by(User.id.desc()).limit(LIST_LIMIT).all()
    # 농장주별 등록 농장 수 — 목록에서 한눈에 보이게 미리 센다.
    farm_counts = dict(
        db.session.query(Experience.farmer_id, func.count(Experience.id))
        .group_by(Experience.farmer_id).all()
    )
    return render_template('admin/users.html', users=users, role=role,
                           roles=USER_ROLES, verifications=VERIFICATION_STATUSES,
                           farm_counts=farm_counts)


def admin_user_update(user_id):
    user = User.query.get_or_404(user_id)

    role = request.form.get('role')
    if role in USER_ROLES:
        user.role = role

    verification = request.form.get('verification_status')
    if verification in VERIFICATION_STATUSES:
        user.verification_status = verification

    db.session.commit()
    flash(f"'{user.nickname}' 회원 정보를 수정했습니다.", "success")
    return redirect(request.form.get('next') or url_for('admin_users'))


def admin_user_delete(user_id):
    user = User.query.get_or_404(user_id)

    # 마지막 관리자를 지우면 아무도 관리자 화면에 못 들어간다. 사전에 막는다.
    if user.role == 'admin' and User.query.filter_by(role='admin').count() <= 1:
        flash("마지막 관리자 계정은 삭제할 수 없습니다.", "danger")
        return redirect(url_for('admin_users'))

    nickname = user.nickname
    db.session.delete(user)
    db.session.commit()
    flash(f"'{nickname}' 회원을 삭제했습니다.", "info")
    return redirect(request.form.get('next') or url_for('admin_users'))


# ---------------------------------------------------------------- 예약 관리

def admin_reservations():
    reservations = (Application.query
                    .order_by(Application.apply_date.desc(), Application.id.desc())
                    .limit(LIST_LIMIT).all())
    # 예약 상태는 한글 문자열로 저장된다(models/reservation.py: default='예정').
    return render_template('admin/reservations.html', reservations=reservations,
                           statuses=['예정', '완료', '취소'])


def admin_reservation_update(reservation_id):
    reservation = Application.query.get_or_404(reservation_id)
    status = request.form.get('status')
    if status in ('예정', '완료', '취소'):
        reservation.status = status
        db.session.commit()
        flash(f"예약 #{reservation.id} 상태를 '{status}'로 변경했습니다.", "success")
    else:
        flash("알 수 없는 예약 상태입니다.", "warning")
    return redirect(request.form.get('next') or url_for('admin_reservations'))


def admin_reservation_delete(reservation_id):
    reservation = Application.query.get_or_404(reservation_id)
    db.session.delete(reservation)
    db.session.commit()
    flash(f"예약 #{reservation_id}을(를) 삭제했습니다.", "info")
    return redirect(request.form.get('next') or url_for('admin_reservations'))


def register(app):
    # 모든 관리자 라우트는 admin_required로 감싼다. 상태를 바꾸는 것은 전부 POST.
    rules = [
        ('/admin', 'admin_dashboard', admin_dashboard, ['GET']),
        ('/admin/farms', 'admin_farms', admin_farms, ['GET']),
        ('/admin/farms/<int:item_id>/approve', 'admin_farm_approve', admin_farm_approve, ['POST']),
        ('/admin/farms/<int:item_id>/reject', 'admin_farm_reject', admin_farm_reject, ['POST']),
        ('/admin/farms/<int:item_id>/update', 'admin_farm_update', admin_farm_update, ['POST']),
        ('/admin/farms/<int:item_id>/delete', 'admin_farm_delete', admin_farm_delete, ['POST']),
        ('/admin/users', 'admin_users', admin_users, ['GET']),
        ('/admin/users/<int:user_id>/update', 'admin_user_update', admin_user_update, ['POST']),
        ('/admin/users/<int:user_id>/delete', 'admin_user_delete', admin_user_delete, ['POST']),
        ('/admin/reservations', 'admin_reservations', admin_reservations, ['GET']),
        ('/admin/reservations/<int:reservation_id>/update', 'admin_reservation_update',
         admin_reservation_update, ['POST']),
        ('/admin/reservations/<int:reservation_id>/delete', 'admin_reservation_delete',
         admin_reservation_delete, ['POST']),
    ]
    for rule, endpoint, view, methods in rules:
        app.add_url_rule(rule, endpoint, admin_required(view), methods=methods)
