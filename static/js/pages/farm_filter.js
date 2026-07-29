/* static/js/pages/farm_filter.js
   재사용 상세조건 아코디언 드롭박스 컴포넌트(바닐라 JS, 의존성 0).
   상세검색 + 역제안 요청글 양쪽에서 FarmFilter.mount(el, opts)로 사용.

   사용:
     var f = FarmFilter.mount(document.getElementById('cond-filter'), {
       endpoint: '/api/search-categories',   // 카테고리 트리(중첩) 소스. 실패 시 목업으로 폴백.
       onApply: function (selected) { ... }   // {카테고리코드: [잎코드,...]} (빈 카테고리는 제외)
     });
     f.getSelected(); f.reset();
*/
window.FarmFilter = (function () {
    'use strict';

    // API 실패 시 폴백용 최소 목업(실제 연동으로 쉽게 교체되도록 분리).
    var MOCK_TREE = [
        { code: 'region', label: '지역', children: [
            { code: 'gyeonggi', label: '경기', children: [
                { code: 'icheon', label: '이천' }, { code: 'anseong', label: '안성' }] }] },
        { code: 'activity', label: '액티비티', children: [
            { code: 'harvest', label: '수확체험' }, { code: 'fishing', label: '낚시' }] }
    ];

    function esc(s) { var d = document.createElement('div'); d.textContent = (s == null ? '' : String(s)); return d.innerHTML; }

    function renderNodes(nodes, topCode) {
        var leaves = nodes.filter(function (n) { return !(n.children && n.children.length); });
        var groups = nodes.filter(function (n) { return n.children && n.children.length; });
        var html = '';
        if (leaves.length) {
            html += '<div class="fl-checks">' + leaves.map(function (n) {
                return '<label class="fl-check"><input type="checkbox" data-cat="' + esc(topCode) + '" value="' + esc(n.code) + '">'
                    + '<span>' + esc(n.label) + '</span></label>';
            }).join('') + '</div>';
        }
        groups.forEach(function (g) {
            html += '<div class="fl-group">'
                + '<button type="button" class="fl-group__head" aria-expanded="false"><span>' + esc(g.label) + '</span>'
                + '<i class="fa-solid fa-chevron-down fl-acc__toggle" aria-hidden="true"></i></button>'
                + '<div class="fl-group__body" hidden>' + renderNodes(g.children, topCode) + '</div></div>';
        });
        return html;
    }

    function renderTree(root, tree) {
        var acc = tree.map(function (cat) {
            return '<div class="fl-acc__item">'
                + '<button type="button" class="fl-acc__head" data-cat="' + esc(cat.code) + '" aria-expanded="false">'
                + '<span>' + esc(cat.label) + '<span class="fl-acc__count" hidden>0</span></span>'
                + '<i class="fa-solid fa-chevron-down fl-acc__toggle" aria-hidden="true"></i></button>'
                + '<div class="fl-acc__body" hidden>' + renderNodes(cat.children || [], cat.code) + '</div></div>';
        }).join('');

        root.innerHTML =
            '<div class="fl-chips" data-role="chips" aria-live="polite"></div>'
            + '<div class="fl-acc" data-role="acc">' + acc + '</div>'
            + '<div class="fl-actions">'
            + '<button type="button" class="fl-btn fl-btn--ghost" data-role="reset">초기화</button>'
            + '<button type="button" class="fl-btn fl-btn--primary" data-role="apply">이 조건으로 추천받기</button>'
            + '</div>';
    }

    function mount(root, opts) {
        opts = opts || {};
        var chipsEl, applyBtn;

        function refresh() {
            var checked = Array.prototype.slice.call(root.querySelectorAll('input[type=checkbox]:checked'));
            chipsEl.innerHTML = checked.map(function (cb) {
                var label = cb.parentNode.querySelector('span').textContent;
                return '<span class="fl-chip" data-cat="' + esc(cb.dataset.cat) + '" data-value="' + esc(cb.value) + '">'
                    + esc(label) + '<button type="button" class="fl-chip__x" aria-label="' + esc(label) + ' 제거">&times;</button></span>';
            }).join('');
            root.querySelectorAll('.fl-acc__head').forEach(function (head) {
                var n = root.querySelectorAll('input[data-cat="' + head.dataset.cat + '"]:checked').length;
                var badge = head.querySelector('.fl-acc__count');
                badge.textContent = n;
                badge.hidden = n === 0;
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

        function bind() {
            chipsEl = root.querySelector('[data-role=chips]');
            applyBtn = root.querySelector('[data-role=apply]');

            root.addEventListener('click', function (e) {
                var head = e.target.closest('.fl-acc__head, .fl-group__head');
                if (head && root.contains(head)) {
                    var expanded = head.getAttribute('aria-expanded') === 'true';
                    head.setAttribute('aria-expanded', String(!expanded));
                    head.nextElementSibling.hidden = expanded;
                    return;
                }
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
            var done = function (tree) { renderTree(root, tree); bind(); };
            if (!url) { done(MOCK_TREE); return; }
            fetch(url).then(function (r) { return r.json(); }).then(function (res) {
                var tree = (res && res.data && res.data.categories) || [];
                done(tree.length ? tree : MOCK_TREE);
            }).catch(function () { done(MOCK_TREE); });
        }

        load();
        return { getSelected: getSelected, reset: reset };
    }

    return { mount: mount };
})();
