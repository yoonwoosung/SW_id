// FarmLink Service Worker — 1단계(설치용 껍데기).
//
// 캐시 대상은 "정적 파일"뿐이다. 예약·결제·추천처럼 실시간성이 중요한 응답을
// 캐시하면 옛 정보가 화면에 남을 수 있어, 아래 규칙으로 명확히 배제한다.
//
// 배포 시 CACHE_VERSION 만 올리면 옛 캐시가 activate 단계에서 정리된다.

const CACHE_VERSION = 'farmlink-v1';

// 설치 시 미리 받아둘 최소 자원(실패해도 설치가 깨지지 않게 개별 처리).
const PRECACHE_URLS = [
  '/static/css/theme.css',
  '/static/css/style.css',
  '/static/icons/icon-192.png',
  '/static/icons/icon-512.png',
];

// 캐시해도 되는 정적 자원 경로.
const STATIC_PREFIXES = ['/static/css/', '/static/js/', '/static/icons/', '/static/fonts/'];

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

function isStaticAsset(url) {
  return STATIC_PREFIXES.some((p) => url.pathname.startsWith(p));
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

  if (isStaticAsset(url)) {
    // 정적 파일: cache-first
    event.respondWith(
      caches.match(request).then((cached) => {
        if (cached) return cached;
        return fetch(request).then((response) => {
          if (response && response.ok) {
            const copy = response.clone();
            caches.open(CACHE_VERSION).then((cache) => cache.put(request, copy));
          }
          return response;
        });
      })
    );
    return;
  }

  // 그 외(HTML 페이지 등): network-first, 실패 시에만 캐시로 대체
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
