# 기여 가이드 (CONTRIBUTING)

FarmLink 개발 기록·협업 규칙의 진입점입니다. 자세한 내용은 아래 문서를 참고하세요.

## 빠른 요약

1. **Issue** 생성 → 완료 조건 작성 (`.github/ISSUE_TEMPLATE`)
2. Issue 번호로 **브랜치** 생성 (예: `feature/124-...`)
3. [Conventional Commits](docs/development/commit-convention.md)로 **커밋**
4. **PR** 작성 — 무엇을/왜/어떻게 + 테스트 결과 (`Closes #번호`)
5. 중요한 기술 결정은 [ADR](docs/adr/README.md) 작성
6. 매주 [Worklog](docs/worklog/README.md) 정리
7. 중요 PR에 [포트폴리오 라벨](docs/development/github-labels.md) 부여

## 상세 문서

- [팀 개발 워크플로](docs/development/team-workflow.md)
- [커밋 메시지 규칙](docs/development/commit-convention.md)
- [GitHub 라벨 기준](docs/development/github-labels.md)
- [ADR](docs/adr/README.md)
- [주간 개발 기록](docs/worklog/README.md)
- [포트폴리오 정리 가이드](docs/portfolio/README.md)
- [릴리스 노트](docs/releases/README.md)

## 안전 규칙

- 비밀정보(키·토큰·비밀번호)를 커밋하지 않는다. 값은 `.env`(환경변수)로 관리한다.
- 남의 데이터를 수정/삭제하는 라우트에는 로그인·소유 확인을 넣는다.
- 커밋 메시지는 짧게. 상세 서술은 PR에 쓴다.
