# 포트폴리오 정리 가이드

프로젝트 종료 후, 개발 중 축적한 기록(PR·ADR·Worklog·Release)을 조합해 이력서·포트폴리오를 만드는 과정을 정리한다.

## 절차

1. `portfolio` 라벨이 붙은 병합 PR 조회
2. 본인이 작성한 병합 PR 조회
3. `troubleshooting` 라벨 PR 조회
4. [ADR](../adr/README.md) 조회 (기술 선택 이유)
5. 주간 [Worklog](../worklog/README.md) 조회 (문제 해결·협업 사례)
6. [Release Note](../releases/README.md) 조회
7. 테스트 결과·성능 측정 자료 조회
8. 본인의 담당 범위 확인
9. 공개할 수 없는 정보 제거
10. [project-template.md](project-template.md)로 프로젝트 설명 재구성

## GitHub 검색 예시

```text
is:pr is:merged label:portfolio
is:pr is:merged author:@me
is:pr is:merged author:@me label:troubleshooting
is:pr is:merged label:architecture
is:pr is:merged label:performance
```

## 원칙

- 확인되지 않은 성과 수치를 만들지 않는다.
- 남이 구현한 작업을 본인 성과로 쓰지 않는다.
- 장점뿐 아니라 한계·개선 방향도 적는다.
- 개인정보·보안정보·외부 비공개 정보를 포함하지 않는다.

## 템플릿

- [프로젝트 포트폴리오](project-template.md)
- [트러블슈팅 (PAAR)](troubleshooting-template.md)
