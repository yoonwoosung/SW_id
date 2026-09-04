# 브랜치 머지 워크플로우 (frontend ← develop)

## 진행 방식
Claude와 대화하면서 충돌 파일을 하나씩 해결한다.

## 단계별 절차

### 1단계 — 최신 develop 가져오기
```bash
git fetch origin
git merge origin/develop --no-commit --no-ff
```
- `--no-commit`: 충돌 해결 전에 커밋하지 않음
- `--no-ff`: fast-forward 방지, 머지 커밋 생성

### 2단계 — 충돌 파일 목록 확인
```bash
git diff --name-only --diff-filter=U
```

### 3단계 — Claude와 충돌 해결 (대화)
충돌 파일마다:
1. Claude가 양쪽 내용을 읽고 분석
2. 어느 쪽을 살릴지 또는 합칠지 제안
3. 준형이 결정하면 Claude가 파일 직접 수정
4. 다음 파일로 이동

### 4단계 — 머지 완료 커밋
```bash
git add .
git commit -m "merge: origin/develop → frontend"
git push origin frontend
```

## 충돌 해결 원칙
| 파일 유형 | 원칙 |
|-----------|------|
| `templates/` HTML | UI 변경은 frontend 우선, 기능 추가는 합치기 |
| `static/css/` | frontend 스타일 우선, develop 신규 클래스 추가 |
| `static/js/` | 기능 로직은 최신 쪽 선택, 준형이 최종 결정 |
| `routes/`, `models/` | 백엔드 파일 — develop 우선 (frontend에서 수정 안 함) |
| `app.py`, `config.py` | develop 우선 |

## 주의
- 백엔드 파일(`routes/`, `models/`, `app.py`)은 develop 것을 그대로 사용
- 충돌이 없는 파일은 자동 머지됨
