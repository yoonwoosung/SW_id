# 추억 광장(커뮤니티) 백엔드 구현 요청 명세

> 요청자: 프론트엔드 (준형)
> 작성일: 2026-08-27
> 목적: 사용자가 만든 앨범을 공개 공유하고, 추억 광장 페이지에서 다른 사람의 앨범을 탐색할 수 있는 기능

---

## 현재 상태

- **프론트 완료**: `/community` 페이지 목업, 공유 버튼·모달 UI 구현
- **데이터 연동 미완**: 현재 더미 데이터 및 localStorage 임시 저장 중
- **필요**: 아래 API + 라우트 + DB 변경 구현

---

## 1. DB 변경 — Album 테이블 컬럼 추가

기존 `album` 테이블에 아래 컬럼 1개 추가:

```sql
ALTER TABLE album
    ADD COLUMN is_public BOOLEAN NOT NULL DEFAULT FALSE;
```

| 컬럼 | 타입 | 기본값 | 설명 |
|------|------|--------|------|
| `is_public` | BOOLEAN | FALSE | TRUE이면 추억 광장에 노출 |

---

## 2. Flask 라우트 추가

### 커뮤니티 페이지 렌더링

```
GET /community
```

- 인증: 불필요 (비로그인도 접근 가능)
- 처리: `templates/community.html` 렌더링만 하면 됨 (데이터는 API로 별도 로드)
- 예시:

```python
@app.route('/community')
def community_page():
    return render_template('community.html')
```

---

## 3. API 목록

### 3-1. 공개 앨범 목록 조회

```
GET /api/community/albums
```

- 인증: 불필요
- 쿼리 파라미터:

| 파라미터 | 타입 | 기본값 | 설명 |
|----------|------|--------|------|
| `category` | string | `all` | `all` / `harvest` / `tour` / `family` / `eco` |
| `page` | int | 1 | 페이지 번호 |
| `per_page` | int | 16 | 페이지당 항목 수 |

- 응답:

```json
{
  "success": true,
  "total": 42,
  "page": 1,
  "pages": 3,
  "albums": [
    {
      "id": 7,
      "title": "딸기 수확의 날",
      "cover_theme": "cover-green",
      "shape_theme": "shape-portrait",
      "category": "harvest",
      "user_nickname": "김민지",
      "created_at": "2026-08-25T10:00:00"
    }
  ]
}
```

> `category` 값은 앨범 생성 시 사용자가 선택. Album 테이블에 `category VARCHAR(20)` 컬럼도 함께 추가 필요 (아래 참고).

---

### 3-2. 공개 앨범 단건 조회 (뷰어용)

```
GET /api/community/albums/<album_id>
```

- 인증: 불필요 (is_public=TRUE인 경우만 반환)
- 응답:

```json
{
  "success": true,
  "album": {
    "id": 7,
    "title": "딸기 수확의 날",
    "cover_theme": "cover-green",
    "shape_theme": "shape-portrait",
    "paper_theme": "paper-white",
    "inner_page_count": 4,
    "pages_data": [ ... ],
    "user_nickname": "김민지",
    "created_at": "2026-08-25T10:00:00"
  }
}
```

- is_public=FALSE인 앨범 요청 시:

```json
{ "success": false, "error": "not_found" }
```

---

### 3-3. 앨범 공개/비공개 전환

```
PUT /api/albums/<album_id>/visibility
Content-Type: application/json
```

- 인증: 필수 (본인 앨범만)
- 요청 바디:

```json
{
  "is_public": true,
  "category": "harvest"
}
```

- 응답:

```json
{ "success": true }
```

- 본인 소유가 아닌 앨범 요청 시:

```json
{ "success": false, "error": "forbidden" }
```

---

## 4. DB 변경 전체 요약

기존 `api_album_spec.md`의 테이블에 컬럼 2개 추가:

```sql
ALTER TABLE album
    ADD COLUMN is_public  BOOLEAN     NOT NULL DEFAULT FALSE,
    ADD COLUMN category   VARCHAR(20) NOT NULL DEFAULT 'all';
```

| 컬럼 | 타입 | 설명 |
|------|------|------|
| `is_public` | BOOLEAN | 추억 광장 공개 여부 |
| `category` | VARCHAR(20) | `all` / `harvest` / `tour` / `family` / `eco` |

---

## 5. 프론트 연동 계획

API 구현 완료 시 아래 2곳만 수정하면 됩니다:

| 위치 | 현재 (더미) | 교체 방향 |
|------|-------------|-----------|
| `community.html` 탭 필터 | 하드코딩 8장 | `GET /api/community/albums?category=` 호출로 교체 |
| `album_create.html` 공유 모달 확인 버튼 | localStorage 임시 저장 | `PUT /api/albums/<id>/visibility` 호출로 교체 |
| 뷰어 클릭 | `alert()` 임시 처리 | `GET /api/community/albums/<id>` → 앨범 뷰어 모달 오픈 |

---

## 6. 참고 사항

- `pages_data`가 base64 이미지 포함 시 응답 크기 문제 → 목록 조회(`3-1`)에서는 `pages_data` 제외, 단건 조회(`3-2`)에서만 포함
- 비로그인 사용자도 `/community` 페이지와 공개 앨범 조회 API는 접근 가능해야 함
- 앨범 뷰어에서 공개 앨범 표시 시 작성자 닉네임만 표시 (이메일, 개인정보 노출 금지)
