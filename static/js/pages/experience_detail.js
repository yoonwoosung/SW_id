/* static/js/pages/experience_detail.js
   체험 상세 페이지 컨트롤러: 갤러리·라이트박스, 찜/공유(목업), 긴박감, 리뷰 분포/더보기,
   비슷한 체험, AI 코스·ESG·주변시설 위젯, 카카오맵.
   서버 데이터는 #detail-data(JSON, tojson)로 주입받는다. */
(function () {
    'use strict';

    // ▼▼▼ 목업 값만 직접 채우세요. 비우면(null/[]) 화면에서 자동 숨김. 준형이 임의로 채우지 말 것 ▼▼▼
    var DETAIL_MOCK = {
        viewers_now: null,        // 예: 12  → "지금 12명이 보는 중"
        review_ai_summary: null,  // 예: "당도 높은 포도와 친절한 농장주 후기가 많아요"
        badwords: []              // 예: ["비속어1","비속어2"] → 리뷰 표시에서 *** 처리
    };
    // ▲▲▲ 여기까지 목업 영역 ▲▲▲

    var DATA = {};
    try { DATA = JSON.parse(document.getElementById('detail-data').textContent); } catch (e) { DATA = {}; }

    function esc(s) { var d = document.createElement('div'); d.textContent = (s == null ? '' : String(s)); return d.innerHTML; }
    function $(id) { return document.getElementById(id); }
    var TYPE_ICON = { experience: 'sprout', restaurant: 'utensils', attraction: 'landmark', cafe: 'coffee' };

    // ---------- 갤러리 & 라이트박스 ----------
    (function gallery() {
        var main = $('ed-gallery-main');
        var lightbox = $('ed-lightbox');
        if (!main) return;
        document.querySelectorAll('.ed-gallery__thumb').forEach(function (t) {
            t.addEventListener('click', function () {
                main.src = t.src;
                document.querySelectorAll('.ed-gallery__thumb').forEach(function (x) { x.classList.remove('is-active'); });
                t.classList.add('is-active');
            });
        });
        if (lightbox) {
            var img = lightbox.querySelector('img');
            main.addEventListener('click', function () { img.src = main.src; lightbox.classList.add('is-open'); });
            lightbox.addEventListener('click', function () { lightbox.classList.remove('is-open'); });
            document.addEventListener('keydown', function (e) { if (e.key === 'Escape') lightbox.classList.remove('is-open'); });
        }
    })();

    // ---------- 긴박감: "지금 N명 보는 중" (목업) ----------
    (function urgency() {
        var el = $('ed-viewers');
        if (el && DETAIL_MOCK.viewers_now != null) {
            el.textContent = '👀 지금 ' + DETAIL_MOCK.viewers_now + '명이 보는 중';
            el.hidden = false;
        }
    })();

    // ---------- 찜하기(백엔드 API: POST/DELETE /api/wishlists) ----------
    (function wishlist() {
        var btn = $('ed-wish');
        if (!btn) return;
        var wishId = null;  // 찜된 상태면 wishlist id, 아니면 null
        function reflect() {
            var on = wishId != null;
            btn.classList.toggle('is-wished', on);
            btn.querySelector('.ed-wish-label').textContent = on ? '찜함' : '찜하기';
        }
        // 초기 상태: 내 찜 목록에서 이 체험 찾아 wishId 확보(비로그인이면 403 → 무시)
        fetch('/api/wishlists').then(function (r) { return r.json(); }).then(function (res) {
            if (res.success) {
                var found = (res.data.wishlists || []).find(function (w) { return w.experience_id === DATA.id; });
                if (found) { wishId = found.id; reflect(); }
            }
        }).catch(function () {});

        btn.addEventListener('click', function () {
            btn.disabled = true;
            var done = function () { btn.disabled = false; };
            if (wishId == null) {
                fetch('/api/wishlists', {
                    method: 'POST', headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ experience_id: DATA.id })
                }).then(function (r) { return r.json().then(function (j) { return { status: r.status, body: j }; }); })
                    .then(function (res) {
                        if (res.body.success) { wishId = res.body.data.id; reflect(); toast('내 활동에 담았어요'); }
                        else if (res.status === 403) { toast('로그인이 필요해요'); }
                        else { toast('찜에 실패했어요'); }
                    }).catch(function () { toast('찜에 실패했어요'); }).then(done);
            } else {
                fetch('/api/wishlists/' + wishId, { method: 'DELETE' })
                    .then(function (r) { return r.json(); })
                    .then(function (res) {
                        if (res.success) { wishId = null; reflect(); toast('찜을 해제했어요'); }
                        else { toast('해제에 실패했어요'); }
                    }).catch(function () { toast('해제에 실패했어요'); }).then(done);
            }
        });
    })();

    // ---------- 공유(링크 복사) ----------
    (function share() {
        var btn = $('ed-share');
        if (!btn) return;
        btn.addEventListener('click', function () {
            var url = window.location.href;
            if (navigator.clipboard) {
                navigator.clipboard.writeText(url).then(function () { toast('링크를 복사했어요'); }, function () { toast('복사에 실패했어요'); });
            } else { toast(url); }
        });
    })();

    function toast(msg) {
        var t = $('ed-toast');
        if (!t) return;
        t.textContent = msg;
        t.classList.add('is-show');
        clearTimeout(toast._timer);
        toast._timer = setTimeout(function () { t.classList.remove('is-show'); }, 1800);
    }

    // ---------- 리뷰: 별점 분포 · AI 요약 · 더보기 ----------
    (function reviews() {
        var distEl = $('ed-review-dist');
        var ratings = DATA.ratings || [];
        if (distEl && ratings.length) {
            var counts = { 5: 0, 4: 0, 3: 0, 2: 0, 1: 0 };
            ratings.forEach(function (r) { if (counts[r] != null) counts[r]++; });
            distEl.innerHTML = [5, 4, 3, 2, 1].map(function (star) {
                var pct = Math.round(counts[star] / ratings.length * 100);
                return '<div class="ed-review-dist__row"><span>' + star + '점</span>'
                    + '<div class="ed-review-dist__bar"><div class="ed-review-dist__fill" style="width:' + pct + '%"></div></div>'
                    + '<span>' + counts[star] + '</span></div>';
            }).join('');
        }
        var sumEl = $('ed-ai-summary');
        if (sumEl && DETAIL_MOCK.review_ai_summary) {
            sumEl.innerHTML = '<span class="ai-badge-label">AI</span> ' + esc(DETAIL_MOCK.review_ai_summary);
            sumEl.hidden = false;
        }
        // 욕설 필터(목업): badwords가 있으면 리뷰 본문에서 마스킹
        if (DETAIL_MOCK.badwords.length) {
            document.querySelectorAll('.review-item-content').forEach(function (p) {
                var txt = p.textContent;
                DETAIL_MOCK.badwords.forEach(function (w) {
                    if (!w) return;
                    txt = txt.split(w).join('*'.repeat(w.length));
                });
                p.textContent = txt;
            });
        }
        // 더보기: N개 초과분 접기
        var LIMIT = 3;
        var items = Array.prototype.slice.call(document.querySelectorAll('#ed-review-list .review-item'));
        var moreBtn = $('ed-review-more');
        if (items.length > LIMIT && moreBtn) {
            items.slice(LIMIT).forEach(function (el) { el.classList.add('is-hidden'); });
            moreBtn.hidden = false;
            moreBtn.textContent = '후기 ' + (items.length - LIMIT) + '개 더보기';
            moreBtn.addEventListener('click', function () {
                items.forEach(function (el) { el.classList.remove('is-hidden'); });
                moreBtn.hidden = true;
            });
        }
    })();

    // ---------- 비슷한 체험 (기존 목록 API 재사용, 같은 작물) ----------
    (function similar() {
        var el = $('ed-similar');
        if (!el) return;
        fetch('/api/experiences').then(function (r) { return r.json(); }).then(function (list) {
            var similar = (list || []).filter(function (x) { return x.id !== DATA.id && x.crop === DATA.crop; }).slice(0, 8);
            if (!similar.length) { el.closest('.section-block').hidden = true; return; }
            el.innerHTML = similar.map(function (x) {
                return '<a class="ed-similar-card" href="/experience/' + x.id + '">'
                    + '<div class="ed-similar-card__thumb"><i data-lucide="sprout"></i></div>'
                    + '<div class="ed-similar-card__body">'
                    + '<div class="ed-similar-card__title">' + esc(x.crop) + ' 체험</div>'
                    + '<div class="ed-similar-card__loc">' + esc(x.location || '') + '</div>'
                    + '<div class="ed-similar-card__price">' + Number(x.cost || 0).toLocaleString() + '원</div>'
                    + '</div></a>';
            }).join('');
        }).catch(function () { el.closest('.section-block').hidden = true; });
    })();

    // ---------- 우측 사이드: 주변 시설 요약 (맛집·관광 각 2곳) ----------
    (function sideNearby() {
        var body = $('ed-nearby-body');
        if (!body) return;

        function group(label, list) {
            if (!list || !list.length) return '';
            var items = list.map(function (p) {
                var dist = p.distance_km != null
                    ? '<span class="ed-side-dist">' + p.distance_km + 'km</span>' : '';
                return '<li><span class="ed-side-name">' + esc(p.name) + '</span>' + dist + '</li>';
            }).join('');
            return '<div class="ed-side-group"><p class="ed-side-group__label">' + label + '</p>'
                 + '<ul class="ed-side-list">' + items + '</ul></div>';
        }

        fetch('/api/experiences/' + DATA.id + '/nearby-summary')
            .then(function (r) { return r.json(); })
            .then(function (res) {
                if (!res.success || !res.data) {
                    body.innerHTML = '<p class="ed-side-empty">정보 없음</p>'; return;
                }
                var html = group('맛집', res.data.restaurants) + group('관광', res.data.attractions);
                body.innerHTML = html || '<p class="ed-side-empty">정보 없음</p>';
                if (window.lucide) lucide.createIcons();
            })
            .catch(function () {
                body.innerHTML = '<p class="ed-side-empty">정보 없음</p>';
            });
    })();

    // ---------- 우측 사이드: AI 코스 요약 (미니 타임라인) ----------
    (function sideCourse() {
        var body = $('ed-course-body');
        if (!body) return;
        var costWrap = $('ed-course-cost'), costNum = $('ed-course-cost-num');

        function empty(msg) { body.innerHTML = '<p class="ed-side-empty">' + esc(msg) + '</p>'; }

        fetch('/api/experiences/' + DATA.id + '/course')
            .then(function (r) { return r.json(); })
            .then(function (res) {
                if (!res.success || !res.data) { empty('정보 없음'); return; }
                var data = res.data;
                var items = data.items || [];
                var hasPlace = items.some(function (it) { return it.type !== 'experience'; });
                if (!hasPlace) { empty(data.message || '정보 없음'); return; }

                // 우측은 요약 수준이라 앞 3개만 보여주고 자세한 건 '코스 보기'로 넘긴다.
                body.innerHTML = '<ul class="ed-course-line">' + items.slice(0, 3).map(function (it) {
                    var name = it.type === 'experience' ? '이 체험' : (it.name || '');
                    return '<li><span class="ed-course-time">' + esc(it.time) + '</span>'
                         + '<span class="ed-course-name">' + esc(name) + '</span></li>';
                }).join('') + '</ul>';

                var cost = data.summary && data.summary.estimated_cost;
                if (cost && costWrap && costNum) {
                    costNum.textContent = cost.toLocaleString('ko-KR') + '원';
                    costWrap.hidden = false;
                }
            })
            .catch(function () { empty('정보 없음'); });
    })();

    // ---------- ESG ----------
    (function esg() {
        var esgEl = $('esg-content');
        if (!esgEl) return;
        var GRADE_COLOR = { A: '#4CAF50', B: '#81C784', C: '#fbc02d', D: '#bbb' };
        fetch('/api/experiences/' + DATA.id + '/esg').then(function (r) { return r.json(); }).then(function (res) {
            if (!res.success || !res.data) { esgEl.textContent = 'ESG 점수를 불러올 수 없습니다.'; return; }
            var d = res.data, c = GRADE_COLOR[d.grade] || '#999';
            var chip = $('ed-esg-chip');   // 상단 칩에 ESG 등급 표시
            if (chip) { chip.innerHTML = '<i data-lucide="leaf"></i> ESG ' + esc(d.grade); chip.hidden = false; }
            var bars = d.breakdown.map(function (b) {
                var pct = b.max ? Math.round(b.earned / b.max * 100) : 0;
                return '<div style="margin:6px 0;"><div style="display:flex;justify-content:space-between;font-size:0.9rem;color:#555;">'
                    + '<span>' + esc(b.label) + '</span><span>' + b.earned + '/' + b.max + '</span></div>'
                    + '<div style="height:8px;background:#eee;border-radius:4px;overflow:hidden;"><div style="height:100%;width:' + pct + '%;background:' + (b.earned ? c : '#eee') + ';"></div></div></div>';
            }).join('');
            esgEl.innerHTML = '<div style="display:flex;align-items:center;gap:16px;margin-bottom:10px;">'
                + '<div style="font-size:2.4rem;font-weight:800;color:' + c + ';">' + esc(d.grade) + '</div>'
                + '<div><div style="font-size:1.4rem;font-weight:700;">' + d.score + '<span style="font-size:0.9rem;color:#999;">/100</span></div>'
                + '<div style="font-size:0.85rem;color:#888;">무농약·유기농·봉사·접근성 기준</div></div></div>' + bars;
        }).catch(function () { esgEl.textContent = 'ESG 점수를 불러오는 중 오류.'; });
    })();

    // ---------- 주변 맛집·카페·편의점(개별 장소, 코스 아님 · 카카오 카테고리 검색) ----------
    (function amenities() {
        var el = $('ed-amenities');
        if (!el) return;
        if (!window.kakao || !kakao.maps || DATA.lat == null || DATA.lng == null) {
            el.innerHTML = '<small class="text-muted">주변 편의시설을 표시할 수 없어요.</small>'; return;
        }
        var CATS = [
            { code: 'FD6', cat: '음식점', icon: 'utensils' },
            { code: 'CE7', cat: '카페', icon: 'coffee' },
            { code: 'CS2', cat: '편의점', icon: 'store' },
            { code: 'MT1', cat: '마트', icon: 'shopping-cart' }
        ];
        function distStr(m) {
            var n = Number(m);
            if (!n) return '';
            return n >= 1000 ? (n / 1000).toFixed(1) + 'km' : Math.round(n) + 'm';
        }
        function render(list) {
            if (!list.length) { el.innerHTML = '<small class="text-muted">주변 편의시설 정보를 찾지 못했어요.</small>'; return; }
            el.innerHTML = list.map(function (p) {
                var d = distStr(p.distance);
                return '<a class="ed-amenity" href="https://map.kakao.com/link/map/' + encodeURIComponent(p.name) + ',' + p.y + ',' + p.x + '" target="_blank" rel="noopener">'
                    + '<span class="ed-amenity__ico"><i data-lucide="' + esc(p.icon) + '"></i></span>'
                    + '<span class="ed-amenity__body"><span class="ed-amenity__name">' + esc(p.name) + '</span>'
                    + '<span class="ed-amenity__meta">' + esc(p.cat) + (d ? ' · ' + d : '') + '</span></span>'
                    + '<i data-lucide="external-link" class="ed-amenity__link"></i></a>';
            }).join('');
        }
        function run() {
            var center = new kakao.maps.LatLng(DATA.lat, DATA.lng);
            var ps = new kakao.maps.services.Places();
            var all = [], done = 0;
            CATS.forEach(function (c) {
                ps.categorySearch(c.code, function (result, status) {
                    if (status === kakao.maps.services.Status.OK) {
                        result.slice(0, 3).forEach(function (r) {
                            all.push({ name: r.place_name, x: r.x, y: r.y, distance: r.distance, cat: c.cat, icon: c.icon });
                        });
                    }
                    done++;
                    if (done === CATS.length) {
                        all.sort(function (a, b) { return (Number(a.distance) || 0) - (Number(b.distance) || 0); });
                        render(all.slice(0, 8));
                    }
                }, { location: center, radius: 5000, sort: kakao.maps.services.SortBy.DISTANCE });
            });
        }
        if (kakao.maps.load) { kakao.maps.load(run); } else { run(); }
    })();

    // ---------- 카카오맵 + 주변 거리 + 시간표 채우기 ----------
    (function kakaoMap() {
        if (!window.kakao || !kakao.maps || !$('map')) return;
        if (kakao.maps.load) { kakao.maps.load(run); } else { run(); }
        function run() {
        var center = new kakao.maps.LatLng(DATA.lat, DATA.lng);
        var map = new kakao.maps.Map($('map'), { center: center, level: 3 });
        new kakao.maps.Marker({ position: center }).setMap(map);

        var cats = [
            { code: 'CS2', name: '편의점', emoji: 'store' }, { code: 'PM9', name: '약국', emoji: 'pill' },
            { code: 'HP8', name: '병원', emoji: 'heart-pulse' }, { code: 'PK6', name: '주차장', emoji: 'square-parking' }
        ];
        var ps = new kakao.maps.services.Places();
        var listEl = $('distance-list');
        if (listEl) {
            listEl.innerHTML = '';
            cats.forEach(function (cat) {
                ps.categorySearch(cat.code, function (result, status) {
                    var p = document.createElement('p');
                    p.className = 'detail-nearby-row';
                    if (status === kakao.maps.services.Status.OK && result.length > 0) {
                        var pl = result[0];
                        var line = new kakao.maps.Polyline({ path: [center, new kakao.maps.LatLng(pl.y, pl.x)] });
                        var dist = Math.round(line.getLength());
                        var distStr = dist > 1000 ? '약 ' + (dist / 1000).toFixed(1) + 'km' : '약 ' + dist + 'm';
                        p.innerHTML = '<i data-lucide="' + cat.emoji + '"></i> <span class="nearby-name">' + cat.name + '</span> <strong>' + distStr + '</strong> <small>(' + esc(pl.place_name) + ')</small>';
                    } else {
                        p.innerHTML = '<i data-lucide="' + cat.emoji + '"></i> <span class="nearby-name">' + cat.name + '</span> <span class="text-muted">주변에 없음</span>';
                    }
                    listEl.appendChild(p);
                }, { location: center, radius: 20000, size: 1, sort: kakao.maps.services.SortBy.DISTANCE });
            });
        }

        var ttData = DATA.timetable || '';
        if (ttData) {
            var dayMap = { '월': 1, '화': 2, '수': 3, '목': 4, '금': 5, '토': 6, '일': 7 };
            var timeMap = { '09:00': 1, '10:00': 2, '11:00': 3, '12:00': 4, '13:00': 5, '14:00': 6, '15:00': 7, '16:00': 8 };
            var table = document.querySelector('.timetable-display');
            if (table) {
                ttData.split(',').forEach(function (s) {
                    var parts = s.split('-'), day = parts[0], time = parts[1];
                    if (day && time && dayMap[day] && timeMap[time]) {
                        var cell = table.rows[timeMap[time]].cells[dayMap[day]];
                        if (cell) { cell.classList.add('selected'); cell.textContent = '✓'; }
                    }
                });
            }
        }
        }
    })();
})();
