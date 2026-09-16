# 외부 API 출처 기록

| 기능 | API명 | 엔드포인트(우리 서버) | 화면 | 주요 응답 필드 | 키(.env) | 구현 파일 |
|---|---|---|---|---|---|---|
| 반려동물 동반여행 | 한국관광공사 반려동물 동반여행 | `GET /api/experiences/<id>/pet-facilities` | 체험 상세 · 주변 정보 | name, category, address, tel, lat, lng, distance_km | `PET_API_KEY` | external/pet_travel_api.py → services/nearby_service.py → routes/nearby.py |
| 무장애 여행 | 한국관광공사 무장애 여행(KorWith) | `GET /api/experiences/<id>/barrier-free` | 체험 상세 · 접근성 | name, address, lat, lng, wheelchair, stroller, disabled_toilet, distance_km | `BARRIER_FREE_API_KEY` | external/barrier_free_api.py → services/nearby_service.py → routes/nearby.py |
| 의료관광 | 한국관광공사 의료관광 | `GET /api/experiences/<id>/medical` | 체험 상세 · 주변 의료 | name, category, address, tel, lat, lng, distance_km | `MEDICAL_API_KEY` | external/medical_tour_api.py → services/nearby_service.py → routes/nearby.py |

## 공통 동작
- 모든 external 함수: `(lat, lng, radius_m)` → 정리된 `list[dict]`. 타임아웃 3초(`HTTP_TIMEOUT_SEC`), 실패 시 예외 없이 빈 리스트.
- 키는 `os.environ.get("...", "DUMMY_...")` 로 읽으며, `.env`에 실제 키를 넣으면 그대로 동작.
- 거리(`distance_km`)는 `services/distance.haversine` 재사용, 가까운 순 정렬.
- 검색 반경·타임아웃·결과 개수 등 숫자는 전부 `common/constants.py` 상수.

## TODO (실제 키 발급 후)
- 각 external 파일 상단 `*_URL` 을 관광공사 실제 서비스 URL로 확정.
- barrier_free 의 휠체어/유모차/장애인화장실 상세 플래그는 detail 계열 응답 필드명으로 매핑 확정.
