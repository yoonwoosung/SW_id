# services/experience_validator.py — 체험 등록·수정 폼 입력 검증(순수 함수, 테스트 가능).
#
# 체험 등록 경로가 두 개다(routes/experience.py 일반 등록, routes/farmer.py 간편 등록).
# 검증을 여기 모아 양쪽이 같은 규칙을 쓰게 한다. 한쪽만 검증하면 우회된다.

import math
import re

# 반려견 허용 몸무게 상한. 검색 필터의 최대 티어가 25kg(dog_large)이라
# 그보다 넉넉히 잡되 오입력(300kg 등)은 거른다.
PET_MAX_WEIGHT_KG = 100

# --- 과생산(잉여) 수확 체험 ---
# 약관: 정가 대비 이 비율 이상 싸게 판다. 미만이면 등록을 막는다.
SURPLUS_MIN_DISCOUNT_RATE = 0.20
SURPLUS_UNITS = ('kg', 'g', '박스', '구좌', '포기', '단')
SURPLUS_MAX_QTY = 100000          # 총 수량 상한(오입력 방지)
SURPLUS_MAX_PER_PERSON = 1000     # 1인당 수확량 상한


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
    """정가 대비 할인율(0~1). 정가가 없거나 0 이면 None."""
    if not list_price or list_price <= 0 or cost is None:
        return None
    return (list_price - cost) / list_price


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
        'surplus_unit': None, 'surplus_origin': None,
    }
    if 'is_surplus' not in form:
        return off, None

    # 약관 동의 없이는 과생산으로 올릴 수 없다.
    if 'surplus_terms_agreed' not in form:
        return None, "과생산 농산물로 등록하려면 정가 대비 20% 이상 할인 약관에 동의해야 합니다."

    list_price, err = _parse_int(form.get('list_price'), "정가", minimum=1)
    if err:
        return None, err

    if cost is None:
        return None, "판매 가격을 먼저 입력해 주세요."
    if cost >= list_price:
        return None, "판매 가격이 정가보다 낮아야 합니다."

    rate = discount_rate(list_price, cost)
    if rate < SURPLUS_MIN_DISCOUNT_RATE:
        return None, (
            f"과생산 농산물은 정가 대비 {int(SURPLUS_MIN_DISCOUNT_RATE * 100)}% 이상 "
            f"저렴해야 합니다. (현재 {rate * 100:.1f}%)"
        )

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

    origin = (form.get('surplus_origin') or '').strip() or None

    return {
        'is_surplus': True,
        'surplus_terms_agreed': True,
        'list_price': list_price,
        'surplus_qty_total': qty_total,
        'surplus_per_person': per_person,
        'surplus_unit': unit,
        'surplus_origin': origin,
    }, None


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
