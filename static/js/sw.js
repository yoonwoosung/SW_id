// FarmLink Service Worker — 1단계(설치용 껍데기).
//
// 캐시 대상은 "정적 파일"뿐이다. 예약·결제·추천처럼 실시간성이 중요한 응답을
// 캐시하면 옛 정보가 화면에 남을 수 있어, 아래 규칙으로 명확히 배제한다.
//
// ★코드(CSS·JS)와 미디어(아이콘·폰트)의 전략을 나눈다.★
//
//   CSS·JS   network-first — 항상 최신을 먼저 받고, 실패할 때만 캐시로 대체
//   아이콘·폰트 stale-while-revalidate — 거의 바뀌지 않고 용량이 커서 캐시 우선
//
// v2 는 CSS·JS 도 stale-while-revalidate 였다. 캐시를 즉시 돌려주고 뒤에서
// 갱신하는 방식이라 ★배포 직후 첫 방문에는 옛 파일이 그대로 보였다.★
// 강력 새로고침(Cmd+Shift+R)으로도 서비스워커는 우회되지 않아, 시크릿 창에서만
// 최신이 보였다. 새 기능을 배포해도 바로 확인할 수 없고, 처음 온 사람도
// 두 번 새로고침해야 제대로 된 화면을 본다.
//
// network-first 로 바꾸면 배포 즉시 반영된다. 오프라인에서는 캐시가 그대로
// 대체하므로 PWA 오프라인 동작은 유지된다. CSS·JS 는 작아서 왕복 비용도 작다.
//
// v1 은 cache-first 였다(캐시에 있으면 서버에 묻지도 않음).
// CACHE_VERSION 을 올리면 activate 단계에서 옛 캐시가 통째로 정리된다.

const CACHE_VERSION = 'farmlink-v3';

// 설치 시 미리 받아둘 최소 자원(실패해도 설치가 깨지지 않게 개별 처리).
// CSS 는 넣지 않는다. 프리캐시는 오프라인 최소 보장용이고,
// CSS 갱신은 아래 stale-while-revalidate 가 맡는다.
const PRECACHE_URLS = [
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// 미디어 — 거의 바뀌지 않고 용량이 크다(stale-while-revalidate).
// 여기 없는 정적 파일(CSS·JS)과 HTML 은 아래 기본 분기(network-first)가 맡는다.
const MEDIA_PREFIXES = ['/static/icons/', '/static/fonts/', '/static/images/'];

// 절대 캐시하지 않을 경로(실시간 데이터·인증·결제).
const NEVER_CACHE_PREFIXES = [
  '/api/',            // 모든 JSON API
  '/payments/',       // 결제 화면·성공·실패
  '/admin/',          // 관리자
  '/login',
  '/logout',
  '/register',
  '/check_email',
  '/verify_password',
];

function isMedia(url) {
  return MEDIA_PREFIXES.some((p) => url.pathname.startsWith(p));
}

function isNeverCache(url) {
  return NEVER_CACHE_PREFIXES.some((p) => url.pathname.startsWith(p));
}

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_VERSION).then((cache) =>
      // 하나가 404여도 설치가 실패하지 않도록 개별적으로 담는다.
      Promise.all(PRECACHE_URLS.map((u) => cache.add(u).catch(() => null)))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE_VERSION).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const request = event.request;

  // GET 이 아닌 요청(로그인 POST·결제 POST 등)은 그대로 통과시킨다.
  if (request.method !== 'GET') return;

  const url = new URL(request.url);

  // 다른 도메인(카카오·토스·관광공사·CDN)은 건드리지 않는다.
  if (url.origin !== self.location.origin) return;

  // 실시간 데이터·인증·결제는 캐시에 넣지도, 캐시에서 꺼내지도 않는다.
  if (isNeverCache(url)) return;

  if (isMedia(url)) {
    // 아이콘·폰트·이미지: stale-while-revalidate
    // 거의 바뀌지 않고 용량이 커서 캐시를 먼저 준다. 뒤에서 조용히 갱신한다.
    event.respondWith(
      caches.match(request).then((cached) => {
        const network = fetch(request).then((response) => {
          if (response && response.ok) {
            const copy = response.clone();
            caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy));
          }
          return response;
        });
        if (cached) {
          network.catch(() => {});   // 뒤에서 도는 갱신 실패(오프라인 등)는 무시
          return cached;
        }
        return network;
      })
    );
    return;
  }

  // 코드(CSS·JS)와 HTML: network-first, 실패할 때만 캐시로 대체
  // ★배포 즉시 반영된다.★ 오프라인에서는 캐시가 받쳐 주므로 PWA 동작은 유지된다.
  event.respondWith(
    fetch(request)
      .then((response) => {
        if (response && response.ok) {
          const copy = response.clone();
          caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy));
        }
        return response;
      })
      .catch(() => caches.match(request))
  );
});
