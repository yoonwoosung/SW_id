/* static/js/pages/ai_recommend.js
   추천 화면: 검색바(페이지 내 코스 필터) + 인적사항 단축버튼 2개 + 접힘형 상세조건(FarmFilter)
   + 추천 코스 3섹션(지금 내 주변 / 또래 / 친환경 ESG). 각 섹션은 가로 스크롤 카드 행. */
(function () {
    'use strict';
    var TYPE_ICON = { experience: 'sprout', restaurant: 'utensils', attraction: 'landmark', cafe: 'coffee' };

    // ▼▼ 목업: 코스별 "지금 N명이 보는 중" 값만 직접 채우세요(비우면 안 보임). {체험id: 인원} ▼▼
    var COURSE_MOCK = { viewers: {} };   // 예: { 2: 12, 3: 7 }
    // ▲▲

    // 코스 섹션 정의: segment=null이면 종합 점수순, 'peers'/'esg'는 세그먼트 적용.
    var SECTIONS = [
        { key: 'nearby', rowId: 'sec-nearby', segment: null,   esg: false },
        { key: 'peers',  rowId: 'sec-peers',  segment: 'peers', esg: false },
        { key: 'esg',    rowId: 'sec-esg',    segment: 'esg',   esg: true }
    ];

    function esc(s) { var d = document.createElement('div'); d.textContent = (s == null ? '' : String(s)); return d.innerHTML; }
    function $(id) { return document.getElementById(id); }
    function shortRegion(addr) { if (!addr) return ''; var m = addr.match(/([가-힣]+?)(시|군|구)/); return m ? m[1] : addr.split(' ')[0]; }
    function won(n) { return Number(n || 0).toLocaleString() + '원'; }

    var filterEl = $('cond-filter'), noteEl = $('rec-note'),
        quickEl = $('quick-segments'), searchInput = $('course-q'), searchEmpty = $('search-empty');
    var coords = { lat: null, lon: null };
    var lastSelected = {};
    var currentQuery = '';
    var cardStore = {};   // storeKey → { rec, course, section }

    FarmFilter.mount(filterEl, { endpoint: filterEl.dataset.endpoint, onApply: function (sel) { lastSelected = sel; loadAll(); } });

    // ---- 상세조건 접힘 토글 ----
    var collapseToggle = document.querySelector('.fl-collapse__toggle');
    if (collapseToggle) collapseToggle.addEventListener('click', function () {
        var open = this.getAttribute('aria-expanded') === 'true';
        this.setAttribute('aria-expanded', String(!open));
        $(this.getAttribute('aria-controls')).hidden = open;
    });

    // ---- 섹션 제목/문구 개인화(회원 세그먼트 라벨) ----
    fetch('/api/recommendations/segments').then(function (r) { return r.json(); }).then(function (res) {
        if (!res.success) return;
        var label = (res.data && res.data.segment_label) || '';        // 예: "20대·남성"
        var age = label.split('·').filter(function (p) { return /대$/.test(p); })[0] || '';
        if (noteEl && label) noteEl.textContent = label + ' 회원님께 어울리는 코스를 준비했어요.';
        if (age) { var pt = $('peers-title'); if (pt) pt.textContent = '🌿 ' + age + '가 놀러가기 좋은 코스'; }
    }).catch(function () {});

    // ---- 인적사항 단축 버튼 2개(백엔드 segment-buttons 응답으로 렌더, 문구 하드코딩 금지) ----
    fetch('/api/recommend/segment-buttons').then(function (r) { return r.json(); }).then(function (res) {
        var btns = (res.data && res.data.buttons) || [];
        if (!quickEl || !btns.length) return;
        quickEl.innerHTML = btns.map(function (b) {
            return '<button type="button" class="fl-quickbtn" data-segment="' + esc(b.segment) + '" data-label="' + esc(b.label) + '" data-icon="' + esc(b.icon) + '">'
                + '<span class="fl-quickbtn__icon">' + esc(b.icon) + '</span><span>' + esc(b.label) + '</span></button>';
        }).join('');
    }).catch(function () {});

    // 버튼 클릭 → 해당 세그먼트 코스 섹션으로 이동, 또래 섹션이면 버튼 라벨로 제목 갱신.
    if (quickEl) quickEl.addEventListener('click', function (e) {
        var btn = e.target.closest('.fl-quickbtn');
        if (!btn) return;
        var seg = btn.dataset.segment || 'peers';
        var target = SECTIONS.filter(function (s) { return (s.segment || '') === seg; })[0];
        if (!target) return;
        if (target.rowId === 'sec-peers') {
            var pt = $('peers-title');
            if (pt) pt.textContent = btn.dataset.icon + ' ' + btn.dataset.label;
        }
        $(target.rowId).closest('.fl-sec').scrollIntoView({ behavior: 'smooth', block: 'start' });
    });

    // ---- 트렌드 키워드(상세조건 안) ----
    fetch('/api/trend-keywords').then(function (r) { return r.json(); }).then(function (res) {
        var kws = (res.data && res.data.keywords) || [];
        var el = $('trend');
        if (!el || !kws.length) return;
        el.innerHTML = '<span class="fl-empty" style="width:100%;padding:0 0 4px;">지금 뜨는 키워드</span>'
            + kws.map(function (k) { return '<span class="fl-trend__tag">#' + esc(k.label) + ' <b>' + k.count + '</b></span>'; }).join('');
    }).catch(function () {});

    // ---- 코스 로드 ----
    function buildQuery(selected, segment) {
        var qs = new URLSearchParams();
        if (coords.lat != null && coords.lon != null) { qs.set('lat', coords.lat); qs.set('lon', coords.lon); }
        if (segment) qs.set('segment', segment);
        Object.keys(selected || {}).forEach(function (cat) {
            (selected[cat] || []).forEach(function (v) { qs.append('cond_' + cat, v); });
        });
        return qs.toString();
    }

    function loadAll() {
        SECTIONS.forEach(function (s) { loadSection(s); });
    }

    function loadSection(s) {
        var row = $(s.rowId);
        row.innerHTML = '<p class="fl-empty">코스를 준비하는 중…</p>';
        fetch('/api/recommendations/personalized?' + buildQuery(lastSelected, s.segment))
            .then(function (r) { return r.json(); })
            .then(function (res) {
                if (!res.success) { row.innerHTML = '<p class="fl-empty">' + esc((res.error && res.error.message) || '추천을 불러올 수 없어요.') + '</p>'; return; }
                var list = (res.data.results || []).slice(0, 3);
                if (!list.length) { row.innerHTML = '<p class="fl-empty">추천할 코스를 찾지 못했어요.</p>'; return; }
                Promise.all(list.map(function (x) {
                    return fetch('/api/experiences/' + x.id + '/course')
                        .then(function (r) { return r.json(); })
                        .then(function (c) { return { rec: x, course: c.data || {} }; });
                })).then(function (cards) { renderRow(row, cards, s); });
            })
            .catch(function () { row.innerHTML = '<p class="fl-empty">추천을 불러오는 중 오류가 발생했어요.</p>'; });
    }

    function badges(x, isEsg) {
        var b = '';
        if (x.d_day != null && x.d_day >= 0 && x.d_day <= 7) b += '<span class="fl-badge fl-badge--urgent">마감임박</span>';
        if (isEsg && x.esg_grade) b += '<span class="fl-badge fl-badge--esg">ESG ' + esc(x.esg_grade) + '</span>';
        else if (x.eco) b += '<span class="fl-badge fl-badge--eco"><i data-lucide="leaf"></i> 친환경</span>';
        b += '<span class="fl-badge fl-badge--day">당일치기</span>';
        return b;
    }

    function metaHtml(summary) {
        var s = summary || {}, out = '';
        if (s.transport) out += '<span><i class="fa-solid fa-' + (s.transport === '자가용' ? 'car' : 'bus') + '"></i> 추천 ' + esc(s.transport) + '</span>';
        if (s.barrier_free) out += '<span class="fl-barrier"><i class="fa-solid fa-wheelchair"></i> 무장애</span>';
        return out;
    }

    function timelineHtml(items) {
        var stops = (items || []).filter(function (it) { return it.type !== 'experience'; }).length;
        if (!stops) return '<p class="fl-empty">주변 장소가 부족해 상세 코스를 만들지 못했어요.</p>';
        return (items || []).map(function (it) {
            var sub = it.type === 'experience' ? '이 체험' : (esc(it.address || '') + (it.distance_km != null ? ' · ' + it.distance_km + 'km' : ''));
            return '<div class="ai-timeline-item"><div class="ai-time">' + esc(it.time) + '</div><div class="ai-dot"></div>'
                + '<div class="ai-timeline-body"><div class="ai-act-name">' + esc(it.name || '') + '</div><div class="ai-act-sub">' + sub + '</div></div>'
                + '<div class="ai-thumb">' + ('<i data-lucide="' + (TYPE_ICON[it.type] || 'map-pin') + '"></i>') + '</div></div>';
        }).join('');
    }

    function renderRow(row, cards, s) {
        row.innerHTML = cards.map(function (cd, i) {
            var x = cd.rec, d = cd.course, sm = (d && d.summary) || {};
            var region = shortRegion(x.address);
            var title = (region ? esc(region) + ' ' : '') + esc(x.crop) + ' 힐링 코스';
            var searchKey = (title + ' ' + (x.address || '') + ' ' + (x.crop || '')).toLowerCase();
            var viewers = COURSE_MOCK.viewers[x.id];
            var reasons = (x.reasons || []).map(function (r) { return '<span class="fl-reason">' + esc(r) + '</span>'; }).join('');
            var storeKey = s.key + '-' + i;
            cardStore[storeKey] = { rec: x, course: d || {}, section: s };
            return '<article class="fl-course-card" data-search="' + esc(searchKey) + '" data-store-key="' + storeKey + '">'
                + '<div class="fl-course-card__band">' + badges(x, s.esg) + '</div>'
                + '<div class="fl-course-card__head">'
                + '<h3 class="fl-course-card__title">' + title + '</h3>'
                + (viewers != null ? '<p class="fl-course-viewers"><i data-lucide="eye"></i> 지금 ' + esc(viewers) + '명이 보는 중</p>' : '')
                + '<div class="fl-reasons">' + reasons + '</div>'
                + '<div class="fl-course-meta">' + metaHtml(sm) + '</div>'
                + '<div class="fl-course-price"><span class="fl-cost">' + won(sm.estimated_cost) + '</span><span class="fl-per">＊1인당 가격</span></div>'
                + '</div>'
                + '<button type="button" class="fl-course-card__toggle">'
                + '코스 상세보기 <i class="fa-solid fa-chevron-right" aria-hidden="true"></i></button>'
                + '</article>';
        }).join('');
        applySearch();   // 새로 그린 카드에도 현재 검색어 반영
    }

    // ---- 코스 카드 클릭 → 모달 ----
    document.querySelector('.ai-rec-wrap').addEventListener('click', function (e) {
        var card = e.target.closest('.fl-course-card[data-store-key]');
        if (!card) return;
        var data = cardStore[card.dataset.storeKey];
        if (data) openCourseModal(data);
    });

    var ciModal = document.getElementById('ci-modal');

    function openCourseModal(data) {
        var rec = data.rec, course = data.course, s = data.section;
        var sm = (course && course.summary) || {};
        var items = (course && course.items) || [];
        var region = shortRegion(rec.address);
        var title = (region ? region + ' ' : '') + rec.crop + ' 힐링 코스';

        document.getElementById('ci-badges').innerHTML = badges(rec, s.esg);
        document.getElementById('ci-title').textContent = title;

        var mHtml = '';
        if (sm.transport) mHtml += '<span><i class="fa-solid fa-' + (sm.transport === '자가용' ? 'car' : 'bus') + '"></i> 추천 ' + esc(sm.transport) + '</span>';
        if (sm.barrier_free) mHtml += '<span style="color:#1565c0;font-weight:700;"><i class="fa-solid fa-wheelchair"></i> 무장애</span>';
        document.getElementById('ci-meta').innerHTML = mHtml;

        document.getElementById('ci-reasons').innerHTML = (rec.reasons || []).map(function (r) {
            return '<span class="fl-reason">' + esc(r) + '</span>';
        }).join('');

        var costEl = document.getElementById('ci-cost');
        if (sm.estimated_cost) {
            costEl.innerHTML = '<div class="ci-modal__cost-num">' + Number(sm.estimated_cost).toLocaleString() + '원</div>'
                + '<div class="ci-modal__cost-lbl">1인당 예상 비용 · 체험비 + 식사 + 교통 포함</div>';
            costEl.hidden = false;
        } else {
            costEl.hidden = true;
        }

        document.getElementById('ci-timeline').innerHTML = buildModalTimeline(items);

        document.getElementById('ci-footer').innerHTML =
            '<a href="/experience/' + rec.id + '" class="fl-btn fl-btn-primary" style="width:100%;justify-content:center;">'
            + '<i class="fa-solid fa-calendar-check" style="margin-right:6px;"></i>이 체험 예약하러 가기</a>';

        ciModal.hidden = false;
        document.body.style.overflow = 'hidden';
        if (window.lucide) lucide.createIcons();
    }

    var TL_ICON = { experience: 'sprout', restaurant: 'utensils', attraction: 'landmark', cafe: 'coffee' };

    function buildModalTimeline(items) {
        if (!items || !items.length) return '<p class="fl-empty">코스 정보를 불러올 수 없어요.</p>';
        var stops = items.filter(function (it) { return it.type !== 'experience'; });
        var tlHtml = '<div class="ci-tl">' + items.map(function (it) {
            var icon = TL_ICON[it.type] || 'map-pin';
            var sub = it.type === 'experience'
                ? '메인 체험'
                : ((it.address || '') + (it.distance_km != null ? ' · ' + it.distance_km + 'km' : ''));
            return '<div class="ci-tl-item">'
                + '<div class="ci-tl-time">' + esc(it.time) + '</div>'
                + '<div class="ci-tl-icon"><i data-lucide="' + icon + '"></i></div>'
                + '<div><div class="ci-tl-name">' + esc(it.name || '') + '</div>'
                + (sub ? '<div class="ci-tl-sub">' + esc(sub) + '</div>' : '')
                + '</div></div>';
        }).join('') + '</div>';
        if (!stops.length) {
            return '<p class="fl-empty" style="margin-bottom:10px;">주변 관광지 정보를 불러오지 못했어요.<br>체험 장소만 표시됩니다.</p>' + tlHtml;
        }
        return tlHtml;
    }

    document.getElementById('ci-close').addEventListener('click', closeCourseModal);
    document.getElementById('ci-backdrop').addEventListener('click', closeCourseModal);
    function closeCourseModal() { ciModal.hidden = true; document.body.style.overflow = ''; }

    // ---- 검색: 페이지 내 코스 필터 ----
    function applySearch() {
        var q = currentQuery;
        var anyVisible = false;
        document.querySelectorAll('.fl-sec').forEach(function (sec) {
            var cardEls = sec.querySelectorAll('.fl-course-card');
            var visible = 0;
            cardEls.forEach(function (c) {
                var match = !q || (c.dataset.search || '').indexOf(q) !== -1;
                c.hidden = !match;
                if (match) visible++;
            });
            sec.hidden = (q !== '' && cardEls.length > 0 && visible === 0);
            if (visible > 0) anyVisible = true;
        });
        if (searchEmpty) searchEmpty.hidden = !(q !== '' && !anyVisible);
    }

    if (searchInput) searchInput.addEventListener('input', function () {
        currentQuery = this.value.trim().toLowerCase();
        applySearch();
    });

    // ---- 결제 후 연동: ?experience=<id> 있으면 '방금 예약한 체험 코스'를 상단에 표시 ----
    function loadBooked(id) {
        var sec = $('booked-sec'), row = $('sec-booked');
        if (!sec || !row) return;
        sec.hidden = false;
        row.innerHTML = '<p class="fl-empty">방금 예약한 체험 코스를 준비하는 중…</p>';
        fetch('/api/experiences/' + encodeURIComponent(id) + '/course')
            .then(function (r) { return r.json(); })
            .then(function (c) {
                var d = c.data;
                if (!d) { row.innerHTML = '<p class="fl-empty">코스를 불러오지 못했어요.</p>'; return; }
                var expItem = (d.items || []).filter(function (it) { return it.type === 'experience'; })[0] || {};
                var rec = { id: d.experience_id, crop: expItem.name || '예약한 체험', address: '',
                    reasons: ['방금 예약한 체험'], eco: false, esg_grade: null, d_day: null };
                renderRow(row, [{ rec: rec, course: d }], { key: 'booked', esg: false });
                sec.scrollIntoView({ behavior: 'smooth', block: 'start' });
            })
            .catch(function () { row.innerHTML = '<p class="fl-empty">코스를 불러오는 중 오류가 발생했어요.</p>'; });
    }

    var bookedId = new URLSearchParams(window.location.search).get('experience');
    if (bookedId) loadBooked(bookedId);

    // ---- 진입: 위치 1회 확보 후 3섹션 로드(위치 거부/미지원이면 위치 없이) ----
    function boot() {
        if (!navigator.geolocation) { loadAll(); return; }
        navigator.geolocation.getCurrentPosition(
            function (pos) { coords.lat = pos.coords.latitude; coords.lon = pos.coords.longitude; loadAll(); },
            function () { loadAll(); },
            { enableHighAccuracy: false, timeout: 15000, maximumAge: 0 }
        );
    }
    boot();
})();
