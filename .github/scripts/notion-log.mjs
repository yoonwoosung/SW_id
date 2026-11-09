// 팀 노션 DB에 작업/배포 로그 row 를 추가한다.
// GitHub Actions(worklog.yml)의 env 로 값을 받는다. Node 18+ (fetch 내장).
//
// 필요한 env: NOTION_TOKEN, NOTION_DB_ID
// 컬럼명은 create-notion-db.mjs 로 만든 DB 스키마와 반드시 일치해야 한다.

const P = process.env;

if (!P.NOTION_TOKEN || !P.NOTION_DB_ID) {
  console.error('NOTION_TOKEN / NOTION_DB_ID 가 없습니다. 시크릿을 확인하세요.');
  process.exit(1);
}

// 시크릿 값 자체가 잘못된 경우를 즉시 잡는다.
// 2026-11 KOSP-Backend 에서 NOTION_DB_ID 에 integration 토큰(ntn_...)이 들어가 넉 달간 기록이 전부 실패했다.
const _db = (process.env.NOTION_DB_ID || '').replace(/-/g, '');
if (/^ntn_/i.test(process.env.NOTION_DB_ID || '')) {
  console.error('NOTION_DB_ID 에 integration 토큰(ntn_...)이 들어 있습니다. DB 주소의 32자리 ID 를 넣으세요. 예) notion.so/.../39c197909e6b81d49a21c8fca0e62fc6?v=... → 39c197909e6b81d49a21c8fca0e62fc6');
  process.exit(1);
}
if (!/^[0-9a-f]{32}$/i.test(_db)) {
  console.error(`NOTION_DB_ID 형식이 아닙니다(32자리 hex 여야 함): "${process.env.NOTION_DB_ID}"`);
  process.exit(1);
}

const short = (P.GITHUB_SHA || '').slice(0, 7);
const runUrl = `${P.GITHUB_SERVER_URL}/${P.GITHUB_REPOSITORY}/actions/runs/${P.GITHUB_RUN_ID}`;

// 이벤트 종류 판별
const isPr = P.GITHUB_EVENT_NAME === 'pull_request';
const prMerged = P.PR_MERGED === 'true';
// develop push = 사실상 배포 대상(dev). PR open/close 는 아직 배포 아님.
const isDevelopPush = P.GITHUB_EVENT_NAME === 'push' && P.GITHUB_REF_NAME === 'develop';

const title =
  (P.PR_TITLE && P.PR_TITLE.trim()) ||
  (P.COMMIT_MSG && P.COMMIT_MSG.split('\n')[0]) ||
  short ||
  'work';

const num = (v) => Number.parseInt(v || '0', 10) || 0;

const props = {
  '작업명': { title: [{ text: { content: title.slice(0, 200) } }] },
  '프로젝트': { select: { name: P.PROJECT_NAME || 'FarmLink' } },
  '날짜': { date: { start: new Date().toISOString() } },
  '브랜치': { rich_text: [{ text: { content: P.GITHUB_REF_NAME || '' } }] },
  '커밋해시': { rich_text: [{ text: { content: short } }] },
  '작성자': { rich_text: [{ text: { content: P.GITHUB_ACTOR || '' } }] },
  '작업유형': { select: { name: P.WORK_TYPE || 'chore' } },
  '이벤트': { select: { name: P.GITHUB_EVENT_NAME || 'push' } },
  '백엔드변경파일수': { number: num(P.BACKEND_FILES) },
  '프론트변경파일수': { number: num(P.FRONTEND_FILES) },
  '엔티티DTO변경수': { number: num(P.ENTITY_DTO_FILES) },
  '마이그레이션변경수': { number: num(P.MIGRATION_FILES) },
  '총변경파일수': { number: num(P.TOTAL_FILES) },
  '테스트통과': { checkbox: P.TEST_PASSED === 'true' },
  '배포환경': { select: { name: isDevelopPush ? 'dev' : 'none' } },
  '배포성공': { checkbox: isDevelopPush && P.TEST_PASSED === 'true' },
  'ActionRunURL': { url: runUrl },
};

if (isPr && P.PR_NUMBER) {
  props['PR번호'] = { number: num(P.PR_NUMBER) };
  props['PR제목'] = { rich_text: [{ text: { content: (P.PR_TITLE || '').slice(0, 200) } }] };
  props['PR병합됨'] = { checkbox: prMerged };
}

const res = await fetch('https://api.notion.com/v1/pages', {
  method: 'POST',
  headers: {
    Authorization: `Bearer ${P.NOTION_TOKEN}`,
    'Notion-Version': '2022-06-28',
    'Content-Type': 'application/json',
  },
  body: JSON.stringify({ parent: { database_id: P.NOTION_DB_ID }, properties: props }),
});

const bodyText = await res.text();
if (!res.ok) {
  console.error(`Notion API 실패 (${res.status}):`, bodyText);
  process.exit(1);
}
console.log('Notion 기록 완료:', title);
