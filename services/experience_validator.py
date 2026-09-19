# services/experience_validator.py — 체험 등록·수정 폼 입력 검증(순수 함수, 테스트 가능).
#
# 체험 등록 경로가 두 개다(routes/experience.py 일반 등록, routes/farmer.py 간편 등록).
# 검증을 여기 모아 양쪽이 같은 규칙을 쓰게 한다. 한쪽만 검증하면 우회된다.

import math
import re

from common.constants import (
    SURPLUS_DEFAULT_DISCOUNT_PERCENT,
    SURPLUS_DISCOUNT_TIERS,
    SURPLUS_UNIT_CONVERSION,
)

# 반려견 허용 몸무게 상한. 검색 필터의 최대 티어가 25kg(dog_large)이라
# 그보다 넉넉히 잡되 오입력(300kg 등)은 거른다.
PET_MAX_WEIGHT_KG = 100

# --- 과생산(잉여) 수확 체험 ---
# 할인율은 농장주가 정하지 않는다. 총 과생산량과 단위로 시스템이 구간표
# (common/constants.SURPLUS_DISCOUNT_TIERS)에서 뽑고, 그 할인율로 계산한
# '최대 체험료'를 상한으로 둔다. 농장주는 상한 이하로만 값을 정할 수 있다.
SURPLUS_UNITS = ('kg', 'g', '박스', '구좌', '포기', '단')
SURPLUS_MAX_QTY = 100000          # 총 수량 상한(오입력 방지)
SURPLUS_MAX_PER_PERSON = 1000     # 1인당 수확량 상한

# 할인 사유. 리본에 "사유 + 할인율"로 찍히므로 짧아야 한다.
SURPLUS_REASONS = ('과잉생산', '못난이', '수확임박', '규격외')
# 사유가 없는 체험(사유 컬럼이 생기기 전에 등록된 건)의 리본 기본 문구.
# 할인율만 '90%' 라고 띄우면 무엇이 90% 인지 알 수 없어 탭 이름과 같은 말을 쓴다.
SURPLUS_RIBBON_DEFAULT_REASON = '과생산'
SURPLUS_REASON_ETC = '기타'
SURPLUS_REASON_MAX_LEN = 6        # '기타' 자유 입력 상한. 리본 폭이 한계다.


def parse_pet_fields(form):
    """반려견 동반 입력을 파싱·검증한다.

    반환: (pet_allowed, pet_max_weight_kg, error)

    동반 가능을 켰으면 몸무게를 반드시 받는다. 몸무게가 비어 있으면
    services/category_match._has_pet() 이 None 을 만나 어떤 몸무게 티어에도
    매칭되지 않는다 — 농장주는 체크했는데 검색에서 사라지는 함정이 된다.
    """
    pet_allowed = 'pet_allowed' in form

    if not pet_allowed:
        # 동반 불가면 몸무게는 의미가 없다. 이전 값이 남지 않게 비운다.
        return False, None, None

    raw = form.get('pet_max_weight_kg')
    if raw is None or not str(raw).strip():
        return None, None, "반려견 동반을 허용하면 허용 최대 몸무게를 입력해 주세요."

    try:
        weight = int(str(raw).strip())
    except (TypeError, ValueError):
        return None, None, "반려견 허용 몸무게는 숫자로 입력해 주세요."

    if weight < 1:
        return None, None, "반려견 허용 몸무게는 1kg 이상이어야 합니다."
    if weight > PET_MAX_WEIGHT_KG:
        return None, None, f"반려견 허용 몸무게는 {PET_MAX_WEIGHT_KG}kg 이하로 입력해 주세요."

    return True, weight, None


# ----------------------------------------------------------------------
# 과생산(잉여) 수확 체험
# ----------------------------------------------------------------------

def discount_rate(list_price, cost):
    """정가 대비 ★실제★ 할인율(0~1). 정가가 없거나 0 이면 None.

    자동 산출된 할인율(auto_discount_percent)이 아니라 실제로 매긴 체험비
    기준이다. 농장주가 상한보다 더 싸게 팔면 이쪽이 더 커진다.
    리본에는 이 값을 쓴다.
    """
    if not list_price or list_price <= 0 or cost is None:
        return None
    return (list_price - cost) / list_price


def _tier_quantity(qty_total, unit):
    """구간표 조회에 쓸 (수량, 표 이름). 쓸 표가 없으면 (None, None).

    g 처럼 환산만 하면 되는 단위는 kg 표로 넘긴다(200g → 0.2kg).
    """
    if unit in SURPLUS_UNIT_CONVERSION:
        table, divisor = SURPLUS_UNIT_CONVERSION[unit]
        return qty_total / divisor, table
    if unit in SURPLUS_DISCOUNT_TIERS:
        return qty_total, unit
    return None, None


def auto_discount_percent(qty_total, unit):
    """총 과생산량과 단위로 정하는 할인율(정수 %). 수량이 없으면 None.

    많이 남을수록 싸게 푼다. 구간표가 없는 단위(포기·단)는 기본값을 준다.
    """
    if not qty_total or qty_total <= 0:
        return None
    amount, table = _tier_quantity(qty_total, unit)
    if table is None:
        return SURPLUS_DEFAULT_DISCOUNT_PERCENT
    for upper, percent in SURPLUS_DISCOUNT_TIERS[table]:
        if upper is None or amount < upper:
            return percent
    return SURPLUS_DEFAULT_DISCOUNT_PERCENT


def max_cost(list_price, qty_total, unit):
    """받을 수 있는 최대 체험료(원). 정가 × (1 − 자동 할인율), 내림.

    부동소수 곱을 피하려고 정수 퍼센트로 계산한다. 0.6 을 곱하면
    50,000 × 0.6 이 29,999.999… 가 되어 상한이 1원 줄어든다.
    """
    percent = auto_discount_percent(qty_total, unit)
    if percent is None or not list_price or list_price <= 0:
        return None
    return list_price * (100 - percent) // 100


def capacity_from_quantity(qty_total, per_person):
    """총 수량으로 받을 수 있는 최대 인원. 나머지는 버린다.

    503kg 을 1인 5kg 씩 주면 100명까지다. 101명째는 3kg 밖에 못 받아
    분쟁이 되므로 버림으로 처리하고 자투리는 표시만 한다.
    """
    if not qty_total or not per_person or per_person <= 0:
        return None
    return math.floor(qty_total / per_person)


def suggest_origin(address):
    """농장 주소에서 '시도 + 시군구' 수준의 원산지 기본값을 뽑는다.

    등록 화면의 기본값 제안일 뿐이고 농장주가 고칠 수 있다.
    지역마다 주소 형식이 달라 완벽할 수 없으므로 실패하면 None 을 준다.
    """
    if not address or not str(address).strip():
        return None
    tokens = str(address).split()
    if not tokens:
        return None
    sido = tokens[0]
    for token in tokens[1:]:
        if re.search(r'(시|군|구)$', token):
            return f"{sido} {token}"
    return sido


def _parse_int(raw, field_label, minimum=1, maximum=None):
    if raw is None or not str(raw).strip():
        return None, f"{field_label}을(를) 입력해 주세요."
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None, f"{field_label}은(는) 숫자로 입력해 주세요."
    if value < minimum:
        return None, f"{field_label}은(는) {minimum} 이상이어야 합니다."
    if maximum is not None and value > maximum:
        return None, f"{field_label}은(는) {maximum} 이하로 입력해 주세요."
    return value, None


def parse_surplus_fields(form, cost):
    """과생산 입력을 파싱·검증한다.

    cost 는 이미 파싱된 판매가(기존 price 필드)다. 과생산은 별도 판매가 컬럼을
    두지 않고 cost 를 그대로 쓴다(결제 흐름을 건드리지 않기 위해서다).

    반환: (data, error)
      data: 과생산이 아니면 모든 값이 꺼진 dict, 맞으면 채워진 dict
    """
    off = {
        'is_surplus': False, 'surplus_terms_agreed': False, 'list_price': None,
        'surplus_qty_total': None, 'surplus_per_person': None,
        'surplus_unit': None, 'surplus_origin': None, 'surplus_reason': None,
    }
    if 'is_surplus' not in form:
        return off, None

    # 약관 동의 없이는 과생산으로 올릴 수 없다.
    if 'surplus_terms_agreed' not in form:
        return None, "과생산 농산물로 등록하려면 자동 산출된 할인율 약관에 동의해야 합니다."

    list_price, err = _parse_int(form.get('list_price'), "정가", minimum=1)
    if err:
        return None, err

    # 할인율은 수량·단위에서 나온다. 상한을 알려면 둘을 먼저 읽어야 하므로
    # 체험비 검증보다 앞에 둔다.
    qty_total, err = _parse_int(form.get('surplus_qty_total'), "총 수량",
                                minimum=1, maximum=SURPLUS_MAX_QTY)
    if err:
        return None, err

    per_person, err = _parse_int(form.get('surplus_per_person'), "1인당 수확량",
                                 minimum=1, maximum=SURPLUS_MAX_PER_PERSON)
    if err:
        return None, err

    if per_person > qty_total:
        return None, "1인당 수확량이 총 수량보다 많을 수 없습니다."

    unit = (form.get('surplus_unit') or 'kg').strip()
    if unit not in SURPLUS_UNITS:
        return None, "수량 단위가 올바르지 않습니다."

    if cost is None:
        return None, "체험비를 먼저 입력해 주세요."

    # 상한 초과는 거부한다. 잘라서 저장하면 농장주가 정한 값과 다른 금액이
    # 결제에 쓰이고, 왜 바뀌었는지 알 수 없다.
    cap = max_cost(list_price, qty_total, unit)
    if cap is not None and cost > cap:
        percent = auto_discount_percent(qty_total, unit)
        return None, (
            f"총 {qty_total}{unit}은 할인율 {percent}% 구간이라 "
            f"최대 {cap:,}원까지 가능합니다. (현재 {cost:,}원)"
        )

    origin = (form.get('surplus_origin') or '').strip() or None

    reason, err = _parse_reason(form)
    if err:
        return None, err

    return {
        'is_surplus': True,
        'surplus_terms_agreed': True,
        'list_price': list_price,
        'surplus_qty_total': qty_total,
        'surplus_per_person': per_person,
        'surplus_unit': unit,
        'surplus_origin': origin,
        'surplus_reason': reason,
    }, None


def _parse_reason(form):
    """할인 사유를 고른다. 반환: (reason, error)

    리본에 "사유 + 할인율"이 찍히므로 길면 잘린다. '기타'를 골랐을 때만
    자유 입력을 받고 6자로 제한한다. 잘라서 저장하지 않고 거부하는 이유는,
    잘라 두면 농장주는 모르는 채 사용자에게 어중간한 문구가 보이고
    나중에 원인을 찾기 어렵기 때문이다.
    """
    choice = (form.get('surplus_reason') or '').strip()
    if not choice:
        return None, "할인 사유를 선택해 주세요."

    if choice in SURPLUS_REASONS:
        return choice, None

    if choice != SURPLUS_REASON_ETC:
        return None, "할인 사유가 올바르지 않습니다."

    etc = (form.get('surplus_reason_etc') or '').strip()
    if not etc:
        return None, "기타 사유를 입력해 주세요."
    if len(etc) > SURPLUS_REASON_MAX_LEN:
        return None, f"기타 사유는 {SURPLUS_REASON_MAX_LEN}자 이내로 입력해주세요. (현재 {len(etc)}자)"
    return etc, None


def resolve_max_participants(requested_raw, capacity):
    """과생산 체험의 정원을 정한다.

    capacity 는 수량으로 받을 수 있는 최대 인원(총수량 ÷ 1인당수확량, 버림)이다.
    농장주가 이보다 적게 받는 건 허용한다(재고는 100명분이지만 하루 20명만
    받고 싶은 경우). 늘리는 건 재고 초과라 막는다.

    과생산이 아니면(capacity is None) 입력값을 그대로 쓴다.

    반환: (max_participants, error)
    """
    if capacity is None:
        value, err = _parse_int(requested_raw, "하루 최대 인원", minimum=1)
        return (None, err) if err else (value, None)

    if capacity < 1:
        return None, "총 수량이 1인당 수확량보다 적어 체험을 등록할 수 없습니다."

    # 비워 두면 수량으로 계산한 값을 그대로 쓴다.
    if requested_raw is None or not str(requested_raw).strip():
        return capacity, None

    requested, err = _parse_int(requested_raw, "하루 최대 인원", minimum=1)
    if err:
        return None, err
    if requested > capacity:
        return None, (
            f"총 수량으로 받을 수 있는 인원은 {capacity}명입니다. "
            f"({requested}명은 재고를 넘습니다. 인원을 줄이거나 총 수량을 늘려주세요.)"
        )
    return requested, None


def discount_percent(experience):
    """정가 대비 ★실제★ 할인율(정수 %). 계산할 수 없으면 None.

    ★내림한다.★ 반올림하면 66.67% 가 67% 로 보여 실제보다 더 깎아준 것처럼
    말하게 된다. 할인 표시는 과장하지 않는 쪽이 안전하다.

    목록 리본·상세 배지·과생산 API 가 모두 이 함수를 쓴다. 예전에는 리본이
    반올림, 상세 배지가 템플릿 안에서 내림이라 같은 체험이 67%·66% 로 달랐다.
    """
    rate = discount_rate(getattr(experience, 'list_price', None),
                         getattr(experience, 'cost', None))
    if rate is None:
        return None
    return int(math.floor(rate * 100))


def ribbon_text(experience):
    """카드·상세 리본 문구. 과생산이 아니거나 약관 미동의면 None.

    ★사유나 할인율이 없어도 리본은 띄운다.★ 예전에는 둘 중 하나라도 없으면
    None 이라, 사유 컬럼이 생기기 전에 등록된 체험은 과생산 탭에 나오면서도
    리본만 빠졌다. 같은 목록에서 어떤 카드는 뜨고 어떤 카드는 안 떠 보였다.

        사유 + 할인율 → '과잉생산 33%'
        할인율만      → '과생산 90%'    (기본 문구를 붙여 맥락을 준다)
        사유만        → '과잉생산'      (정가가 없어 할인율을 못 구하는 경우)
        둘 다 없음    → '과생산'

    리본 폭이 한계라 사유는 등록 때 6자로 제한해 뒀다.
    """
    if experience is None or not getattr(experience, 'is_surplus', False):
        return None
    # 목록 쿼리가 이미 거르지만 함수에서도 막는다.
    # 상세 등 쿼리를 거치지 않는 화면에서 직접 부르기 때문이다.
    if not getattr(experience, 'surplus_terms_agreed', False):
        return None

    label = getattr(experience, 'surplus_reason', None) or SURPLUS_RIBBON_DEFAULT_REASON
    percent = discount_percent(experience)
    return f"{label} {percent}%" if percent is not None else label
