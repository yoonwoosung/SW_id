# services/eco_filter.py — 추천 목록에서 조건에 맞지 않는 체험을 '제외'한다.
#
# 지금까지 조건은 점수 가점(category_bonus)이었고 ESG 섹션은 정렬(sort)이었다.
# 그래서 조건을 하나도 충족하지 못한 체험도 목록에 남아 뒤쪽에 붙었다.
# 사용자는 필터를 켰다고 생각하는데 안 맞는 결과가 보이는 문제다.
# 여기서는 가점이 아니라 통과/제외를 판정한다. 점수 계산은 건드리지 않는다.
from common.constants import ESG_GRADE_B
from services import category_match
from services.category_match import matched_categories
from services.esg_service import compute_esg

# matched_categories() 가 실제로 판정하는 대분류.
#
# ★나머지 7개(companion_type·party·schedule·experience_type·mood·season·
#   duration_hours)는 Experience 에 대응 데이터가 없어 판정 자체가 불가능하다.★
# 이들까지 AND 에 넣으면 사용자가 '가족(아이)' 하나만 켜도 결과가 항상 0건이 된다.
# 그래서 필터 대상에서 뺀다. 지금도 가점을 받지 못하므로 동작이 달라지지 않는다.
# ★activity 를 뺀 이유★: activity_type 컬럼은 있으나 저장하는 코드가 없어
# 모든 체험이 NULL 이다. 여기 두면 저장된 ?cond_activity=kayak 링크로 들어온
# 사용자에게 결과가 항상 0건이 된다. 화면에서도 감췄다(search_categories 의 hidden).
# ★'pet_dog' → 'companion_type'★ (2026-09-20 리팩터)
# 반려견이 독립 대분류에서 동반유형 하위 그룹으로 옮겨졌다. 판정 코드가
# 옛 대분류를 가리키고 있어 반려견 필터가 아무것도 거르지 못하고 있었다.
# 동반유형 안의 인원수·동반구성은 판정할 수 없어 category_match.pet_selection 이
# 반려견 코드만 추린다(자세한 이유는 그 함수 주석).
JUDGEABLE_CATEGORIES = frozenset({
    'region', 'budget_range', 'facility', 'companion_type', 'transport',
    # 2026-09-20: 체험명·설명 키워드로 판정할 수 있게 돼 다시 넣었다.
    # (activity_type 컬럼이 채워지면 그쪽이 우선한다 — category_match._has_activity)
    'activity',
})


def selected_categories(conditions):
    """사용자가 실제로 값을 고른 대분류 중 판정 가능한 것만."""
    if not conditions:
        return set()
    return {
        code for code, values in conditions.items()
        if values and code in JUDGEABLE_CATEGORIES and _judgeable_values(code, values)
    }


def _judgeable_values(category_code, values):
    """대분류 안에서 실제로 판정할 수 있는 선택값만 남긴다.

    판정 가능·불가가 한 대분류에 섞여 있다. 불가한 것만 골랐다면 그 대분류는
    건너뛴다 — 넣으면 결과가 항상 0건이 된다.

      동반유형  반려견은 가능, 인원수·동반구성은 불가
      교통수단  자가용만 가능(주차 연동), 대중교통·택시는 불가
      편의시설  주차·와이파이·무농약·유기농·무장애는 가능, 화장실·수유실은 불가

    ★불가한 값도 코스 쪽에서는 반영될 수 있다.★ 교통수단은 이동시간·교통비
    추정에, 화장실·수유실은 장소 종류 기준값에 쓰인다. 여기서 거르는 것은
    '체험 목록을 AND 로 좁힐 수 있는가'뿐이다.
    """
    return category_match.judgeable_selection(category_code, values)


def passes_conditions(conditions, experience):
    """고른 대분류를 '모두' 충족해야 통과(대분류 단위 AND).

    대분류 '안'에서는 기존 OR 규칙을 그대로 쓴다. 예를 들어 지역에서
    천안·공주를 고르면 둘 중 하나만 맞아도 지역 대분류는 충족이다.

    ※ 알려진 한계: 유기농·무농약이 '편의시설(facility)' 대분류에 주차·화장실과
      함께 묶여 있다. 그래서 '유기농 + 주차'를 같이 고르면 대분류가 하나뿐이라
      둘 중 하나만 맞아도 통과한다. 유기농만 고르면 정확히 동작한다.
      카테고리를 다시 나누려면 search_categories 구조와 채점·역제안까지 함께
      손봐야 해서 이번 범위에서는 제외했다.
    """
    needed = selected_categories(conditions)
    if not needed:
        return True     # 아무 조건도 고르지 않았으면 전부 통과
    return needed.issubset(matched_categories(conditions, experience))


def is_eco_certified(experience):
    """농장주가 설정한 친환경 항목이 있는가.

    ESG 6개 항목 중 E축(환경) 2개만 본다 — 무농약 재배, 유기농 인증.
    S축(봉사·무장애·주차)·G축(증빙)은 친환경이 아니라 사회·지배구조라
    '친환경 인증 농장' 섹션의 기준으로 쓰면 사용자 기대와 어긋난다.

    기존 응답의 eco 필드와 같은 정의를 쓴다(정의가 두 벌이 되지 않게).
    """
    if experience is None:
        return False
    return bool(
        getattr(experience, 'pesticide_free', False)
        or getattr(experience, 'organic_certification_type', None)
    )


def is_organic_certified(experience):
    """유기농 '인증'이 있는가. 무농약은 포함하지 않는다.

    무농약과 유기농은 별개 인증이다. 유기농 필터를 켠 사용자에게
    무농약 농장을 보여주면 잘못된 결과다.

    ★판정은 한 곳에서만 한다.★ 예전에는 여기와 category_match 와 메인
    페이지가 각자 판정해 결과가 달랐다(실측: 메인 2건, 추천 5건).
    """
    return category_match.is_organic_approved(experience)


def passes_eco_section(experience):
    """'친환경 인증 농장' 섹션에 노출할지.

    두 조건을 모두 본다.
      1. 친환경 항목(E축)이 하나라도 설정돼 있을 것
      2. ESG 등급 B 이상(60점 이상)

    현재 배점으로는 2번이 1번을 함축한다(E 없이 받을 수 있는 최대가
    S35 + G10 = 45 점이라 60 에 못 미친다). 그래도 둘 다 검사하는 이유는
    배점이 바뀌면 그 보장이 조용히 깨지기 때문이다. 의도를 코드에 남긴다.
    """
    if not is_eco_certified(experience):
        return False
    return compute_esg(experience)["score"] >= ESG_GRADE_B
