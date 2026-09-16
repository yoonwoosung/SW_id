# services/course_reason.py — AI 추천 코스의 '추천 이유' 문장 생성.
# 지금은 규칙 기반 문장. 나중에 LLM(external/clova_api)으로 교체 가능하게 분리해 둔다.
# LLM으로 바꿀 때도, 주어진 코스 항목(장소) 목록 안에서만 설명하게 해서 장소를 지어내지 않게 한다.
from common.constants import COURSE_REASON_FALLBACK


def build_course_reason(experience, course_items):
    """코스에 대한 한 줄 추천 이유. 코스에 담긴 장소만 근거로 하며 새 장소를 만들지 않는다."""
    place_count = sum(1 for item in course_items if item.get("type") != "experience")
    if place_count == 0:
        return COURSE_REASON_FALLBACK
    return f"'{experience.crop} 체험'과 가까운 인기 장소 {place_count}곳으로 구성한 코스입니다."
    # TODO: 실제 LLM 적용 시 이 함수만 교체.
    #   external/clova_api를 호출하되 course_items(장소 목록)만 컨텍스트로 주고
    #   "이 목록 안에서만 설명하라"고 프롬프트에 명시. 실패 시 위 규칙 기반 문장으로 폴백.
