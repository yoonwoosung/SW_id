# FarmLink UI 규격 정의서

> 작성 기준: 현재 코드베이스 실측 기반
> 적용 대상: 프론트엔드 작업 전원
>
> **확정 결정사항**
> - 색상: 신규 토큰(`--fl-*`) 값 기준으로 통일
> - 브레이크포인트: 레거시 방식(`max-width`) 기준으로 통일

---

## 목차

1. [시스템 구조](#1-시스템-구조)
2. [색상 토큰](#2-색상-토큰)
3. [타이포그래피](#3-타이포그래피)
4. [간격 시스템](#4-간격-시스템)
5. [형태 (radius · shadow)](#5-형태-radius--shadow)
6. [반응형 브레이크포인트](#6-반응형-브레이크포인트)
7. [컴포넌트](#7-컴포넌트)
8. [페이지별 적용 기준](#8-페이지별-적용-기준)

---

## 1. 시스템 구조

FarmLink는 CSS 클래스 시스템이 두 개 병존한다.

| 시스템 | 파일 | 클래스 접두사 | 적용 대상 |
|--------|------|-------------|---------|
| **레거시** | `static/css/style.css` | 없음 (`exp-card`, `section-block` 등) | 일반 사용자 페이지 (메인, 상세, 마이페이지 등) |
| **신규** | `static/css/theme.css` | `fl-` | 농장주 Easy Mode 전용 |

> **규칙**: 신규 페이지 작업 전 어떤 시스템을 쓸지 먼저 결정한다.
> 현재 일반 사용자 페이지는 레거시 시스템 기준으로 유지한다.

---

## 2. 색상 토큰

**색상 값은 신규 토큰(`--fl-*`) 기준으로 통일한다.**

### 공식 색상 값

```css
/* 브랜드 그린 */
--fl-green-700: #4CAF50   /* 메인 액션, 버튼, 아이콘, 활성 상태 */
--fl-green-100: #E8F5E9   /* 배경 틴트, 호버 배경 */

/* 포인트 오렌지 */
--fl-orange:     #ea6a1e  /* 가격, 강조 수치 */
--fl-orange-100: #fdeee2  /* 오렌지 배경 틴트 */

/* 위험/에러 */
--fl-danger:     #e5484d
--fl-danger-100: #fdecec

/* 텍스트 */
--fl-text:       #1a1a1a  /* 본문 기본 */
--fl-text-muted: #717171  /* 보조 텍스트, 라벨 */

/* 보더 */
--fl-border:     #f0f0f0
```

### 레거시 페이지에서의 토큰 사용법

레거시 페이지는 `style.css :root`에 선언된 별칭 토큰을 사용한다.
값은 신규 토큰과 동일하게 맞춰져 있다.

```css
/* style.css :root — 별칭 (레거시 페이지 전용) */
--green-dark:  var(--fl-green-700)  /* = #4CAF50 */
--green-light: var(--fl-green-100)  /* = #E8F5E9 */
--orange:      #ea6a1e              /* = --fl-orange 동일 값 */
```

| 용도 | 레거시 페이지 | 농장주(fl-) 페이지 |
|------|------------|----------------|
| 메인 그린 | `var(--green-dark)` | `var(--fl-green-700)` |
| 라이트 그린 | `var(--green-light)` | `var(--fl-green-100)` |
| 가격/강조 오렌지 | `var(--orange)` | `var(--fl-orange)` |
| 보더 | `var(--fl-border)` | `var(--fl-border)` |
| 본문 텍스트 | `#1a1a1a` | `var(--fl-text)` |
| 보조 텍스트 | `#717171` | `var(--fl-text-muted)` |

> 색상을 하드코딩하지 않는다. 반드시 위 토큰을 사용한다.

---

## 3. 타이포그래피

### 폰트 패밀리

```css
"Pretendard", "Apple SD Gothic Neo", "Malgun Gothic", -apple-system, BlinkMacSystemFont, sans-serif
```

### 일반 사용자 페이지 폰트 스케일

| 용도 | 크기 | 굵기 |
|------|------|------|
| 히어로 메인 제목 | `2rem` ~ `2.7rem` | 700 |
| 섹션 제목 (`.section-title`) | `1.2rem` | 700 |
| 카드 제목 | `0.97rem` | 700 |
| 본문 기본 | `1rem` | 400 |
| 카드 위치·메타 | `0.83rem` | 400 |
| 배지·라벨 | `0.72rem` ~ `0.8rem` | 700 |
| 더보기 링크 | `0.83rem` | 600 |

### 농장주 페이지 폰트 스케일 (고령층 접근성 기준)

```css
--farmer-font-base:    18px   /* 본문 최소 — .fl-card-body 기본 적용 */
--farmer-font-label:   16px   /* 폼 라벨·보조 */
--farmer-font-heading: 24px   /* 섹션 제목 — .fl-section-head h2 적용 */
--farmer-font-title:   30px   /* 페이지 제목 */
--farmer-font-btn:     18px   /* 버튼 텍스트 */
```

> **적용 현황**: `easy-*` / `em-*` 클래스(style.css)와 `fl-*` 테마 컴포넌트(theme.css) 모두 위 토큰 기준으로 통일 완료.

---

## 4. 간격 시스템

### 신규 시스템 (fl-* 페이지)

```css
--fl-s1: 4px   --fl-s2: 8px   --fl-s3: 12px  --fl-s4: 16px
--fl-s5: 24px  --fl-s6: 32px  --fl-s8: 48px
```

### 레거시 주요 간격

| 용도 | 값 |
|------|-----|
| 섹션 블록 패딩 | `44px 0` |
| 메인 콘텐츠 래퍼 패딩 | `0 24px 60px` |
| 카드 내부 패딩 | `14px` |
| 카드 그리드 gap | `16px` |
| 섹션 헤더 하단 여백 | `20px` |

---

## 5. 형태 (radius · shadow)

### Border Radius

| 용도 | 값 | 변수 |
|------|-----|------|
| 카드 | `12px` | `var(--radius-card)` / `var(--fl-radius)` |
| 버튼·필터 pill | `20px` ~ `999px` | `var(--fl-pill)` |
| 소형 요소 (인풋 등) | `6px` ~ `8px` | `var(--fl-radius-sm)` |
| 배지 | `4px` | — |
| 아바타 | `50%` | — |

### Box Shadow

| 용도 | 값 | 변수 |
|------|-----|------|
| 카드 기본 | `0 2px 12px rgba(0,0,0,0.08)` | `var(--shadow-card)` / `var(--fl-shadow)` |
| 강조 카드 | `0 6px 20px rgba(0,0,0,0.12)` | `var(--fl-shadow-lg)` |
| 그림자 없음 | `none` | — |

---

## 6. 반응형 브레이크포인트

**`max-width` 기준(데스크톱 우선)으로 통일한다.**

```css
/* 작성 방식 — 반드시 이 순서로 */
.element { /* 데스크톱 기본 스타일 */ }

@media (max-width: 1200px) { /* 태블릿 이하 */ }
@media (max-width: 1024px) { /* 중간 태블릿 */ }
@media (max-width: 860px)  { /* 헤더 네비 → 햄버거 */ }
@media (max-width: 600px)  { /* 모바일 */ }
@media (max-width: 480px)  { /* 소형 모바일 */ }
```

### 주요 브레이크포인트 기준

| 값 | 주요 변화 |
|----|---------|
| `1200px` | 메인 콘텐츠 최대 너비 |
| `1024px` | 태블릿 레이아웃 조정, 카드 그리드 3컬럼 |
| `860px` | 헤더 네비 → 햄버거 메뉴 전환 |
| `600px` | 카드 그리드 2컬럼 |
| `480px` | 카드 그리드 1컬럼, 소형 모바일 |

> `min-width` 미디어쿼리는 작성하지 않는다.
> 기존 `theme.css`(농장주 전용)의 `min-width` 쿼리는 예외로 유지한다.

---

## 7. 컴포넌트

### 7-1. 체험 카드 (`.exp-card`)

```
┌─────────────────────┐
│  이미지 (175px 고정) │ ← .exp-card-img-wrap
│  [배지]             │ ← .exp-badge (좌상단)
│  [거리 배지]        │ ← .exp-card-dist-badge (좌하단, GPS 정렬 시만)
├─────────────────────┤
│  작물명 체험         │ ← .exp-card-title (0.97rem, 700)
│  📍 주소            │ ← .exp-card-location (0.83rem)
│  👥 2-4인  ⏰ D-5  │ ← .exp-card-meta (0.83rem)
│  25,000원~          │ ← .exp-card-price (var(--orange), 700)
└─────────────────────┘
```

- `border-radius: 12px`, `box-shadow: var(--shadow-card)`
- hover: `transform: translateY(-4px)`
- 마감: `.closed` → `opacity: 0.65`

**배지 종류 (`.exp-badge`)**

| 클래스 | 상황 | 텍스트 |
|--------|------|--------|
| `.badge-open` | 기본 | 예약가능 |
| `.badge-family` | 지역 특산물 | 가족추천 |
| `.badge-eco` | 친환경 인증 | 친환경 |
| `.badge-closed` | 잔여석 0 | 마감임박 |

---

### 7-2. 섹션 블록 (`.section-block`)

```html
<section class="section-block">
    <div class="section-header">
        <h2 class="section-title">
            <i data-lucide="sprout" class="text-success"></i> 섹션명
        </h2>
        <a href="#" class="more-link">더보기 <i data-lucide="chevron-right"></i></a>
    </div>
    <!-- 콘텐츠 -->
</section>
```

- 섹션 상단 border: `1px solid #f0f0f0`
- 패딩: `44px 0`

---

### 7-3. 정렬 필터 (`.sort-pill`)

```html
<div class="sort-pills">
    <a href="#" class="sort-pill active">모집 임박순</a>
    <a href="#" class="sort-pill">리뷰 많은순</a>
</div>
```

- 기본: `color: #777`, `border-bottom: 2px solid transparent`
- `.active`: `color: var(--green-dark)`, `border-bottom-color: var(--green-dark)`

---

### 7-4. 버튼

**레거시 페이지** — Bootstrap `.btn` 기반

```html
<button class="btn btn-success">기본 액션</button>
<button class="btn btn-outline-success">보조 액션</button>
```

**농장주 페이지** — `.fl-btn` 시스템

```html
<button class="fl-btn fl-btn-primary">기본 액션</button>
<button class="fl-btn fl-btn-outline">보조 액션</button>
<button class="fl-btn fl-btn-orange">강조 액션</button>
<button class="fl-btn fl-btn-sm">소형 버튼</button>
```

---

### 7-5. 아이콘

**Lucide Icons** 사용. 인라인 SVG 방식.

```html
<i data-lucide="sprout"></i>
<i data-lucide="map-pin"></i>
```

JS로 동적 콘텐츠 추가 후 반드시 재호출:

```javascript
if (window.lucide) lucide.createIcons();
```

---

### 7-6. 스켈레톤 로딩

```html
<div class="skeleton-card">
    <div class="skeleton-img"></div>
    <div class="skeleton-body">
        <div class="skeleton-line"></div>
        <div class="skeleton-line short"></div>
        <div class="skeleton-line shorter"></div>
    </div>
</div>
```

- shimmer 애니메이션 적용 (1.2s infinite)
- `.short`: width 65% / `.shorter`: width 40%

---

### 7-7. 페이지네이션

Bootstrap `.pagination` 사용.

```html
<nav class="pagination-container mt-4">
    <ul class="pagination justify-content-center">
        <li class="page-item disabled"><a class="page-link" href="#">«</a></li>
        <li class="page-item active"><a class="page-link" href="#">1</a></li>
        <li class="page-item"><a class="page-link" href="#">2</a></li>
        <li class="page-item"><a class="page-link" href="#">»</a></li>
    </ul>
</nav>
```

---

## 8. 페이지별 적용 기준

| 페이지 | CSS 시스템 | 색상 토큰 |
|--------|-----------|---------|
| 메인 (`/`) | 레거시 | `--green-dark`, `--orange` |
| 체험 상세 | 레거시 | `--green-dark`, `--orange` |
| 마이페이지 | 레거시 | `--green-dark`, `--orange` |
| 결제 | 레거시 (인라인 스타일) | `--orange` |
| 농장주 Easy Mode | fl-* | `--fl-green-700`, `--fl-orange` |
| 신규 페이지 | 작업 전 합의 후 결정 | 위 기준에 맞춰 선택 |

---

## 9. 농장주 UI CSS 클래스 목록

> 적용 파일: `static/css/style.css` (맨 끝에 추가됨)
> 기준: 서울시·서울디지털재단 「고령층 친화 디지털 접근성 표준」

### 9-1. 레이아웃 · 래퍼

| 클래스 | 설명 |
|--------|------|
| `.easy-mode-container` | 페이지 래퍼. max-width 860px, 중앙 정렬 (폼 페이지 전용 유지) |
| `.fl-container` | 농장주 앱 페이지 래퍼. **max-width 없음 (풀 너비)**, 좌우 padding 24px |
| `.easy-header` | 페이지 상단 제목+설명 영역 |
| `.easy-header h1` | 페이지 제목. `--farmer-font-title(30px)`, 800 |
| `.easy-header p` | 부제목. `--farmer-font-base(18px)`, muted |
| `.easy-section-title` | 섹션 소제목. `--farmer-font-heading(24px)`, 800 |
| `.farmer-tab-panel` | 탭 패널 (기본 `display:none`). `.is-active` 추가 시 표시 |
| `.timetable-wrapper` | 시간표 가로 스크롤 래퍼 (모바일용) |

---

### 9-2. 통계 박스

| 클래스 | 설명 |
|--------|------|
| `.easy-stats-grid` | 3열 그리드 (모바일 1열) |
| `.easy-stat-box` | 개별 통계 박스. `--fl-green-100` 배경 |
| `.easy-stat-label` | 라벨. `--farmer-font-label(16px)`, muted |
| `.easy-stat-value` | 수치. 28px, 800, `--fl-green-700` |
| `.easy-stat-icon` | 아이콘 영역. 28px |
| `.easy-stat-unit` | 단위 텍스트. 15px, muted |

---

### 9-3. 폼

| 클래스 | 설명 |
|--------|------|
| `.easy-form` | 폼 래퍼. 내부 `label`, `input`, `textarea`, `select` 크기 일괄 적용 |
| `.easy-form-label-lg` | 큰 라벨. `--farmer-font-base(18px)`, 700 |
| `.easy-form-hint` | 힌트 문구. `--farmer-font-label(16px)`, muted |
| `.farm-organic-check` | 친환경 체크박스 행. 체크박스 22px |

---

### 9-4. 버튼

| 클래스 | 설명 |
|--------|------|
| `.easy-submit-button` | 주요 실행 버튼 (저장·등록). 100% 너비, `--farmer-btn-height(56px)` |
| `.easy-confirm-button` | 확정 버튼. submit과 동일 스타일 |
| `.easy-back-button` | 뒤로 가기·보조 버튼. 48px 최소 높이 |
| `.easy-btn-gap` | 버튼 상단 여백 보조 (`--farmer-btn-gap: 12px`) |
| `.em-btn-accept` | 예약 수락 버튼. 녹색 채움, 44px |
| `.em-btn-reject` | 예약 거절 버튼. 흰 배경 + 빨간 테두리, 44px |
| `.em-btn-register` | 체험 등록 버튼. 녹색 채움, 44px |
| `.em-btn-edit` | 수정 버튼. 파란 테두리, 40px |
| `.em-btn-delete` | 삭제·숨김 버튼. 흰 배경 + 빨간 테두리, 40px |
| `.em-btn-reply` | 답변 버튼. 녹색 테두리, 40px |

---

### 9-5. 카드 · 목록

| 클래스 | 설명 |
|--------|------|
| `.easy-reservation-card` | 예약 카드 |
| `.easy-modify-item` | 체험 수정 항목 카드 (링크형, hover 그림자) |
| `.easy-inquiry-card` | 문의 카드 |
| `.easy-feedback-card` | 피드백 카드 |
| `.easy-card-header` | 카드 헤더(날짜). `--farmer-font-heading(24px)`, 800 |
| `.easy-card-body` | 카드 본문. `--farmer-font-base(18px)`, 줄간격 1.7 |
| `.easy-reservation-name` | 예약자명. 22px, 700 |

---

### 9-6. 예약 관리 패널 (날짜별 뷰)

| 클래스 | 설명 |
|--------|------|
| `.em-date-nav` | 날짜 이동 네비게이션 바 |
| `.em-day-label` | 날짜 표시 텍스트. 20px, 700 |
| `.em-res-card` | 예약 1건 카드 (체험별 색상 border-left 인라인으로 추가) |
| `.em-res-time` | 시간 표시. 18px, 700, `--fl-green-700` |
| `.em-res-info` | 예약 정보 영역 (flex:1) |
| `.em-res-crop` | 체험명. 18px, 700 (색상은 JS로 인라인 적용) |
| `.em-res-meta` | 예약자·인원 정보. 15px |
| `.em-res-actions` | 수락/거절 버튼 묶음 |

---

### 9-7. 수락 대기 예약

| 클래스 | 설명 |
|--------|------|
| `.em-pending-badge` | 대기 건수 뱃지. 빨간 원형 |
| `.em-pending-row` | 대기 예약 행 |
| `.em-pending-info` | 체험명 + 날짜 영역 |
| `.em-pending-person` | 예약자명 + 인원 영역 |
| `.em-pending-actions` | 수락/거절 버튼 묶음 |

---

### 9-8. 운영 관리 패널

| 클래스 | 설명 |
|--------|------|
| `.em-listing-row` | 체험 목록 행 |
| `.em-listing-name` | 체험명. 18px, 700 |
| `.em-listing-actions` | 수정/숨김 버튼 묶음 |
| `.em-listing-divider` | 행 구분선 |
| `.em-inquiry-row` | 문의 목록 행 |
| `.em-inquiry-info` | 문의자명 + 내용 영역 |
| `.em-inquiry-author` | 문의자명. 17px, 700 |
| `.em-inquiry-content` | 내용 미리보기. ellipsis 처리 |

---

### 9-9. 문의 관리 (easy_communication)

| 클래스 | 설명 |
|--------|------|
| `.ec-inquiry-meta` | 문의 메타 정보 행 |
| `.ec-inquiry-crop` | 체험명 태그. 녹색 pill |
| `.ec-replies` | 답변 목록 컨테이너 |
| `.ec-reply-item` | 답변 1건. 녹색 left-border 카드 |
| `.ec-reply-label` | "농장주 답변" 라벨. 녹색, 13px |
| `.ec-reply-text` | 답변 본문. `--farmer-font-base(18px)` |
| `.ec-reply-date` | 날짜. 13px, muted |
| `.ec-reply-actions` | 수정/삭제 버튼 묶음 |
| `.ec-btn-sm` | 소형 버튼. 13px, 32px 높이 |
| `.ec-btn-del` | 삭제 버튼. 빨간 테두리 |
| `.ec-edit-form` | 답변 수정 인라인 폼 |
| `.ec-new-reply-form` | 새 답변 입력 폼 영역 |
| `.easy-reply-textarea` | 답변 입력창. `--farmer-font-base(18px)` |

---

### 9-10. 5단계 마법사 (체험 등록)

| 클래스 | 설명 |
|--------|------|
| `.step-label-text` | 현재 단계 안내 텍스트 |
| `.step-dots` | 진행 단계 도트 묶음 |
| `.step-item` | 단계 1개 (도트 + 라벨) |
| `.step-dot` | 단계 도트. 44px 원형. `.active` / `.done` |
| `.step-dot-label` | 도트 하단 라벨. 12px |
| `.step-line` | 단계 연결선. `.done` 시 녹색 |
| `.step-encourage` | 격려 메시지 박스. 녹색 배경 |
| `.step-nav-btns` | 이전/다음 버튼 행 |

---

### 9-11. 계정 설정

| 클래스 | 설명 |
|--------|------|
| `.ac-gender-group` | 성별 버튼 묶음 |
| `.ac-gender-btn` | 성별 선택 버튼. `.active` 시 녹색 채움 |
| `.ac-farm-card` | 농장 정보 카드 |
| `.ac-farm-address` | 농장 주소. 18px, 700 |
| `.ac-farm-size` | 농장 규모. 15px, muted |
| `.ac-modal-overlay` | 모달 오버레이 (fixed, 반투명) |
| `.ac-modal-box` | 모달 박스. 최대 400px, border-radius 20px |
| `.ac-modal-title` | 모달 제목. 22px, 700 |
| `.ac-modal-desc` | 모달 설명. 16px, muted |

---

### 9-12. 상태 뱃지

| 클래스 | 색상 | 용도 |
|--------|------|------|
| `.fl-badge--confirmed` | 녹색 | 확정 |
| `.fl-badge--pending` | 회색 | 대기 |
| `.fl-badge--done` | 파랑 | 완료 |
| `.fl-badge--cancelled` | 빨강 | 취소 |
| `.fl-badge--active` | 녹색 | 모집 중 |
| `.fl-badge--hidden` | 회색 | 숨김 |

---

### 9-13. 보조 텍스트 · 빈 상태

| 클래스 | 설명 |
|--------|------|
| `.fl-meta` | 보조 정보 텍스트. `--farmer-font-label(16px)` |
| `.fl-address` | 주소 텍스트. `--farmer-font-label(16px)`, 줄간격 1.5 |
| `.easy-no-item` | 빈 상태 안내 (대형). 중앙 정렬, 48px 패딩 |
| `.easy-no-item-icon` | 빈 상태 아이콘. 48px |
| `.easy-no-item-small` | 빈 상태 안내 (소형). 24px 패딩 |
| `.easy-feedback-list` | 피드백 리스트. `--farmer-font-base(18px)`, 줄간격 1.7 |

---

### 9-14. AI 리포트 카드

| 클래스 | 설명 |
|--------|------|
| `.st-report-exp` | 체험 단위 리포트 블록 |
| `.st-report-exp-name` | 체험명. 20px, 700 |
| `.st-report-cards` | 2열 카드 그리드 (모바일 1열) |
| `.st-report-card` | 리포트 카드. `.st-pos`(긍정, 연녹) / `.st-imp`(개선, 연노) |
| `.st-report-card-icon` | 카드 아이콘. 28px |
| `.st-report-card-head` | 카드 구분 라벨. 12px, uppercase |
| `.st-report-card-text` | 카드 본문. `--farmer-font-base(18px)` |
| `.st-satisfaction-card` | 만족도 점수 카드. 회색 배경 |
