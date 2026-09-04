# develop 브랜치 협업 워크플로우

## 기본 원칙
3명이 develop 브랜치에서 직접 협업한다.
작업 전 항상 pull, 올리기 전에도 pull 먼저.

## 매일 작업 루틴

### 작업 시작 전
```bash
git pull origin develop
```

### 작업 후 올리기
```bash
git pull origin develop   # 남이 올린 거 먼저 당기기
# 충돌 있으면 해결 후 커밋
git add .
git commit -m "타입: 작업 내용"
git push origin develop
```

## 충돌 발생 시

### 1단계 — 충돌 파일 확인
```bash
git diff --name-only --diff-filter=U
```

### 2단계 — Claude와 충돌 해결 (대화)
충돌 파일마다:
1. Claude가 양쪽 내용을 읽고 분석
2. 어느 쪽을 살릴지 또는 합칠지 제안
3. 준형이 결정하면 Claude가 파일 직접 수정
4. 다음 파일로 이동

### 3단계 — 머지 완료 커밋
```bash
git add .
git commit -m "merge: 충돌 해결 내용 요약"
git push origin develop
```

## 충돌 해결 원칙
| 파일 유형 | 원칙 |
|-----------|------|
| `templates/` HTML | UI 변경은 프론트 우선, 기능 추가는 합치기 |
| `static/css/` | 프론트 스타일 우선, 신규 클래스 추가 |
| `static/js/` | 기능 로직은 최신 쪽 선택, 준형이 최종 결정 |
| `routes/`, `models/` | 백엔드 파일 — 건드리지 않음 |
| `app.py`, `config.py` | 백엔드 파일 — 건드리지 않음 |

## 주의
- 오래 작업할 거면 중간중간 pull해서 충돌 작게 유지
- 큰 작업은 미리 팀원에게 "나 이 파일 건드린다" 공유
- push 거절되면 pull 먼저 하고 다시 push
- 실수로 망했을 때: `git reset --hard origin/develop` (로컬 변경사항 버림)
