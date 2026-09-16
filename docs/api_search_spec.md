# `/api/search` 엔드포인트 명세

> 요청자: 프론트엔드 (준형)
> 목적: 메인 페이지 통합검색 AJAX 처리

---

## 기본 정보

| 항목 | 내용 |
|------|------|
| Method | `GET` |
| URL | `/api/search` |
| 인증 | 불필요 (비로그인 접근 가능) |

---

## 요청 파라미터 (Query String)

| 파라미터 | 타입 | 필수 | 설명 | 예시 |
|----------|------|------|------|------|
| `crop_query` | string | 선택 | 작물명·지역명·점포명 텍스트 검색 (LIKE) | `딸기` |
| `region` | string | 선택 | 지역 필터 (address_detail LIKE) | `경기` |
| `date_filter` | string (ISO 8601) | 선택 | 해당 날짜에 체험 가능한 항목만 반환.<br>`duration_start ≤ date_filter ≤ end_date` | `2026-08-30` |
| `people_count` | string | 선택 | 잔여석 ≥ 인원수인 항목만 반환.<br>값이 `5+` 이거나 없으면 필터 미적용 | `2` |
| `sort` | string | 선택 | 정렬 방식. 기본값: `deadline` | `deadline` \| `reviews` \| `recommended` |
| `page` | integer | 선택 | 페이지 번호. 기본값: `1` | `1` |
| `lat` | float | 선택 | 사용자 위도. `sort=recommended` 시 사용 | `37.5665` |
| `lon` | float | 선택 | 사용자 경도. `sort=recommended` 시 사용 | `126.9780` |

### 정렬 방식 상세

| sort 값 | 동작 |
|---------|------|
| `deadline` | 마감 임박순 (`end_date` 오름차순). 마감된 항목은 뒤로 |
| `reviews` | 리뷰 많은순 (Review COUNT 내림차순). 마감된 항목은 뒤로 |
| `recommended` | GPS 기반 추천순. `lat`/`lon` 없으면 `deadline`과 동일하게 처리 |

---

## 공통 필터 조건 (항상 적용)

- `Experience.status == 'recruiting'`
- `Experience.end_date >= 오늘 날짜`

---

## 응답 형식

### 성공 (200 OK)

```json
{
  "success": true,
  "items": [
    {
      "id": 1,
      "crop": "딸기",
      "address_detail": "경기도 용인시 처인구",
      "cost": 25000,
      "first_image": "exp_1_abc123.jpg",
      "remaining_spots": 3,
      "pesticide_free": false,
      "is_specialty": true,
      "d_day": 5,
      "distance": 12.3
    }
  ],
  "total": 42,
  "pages": 3,
  "page": 1
}
```

### 실패 (서버 오류 등)

```json
{
  "success": false,
  "message": "오류 설명"
}
```

---

## 응답 필드 상세

### 최상위 필드

| 필드 | 타입 | 설명 |
|------|------|------|
| `success` | boolean | 성공 여부 |
| `items` | array | 체험 목록 (최대 15개/페이지) |
| `total` | integer | 전체 결과 수 |
| `pages` | integer | 전체 페이지 수 |
| `page` | integer | 현재 페이지 번호 |

### `items[]` 각 항목

| 필드 | 타입 | 설명 |
|------|------|------|
| `id` | integer | 체험 ID (`/experience/{id}` URL 구성에 사용) |
| `crop` | string | 작물명 |
| `address_detail` | string | 주소 |
| `cost` | integer | 1인 체험 비용 (원) |
| `first_image` | string \| null | 대표 이미지 파일명. 없으면 `null`.<br>프론트에서 `/static/uploads/{first_image}` 로 조합 |
| `remaining_spots` | integer | 잔여석 (`max_participants - current_participants`) |
| `pesticide_free` | boolean | 친환경 여부 |
| `is_specialty` | boolean | 지역 특산물 여부 (기존 `matches_specialty` 로직 그대로) |
| `d_day` | integer | 마감까지 남은 일수. 날짜 없으면 `999` |
| `distance` | float \| null | 사용자와의 거리(km). `sort=recommended` + GPS 있을 때만 값, 나머지는 `null` |

---

## 요청 예시

```
GET /api/search?crop_query=딸기&region=경기&date_filter=2026-08-30&people_count=2&sort=deadline&page=1
```

```
GET /api/search?sort=recommended&lat=37.5665&lon=126.9780&page=1
```

---

## 참고 사항

- 페이지당 고정 15건
- `sort=recommended` + GPS 있을 때: 반경 150km 이내만 반환, `calculate_score` 기준 정렬 (기존 `index()` 로직과 동일)
- 기존 `index()` 함수의 필터링·정렬 로직을 그대로 재사용 가능
- `is_specialty` 판정은 기존 `REGIONAL_SPECIALTIES` + `matches_specialty` 함수 그대로 사용
