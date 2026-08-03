/* static/js/pages/ai_recommend.js
   AI 맞춤 추천 페이지 컨트롤러: 재사용 FarmFilter 마운트 → 위치 기반 추천 → 맞춤 코스 카드 렌더.
   코스 시간표는 공용 .ai-timeline* 스타일을 재사용한다. */
(function () {
    'use strict';
    var TYPE_EMOJI = { experience: '🌱', restaurant: '🍽️', attraction: '🏛️', cafe: '☕' };

    function esc(s) { var d = document.createElement('div'); d.textContent = (s == null ? '' : String(s)); return d.innerHTML; }

    function shortRegion(addr) {
        if (!addr) return '';
        var m = addr.match(/([가-힣]+?)(시|군|구)/);
        return m ? m[1] : addr.split(' ')[0];
    }

    var filterEl = document.getElementById('cond-filter');
    var resultsEl = document.getElementById('course-results');
    var noteEl = document.getElementById('rec-note');

    FarmFilter.mount(filterEl, { endpoint: filterEl.dataset.endpoint, onApply: run });

    // 진입 즉시: 좌표 없이 회원정보 기반 '기본 추천 코스'를 보여준다(위치·조건은 이후 정교화).
    loadCourses(null, null, {}, true);

    // 트렌드 키워드(검색창 하단)
    fetch('/api/trend-keywords').then(function (r) { return r.json(); }).then(function (res) {
        var kws = (res.data && res.data.keywords) || [];
        var el = document.getElementById('trend');
        if (!el || !kws.length) return;
        el.innerHTML = '<span class="fl-empty" style="width:100%;padding:0 0 4px;">지금 뜨는 키워드</span>'
            + kws.map(function (k) { return '<span class="fl-trend__tag">#' + esc(k.label) + ' <b>' + k.count + '</b></span>'; }).join('');
    }).catch(function () {});

    function run(selected) {
        if (!navigator.geolocation) { resultsEl.innerHTML = '<p class="fl-empty">이 브라우저는 위치 정보를 지원하지 않아요.</p>'; return; }
        resultsEl.innerHTML = '<p class="fl-empty">내 위치로 맞춤 코스를 찾는 중…</p>';
        navigator.geolocation.getCurrentPosition(
            function (pos) { loadCourses(pos.coords.latitude, pos.coords.longitude, selected); },
            function () { resultsEl.innerHTML = '<p class="fl-empty">위치 권한을 허용해야 맞춤 코스를 추천할 수 있어요.</p>'; },
            { enableHighAccuracy: false, timeout: 15000, maximumAge: 0 }
        );
    }

    function buildQuery(lat, lon, selected) {
        var qs = new URLSearchParams();
        if (lat != null && lon != null) { qs.set('lat', lat); qs.set('lon', lon); }
        Object.keys(selected || {}).forEach(function (cat) {
            (selected[cat] || []).forEach(function (v) { qs.append('cond_' + cat, v); });
        });
        return qs.toString();
    }

    function loadCourses(lat, lon, selected, isDefault) {
        resultsEl.innerHTML = '<p class="fl-empty">' + (isDefault ? '기본 추천 코스를 준비하는 중…' : '내 위치로 맞춤 코스를 찾는 중…') + '</p>';
        fetch('/api/recommendations/personalized?' + buildQuery(lat, lon, selected))
            .then(function (r) { return r.json(); })
            .then(function (res) {
                if (!res.success) { resultsEl.innerHTML = '<p class="fl-empty">' + esc((res.error && res.error.message) || '추천을 불러올 수 없어요.') + '</p>'; return; }
                var list = (res.data.results || []).slice(0, 3);
                if (!list.length) { resultsEl.innerHTML = '<p class="fl-empty">추천할 체험을 찾지 못했어요.</p>'; return; }
                if (noteEl) {
                    if (res.data.segment_applied) { noteEl.textContent = '회원님과 비슷한 분들이 좋아한 코스를 반영했어요.'; }
                    else if (isDefault) { noteEl.textContent = '기본 추천이에요. ‘내 위치로 맞춤 추천받기’를 누르거나 조건을 고르면 더 정확해져요.'; }
                }
                Promise.all(list.map(function (x) {
                    return fetch('/api/experiences/' + x.id + '/course')
                        .then(function (r) { return r.json(); })
                        .then(function (c) { return { rec: x, course: c.data || {} }; });
                })).then(renderCards);
            })
            .catch(function () { resultsEl.innerHTML = '<p class="fl-empty">추천을 불러오는 중 오류가 발생했어요.</p>'; });
    }

    function metaHtml(summary) {
        var s = summary || {}, out = '';
        if (s.estimated_cost != null) out += '<span class="fl-cost">예상 ' + Number(s.estimated_cost).toLocaleString() + '원</span>';
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
            var x = cd.rec, d = cd.course;
            var region = shortRegion(x.address);
            var title = (region ? esc(region) + ' ' : '') + esc(x.crop) + ' 힐링 코스';
            var reasons = (x.reasons || []).map(function (r) { return '<span class="fl-reason">' + esc(r) + '</span>'; }).join('');
            var bodyId = 'course-body-' + i;
            return '<article class="fl-course-card">'
                + '<div class="fl-course-card__head">'
                + '<h3 class="fl-course-card__title">' + title + '<span class="fl-course-badge">당일치기</span></h3>'
                + '<div class="fl-reasons">' + reasons + '</div>'
                + '<div class="fl-course-meta">' + metaHtml(d.summary) + '</div></div>'
                + '<button type="button" class="fl-course-card__toggle" aria-expanded="false" aria-controls="' + bodyId + '">'
                + '자세히 보기 <i class="fa-solid fa-chevron-down fl-acc__toggle" aria-hidden="true"></i></button>'
                + '<div class="fl-course-card__body ai-timeline" id="' + bodyId + '" hidden>' + timelineHtml(d.items) + '</div>'
                + '</article>';
        }).join('');
    }

    // 코스 카드 '자세히 보기' 아코디언(위임)
    resultsEl.addEventListener('click', function (e) {
        var t = e.target.closest('.fl-course-card__toggle');
        if (!t) return;
        var expanded = t.getAttribute('aria-expanded') === 'true';
        t.setAttribute('aria-expanded', String(!expanded));
        document.getElementById(t.getAttribute('aria-controls')).hidden = expanded;
    });
})();
