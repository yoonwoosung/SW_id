# services/segment_score.py — 세그먼트별로 다른 기준을 점수에 반영한다(순수 함수).
#
# 문제: 세그먼트 3개에 같은 체험이 나왔다. peers 는 분기 자체가 없어
# nearby 와 완전히 같은 결과였고, esg 만 따로 정렬했기 때문이다.
#
# 여기서는 기본 점수(recommend_service.calculate_score)를 건드리지 않고
# 그 위에 더할 보너스만 계산한다. 기본 로직은 그대로 두고 세그먼트 색깔만 입힌다.
#
# 쓸 축은 실제 데이터 분포를 보고 골랐다(배포 10건 기준).
#   cost 10,000~30,000(3배) · remaining 5~30(6배) · has_parking 4/10 → 변별력 있음
#   barrier_free 0/10 · pet_allowed 거의 없음 → 넣어도 전부 0점이라 순위가 안 바뀐다
from common.constants import (
    SEGMENT_LIGHT_CHEAP_WEIGHT,
    SEGMENT_LIGHT_NEAR_WEIGHT,
    SEGMENT_GROUP_CAPACITY_WEIGHT,
    SEGMENT_GROUP_PARKING_WEIGHT,
)

# 화면 섹션 ↔ 세그먼트 키. URL(?segment=peers)은 이미 쓰이고 있어 그대로 두고
# 표시 이름만 기준에 맞게 바꿨다.
SEGMENT_LIGHT = 'peers'    # 화면: '가볍게 다녀오기 좋은 코스'
SEGMENT_GROUP = 'group'    # 화면: '단체로 가기 좋은 코스'
SEGMENT_ESG = 'esg'        # 화면: '친환경 인증 농장'

# 거리 정규화 기준(km). calculate_score 의 거리 감쇠와 같은 값을 쓴다.
NEAR_MAX_KM = 50


def _relative(value, low, high, invert=False):
    """후보군 안에서의 상대 위치를 0~1 로 만든다.

    절대 기준(예: "2만원 이하면 저렴")을 쓰면 지역·작물에 따라 전부 저렴하거나
    전부 비싸져 변별이 안 된다. 같은 목록 안에서 상대 평가한다.
    값이 하나뿐이거나 전부 같으면 변별할 수 없으므로 0 을 준다.
    """
    if value is None or low is None or high is None or high <= low:
        return 0.0
    ratio = (value - low) / (high - low)
    ratio = max(0.0, min(1.0, ratio))
    return 1.0 - ratio if invert else ratio


def _remaining(experience):
    """잔여석을 '절대 인원수'로 본다.

    비율(remaining / max)로 보면 정원 4명에 4명 남은 곳이 만점이 되는데,
    단체로 가려는 사람에게는 '몇 명 들어가나'가 중요하다.
    """
    max_p = getattr(experience, 'max_participants', None) or 0
    current = getattr(experience, 'current_participants', None) or 0
    return max(0, max_p - current)


def build_context(experiences):
    """후보군 전체를 훑어 상대 평가에 쓸 최소·최대를 구한다."""
    costs = [e.cost for e in experiences if getattr(e, 'cost', None) is not None]
    rooms = [_remaining(e) for e in experiences]
    return {
        'cost_min': min(costs) if costs else None,
        'cost_max': max(costs) if costs else None,
        'room_min': min(rooms) if rooms else None,
        'room_max': max(rooms) if rooms else None,
    }


def bonus(segment, experience, distance_km, context):
    """세그먼트 보너스. 해당 없는 세그먼트는 0 이라 기본 점수만 남는다."""
    if segment == SEGMENT_LIGHT:
        return _light_bonus(experience, distance_km, context)
    if segment == SEGMENT_GROUP:
        return _group_bonus(experience, context)
    return 0.0


def _light_bonus(experience, distance_km, context):
    """가볍게 다녀오기: 값이 싸고 가까울수록 높다."""
    cheap = _relative(getattr(experience, 'cost', None),
                      context.get('cost_min'), context.get('cost_max'), invert=True)
    score = SEGMENT_LIGHT_CHEAP_WEIGHT * cheap

    # 좌표가 없으면 거리 요소를 빼고 가격만 본다(비로그인·위치 거부).
    if distance_km is not None:
        near = max(0.0, 1.0 - (distance_km / NEAR_MAX_KM))
        score += SEGMENT_LIGHT_NEAR_WEIGHT * near
    return score


def _group_bonus(experience, context):
    """단체로 가기: 남은 자리가 많고 주차가 되면 높다."""
    room = _relative(_remaining(experience),
                     context.get('room_min'), context.get('room_max'))
    score = SEGMENT_GROUP_CAPACITY_WEIGHT * room
    if getattr(experience, 'has_parking', False):
        score += SEGMENT_GROUP_PARKING_WEIGHT
    return score


def apply(segment, ranked):
    """ranked [(experience, distance, score, reasons), ...] 를 세그먼트 기준으로 다시 정렬한다.

    기본 점수를 덮어쓰지 않고 보너스를 더한 값으로 순서만 바꾼다.
    """
    if segment not in (SEGMENT_LIGHT, SEGMENT_GROUP) or not ranked:
        return ranked
    context = build_context([item[0] for item in ranked])
    return sorted(
        ranked,
        key=lambda item: item[2] + bonus(segment, item[0], item[1], context),
        reverse=True,
    )
