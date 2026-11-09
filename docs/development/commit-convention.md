# 커밋 메시지 규칙

FarmLink는 [Conventional Commits](https://www.conventionalcommits.org/) 기반 규칙을 사용한다.

## 형식

```text
type(scope): 변경 내용
```

- `type`: 아래 표 중 하나 (필수)
- `scope`: 변경이 속한 영역 (선택, 예: ranking, auth, nearby)
- 변경 내용: 무엇을 바꿨는지 한 줄로 (한국어)

## 타입

| type | 의미 |
|---|---|
| feat | 새로운 기능 |
| fix | 버그 수정 |
| refactor | 기능 변화가 없는 코드 구조 개선 |
| test | 테스트 추가 또는 수정 |
| docs | 문서 추가 또는 수정 |
| chore | 설정, 의존성, 기타 작업 |
| perf | 성능 개선 |
| build | 빌드 시스템 또는 의존성 변경 |
| ci | CI/CD 설정 변경 |
| style | 코드 동작에 영향을 주지 않는 형식 수정 |
| revert | 이전 변경 복구 |

## 예시

```text
feat(nearby): 관광공사 주변시설 API 3종 추가
fix(my-info): 회원정보 수정 시 NOT NULL 위반 500 해결
refactor(app): 단일 app.py를 도메인 구조로 분할
test(match): 역제안 매칭 점수 테스트 추가
docs(adr): app.py 도메인 분할 결정 기록
```

## 원칙

- **커밋 메시지는 코드 변경 사실만 짧게 표현한다.** "무엇을/왜"의 상세 서술은 커밋이 아니라 PR에 쓴다.
- **커밋마다 포트폴리오용 장문 기록을 작성하지 않는다.** 포트폴리오 재료의 핵심 단위는 커밋이 아니라 PR이다.
- 의미 있는 단위로 나눠서 커밋한다(기능/버그/리팩터를 한 커밋에 섞지 않는다).
- 비밀정보(키·토큰·비밀번호)를 커밋에 포함하지 않는다.

## 관련 문서

- [팀 개발 워크플로](team-workflow.md)
- [GitHub 라벨 기준](github-labels.md)
