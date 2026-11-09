# FarmLink → 노션 작업/배포 로그 자동 기록

K-OSP와 같은 노션 DB("KOSP 작업/배포 로그", 프로젝트 select = `FarmLink`)에 develop push / PR 단위로 row를 남긴다.

## 1회 설정
저장소 **Settings → Secrets and variables → Actions**에 두 개 등록 (K-OSP-Frontend 저장소와 **같은 값**):

| 이름 | 값 |
|---|---|
| `NOTION_TOKEN` | integration "KOSP" 토큰 (`ntn_…`) |
| `NOTION_DB_ID` | `39c197909e6b81d49a21c8fca0e62fc6` (DB 주소의 32자리) |

둘을 바꿔 넣으면 스크립트가 바로 멈추고 이유를 출력한다(2026-11 KOSP-Backend에서 실제로 있었던 실수).

## 과거 커밋 백필 (1회, 로컬)
`backfill-farmlink.json`에 develop 기준 본인(yoonwoosung) 커밋 113건이 들어 있다.
```bash
NOTION_TOKEN=ntn_xxx NOTION_DB_ID=39c197909e6b81d49a21c8fca0e62fc6 \
  node .github/scripts/backfill-notion.mjs .github/scripts/backfill-farmlink.json
```
Notion rate limit 때문에 요청 사이에 딜레이가 있어 수 분 걸린다.
