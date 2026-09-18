# services/experience_validator.py — 체험 등록·수정 폼 입력 검증(순수 함수, 테스트 가능).
#
# 체험 등록 경로가 두 개다(routes/experience.py 일반 등록, routes/farmer.py 간편 등록).
# 검증을 여기 모아 양쪽이 같은 규칙을 쓰게 한다. 한쪽만 검증하면 우회된다.

# 반려견 허용 몸무게 상한. 검색 필터의 최대 티어가 25kg(dog_large)이라
# 그보다 넉넉히 잡되 오입력(300kg 등)은 거른다.
PET_MAX_WEIGHT_KG = 100


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
