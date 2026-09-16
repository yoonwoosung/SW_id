# 추억 앨범(추억일지) 백엔드 구현 요청 명세

> 요청자: 프론트엔드 (준형)
> 작성일: 2026-08-26
> 목적: 현재 localStorage 전용인 앨범 데이터를 서버에 영속 저장하기 위한 API 구현 요청

---

## 현재 상태

- **라우트**: `GET /album/create` → `album_create.html` 렌더링 (이미 구현됨)
- **데이터 저장**: 브라우저 localStorage (`fl_albums` 키)에만 저장
- **문제**: 브라우저 초기화·타기기 접근 시 앨범 유실

---

## 데이터 모델 (Album)

프론트에서 현재 사용하는 앨범 객체 구조:

```json
{
  "id": "album_1724629800000",
  "title": "딸기 추억 앨범",
  "shapeTheme": "shape-portrait",
  "coverTheme": "cover-green",
  "paperTheme": "paper-white",
  "innerPageCount": 4,
  "pagesData": [
    {
      "title": "딸기 추억 앨범",
      "elements": [],
      "template": "free"
    }
  ],
  "createdAt": "2026-08-26T10:00:00.000Z",
  "updatedAt": "2026-08-26T12:00:00.000Z"
}
```

### `pagesData[].elements[]` 항목 구조

| type | 필드 | 설명 |
|------|------|------|
| `slot` | `id`, `type`, `label`, `top`, `left`, `width`, `height`, `src` | 레이아웃 틀 사진 슬롯 |
| `image` | `id`, `type`, `src`, `top`, `left`, `width`, `height`, `rotation` | 자유 배치 사진 |
| `text` | `id`, `type`, `text`, `top`, `left`, `width`, `height`, `rotation` | 자유 배치 텍스트 |

> `src`는 현재 base64 data URL 또는 `/static/uploads/` 경로 문자열

---

## 필요한 API 목록

### 1. 앨범 목록 조회

```
GET /api/albums
```

- 인증: 필수 (세션)
- 응답:
```json
{
  "success": true,
  "albums": [
    {
      "id": 1,
      "title": "딸기 추억 앨범",
      "shape_theme": "shape-portrait",
      "cover_theme": "cover-green",
      "paper_theme": "paper-white",
      "inner_page_count": 4,
      "created_at": "2026-08-26T10:00:00",
      "updated_at": "2026-08-26T12:00:00"
    }
  ]
}
```

---

### 2. 앨범 생성

```
POST /api/albums
Content-Type: application/json
```

- 인증: 필수
- 요청 바디:
```json
{
  "title": "딸기 추억 앨범",
  "shape_theme": "shape-portrait",
  "cover_theme": "cover-green",
  "paper_theme": "paper-white",
  "inner_page_count": 4,
  "pages_data": [ ... ]
}
```
- 응답:
```json
{
  "success": true,
  "album_id": 1
}
```

---

### 3. 앨범 수정 (저장)

```
PUT /api/albums/<album_id>
Content-Type: application/json
```

- 인증: 필수 (본인 앨범만)
- 요청 바디: 생성과 동일 구조
- 응답:
```json
{ "success": true }
```

---

### 4. 앨범 삭제

```
DELETE /api/albums/<album_id>
```

- 인증: 필수 (본인 앨범만)
- 응답:
```json
{ "success": true }
```

---

### 5. 앨범 단건 조회 (편집 재개용)

```
GET /api/albums/<album_id>
```

- 인증: 필수
- 응답:
```json
{
  "success": true,
  "album": {
    "id": 1,
    "title": "딸기 추억 앨범",
    "shape_theme": "shape-portrait",
    "cover_theme": "cover-green",
    "paper_theme": "paper-white",
    "inner_page_count": 4,
    "pages_data": [ ... ],
    "created_at": "...",
    "updated_at": "..."
  }
}
```

---

## DB 테이블 제안

```sql
CREATE TABLE album (
    id          INT AUTO_INCREMENT PRIMARY KEY,
    user_id     INT NOT NULL,
    title       VARCHAR(20) NOT NULL DEFAULT '제목 없음',
    shape_theme VARCHAR(30) NOT NULL DEFAULT 'shape-portrait',
    cover_theme VARCHAR(30) NOT NULL DEFAULT 'cover-green',
    paper_theme VARCHAR(30) NOT NULL DEFAULT 'paper-white',
    inner_page_count INT NOT NULL DEFAULT 2,
    pages_data  LONGTEXT,          -- JSON 직렬화 저장
    created_at  DATETIME DEFAULT CURRENT_TIMESTAMP,
    updated_at  DATETIME DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user(id) ON DELETE CASCADE
);
```

---

## 프론트 연동 계획

API가 구현되면 프론트에서 아래 함수만 교체하면 됩니다 (나머지 UI 코드는 변경 없음):

| 현재 함수 | 교체 방향 |
|-----------|-----------|
| `getAllAlbums()` | `GET /api/albums` 호출로 교체 |
| `saveAllAlbums()` | `POST` 또는 `PUT /api/albums/<id>` 호출로 교체 |
| `deleteAlbum(id)` | `DELETE /api/albums/<id>` 호출로 교체 |

---

## 참고 사항

- `pages_data`는 JSON이 크므로 LONGTEXT 권장
- 사진 `src`가 현재 base64라면 서버 저장 시 용량 문제 있음 → 별도 이미지 업로드 API(`POST /api/albums/images`) 추가 고려
- 현재 `/album/create` 라우트에서 `applications`(예약 목록)을 이미 전달 중 → 앨범-체험 연동 필요 시 `experience_id` 필드 추가 가능
