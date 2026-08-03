/* static/js/pages/ai_recommend.js
   AI 맞춤 추천 페이지: 회원정보 기반 자동 추천 세그먼트 + 상세조건 필터 + 맞춤 코스 카드.
   진입 즉시 기본(또래 인기) 추천을 보여주고, 세그먼트 카드/조건/위치로 정교화한다. */
(function () {
    'use strict';
    var TYPE_EMOJI = { experience: '🌱', restaurant: '🍽️', attraction: '🏛️', cafe: '☕' };

    // ▼▼ 목업: 코스별 "지금 N명이 보는 중" 값만 직접 채우세요(비우면 안 보임). {체험id: 인원} ▼▼
    var COURSE_MOCK = { viewers: {} };   // 예: { 2: 12, 3: 7 }
    // ▲▲

    function esc(s) { var d = document.createElement('div'); d.textContent = (s == null ? '' : String(s)); return d.innerHTML; }
    function $(id) { return document.getElementById(id); }
    function shortRegion(addr) { if (!addr) return ''; var m = addr.match(/([가-힣]+?)(시|군|구)/); return m ? m[1] : addr.split(' ')[0]; }
    function won(n) { return Number(n || 0).toLocaleString() + '원'; }

    var filterEl = $('cond-filter'), resultsEl = $('course-results'), noteEl = $('rec-note'),
        segEl = $('ai-segments'), segPanel = $('ai-seg-panel');
    var activeSegment = 'peers';

    FarmFilter.mount(filterEl, { endpoint: filterEl.dataset.endpoint, onApply: run });

    // 자동 추천 세그먼트 카드
    fetch('/api/recommendations/segments').then(function (r) { return r.json(); }).then(function (res) {
        if (!res.success) return;
        var d = res.data;
        if (noteEl) noteEl.textContent = (d.segment_label ? d.segment_label + ' ' : '') + '정보를 바탕으로 AI가 먼저 추천해요.';
        var segs = d.segments || [];
        if (segPanel && segs.length) {
            segPanel.hidden = false;
            segEl.innerHTML = segs.map(function (s, i) {
                return '<button type="button" class="ai-seg-card' + (i === 0 ? ' is-active' : '') + '" data-seg="' + esc(s.key) + '">'
                    + '<div class="ai-seg-emoji">' + esc(s.emoji) + '</div>'
                    + '<div class="ai-seg-title">' + esc(s.title) + '</div>'
                    + '<div class="ai-seg-sub">' + esc(s.subtitle) + '</div></button>';
            }).join('');
        }
    }).catch(function () {});

    if (segEl) segEl.addEventListener('click', function (e) {
        var card = e.target.closest('.ai-seg-card');
        if (!card) return;
        activeSegment = card.dataset.seg;
        segEl.querySelectorAll('.ai-seg-card').forEach(function (c) { c.classList.toggle('is-active', c === card); });
        loadCourses(null, null, {}, false);
    });

    // 트렌드 키워드
    fetch('/api/trend-keywords').then(function (r) { return r.json(); }).then(function (res) {
        var kws = (res.data && res.data.keywords) || [];
        var el = $('trend');
        if (!el || !kws.length) return;
        el.innerHTML = '<span class="fl-empty" style="width:100%;padding:0 0 4px;">지금 뜨는 키워드</span>'
            + kws.map(function (k) { return '<span class="fl-trend__tag">#' + esc(k.label) + ' <b>' + k.count + '</b></span>'; }).join('');
    }).catch(function () {});

    function run(selected) {
        if (!navigator.geolocation) { loadCourses(null, null, selected, false); return; }
        resultsEl.innerHTML = '<p class="fl-empty">내 위치로 맞춤 코스를 찾는 중…</p>';
        navigator.geolocation.getCurrentPosition(
            function (pos) { loadCourses(pos.coords.latitude, pos.coords.longitude, selected, false); },
            function () { loadCourses(null, null, selected, false); },   // 위치 거부 시 위치 없이라도 추천
            { enableHighAccuracy: false, timeout: 15000, maximumAge: 0 }
        );
    }

    function buildQuery(lat, lon, selected) {
        var qs = new URLSearchParams();
        if (lat != null && lon != null) { qs.set('lat', lat); qs.set('lon', lon); }
        if (activeSegment) qs.set('segment', activeSegment);
        Object.keys(selected || {}).forEach(function (cat) {
            (selected[cat] || []).forEach(function (v) { qs.append('cond_' + cat, v); });
        });
        return qs.toString();
    }

    function loadCourses(lat, lon, selected, isDefault) {
        resultsEl.innerHTML = '<p class="fl-empty">' + (isDefault ? '기본 추천 코스를 준비하는 중…' : '맞춤 코스를 찾는 중…') + '</p>';
        fetch('/api/recommendations/personalized?' + buildQuery(lat, lon, selected))
            .then(function (r) { return r.json(); })
            .then(function (res) {
                if (!res.success) { resultsEl.innerHTML = '<p class="fl-empty">' + esc((res.error && res.error.message) || '추천을 불러올 수 없어요.') + '</p>'; return; }
                var list = (res.data.results || []).slice(0, 3);
                if (!list.length) { resultsEl.innerHTML = '<p class="fl-empty">추천할 체험을 찾지 못했어요.</p>'; return; }
                Promise.all(list.map(function (x) {
                    return fetch('/api/experiences/' + x.id + '/course')
                        .then(function (r) { return r.json(); })
                        .then(function (c) { return { rec: x, course: c.data || {} }; });
                })).then(renderCards);
            })
            .catch(function () { resultsEl.innerHTML = '<p class="fl-empty">추천을 불러오는 중 오류가 발생했어요.</p>'; });
    }

    function badges(x) {
        var b = '';
        if (x.d_day != null && x.d_day >= 0 && x.d_day <= 7) b += '<span class="fl-badge fl-badge--urgent">마감임박</span>';
        if (x.eco) b += '<span class="fl-badge fl-badge--eco">🌱 ESG</span>';
        b += '<span class="fl-badge fl-badge--day">당일치기</span>';
        return b;
    }

    function metaHtml(summary) {
        var s = summary || {}, out = '';
        if (s.transport) out += '<span><i class="fa-solid fa-' + (s.transport === '자가용' ? 'car' : 'bus') + '"></i> ' + esc(s.transport) + '</span>';
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
                + '<div class="ai-thumb">' + (TYPE_EMOJI[it.type] || '📍') + '</div></div>';
        }).join('');
    }

    function renderCards(cards) {
        resultsEl.innerHTML = cards.map(function (cd, i) {
            var x = cd.rec, d = cd.course, s = d.summary || {};
            var region = shortRegion(x.address);
            var title = (region ? esc(region) + ' ' : '') + esc(x.crop) + ' 힐링 코스';
            var viewers = COURSE_MOCK.viewers[x.id];
            var reasons = (x.reasons || []).map(function (r) { return '<span class="fl-reason">' + esc(r) + '</span>'; }).join('');
            var bodyId = 'course-body-' + i;
            return '<article class="fl-course-card">'
                + '<div class="fl-course-card__band">' + badges(x) + '</div>'
                + '<div class="fl-course-card__head">'
                + '<h3 class="fl-course-card__title">' + title + '</h3>'
                + (viewers != null ? '<p class="fl-course-viewers">👀 지금 ' + esc(viewers) + '명이 보는 중</p>' : '')
                + '<div class="fl-reasons">' + reasons + '</div>'
                + '<div class="fl-course-meta">' + metaHtml(s) + '</div>'
                + '<div class="fl-course-price"><span class="fl-cost">' + won(s.estimated_cost) + '</span><span class="fl-per">＊1인당 가격</span></div>'
                + '</div>'
                + '<button type="button" class="fl-course-card__toggle" aria-expanded="false" aria-controls="' + bodyId + '">'
                + '자세히 보기 <i class="fa-solid fa-chevron-down fl-acc__toggle" aria-hidden="true"></i></button>'
                + '<div class="fl-course-card__body ai-timeline" id="' + bodyId + '" hidden>' + timelineHtml(d.items) + '</div>'
                + '</article>';
        }).join('');
    }

    resultsEl.addEventListener('click', function (e) {
        var t = e.target.closest('.fl-course-card__toggle');
        if (!t) return;
        var expanded = t.getAttribute('aria-expanded') === 'true';
        t.setAttribute('aria-expanded', String(!expanded));
        $(t.getAttribute('aria-controls')).hidden = expanded;
    });

    // 진입 즉시 기본 추천(또래 인기)
    loadCourses(null, null, {}, true);
})();
