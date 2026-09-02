// static/js/pages/search.js — 메인 페이지 AJAX 검색 처리

const SEARCH_API_URL = '/api/search';
let currentSort = 'deadline';
let currentPage = 1;

document.addEventListener('DOMContentLoaded', function () {
    const form = document.getElementById('search-form');
    if (form) {
        form.addEventListener('submit', function (e) {
            e.preventDefault();
            currentPage = 1;
            doSearch({});
        });
    }
});

function doSearch(extraParams) {
    const form = document.getElementById('search-form');
    if (!form) return;

    if (extraParams.sort) currentSort = extraParams.sort;
    if (extraParams.page) currentPage = extraParams.page;

    const params = new URLSearchParams({
        crop_query: form.querySelector('[name="crop_query"]').value,
        region:     form.querySelector('[name="region"]').value,
        date_filter: form.querySelector('[name="date_filter"]').value,
        people_count: form.querySelector('[name="people_count"]').value,
        sort: currentSort,
        page: currentPage,
    });
    if (extraParams.lat) params.set('lat', extraParams.lat);
    if (extraParams.lon) params.set('lon', extraParams.lon);
    if (extraParams.region) params.set('region', extraParams.region);

    document.getElementById('default-content').style.display = 'none';
    document.getElementById('search-result-section').style.display = 'block';
    showSkeleton();
    updateSortPills(currentSort);

    fetch(`${SEARCH_API_URL}?${params}`)
        .then(function (res) { return res.json(); })
        .then(function (data) {
            if (data.success) {
                renderResults(data, params);
            } else {
                showError();
            }
        })
        .catch(function () { showError(); });
}

function showSkeleton() {
    const grid = document.getElementById('card-grid');
    const skeleton = document.getElementById('search-skeleton');
    const header = document.getElementById('search-result-header');
    const pagination = document.getElementById('pagination-wrap');

    if (grid) grid.style.display = 'none';
    if (skeleton) skeleton.style.display = 'grid';
    if (header) header.style.display = 'none';
    if (pagination) pagination.style.display = 'none';
}

function renderResults(data, params) {
    const grid = document.getElementById('card-grid');
    const skeleton = document.getElementById('search-skeleton');
    const header = document.getElementById('search-result-header');
    const pagination = document.getElementById('pagination-wrap');

    if (skeleton) skeleton.style.display = 'none';
    if (grid) {
        grid.style.display = 'grid';
        grid.innerHTML = data.items.length > 0 ? data.items.map(buildCard).join('') : buildEmpty();
    }

    if (header) {
        header.style.display = 'flex';
        header.innerHTML = buildResultHeader(data, params);
    }

    if (pagination) {
        if (data.pages > 1) {
            pagination.style.display = 'block';
            pagination.innerHTML = buildPagination(data.page, data.pages, params);
        } else {
            pagination.style.display = 'none';
        }
    }

    if (window.lucide) lucide.createIcons();
    document.getElementById('search-result-section').scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function buildCard(item) {
    const remaining = item.remaining_spots;
    const isClosed = remaining <= 0;
    const imgHtml = item.first_image
        ? `<img src="/static/uploads/${item.first_image}" alt="${item.crop}" class="exp-card-img">`
        : `<div class="exp-card-img-placeholder"><i data-lucide="sprout"></i></div>`;

    let badgeHtml = '';
    if (isClosed) {
        badgeHtml = '<span class="exp-badge badge-closed">마감임박</span>';
    } else if (item.is_specialty) {
        badgeHtml = '<span class="exp-badge badge-family">가족추천</span>';
    } else if (item.pesticide_free) {
        badgeHtml = '<span class="exp-badge badge-eco">친환경</span>';
    } else {
        badgeHtml = '<span class="exp-badge badge-open">예약가능</span>';
    }

    const distBadge = (item.distance !== null && currentSort === 'recommended')
        ? `<div class="exp-card-dist-badge"><i data-lucide="map-pin"></i> ${item.distance}km</div>`
        : '';

    let dDayHtml = '';
    const d = item.d_day;
    if (d >= 0 && d < 999) {
        dDayHtml = d <= 3
            ? `<span class="text-danger font-weight-bold">D-${d}</span>`
            : `D-${d}`;
    } else {
        dDayHtml = '당일 체험';
    }

    return `
    <a href="/experience/${item.id}" class="exp-card${isClosed ? ' closed' : ''}">
        <div class="exp-card-img-wrap">
            ${imgHtml}
            <div class="exp-card-badge-wrap">${badgeHtml}</div>
            ${distBadge}
        </div>
        <div class="exp-card-body">
            <div class="exp-card-title">${item.crop} 체험</div>
            <div class="exp-card-location"><i data-lucide="map-pin"></i> ${item.address_detail}</div>
            <div class="exp-card-meta">
                <span><i data-lucide="users"></i> 2-4인 추천</span>
                <span><i data-lucide="clock"></i> ${dDayHtml}</span>
            </div>
            <div class="exp-card-price">${item.cost.toLocaleString()}원~</div>
        </div>
    </a>`;
}

function buildEmpty() {
    return `<div class="no-items-message" style="grid-column:1/-1;">
        <div class="empty-icon"><i data-lucide="search-x"></i></div>
        <p>검색 결과가 없어요.</p>
        <small>다른 키워드나 지역을 시도해보세요.</small>
    </div>`;
}

function showError() {
    const skeleton = document.getElementById('search-skeleton');
    const grid = document.getElementById('card-grid');
    const header = document.getElementById('search-result-header');

    if (skeleton) skeleton.style.display = 'none';
    if (header) header.style.display = 'none';
    if (grid) {
        grid.style.display = 'grid';
        grid.innerHTML = `<div class="no-items-message" style="grid-column:1/-1;">
            <div class="empty-icon"><i data-lucide="wifi-off"></i></div>
            <p>검색 중 오류가 발생했어요.</p>
            <small>잠시 후 다시 시도해주세요.</small>
        </div>`;
    }
    if (window.lucide) lucide.createIcons();
}

function buildResultHeader(data, params) {
    const cropQuery = params.get('crop_query');
    const region = params.get('region');
    const dateFilter = params.get('date_filter');
    const peopleCount = params.get('people_count');

    const chips = [];
    if (cropQuery) chips.push(makeChip(cropQuery, 'crop_query'));
    if (region)    chips.push(makeChip(region, 'region'));
    if (dateFilter) chips.push(makeChip(dateFilter, 'date_filter'));
    if (peopleCount) chips.push(makeChip(`${peopleCount}명`, 'people_count'));

    return `
    <div class="search-result-info">
        <span>검색결과 <b>${data.total}건</b></span>
        <div class="search-filter-chips">${chips.join('')}</div>
    </div>`;
}

function makeChip(label, field) {
    return `<span class="search-chip">${label} <button type="button" onclick="removeFilter('${field}')" aria-label="필터 제거">✕</button></span>`;
}

function removeFilter(field) {
    const form = document.getElementById('search-form');
    if (!form) return;
    const el = form.querySelector(`[name="${field}"]`);
    if (el) el.value = '';
    currentPage = 1;
    doSearch({});
}

function buildPagination(page, pages, params) {
    let html = '<ul class="pagination justify-content-center">';

    const prevDisabled = page <= 1 ? 'disabled' : '';
    html += `<li class="page-item ${prevDisabled}"><a class="page-link" href="#" onclick="changePage(event,${page-1})">«</a></li>`;

    for (let i = 1; i <= pages; i++) {
        const active = i === page ? 'active' : '';
        html += `<li class="page-item ${active}"><a class="page-link" href="#" onclick="changePage(event,${i})">${i}</a></li>`;
    }

    const nextDisabled = page >= pages ? 'disabled' : '';
    html += `<li class="page-item ${nextDisabled}"><a class="page-link" href="#" onclick="changePage(event,${page+1})">»</a></li>`;
    html += '</ul>';
    return html;
}

function changePage(event, page) {
    event.preventDefault();
    currentPage = page;
    doSearch({});
}

function updateSortPills(sort) {
    document.querySelectorAll('.sort-pill[data-sort]').forEach(function (pill) {
        pill.classList.toggle('active', pill.dataset.sort === sort);
    });
}
