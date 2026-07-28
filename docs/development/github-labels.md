# GitHub 라벨 기준

PR/Issue 분류와 포트폴리오 재료 선별을 위해 다음 라벨을 사용한다.

| 라벨 | 의미·사용 기준 |
|---|---|
| `portfolio` | 최종 포트폴리오에서 대표 사례로 쓸 가능성이 높은 PR |
| `troubleshooting` | 단순 버그 수정이 아니라 원인 분석·해결 과정이 중요한 PR |
| `architecture` | 시스템 구조나 책임 분리에 관한 중요한 변경 |
| `performance` | 응답 시간, 쿼리 수, 처리량, 자원 사용량을 개선한 변경 |
| `security` | 인증·인가·데이터 보호를 강화한 변경 |
| `collaboration` | API 규격, 코드 리뷰, 작업 방식, 팀 생산성을 개선한 변경 |
| `release` | 배포 단위와 관련된 PR |
| `documentation` | 문서 작업 |
| `database` | 스키마·마이그레이션·데이터 관련 변경 |
| `infrastructure` | 배포·CI/CD·환경 구성 변경 |
| `testing` | 테스트·자동화로 품질을 개선한 변경 |

## `portfolio` 라벨 원칙

**모든 PR에 `portfolio`를 붙이지 않는다.** 다음 중 하나 이상에 해당할 때만 붙인다.

- 기술적 선택 이유가 있다.
- 해결 과정이 중요한 문제가 있었다.
- 성능 또는 운영 방식이 개선됐다.
- 데이터 정합성이나 보안을 강화했다.
- 담당 범위가 명확하다.
- 테스트/자동화로 품질을 개선했다.
- 협업 프로세스를 개선했다.
- 프로젝트의 핵심 기능이다.

## 라벨 생성 (승인 후 실행)

> ⚠️ 원격 저장소의 라벨을 임의로 생성/삭제하지 않는다. 아래 명령은 **저장소 관리자가 직접** 확인 후 실행한다.
> GitHub CLI(`gh`) 로그인과 저장소 권한이 있어야 한다.

```bash
# 예시 (색상은 조정 가능)
gh label create portfolio       --color 5319e7 --description "포트폴리오 대표 사례 후보"
gh label create troubleshooting --color d73a4a --description "원인 분석·해결 과정 중심"
gh label create architecture    --color 0e8a16 --description "구조·책임 분리 변경"
gh label create performance     --color fbca04 --description "성능 개선"
gh label create security        --color b60205 --description "보안 강화"
gh label create collaboration   --color 1d76db --description "협업 프로세스 개선"
gh label create release         --color 0052cc --description "배포 단위 관련"
gh label create database        --color 5319e7 --description "스키마·데이터 변경"
gh label create infrastructure  --color 006b75 --description "배포·CI/CD·환경"
gh label create testing         --color c2e0c6 --description "테스트·자동화 품질 개선"
```
