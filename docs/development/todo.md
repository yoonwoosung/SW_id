# 남은 작업 (TODO / 로드맵)

FarmLink 백엔드 기능 구현 중 **아직 안 된 것**과 각각 **무엇을 해야 하는지**를 정리한다.
(이미 된 것: AI 추천 코스, ESG 점수, 맞춤추천 API, 농산물 API, 주변 무장애 여행지, 추천 폴백, my_info/코스 프론트 등)

## 1. admin(관리자) 화면 — 미착수
- **파일**: `routes/admin.py`(빈 스텁), 새 템플릿 필요
- **결정 필요**: 관리자가 무엇을 관리하나?
  - 후보: 농장주 가입 승인(User.verification_status), 신고/문의 관리, 체험 게시물 관리, 통계
- **선행**: 관리자 권한 체크(로그인 + role='admin' 도입 필요 — 현재 role은 experiencer/farmer만)

## 2. 역제안(리버스 매칭) 프론트 — 백엔드 완료, UI 미착수
- **API(완료)**: `POST/GET /api/user-requests`, `GET /api/user-requests/<id>`,
  `POST /api/user-requests/<id>/proposals`, `GET /api/farmers/me/matching-requests`
- **필요**: 화면 — (사용자) 요청글 작성·목록, (농장주) "나에게 맞는 요청" 목록·제안 보내기
- **참고**: 요청 조건은 `/api/search-categories` 코드값 사용

## 3. 카카오 지오코딩 — 키 대기
- **코드**: 이미 `external/kakao_map.py` + farmer_register에 연결됨
- **필요**: `.env`에 `KAKAO_API_KEY` (카카오 developers 발급). 넣으면 바로 동작(TourAPI와 동일 방식)

## 4. 관광공사 pet/medical 엔드포인트 확정 — 외부 확인 필요
- **무장애(barrier)**: `KorWithService2/locationBasedList2` — ✅ 검증 완료(동작함)
- **반려동물(pet)**: 현재 **403 Forbidden** = 계정이 '반려동물 동반여행' 서비스에 활용신청 안 됨
  → data.go.kr에서 해당 서비스 활용신청 후 샘플 URL로 확정
- **의료(medical)**: 현재 **500** = `MedicalTourService`는 placeholder(실재 안 함)
  → 의료관광 서비스 상세페이지의 샘플 요청 URL 확보해 `external/medical_tour_api.py`에 반영
- 프론트(체험 상세 '주변 편의시설')는 데이터 있는 것만 자동 노출하도록 이미 연결됨 → URL만 고치면 바로 뜸

## 5. 운영 MySQL 마이그레이션 — 결정 필요
- 새 테이블: `user_request`, `proposal`(역제안). 로컬은 `db.create_all()`로 생성되나 운영 MySQL엔 반영 필요
- **결정**: Flask-Migrate(Alembic) 도입 여부

## 6. 카테고리 필터 고도화 (선택)
- 현재: index 상세조건 → `cond_*` 파라미터로 **추천 점수 가점**(GPS 필요). 정렬만 영향.
- 개선안: 선택 조건을 **하드 필터(WHERE)** 로도 반영할지 결정(백엔드 index() 수정 필요)

## 7. course_reason LLM 교체 (선택)
- 현재: 규칙 기반 문장. `external/clova_api`로 교체 가능한 seam 있음(코스 장소 목록만 근거로 설명)
- **필요**: CLOVA 키 + 프롬프트 확정
