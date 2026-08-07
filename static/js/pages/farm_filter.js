/* static/js/pages/farm_filter.js
   재사용 상세조건 필터(바닐라 JS, 의존성 0).
   ★UI: 대분류 = 세로 탭(왼쪽) / 중분류(도·묶음) = 가로 아코디언(▶/▼, 초기 전부 접힘)
        · 아코디언 헤더 우측 체크 = 그 중분류의 소분류 전체 선택 / 소분류 = 그리드 체크박스 / 선택 = 칩★
   FarmFilter.mount(el, opts)로 상세검색·역제안 등에서 재사용.
*/
window.FarmFilter = (function () {
    'use strict';

    var MOCK_TREE = [
        { code: 'region', label: '지역', children: [
            { code: 'gyeonggi', label: '경기', children: [
                { code: 'gapyeong', label: '가평' }, { code: 'yongin', label: '용인' }] }] }
    ];

    function esc(s) { var d = document.createElement('div'); d.textContent = (s == null ? '' : String(s)); return d.innerHTML; }

    // 잎은 그리드 체크박스, 중분류(children 있음)는 가로 아코디언(헤더 토글 + 우측 '전체' 부모 체크박스 + 재귀 하위).
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
            html += '<div class="fl-subgroup fl-acc">'
                + '<div class="fl-acc__head">'
                + '<button type="button" class="fl-acc__toggle-btn" aria-expanded="false">'
                + '<i class="fa-solid fa-chevron-right fl-acc__caret" aria-hidden="true"></i>'
                + '<span>' + esc(g.label) + '</span></button>'
                + '<label class="fl-acc__check" title="' + esc(g.label) + ' 전체 선택">'
                + '<input type="checkbox" class="fl-parent" data-cat="' + esc(topCode) + '" value="' + esc(g.code) + '"><span>전체</span></label>'
                + '</div>'
                + '<div class="fl-acc__body" hidden>' + renderPanelNodes(g.children, topCode) + '</div>'
                + '</div>';
        });
        return html;
    }

    function mount(root, opts) {
        opts = opts || {};
        var chipsEl;

        // 상위 '전체'가 이미 체크된 항목은 대표(상위)만 유효 선택으로 본다(칩·조건 중복 방지).
        function hasCheckedAncestor(input) {
            var group = input.closest('.fl-subgroup');
            while (group) {
                var parent = group.querySelector(':scope > .fl-acc__head .fl-parent');
                if (parent && parent !== input && parent.checked) return true;
                var up = group.parentElement;
                group = up ? up.closest('.fl-subgroup') : null;
            }
            return false;
        }
        function effectiveChecked() {
            return Array.prototype.slice.call(root.querySelectorAll('input[type=checkbox]:checked'))
                .filter(function (cb) { return !hasCheckedAncestor(cb); });
        }

        // 부모 체크 상태를 하위 잎 기준으로 동기화(전체 체크→체크, 일부→중간표시).
        function syncParents() {
            root.querySelectorAll('.fl-parent').forEach(function (p) {
                var group = p.closest('.fl-subgroup');
                var leaves = Array.prototype.slice.call(group.querySelectorAll('input[type=checkbox]:not(.fl-parent)'));
                if (!leaves.length) return;
                var checked = leaves.filter(function (c) { return c.checked; }).length;
                p.checked = checked === leaves.length;
                p.indeterminate = checked > 0 && checked < leaves.length;
            });
        }

        function refresh() {
            var checked = effectiveChecked();
            chipsEl.innerHTML = checked.map(function (cb) {
                var label = cb.closest('label').querySelector('span').textContent;
                // 아코디언 '전체'(fl-parent) 칩은 중분류 이름으로 표시.
                if (cb.classList.contains('fl-parent')) {
                    var head = cb.closest('.fl-subgroup').querySelector('.fl-acc__toggle-btn span');
                    if (head) label = head.textContent;
                }
                return '<span class="fl-chip" data-cat="' + esc(cb.dataset.cat) + '" data-value="' + esc(cb.value) + '">'
                    + esc(label) + '<button type="button" class="fl-chip__x" aria-label="' + esc(label) + ' 제거">&times;</button></span>';
            }).join('');
            root.querySelectorAll('.fl-tab').forEach(function (tab) {
                var n = checked.filter(function (cb) { return cb.dataset.cat === tab.dataset.cat; }).length;
                var badge = tab.querySelector('.fl-tab__count');
                if (badge) { badge.textContent = n; badge.hidden = n === 0; }
            });
        }

        function getSelected() {
            var out = {};
            effectiveChecked().forEach(function (cb) {
                (out[cb.dataset.cat] = out[cb.dataset.cat] || []).push(cb.value);
            });
            return out;
        }

        function reset() {
            root.querySelectorAll('input[type=checkbox]').forEach(function (cb) { cb.checked = false; cb.indeterminate = false; });
            refresh();
        }

        function showTab(code) {
            root.querySelectorAll('.fl-tab').forEach(function (t) { t.classList.toggle('is-active', t.dataset.cat === code); });
            root.querySelectorAll('.fl-catpanel').forEach(function (p) { p.hidden = p.dataset.catpanel !== code; });
        }

        function toggleAcc(btn) {
            var body = btn.closest('.fl-acc').querySelector(':scope > .fl-acc__body');
            var open = btn.getAttribute('aria-expanded') === 'true';
            btn.setAttribute('aria-expanded', String(!open));
            if (body) body.hidden = open;
        }

        function renderTree(tree) {
            root.innerHTML =
                '<div class="fl-chips" data-role="chips" aria-live="polite"></div>'
                + '<div class="fl-filter">'
                + '<div class="fl-tabbar fl-tabbar--vertical" role="tablist">' + tree.map(function (c, i) {
                    return '<button type="button" class="fl-tab' + (i === 0 ? ' is-active' : '') + '" data-cat="' + esc(c.code) + '">'
                        + '<span class="fl-tab__label">' + esc(c.label) + '</span><span class="fl-tab__count" hidden>0</span></button>';
                }).join('') + '</div>'
                + '<div class="fl-panel-body">' + tree.map(function (c, i) {
                    return '<div class="fl-catpanel" data-catpanel="' + esc(c.code) + '"' + (i === 0 ? '' : ' hidden') + '>'
                        + renderPanelNodes(c.children || [], c.code)
                        + (c.note ? '<div class="fl-note">' + esc(c.note) + '</div>' : '')
                        + '</div>';
                }).join('') + '</div>'
                + '</div>'
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
                var acc = e.target.closest('.fl-acc__toggle-btn');
                if (acc && root.contains(acc)) { toggleAcc(acc); return; }
                var x = e.target.closest('.fl-chip__x');
                if (x) {
                    var chip = x.closest('.fl-chip');
                    var cb = root.querySelector('input[data-cat="' + chip.dataset.cat + '"][value="' + chip.dataset.value + '"]');
                    if (cb) {
                        cb.checked = false;
                        if (cb.classList.contains('fl-parent')) {
                            cb.closest('.fl-subgroup').querySelectorAll('input[type=checkbox]').forEach(function (d) { d.checked = false; d.indeterminate = false; });
                        }
                        syncParents(); refresh();
                    }
                    return;
                }
                if (e.target.closest('[data-role=reset]')) { reset(); return; }
                if (e.target.closest('[data-role=apply]') && opts.onApply) { opts.onApply(getSelected()); }
            });
            root.addEventListener('change', function (e) {
                if (!e.target.matches('input[type=checkbox]')) return;
                if (e.target.classList.contains('fl-parent')) {   // 중분류 '전체' 체크 → 하위 소분류 전체 선택/해제
                    e.target.closest('.fl-subgroup').querySelectorAll('input[type=checkbox]').forEach(function (cb) {
                        cb.checked = e.target.checked; cb.indeterminate = false;
                    });
                }
                syncParents();
                refresh();
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
