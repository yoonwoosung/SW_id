/* static/js/pages/farm_filter.js
   재사용 상세조건 필터 컴포넌트(바닐라 JS, 의존성 0).
   ★UI: 대분류 = 가로 탭 / 세부 = 같은 크기 체크박스 그리드(한 번에 하나의 대분류만) / 선택 = 상단 칩★
   상세검색 + 역제안 요청글 양쪽에서 FarmFilter.mount(el, opts)로 사용.

   사용:
     var f = FarmFilter.mount(document.getElementById('cond-filter'), {
       endpoint: '/api/search-categories',
       onApply: function (selected) { ... }   // {카테고리코드: [잎코드,...]} (빈 카테고리 제외)
     });
     f.getSelected(); f.reset();
*/
window.FarmFilter = (function () {
    'use strict';

    // API 실패 시 폴백 목업(실제 연동으로 쉽게 교체되도록 분리).
    var MOCK_TREE = [
        { code: 'region', label: '지역', children: [
            { code: 'gyeonggi', label: '경기', children: [
                { code: 'gapyeong', label: '가평' }, { code: 'yongin', label: '용인' }] }] },
        { code: 'activity', label: '액티비티', children: [
            { code: 'kayak', label: '카약' }, { code: 'hiking', label: '등산' }] }
    ];

    function esc(s) { var d = document.createElement('div'); d.textContent = (s == null ? '' : String(s)); return d.innerHTML; }

    // 한 대분류 패널: 잎은 그리드 체크박스, 하위 그룹은 소제목 + 재귀 그리드.
    function renderPanelNodes(nodes, topCode) {
        var leaves = nodes.filter(function (n) { return !(n.children && n.children.length); });
        var groups = nodes.filter(function (n) { return n.children && n.children.length; });
        var html = '';
        if (leaves.length) {
            html += '<div class="fl-grid">' + leaves.map(function (n) {
                return '<label class="fl-cell"><input type="checkbox" data-cat="' + esc(topCode) + '" value="' + esc(n.code) + '">'
                    + '<span>' + esc(n.label) + '</span></label>';
            }).join('') + '</div>';
        }
        groups.forEach(function (g) {
            html += '<div class="fl-subgroup"><div class="fl-subgroup__title">' + esc(g.label) + '</div>'
                + renderPanelNodes(g.children, topCode) + '</div>';
        });
        return html;
    }

    function mount(root, opts) {
        opts = opts || {};
        var chipsEl;

        function refresh() {
            var checked = Array.prototype.slice.call(root.querySelectorAll('input[type=checkbox]:checked'));
            chipsEl.innerHTML = checked.map(function (cb) {
                var label = cb.parentNode.querySelector('span').textContent;
                return '<span class="fl-chip" data-cat="' + esc(cb.dataset.cat) + '" data-value="' + esc(cb.value) + '">'
                    + esc(label) + '<button type="button" class="fl-chip__x" aria-label="' + esc(label) + ' 제거">&times;</button></span>';
            }).join('');
            root.querySelectorAll('.fl-tab').forEach(function (tab) {
                var n = root.querySelectorAll('input[data-cat="' + tab.dataset.cat + '"]:checked').length;
                var badge = tab.querySelector('.fl-tab__count');
                if (badge) { badge.textContent = n; badge.hidden = n === 0; }
            });
        }

        function getSelected() {
            var out = {};
            root.querySelectorAll('input[type=checkbox]:checked').forEach(function (cb) {
                (out[cb.dataset.cat] = out[cb.dataset.cat] || []).push(cb.value);
            });
            return out;
        }

        function reset() {
            root.querySelectorAll('input[type=checkbox]:checked').forEach(function (cb) { cb.checked = false; });
            refresh();
        }

        function showTab(code) {
            root.querySelectorAll('.fl-tab').forEach(function (t) { t.classList.toggle('is-active', t.dataset.cat === code); });
            root.querySelectorAll('.fl-catpanel').forEach(function (p) { p.hidden = p.dataset.catpanel !== code; });
        }

        function renderTree(tree) {
            root.innerHTML =
                '<div class="fl-chips" data-role="chips" aria-live="polite"></div>'
                + '<div class="fl-tabbar" role="tablist">' + tree.map(function (c, i) {
                    return '<button type="button" class="fl-tab' + (i === 0 ? ' is-active' : '') + '" data-cat="' + esc(c.code) + '">'
                        + esc(c.label) + '<span class="fl-tab__count" hidden>0</span></button>';
                }).join('') + '</div>'
                + '<div class="fl-panel-body">' + tree.map(function (c, i) {
                    return '<div class="fl-catpanel" data-catpanel="' + esc(c.code) + '"' + (i === 0 ? '' : ' hidden') + '>'
                        + renderPanelNodes(c.children || [], c.code)
                        + (c.note ? '<div class="fl-note">' + esc(c.note) + '</div>' : '')
                        + '</div>';
                }).join('') + '</div>'
                + '<div class="fl-actions">'
                + '<button type="button" class="fl-btn fl-btn--ghost" data-role="reset">초기화</button>'
                + '<button type="button" class="fl-btn fl-btn--primary" data-role="apply">이 조건으로 추천받기</button>'
                + '</div>';
            chipsEl = root.querySelector('[data-role=chips]');
            bind();
        }

        function bind() {
            root.addEventListener('click', function (e) {
                var tab = e.target.closest('.fl-tab');
                if (tab && root.contains(tab)) { showTab(tab.dataset.cat); return; }
                var x = e.target.closest('.fl-chip__x');
                if (x) {
                    var chip = x.closest('.fl-chip');
                    var cb = root.querySelector('input[data-cat="' + chip.dataset.cat + '"][value="' + chip.dataset.value + '"]');
                    if (cb) { cb.checked = false; refresh(); }
                    return;
                }
                if (e.target.closest('[data-role=reset]')) { reset(); return; }
                if (e.target.closest('[data-role=apply]') && opts.onApply) { opts.onApply(getSelected()); }
            });
            root.addEventListener('change', function (e) {
                if (e.target.matches('input[type=checkbox]')) { refresh(); }
            });
        }

        function load() {
            var url = opts.endpoint || root.dataset.endpoint;
            var done = function (tree) { renderTree(tree && tree.length ? tree : MOCK_TREE); };
            if (!url) { done(MOCK_TREE); return; }
            fetch(url).then(function (r) { return r.json(); }).then(function (res) {
                done((res && res.data && res.data.categories) || []);
            }).catch(function () { done(MOCK_TREE); });
        }

        load();
        return { getSelected: getSelected, reset: reset };
    }

    return { mount: mount };
})();
