# 준형 작업분 병합 가이드

> 기준 커밋: `19dcfa8d`
> 작성일: 2026-08-05

---

## 읽기 전 주의

준형 코드(`frontend` 브랜치)와 팀원 코드는 **둘 다 `19dcfa8d` 이후로 따로 작업**했기 때문에
팀원 코드에 **단순 붙여넣기는 안 됨**.

파일을 두 종류로 나눠서 처리해야 함:
- **[A] 통째로 교체** — 농장주 전용 파일. 팀원이 건드리지 않았을 파일.
- **[B] 수동 병합** — 공통 파일. 팀원 변경사항도 있을 수 있음. 아래 지시대로만 추가.

---

## [A] 통째로 교체할 파일

아래 파일들은 준형이 처음부터 다시 작성한 농장주 전용 파일.
팀원 코드의 해당 파일을 `frontend` 브랜치 버전으로 통째로 덮어쓰면 됨.

| 파일 | 비고 |
|------|------|
| `models/farm.py` | 신규 파일 — 없으면 그냥 추가 |
| `models/inquiry_reply.py` | 신규 파일 — 없으면 그냥 추가 |
| `routes/farmer.py` | 전면 수정 |
| `templates/farmer_easy_mode.html` | 전면 재작성 (4탭 구조) |
| `templates/easy_communication.html` | 전면 수정 |
| `templates/easy_create_experience.html` | 전면 수정 (5단계 마법사) |
| `templates/easy_reservations.html` | 수정 |
| `templates/easy_modify_list.html` | 수정 |
| `templates/easy_edit_bio.html` | 소폭 수정 |
| `templates/farmer_calendar.html` | 소폭 수정 |

---

## [B] 수동 병합할 파일

### 1. `models/__init__.py`

import 목록에 두 줄 추가:

```python
from models.inquiry_reply import InquiryReply  # 추가
from models.farm import Farm                    # 추가
```

`__all__` 리스트에 `'InquiryReply'`, `'Farm'` 추가:

```python
__all__ = [
    'db', 'User', 'Experience', 'Review', 'Inquiry', 'InquiryReply', 'Application',
    'Notification', 'UserRequest', 'Proposal', 'Farm',
]
```

---

### 2. `routes/auth.py`

농장주 로그인 후 리다이렉트 변경.
`login_page()` 함수 안에서 아래 한 줄 교체:

```python
# 변경 전
return redirect(url_for('detailed_farmer_dashboard'))

# 변경 후
return redirect(url_for('farmer_easy_mode'))
```

---

### 3. `routes/experience.py`

농장주가 체험 목록 접근 시 리다이렉트 변경.
`index()` 함수 안 `is_farmer` 블록에서:

```python
# 변경 전
return redirect(url_for('detailed_farmer_dashboard'))

# 변경 후
return redirect(url_for('farmer_easy_mode'))
```

---

### 4. `routes/reservation.py`

**① 리다이렉트 변경**
`confirm_application()` 함수 안:

```python
# 변경 전
return redirect(url_for('easy_reservations'))

# 변경 후
return redirect(url_for('farmer_easy_mode', tab='reservations'))
```

**② 신규 함수 추가**
`delete_application()` 함수 아래에 추가:

```python
def reject_application(app_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        abort(403)
    application = Application.query.get_or_404(app_id)
    experience = Experience.query.get_or_404(application.experience_id)
    if experience.farmer_id != session.get('user_id'):
        abort(403)
    if application.status == '예정':
        experience.current_participants = max(0, experience.current_participants - application.participants_count)
        application.status = '취소'
        db.session.commit()
        flash(f"{application.applicant_name}님의 예약을 거절했습니다.", "success")
    else:
        flash("이미 처리된 예약입니다.", "warning")
    return redirect(url_for('farmer_easy_mode', tab='reservations'))
```

**③ 라우트 등록**
`register(app)` 함수 안에 추가:

```python
app.add_url_rule('/application/reject/<int:app_id>', 'reject_application', reject_application, methods=['POST'])
```

---

### 5. `routes/review.py`

**① import 추가**
파일 상단 `from models import ...` 줄에 `InquiryReply` 추가.
(팀원이 models import에 다른 항목을 추가했을 수 있으므로, 줄 전체 교체 말고 `InquiryReply`만 끼워 넣을 것)

예시:
```python
from models import db, User, Experience, Review, Inquiry, InquiryReply, Application, Notification
#                                                           ↑ 여기 추가
```

**② 신규 함수 3개 추가**
`add_inquiry()` 함수 아래, `register(app)` 함수 바로 위에 추가:

```python
def reply_inquiry(inquiry_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        abort(403)
    inquiry = Inquiry.query.get_or_404(inquiry_id)
    experience = Experience.query.get_or_404(inquiry.experience_id)
    if experience.farmer_id != session['user_id']:
        abort(403)
    content = (request.form.get('content') or '').strip()
    if not content:
        flash('답변 내용을 입력해주세요.', 'warning')
        return redirect(url_for('easy_communication'))
    reply = InquiryReply(inquiry_id=inquiry_id, content=content)
    db.session.add(reply)
    db.session.commit()
    flash('답변이 등록되었습니다.', 'success')
    return redirect(url_for('easy_communication'))


def edit_inquiry_reply(reply_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        abort(403)
    reply = InquiryReply.query.get_or_404(reply_id)
    experience = Experience.query.get_or_404(reply.inquiry.experience_id)
    if experience.farmer_id != session['user_id']:
        abort(403)
    content = (request.form.get('content') or '').strip()
    if not content:
        flash('수정할 내용을 입력해주세요.', 'warning')
        return redirect(url_for('easy_communication'))
    reply.content = content
    reply.timestamp = datetime.utcnow()
    db.session.commit()
    flash('답변이 수정되었습니다.', 'success')
    return redirect(url_for('easy_communication'))


def delete_inquiry_reply(reply_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        abort(403)
    reply = InquiryReply.query.get_or_404(reply_id)
    experience = Experience.query.get_or_404(reply.inquiry.experience_id)
    if experience.farmer_id != session['user_id']:
        abort(403)
    db.session.delete(reply)
    db.session.commit()
    flash('답변이 삭제되었습니다.', 'success')
    return redirect(url_for('easy_communication'))
```

**③ 라우트 등록**
`register(app)` 함수 안에 추가:

```python
app.add_url_rule('/inquiry/<int:inquiry_id>/reply', 'reply_inquiry', reply_inquiry, methods=['POST'])
app.add_url_rule('/inquiry/reply/<int:reply_id>/edit', 'edit_inquiry_reply', edit_inquiry_reply, methods=['POST'])
app.add_url_rule('/inquiry/reply/<int:reply_id>/delete', 'delete_inquiry_reply', delete_inquiry_reply, methods=['POST'])
```

---

### 6. `routes/user_routes.py`

**① import 추가**
파일 상단 `from models import ...` 줄에 `Farm` 추가.
(줄 전체 교체 말고 `Farm`만 끼워 넣을 것)

예시:
```python
from models import db, User, Experience, Review, Inquiry, Application, Notification, Farm
#                                                                                    ↑ 여기 추가
```

**② 리다이렉트 변경**
`my_info()` 함수 안, 농장주 정보 수정 후 리다이렉트:

```python
# 변경 전
return redirect(url_for('detailed_farmer_dashboard'))

# 변경 후
return redirect(url_for('farmer_easy_mode', tab='account'))
```

**③ 신규 함수 4개 추가**
`album_create()` 함수 아래에 추가:

```python
def verify_password():
    if 'user_id' not in session:
        return jsonify({'ok': False})
    user = User.query.get(session['user_id'])
    password = (request.json or {}).get('password', '')
    return jsonify({'ok': check_password_hash(user.password, password)})


def farmer_update_info():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    user = User.query.get_or_404(session['user_id'])
    user.nickname = (request.form.get('nickname') or user.nickname).strip()
    user.name = (request.form.get('name') or '').strip()
    user.birthdate = (request.form.get('birthdate') or '').strip()
    user.gender = request.form.get('gender') or None
    user.profile_bio = (request.form.get('profile_bio') or '').strip()
    db.session.commit()
    session['nickname'] = user.nickname
    flash("기본 정보가 저장되었습니다.", "success")
    return redirect(url_for('farmer_easy_mode', tab='account'))


def add_farm():
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    address = (request.form.get('farm_address') or '').strip()
    if not address:
        flash('농장 주소를 입력해주세요.', 'warning')
        return redirect(url_for('farmer_easy_mode', tab='account'))
    size = (request.form.get('farm_size') or '').strip()
    is_organic = 'is_organic' in request.form

    cert_pdf_name = None
    cert_file = request.files.get('farmer_certificate_pdf')
    if cert_file and cert_file.filename and cert_file.filename.lower().endswith('.pdf'):
        cert_pdf_name = f"farm_cert_{session['user_id']}_{uuid.uuid4().hex}.pdf"
        cert_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], cert_pdf_name))

    organic_img_name = None
    organic_cert_type = None
    if is_organic:
        organic_cert_type = (request.form.get('organic_cert_type') or '').strip()
        org_file = request.files.get('organic_cert_image')
        if org_file and org_file.filename and allowed_file(org_file.filename):
            ext = org_file.filename.rsplit('.', 1)[1].lower()
            organic_img_name = f"organic_{session['user_id']}_{uuid.uuid4().hex}.{ext}"
            org_file.save(os.path.join(current_app.config['UPLOAD_FOLDER'], organic_img_name))

    farm = Farm(
        farmer_id=session['user_id'],
        address=address,
        size=size,
        certificate_pdf=cert_pdf_name,
        is_organic=is_organic,
        organic_cert_image=organic_img_name,
        organic_cert_type=organic_cert_type,
    )
    db.session.add(farm)

    user = User.query.get(session['user_id'])
    if not user.farm_address:
        user.farm_address = address
        user.farm_size = size

    db.session.commit()
    flash('농장이 등록되었습니다.', 'success')
    return redirect(url_for('farmer_easy_mode', tab='account'))


def delete_farm(farm_id):
    if 'user_id' not in session or session.get('role') != 'farmer':
        return redirect(url_for('login_page'))
    farm = Farm.query.get_or_404(farm_id)
    if farm.farmer_id != session['user_id']:
        abort(403)
    db.session.delete(farm)
    user = User.query.get(session['user_id'])
    remaining = Farm.query.filter_by(farmer_id=user.id).order_by(Farm.created_at.asc()).first()
    user.farm_address = remaining.address if remaining else None
    user.farm_size = remaining.size if remaining else None
    db.session.commit()
    flash('농장이 삭제되었습니다.', 'success')
    return redirect(url_for('farmer_easy_mode', tab='account'))
```

**④ 라우트 등록**
`register(app)` 함수 안에 추가:

```python
app.add_url_rule('/verify_password', 'verify_password', verify_password, methods=['POST'])
app.add_url_rule('/farmer/update_info', 'farmer_update_info', farmer_update_info, methods=['POST'])
app.add_url_rule('/farmer/farm/add', 'add_farm', add_farm, methods=['POST'])
app.add_url_rule('/farmer/farm/<int:farm_id>/delete', 'delete_farm', delete_farm, methods=['POST'])
```

---

### 7. `templates/layout.html`

**① `<head>` 안에 theme.css link 추가**
`style.css` 링크 바로 위에 삽입:

```html
<link rel="stylesheet" href="{{ url_for('static', filename='css/theme.css') }}">
<link rel="stylesheet" href="{{ url_for('static', filename='css/style.css') }}">
```

**② 로고 링크 분기**
기존:
```html
<a href="/" class="site-logo">FarmLink</a>
```
변경:
```html
<a href="{% if session.get('role') == 'farmer' %}{{ url_for('farmer_easy_mode') }}{% else %}/{% endif %}" class="site-logo">FarmLink</a>
```

**③ 헤더 드롭다운 정리**
기존 드롭다운에 있던 항목들 교체:

```html
{# 변경 전 — 아래 블록 전체 교체 #}
{% if session.get('role') == 'farmer' %}
<a href="{{ url_for('toggle_view_mode') }}" class="btn-view-mode-toggle"> ... </a>
{% endif %}
```
→ 이 `toggle_view_mode` 버튼 블록 통째로 제거.

```html
{# 변경 전 #}
{% if session.get('role') == 'farmer' %}
<a href="{{ url_for('detailed_farmer_dashboard') }}">...</a>
{% else %}
<a href="{{ url_for('my_info') }}">...</a>
{% endif %}

{# 변경 후 #}
{% if session.get('role') != 'farmer' %}
<a href="{{ url_for('my_info') }}"><i class="fa-solid fa-user mr-1"></i> 내 정보</a>
{% endif %}
```

---

### 8. `static/css/theme.css`

**① CSS 변수 추가**
`:root { }` 블록 안, 기존 변수들 아래에 추가:

```css
/* 농장주 UI 전용 — 고령층 친화 접근성 기준 */
--farmer-font-base:    18px;
--farmer-font-label:   16px;
--farmer-font-heading: 24px;
--farmer-font-title:   30px;
--farmer-font-btn:     18px;
--farmer-btn-height:   56px;
--farmer-btn-padding:  14px 28px;
--farmer-btn-gap:      12px;
--farmer-input-height: 52px;
```

**② 기존 4줄 수정**
아래 줄들을 찾아서 교체 (폰트 크기 및 패딩 값이 변경됨):

```css
/* 변경 전 */
.fl-side-menu a { display:flex; align-items:center; gap:10px; padding:11px 14px; border-radius: var(--fl-radius); color: var(--fl-text); font-weight:600; white-space:nowrap; }

/* 변경 후 */
.fl-side-menu a { display:flex; align-items:center; gap:10px; padding:16px 18px; border-radius: var(--fl-radius); color: var(--fl-text); font-weight:600; white-space:nowrap; font-size: var(--farmer-font-base, 18px); }
```

```css
/* 변경 전 */
.fl-info-row { display:flex; align-items:center; gap:10px; padding:12px 0; border-bottom:1px solid var(--fl-border); }

/* 변경 후 */
.fl-info-row { display:flex; align-items:center; gap:10px; padding:14px 0; border-bottom:1px solid var(--fl-border); }
```

```css
/* 변경 전 */
.fl-info-row .lbl { color: var(--fl-text-muted); font-weight:600; min-width:120px; display:flex; align-items:center; gap:8px; }

/* 변경 후 */
.fl-info-row .lbl { color: var(--fl-text-muted); font-weight:600; min-width:120px; display:flex; align-items:center; gap:8px; font-size: var(--farmer-font-base, 18px); }
```

```css
/* 변경 전 */
.fl-info-row .val { font-weight:600; margin-left:auto; text-align:right; }

/* 변경 후 */
.fl-info-row .val { font-weight:600; margin-left:auto; text-align:right; font-size: var(--farmer-font-base, 18px); }
```

---

### 9. `static/css/style.css`

파일 **맨 끝**에 아래 블록 통째로 붙여넣기.
(기존 내용 건드리지 말고 맨 아래에만 추가)

> 내용이 너무 길어서 별도 파일로 분리: **`docs/style_additions.css`** 참고

---

## 병합 순서 권장

1. `models/farm.py`, `models/inquiry_reply.py` 파일 추가
2. `models/__init__.py` 수정
3. `routes/` 파일들 수정 (auth → experience → reservation → review → user_routes → farmer 순)
4. `templates/layout.html` 수정
5. [A] 파일들 통째로 교체
6. `static/css/theme.css` 수정
7. `static/css/style.css` 끝에 추가
8. 서버 실행 후 농장주 계정으로 로그인해서 4개 탭 동작 확인
