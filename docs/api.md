# FarmLink API 명세 (프론트 연동용)

모든 응답은 아래 공통 형식을 따른다.

```jsonc
// 성공
{ "success": true,  "data": { ... },  "error": null }
// 실패
{ "success": false, "data": null, "error": { "code": "대문자코드", "message": "한글메시지" } }
```

상태코드: 성공 200 / 생성 201 / 잘못된요청 400 / 권한없음 403 / 없음 404 / 서버오류 500

---

## 주변 시설 조회 (관광공사 API)

체험(농장) 좌표를 기준으로 주변 시설을 거리순으로 반환한다.
공통 쿼리 파라미터: `?radius=<미터>` (선택, 기본 3000, 최대 20000).
각 항목에는 농장 기준 거리 `distance_km`가 포함되며 가까운 순으로 정렬된다.

> 참고: 실제 관광공사 키(`PET_API_KEY` 등)가 없으면 `data`는 항상 빈 배열 `[]`로 응답한다(오류 아님).

### 1) 반려동물 동반 시설
`GET /api/experiences/<id>/pet-facilities`

| 필드 | 설명 |
|---|---|
| name | 시설명 |
| category | 분류 코드 |
| address | 주소 |
| tel | 전화번호 |
| lat, lng | 좌표 |
| distance_km | 농장 기준 거리(km) |

### 2) 무장애 여행지
`GET /api/experiences/<id>/barrier-free`

| 필드 | 설명 |
|---|---|
| name | 장소명 |
| address | 주소 |
| lat, lng | 좌표 |
| wheelchair | 휠체어 접근 가능 여부(bool) |
| stroller | 유모차 접근 가능 여부(bool) |
| disabled_toilet | 장애인화장실 유무(bool) |
| distance_km | 농장 기준 거리(km) |

### 3) 의료 시설
`GET /api/experiences/<id>/medical`

| 필드 | 설명 |
|---|---|
| name | 병원/응급센터명 |
| category | 분류 코드 |
| address | 주소 |
| tel | 전화번호 |
| lat, lng | 좌표 |
| distance_km | 농장 기준 거리(km) |

### 응답 예시
```jsonc
// GET /api/experiences/1/pet-facilities  → 200
{ "success": true,
  "data": [
    { "name": "○○카페", "category": "A05", "address": "경기 이천시 ...",
      "tel": "031-000-0000", "lat": 37.27, "lng": 127.44, "distance_km": 1.2 }
  ],
  "error": null }

// GET /api/experiences/9999/pet-facilities  → 404
{ "success": false, "data": null,
  "error": { "code": "EXPERIENCE_NOT_FOUND", "message": "체험을 찾을 수 없습니다." } }
```

### 예시 URL (로컬)
- http://127.0.0.1:8000/api/experiences/1/pet-facilities
- http://127.0.0.1:8000/api/experiences/1/barrier-free
- http://127.0.0.1:8000/api/experiences/1/medical
- http://127.0.0.1:8000/api/experiences/1/pet-facilities?radius=5000

---

## 조건 카테고리 (필터·역제안 공용)

### 카테고리 트리 조회
`GET /api/search-categories`

프론트가 드롭박스(아코디언)를 그리는 기준. 필터 검색과 역제안 요청글이 **동일한 트리**를 쓴다.

```jsonc
// 200
{ "success": true,
  "data": { "categories": [
    { "code": "region", "label": "지역",
      "items": [ {"code":"seoul","label":"서울"}, {"code":"chungnam","label":"충남"}, ... ] },
    { "code": "experience_type", "label": "체험종류",
      "items": [ {"code":"harvest","label":"수확"}, ... ] },
    { "code": "companion_type", "label": "동반유형", "items": [ ... ] },
    { "code": "budget_range", "label": "예산대",
      "items": [ {"code":"range_20k","label":"2만원대"}, ... ] },
    { "code": "facility", "label": "편의시설",
      "items": [ {"code":"parking","label":"주차"}, ... ] }
  ] },
  "error": null }
```

### 선택 조건 형식
```jsonc
{ "region": ["chungnam"], "experience_type": ["harvest"],
  "companion_type": ["child"], "budget_range": ["range_20k"],
  "facility": ["parking","pesticide_free"] }
```

### 추천 목록에 조건 가점 적용
목록 조회(`GET /`, 추천 정렬) 시 조건을 `cond_<카테고리>` 파라미터로 넘기면, 조건과 일치하는
체험이 상위로 온다. 예: `GET /?sort=recommended&lat=..&lon=..&cond_region=chungnam&cond_facility=parking`
- 일치 1건당 `CATEGORY_MATCH_SCORE`(현재 0.3) 가산.
- 점수 반영은 Experience에 데이터가 있는 항목만: **region, budget_range, facility(주차·무농약·유기농인증)**.
  experience_type·companion_type·무장애·화장실은 드롭박스(필터 UI)용이며 점수 미반영(대응 컬럼 없음).

---

## 역제안 (리버스 매칭)

사용자가 조건을 담은 요청글을 올리면, 농장주가 제안을 보낸다. 농장주에게는 자기 농장과
잘 맞는 요청이 `match_score`(카테고리 일치 수) 순으로 뜬다.

| 메서드·경로 | 설명 | 권한 | 성공코드 |
|---|---|---|---|
| `POST /api/user-requests` | 요청글 작성 | 로그인 | 201 |
| `GET /api/user-requests` | 열린 요청글 목록 | - | 200 |
| `GET /api/user-requests/<id>` | 요청글 상세(+제안 목록) | - | 200 |
| `POST /api/user-requests/<id>/proposals` | 농장주가 제안 | 농장주 | 201 |
| `GET /api/farmers/me/matching-requests` | 나에게 맞는 요청(점수순) | 농장주 | 200 |

### 요청글 작성 body 예시
```jsonc
// POST /api/user-requests
{ "title": "주말 수확체험 원해요",
  "conditions": { "region": ["gyeonggi"], "facility": ["parking"] },
  "participants": 4, "desired_date_start": "2026-08-01", "desired_date_end": null }
```
`conditions`는 `/api/search-categories`의 코드값을 그대로 사용한다.

### 제안 작성 body 예시
```jsonc
// POST /api/user-requests/1/proposals
{ "message": "저희 이천 농장 어떠세요", "experience_id": 1,
  "proposed_price": 25000, "proposed_date": null }
```

### 에러 코드
`LOGIN_REQUIRED`(403) · `FARMER_ONLY`(403) · `REQUEST_NOT_FOUND`(404) ·
`TITLE_REQUIRED`/`MESSAGE_REQUIRED`/`INVALID_CONDITIONS`(400)

---

## AI 추천 코스

체험(농장) 위치를 기준으로 주변 장소를 **시간순 코스**(오전 체험 → 점심 맛집 → 오후 관광 → 카페)로 구성한다.
장소 선정·순서는 규칙 기반(거리순·중복 제거)이며, `reason`은 추천 이유 한 줄이다.

### 코스 조회
`GET /api/experiences/<id>/course`

```jsonc
// 200 (정상)
{ "success": true,
  "data": {
    "experience_id": 1,
    "reason": "'딸기 체험'과 가까운 인기 장소 3곳으로 구성한 코스입니다.",
    "items": [
      {"time":"09:00","type":"experience","name":"딸기 체험","distance_km":0.0},
      {"time":"12:30","type":"restaurant","name":"○○식당","address":"...","distance_km":2.1},
      {"time":"15:00","type":"attraction","name":"○○관광지","address":"...","distance_km":5.0},
      {"time":"17:00","type":"cafe","name":"○○카페","address":"...","distance_km":3.2}
    ]
  },
  "error": null }

// 200 (주변 장소를 못 가져온 경우 — 화면이 죽지 않도록 체험 항목 + 안내 메시지)
{ "success": true,
  "data": {
    "experience_id": 1, "reason": null,
    "items": [ {"time":"09:00","type":"experience","name":"딸기 체험","distance_km":0.0} ],
    "message": "코스를 생성할 수 없습니다. 주변 장소 정보를 불러오지 못했습니다."
  },
  "error": null }

// 404 (없는 체험)
{ "success": false, "data": null,
  "error": { "code": "EXPERIENCE_NOT_FOUND", "message": "체험을 찾을 수 없습니다." } }
```

### 참고
- 장소 데이터: 한국관광공사 일반 관광정보 API(`external/tour_api.py`). `.env`에 `TOUR_API_KEY`를 넣으면 실제 장소가 채워지고, 없으면 `items`는 체험 항목만 나온다(오류 아님).
- `reason`은 현재 규칙 기반 문장이며, 추후 LLM(`services/course_reason.py`)으로 교체 가능하다. LLM은 코스에 담긴 장소만 근거로 설명하게 하여 장소를 새로 지어내지 않는다.
- KTO에 별도 '카페' 종류가 없어 카페 슬롯도 음식점(contentType 39)에서 (식당과 중복되지 않게) 선정한다. — 개선 여지(TODO).

