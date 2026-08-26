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
--farmer-font-base:    18px   /* 본문 최소 */
--farmer-font-label:   16px   /* 폼 라벨·보조 */
--farmer-font-heading: 24px   /* 섹션 제목 */
--farmer-font-title:   30px   /* 페이지 제목 */
--farmer-font-btn:     18px   /* 버튼 텍스트 */
```

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
