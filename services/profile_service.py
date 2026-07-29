# services/profile_service.py — 가입폼의 프로필 입력을 검증·정규화한다(순수 함수, DB 비의존).
# 값이 없거나 허용 코드가 아니면 None으로 떨어뜨려 저장한다(선택 입력이므로 폼 통과에 영향 없음).
from common.profile_options import (
    AGE_GROUP_CODES, GENDER_CODES, FAMILY_TYPE_CODES,
    ACTIVITY_OPTIONS, TRANSPORT_OPTIONS,
)


def _one_of(value, allowed):
    value = (value or "").strip()
    return value if value in allowed else None


def clean_profile(single_get, multi_get):
    """single_get(name)->str, multi_get(name)->list[str] 를 받아 검증된 프로필 dict 반환.
    라우트에서 request.form.get / request.form.getlist 를 넘겨 재사용한다."""
    activities = [a for a in (multi_get("interest_activities") or []) if a in ACTIVITY_OPTIONS]
    return {
        "age_group": _one_of(single_get("age_group"), AGE_GROUP_CODES),
        "gender": _one_of(single_get("gender"), GENDER_CODES),
        "family_type": _one_of(single_get("family_type"), FAMILY_TYPE_CODES),
        "interest_activities": ",".join(activities) if activities else None,
        "preferred_transport": _one_of(single_get("preferred_transport"), TRANSPORT_OPTIONS),
    }


def has_recommendation_profile(user):
    """자동 추천 근거가 될 프로필이 하나라도 있는지. 없으면 인기순 폴백 대상."""
    if user is None:
        return False
    return any([
        user.age_group, user.gender, user.family_type,
        user.interest_activities, user.preferred_transport,
    ])
