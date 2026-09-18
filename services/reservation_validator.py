# services/reservation_validator.py — 예약 신청 폼 입력 검증(순수 함수, 테스트 가능).
#
# 라우트에서 int()·strptime() 을 맨몸으로 부르면 잘못된 입력에 500 이 난다.
# 파싱과 검증을 여기 모아 (값, 오류메시지) 쌍으로 돌려주고,
# 라우트는 오류메시지가 있으면 flash 하고 돌려보내기만 한다.
from datetime import datetime

# 인원 상한. 정원 검사(Experience.max_participants)는 라우트가 따로 하므로
# 여기서는 상식 밖 입력만 거르는 안전망이다.
MAX_PER_CATEGORY = 50    # 성인·청소년·아동 각각
MAX_TOTAL = 200          # 총합
MIN_TOTAL = 1

DATE_FORMAT = '%Y-%m-%d'

_FIELDS = ('count_adult', 'count_teen', 'count_child')


def parse_participants(form):
    """인원 입력을 파싱·검증한다.

    반환: (counts, total, error)
      counts: {'count_adult': int, 'count_teen': int, 'count_child': int}
      error : 문제가 있으면 사용자에게 보여줄 문장, 없으면 None

    빈 값은 0 으로 본다(폼에서 선택 안 한 항목).
    """
    counts = {}
    for name in _FIELDS:
        raw = form.get(name, 0)
        if raw is None or (isinstance(raw, str) and not raw.strip()):
            counts[name] = 0
            continue
        try:
            value = int(raw)
        except (TypeError, ValueError):
            return None, 0, "인원 수는 숫자로 입력해 주세요."
        # 음수를 막지 않으면 총합만 양수로 맞춰 정원을 우회할 수 있다.
        # (예: 성인 1 · 청소년 -5 → 총합 -4 가 그대로 정원에서 차감된다)
        if value < 0:
            return None, 0, "인원 수는 0명 이상이어야 합니다."
        if value > MAX_PER_CATEGORY:
            return None, 0, f"인원 수는 항목당 {MAX_PER_CATEGORY}명까지 신청할 수 있습니다."
        counts[name] = value

    total = sum(counts.values())
    if total < MIN_TOTAL:
        return None, 0, "참가 인원을 1명 이상 선택해주세요."
    if total > MAX_TOTAL:
        return None, 0, f"인원 수는 최대 {MAX_TOTAL}명까지 신청할 수 있습니다."

    return counts, total, None


def parse_apply_date(value):
    """신청 날짜(YYYY-MM-DD)를 date 로 바꾼다.

    반환: (date, error). 형식이 틀리거나 없는 날짜(2026-13-45)면 error 를 채운다.
    """
    if not value or not str(value).strip():
        return None, "신청 날짜를 선택해 주세요."
    try:
        return datetime.strptime(str(value).strip(), DATE_FORMAT).date(), None
    except (TypeError, ValueError):
        return None, "신청 날짜 형식이 올바르지 않습니다."
