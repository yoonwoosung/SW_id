# 다음 작업 메모

마감(2026-09-21) 이후에 이어서 할 것들. 각 항목은 "왜 지금 안 했는지"를 함께 적는다.

## 0. ★심사 종료 직후 — 공모전 심사 계정 정리★ (최우선)

공모전 지정 비밀번호(`2026openapi!`)는 ★제출 서류에 공개되는 값★이다.
그 계정이 역할 전환으로 관리자가 될 수 있으므로, 서류를 보는 누구나
농장 승인·반려와 유기농 인증 심사를 조작할 수 있는 상태다.

심사가 끝나면 아래 중 하나는 반드시 한다.

  ㄱ. `common/constants.ROLE_SWITCH_ALLOWED_EMAILS = ()` 로 비운다
      → 전환 기능이 통째로 꺼진다. 가장 확실하다.
  ㄴ. 비밀번호를 바꾼다
      OPENAPI_PASSWORD='새비밀번호' python3 seed_openapi.py
  ㄷ. 세 계정을 지운다 (openapi@ / openapi.farmer@ / openapi.admin@)

왜 지금 안 하나: 심사 기간에는 심사위원이 써야 한다.

관련: `seed_openapi.py`, `routes/auth.switch_role`, `tests/test_role_switch.py`

## 1. CSV 장소로 편의시설 조건 판정

`data/tour_standard.csv`(관광지정보 표준데이터, 전국 840건)에는
관광공사 API 에 ★없는★ 편의시설 정보가 들어 있다.

| 항목 | 채워진 건수 |
|---|---|
| `공공편익시설정보` | 840 / 840 (100%) |
| '화장실' 포함 | **651건** |
| '주차' 포함 | 498건 |
| `주차가능수` > 0 | **744건** |

상위 항목: 화장실 519 · 주차장 459 · 관리사무소 119 · 관광안내소 57 ·
공중화장실 31 · 샤워장 23 · 수유실 21

`external/tour_csv.py` 의 `_to_place()` 가 이미 `facilities`·`parking_count`
필드로 실어 두었다. **지금은 아무 데서도 읽지 않는다.**

### 왜 지금 안 했나
편의시설 대분류는 `services/category_match.py` 가 ★체험(Experience) 속성★으로
판정한다. CSV 는 ★코스 장소★ 속성이라 판정 구조가 다르다. 둘을 섞으려면
`place_score` 에 편의시설 계열 규칙을 새로 붙여야 하는데, 마감일에 감수할
범위가 아니라고 판단했다.

### 할 일
- `services/place_score.py` 에 `facilities` 문자열 포함 여부로 판정하는 규칙 추가
  (`restroom` → '화장실', `parking` → '주차')
- `restroom` 은 2026-09-20 에 "대응 컬럼이 없어" 화면에서 감췄다
  (`common/search_categories.py` 의 `hidden: True`). 되살릴 수 있다.
- 단, 관광공사 결과 장소에는 이 정보가 없어 ★CSV 출처 장소만★ 점수를 받는다.
  그 비대칭을 사용자에게 어떻게 보일지 정해야 한다.

## 2. 충남 올담 API

`external/chungnam_api.py` 는 골격만 완성돼 있고 `_extract_items()`·`_to_place()`
두 함수가 TODO 다. 2026-09-18 부터 서버가 "서비스 확대를 위한 작업 중"으로
HTML 점검 페이지만 돌려준다(9/20 기준 미복구).

복구되면 두 함수만 채우면 된다. 나머지(WAF 우회 UA·HTML 감지·혼합 인코딩·
1시간 캐싱·`place_merge` 연결·화면 표시)는 모두 연결돼 있다.
지금도 빈 리스트를 돌려주어 아무것도 깨뜨리지 않는다.

## 3. 반려동물 동반여행 API

`KorPetTourService2` 는 살아 있으나 키에 활용신청이 안 돼 있다
(`SERVICE_KEY_IS_NOT_REGISTERED_ERROR`). data.go.kr 에서 신청·승인되면
`external/pet_travel_api.py` 를 그대로 두고 바로 동작한다.

승인 전까지 반려견 조건 5개는 `services/place_score.judgeable()` 이
판정 불가로 빼고, 남은 조건끼리 가중치를 다시 나눈다.

## 4. 액티비티 대분류

`activity_type` 컬럼은 있으나 ★저장하는 코드가 어디에도 없어★ 모든 체험이
NULL 이다. 2026-09-20 에 대분류째 감췄다.

살리려면 등록 폼 2곳(`farmer_register.html`·`easy_create_experience.html`)에
드롭다운을 추가하고 라우트 3곳에서 저장해야 한다. 기존 체험은 농장주가
다시 수정해야 값이 생긴다.

## 5. 남은 테스트 실패 2건

- `tests/test_activity.py::test_experienced_count_excludes_pending_and_cancelled`
- `tests/test_routes_fix.py::test_my_info_post_without_nickname_does_not_500`

오래전부터 실패 중이며 팀 결정이 필요하다.

## 6. API 키 교체 (보안)

- 공개 커밋 `2d5d64d8` 에 카카오 키 2개가 노출됐다
- `scheduled_task.py` 에 운영 MySQL 접속정보가 하드코딩돼 있다

대회 종료 후 반드시 교체할 것.
