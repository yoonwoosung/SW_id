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

**★중첩 구조 + 그룹★**: 각 노드는 `{code, label, children?}`. 최상위 노드엔 `group`(travel/taste/practical)이 붙고,
응답에 `groups`(그룹 라벨)이 함께 온다. `children`은 여러 단계로 중첩된다(지역 → 시/도 → 시/군 → 구, 반려견 → 동반가능 → 몸무게 → 목줄/케이지, 인원 → 인원수/연령대구성).

**최상위 13개**(그룹별):
- **여행 조건(travel)**: `region`(지역) · `companion_type`(혼자/커플/가족(아이)/친구/부모님/반려견) · `pet_dog`(반려견) · `party`(인원수·연령대구성) · `schedule`(당일/1박2일)
- **취향·활동(taste)**: `experience_type`(수확/먹거리/공예/동물교감/자연생태) · `activity`(승마/카약/낚시/등산/자전거) · `mood`(힐링/액티브/인생샷/교육적/전통) · `season`(봄딸기/여름블루베리/가을수확/겨울)
- **실용 조건(practical)**: `budget_range`(코스 총비용 구간·`note` 포함) · `transport`(교통) · `duration_hours`(2시간/반나절/종일) · `facility`(주차/화장실/무장애/와이파이/수유실/무농약/유기농)

```jsonc
// 200
{ "success": true,
  "data": {
    "groups": [ {"code":"travel","label":"여행 조건"}, {"code":"taste","label":"취향·활동"}, {"code":"practical","label":"실용 조건"} ],
    "categories": [
      { "code": "region", "label": "지역", "group": "travel", "children": [
        { "code": "chungnam", "label": "충남", "children": [
          { "code": "cheonan", "label": "천안", "children": [ {"code":"cheonan_dongnam","label":"동남구"}, ... ] } ] } ] },
      { "code": "party", "label": "인원", "group": "travel", "children": [
        { "code": "headcount", "label": "인원수", "children": [ {"code":"party_2","label":"2명"}, ... ] },
        { "code": "age_composition", "label": "연령대 구성", "children": [ {"code":"with_child","label":"아이 동반"}, ... ] } ] },
      { "code": "budget_range", "label": "예산대", "group": "practical",
        "note": "*1인당 코스 총비용(교통·식사 포함) 기준입니다",
        "children": [ {"code":"course_30_50k","label":"3~5만원"}, {"code":"course_50_100k","label":"5~10만원"}, ... ] }
    ] },
  "error": null }
```

**드롭박스 렌더 규칙(준형용)**: `groups` 순서로 섹션을 나누고, 각 최상위 카테고리를 자기 `group` 섹션의 아코디언 헤더로 둔다.
`children`을 재귀로 펼치고, `children`이 없는 노드에만 체크박스. `note`가 있으면 그 카테고리 아래 주석으로 노출(예: 예산대 "*1인당").
선택 시 값은 **잎의 `code`**, 키는 **최상위 카테고리 `code`**.

### 선택 조건 형식
```jsonc
{ "region": ["cheonan_dongnam"], "activity": ["kayak"], "experience_type": ["harvest"],
  "pet_dog": ["dog_medium"], "budget_range": ["course_30_50k"],
  "transport": ["car"], "facility": ["parking","wifi"], "mood": ["healing"] }
```

### 추천 목록에 조건 가점 적용
조건을 `cond_<최상위카테고리>=<잎코드>` 파라미터로 넘기면 일치 체험이 상위로 온다.
예: `GET /api/recommendations/personalized?lat=..&lon=..&cond_region=chungnam&cond_budget_range=course_30_50k&cond_facility=wifi`
- 일치 1건당 `CATEGORY_MATCH_SCORE`(현재 0.3) 가산.
- **점수 반영(Experience 데이터 있는 항목)**: region(주소 키워드), **budget_range(★코스 총비용 1인당★ = 체험비+교통+식사 추정, `course_builder.estimate_course_cost_per_person`)**,
  activity(`activity_type`), pet_dog(몸무게 티어 ↔ `pet_allowed`·`pet_max_weight_kg`), transport(자가용 ↔ `has_parking`),
  facility(주차·와이파이·무농약·유기농).
- **점수 미반영(UI·역제안 저장용)**: companion_type, party, schedule, experience_type, mood, season, duration_hours, 반려견 목줄/케이지 세부, 대중교통/도보/자전거, 화장실·무장애·수유실.

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
    ],
    "summary": { "estimated_cost": 45000, "transport": "자가용", "barrier_free": true }
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

### summary(코스 카드용, 파트 보강)
| 필드 | 설명 |
|---|---|
| estimated_cost | 예상 1인 비용 = 체험 비용 + 점심·카페 추정치(`COURSE_EXTRA_COST_ESTIMATE`) |
| transport | 이동수단: `has_parking` 이면 "자가용", 아니면 "대중교통" |
| barrier_free | 무장애 확인 여부(`Experience.barrier_free`). true인 코스만 무장애 로고 표시 |

### 참고
- 장소 데이터: 한국관광공사 일반 관광정보 API(`external/tour_api.py`). `.env`에 `TOUR_API_KEY`를 넣으면 실제 장소가 채워지고, 없으면 `items`는 체험 항목만 나온다(오류 아님).
- `reason`은 현재 규칙 기반 문장이며, 추후 LLM(`services/course_reason.py`)으로 교체 가능하다. LLM은 코스에 담긴 장소만 근거로 설명하게 하여 장소를 새로 지어내지 않는다.
- KTO에 별도 '카페' 종류가 없어 카페 슬롯도 음식점(contentType 39)에서 (식당과 중복되지 않게) 선정한다. — 개선 여지(TODO).

---

## ESG 점수

`GET /api/experiences/<id>/esg` — 체험(농장)의 지속가능성 점수. Experience 속성(무농약·유기농·봉사·주차)으로 산출.

```jsonc
{ "success": true, "data": {
    "experience_id": 1, "score": 45, "grade": "C",
    "breakdown": [
      {"key":"pesticide_free","label":"무농약 재배","earned":35,"max":35},
      {"key":"organic","label":"유기농 인증","earned":0,"max":30},
      {"key":"volunteer","label":"봉사 프로그램 운영","earned":0,"max":25},
      {"key":"parking","label":"주차 접근성","earned":10,"max":10}
    ] }, "error": null }
```
- 등급: A≥80 / B≥60 / C≥40 / D<40. 배점은 `common/constants.py`(ESG_SCORE_*).

## 맞춤 체험 추천

`GET /api/experiences/recommendations?lat=<위도>&lon=<경도>` — 좌표 기준 추천 점수순 체험 목록.
좌표 없으면 400(`COORDS_REQUIRED`).

```jsonc
{ "success": true, "data": {
    "count": 3,
    "results": [ {"id":1,"crop":"쌀","address":"경기도 이천시 ...","distance_km":4.9,"score":0.83}, ... ]
  }, "error": null }
```

## 맞춤 추천(회원 이력·세그먼트 반영)

`GET /api/recommendations/personalized?lat=<위도>&lon=<경도>` — 위치 + (로그인 시)회원 이력 + 세그먼트 인기를 합산한 추천.
조건은 `cond_<카테고리>=<잎코드>`로 함께 넘길 수 있다. 좌표 없으면 400(`COORDS_REQUIRED`).

```jsonc
{ "success": true, "data": {
    "personalized": true,        // 로그인 사용자 여부
    "segment_applied": true,     // 같은 성별·나이대 인기 신호가 반영됐는지
    "count": 3,
    "results": [
      {"id":2,"crop":"포도","address":"경기도 안성시 ...","cost":25000,"barrier_free":false,
       "distance_km":6.3,"score":1.13,
       "reasons":["나와 비슷한 분들이 많이 봤어요","이 지역 대표 특산물이에요","가까워요(약 6.3km)"]}
    ]
  }, "error": null }
```
- 가점: 과거 신청 작물(`PERSONALIZE_CROP_BOOST`) + 세그먼트 인기(`SEGMENT_TREND_BOOST`) + 조건 일치(`CATEGORY_MATCH_SCORE`).
- **폴백**: 프로필(성별·나이대 등)이 없으면 세그먼트 미적용(`segment_applied:false`) → 규칙 기반(거리·특산물)으로만 추천.

## 클릭 로그 · 트렌드 (파트3)

개인화의 원천. 체험 상세 조회 시 서버가 자동으로 클릭을 적재하며, 프론트가 카테고리/체험 클릭을 직접 보낼 수도 있다.

### 클릭 적재
`POST /api/click-logs`  (성공 201)
```jsonc
// body(JSON 또는 form)
{ "target_type": "category", "target_id": "harvest" }   // target_type: "experience" | "category"
// 200/201
{ "success": true, "data": { "recorded": true }, "error": null }
// 400
{ "success": false, "data": null, "error": { "code": "INVALID_CLICK", "message": "target_type·target_id가 올바르지 않습니다." } }
```
- 로그인 여부와 무관하게 적재(비로그인은 `user_id=null`). **비로그인 클릭은 세그먼트 집계에서 제외**된다.
- 개인정보 최소화: 성별·나이대는 로그에 저장하지 않고, 집계 시 `user_id`로 회원과 join해서만 사용한다.

### 트렌드 키워드
`GET /api/trend-keywords` — 최근 많이 눌린 카테고리 상위(검색창 하단 노출용).
```jsonc
{ "success": true, "data": { "keywords": [
    { "code": "harvest", "label": "수확체험", "count": 42 },
    { "code": "kayak", "label": "카약", "count": 17 } ] }, "error": null }
```
- 세그먼트("가족과 함께 / 20대" 등)는 수동 정의하지 않고, `성별×나이대×대상` 집계에서 **자동 도출**한다.

## 포인트

결제 완료 시 결제금액의 `POINT_EARN_RATE`(현재 5%)만큼 자동 적립. 잔액은 내역 합계로 계산(`PointLog`).

### 내 포인트 조회
`GET /api/users/me/points` — 로그인 필수(비로그인 **403 LOGIN_REQUIRED**)
```jsonc
{ "success": true,
  "data": { "balance": 3750, "logs": [
    { "amount": 3750, "reason": "payment", "application_id": 3, "created_at": "2026-07-29T20:15:03" }
  ] },
  "error": null }
```
| 필드 | 설명 |
|---|---|
| balance | 현재 잔액(내역 SUM) |
| logs[].amount | 적립 `+` / 사용 `−` |
| logs[].reason | 사유 코드(`payment` 등) |
| logs[].application_id | 적립 근거 예약(없으면 `null`) |
| logs[].created_at | 시각(ISO 8601) |

- **적립 시점**: `POST /api/payments` 성공 시. 같은 예약엔 **한 번만**(멱등). 결제 응답에도 `earned_points`가 포함됨.
- **내 활동 연동**: 포인트 영역이 이 API의 `balance`(잔액)와 `logs`(내역)를 사용.

## 더미 결제(간편결제)

실제 PG 연동 없이 **예약 상태만 전이**하는 더미 결제. 로그인 필수, 본인 예약만.

- **팝업 페이지**: `GET /payments/<application_id>` — "간편결제" + 금액(인원수×체험가격) + `[결제하기]`만 있는 간결한 창(로그인·본인 소유 아니면 403/404).
- **결제 처리**: `POST /api/payments` body `{ "application_id": 3 }`
  - 성공 → **201**, 예약 상태 `예정` → `결제완료`
  - 본인 아님 → **403 FORBIDDEN** / 없음 → **404 APPLICATION_NOT_FOUND** / 이미 결제·취소 등 → **400 ALREADY_PROCESSED** / 잘못된 body → **400 INVALID_APPLICATION_ID**
```jsonc
{ "success": true,
  "data": { "application_id": 3, "status": "결제완료", "amount": 50000 },
  "error": null }
```
- **예약 흐름 연결**: 신청(`예정`) → 신청완료 화면의 `[간편결제로 예약 확정하기]` → 팝업 → 성공 시 `결제완료`.
  농장주 확정(`confirm_application`)은 `예정`·`결제완료` 둘 다 `확정`으로 넘길 수 있게 확장됨.
- 상표(토스·카카오페이 등) 미사용, 자체 "FarmLink 간편결제" 명칭.

## 찜(Wishlist)

로그인 필수(비로그인은 모두 `403 LOGIN_REQUIRED`). 응답은 공통 `{success,data,error}`.

### 찜 등록
`POST /api/wishlists`  body: `{ "experience_id": 2 }`
- 신규 → **201**, 이미 찜한 상태 → **200 멱등**(기존 것 반환)
```jsonc
{ "success": true, "data": { "id": 5, "experience_id": 2, "created": true }, "error": null }
// 잘못된 body → 400 INVALID_EXPERIENCE_ID / 없는 체험 → 404 EXPERIENCE_NOT_FOUND
```
`data.id`가 **wishlist id**(해제 시 사용).

### 찜 해제
`DELETE /api/wishlists/<wishlist_id>`  (본인 것만)
```jsonc
{ "success": true, "data": { "removed": true }, "error": null }
// 남의 찜 → 403 FORBIDDEN / 없음 → 404 WISHLIST_NOT_FOUND
```

### 내 찜 목록
`GET /api/wishlists` — 최신순, 체험 정보 포함
```jsonc
{ "success": true, "data": { "wishlists": [
    { "id": 5, "experience_id": 2, "name": "포도 체험", "image": "g1.jpg", "cost": 25000, "created_at": "2026-07-29T20:15:03" }
] }, "error": null }
```
| 필드 | 설명 |
|---|---|
| id | **wishlist id**(해제용) |
| experience_id | 체험 id |
| name | `{작물} 체험`(파생) |
| image | 대표이미지 파일명(`/static/uploads/<image>`), 없으면 `null` |
| cost | 1인 가격(원) |
| created_at | 찜한 시각(ISO 8601) |

> 프론트 연동: 상세 페이지 하트는 로드 시 `GET /api/wishlists`로 현재 체험 포함 여부를 확인해 상태를 표시하고, 클릭 시 `POST`(→ 반환된 `id` 보관) / `DELETE /api/wishlists/<id>`를 호출한다. "내 활동" 찜 목록도 `GET /api/wishlists`를 사용.

## 내 활동 — 최근 본 체험

`GET /api/users/me/recent-views` — 로그인 사용자가 최근 열람한 체험 목록(`click_log` 기반).
같은 체험은 가장 최근 열람 1건만, 최신순, 최대 `RECENT_VIEWS_LIMIT`(현재 10)개. **비로그인은 빈 배열**(오류 아님).

```jsonc
// 200
{ "success": true,
  "data": { "recent_views": [
    { "id": 2, "name": "포도 체험", "image": "grape1.jpg", "cost": 25000, "viewed_at": "2026-07-29T20:15:03" }
  ] },
  "error": null }

// 비로그인 → 200
{ "success": true, "data": { "recent_views": [] }, "error": null }
```
| 필드 | 설명 |
|---|---|
| id | 체험 id |
| name | 표시명(`{작물} 체험`, Experience에 name 컬럼이 없어 파생) |
| image | 대표이미지 **파일명만**. 프론트가 `/static/uploads/<image>`로 조합. 사진 없으면 `null` |
| cost | 1인 가격(원) |
| viewed_at | 열람 시각(ISO 8601) |

> 별도 저장 테이블 없이 기존 열람 로그(`target_type='experience'`)를 조회만 한다.

## 농산물(특산물) 정보

`GET /api/products` — 지역별 특산물 전체. `?region=<지역명>`으로 부분일치 필터.

```jsonc
// GET /api/products?region=이천
{ "success": true, "data": {
    "region": "이천",
    "results": [ {"region":"이천","specialties":["쌀","복숭아"]} ]
  }, "error": null }
```

