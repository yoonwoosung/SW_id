# common/profile_options.py — 회원 프로필 선택지(고정값, 단일 출처).
# 가입폼 렌더와 저장 검증이 함께 참조한다. activity/transport 코드는 search_categories 트리를 재사용.
from common.search_categories import SEARCH_CATEGORIES

# (코드, 표시명) 쌍 — 폼 드롭박스 렌더용. 개인정보 최소화를 위해 나이는 '연령대'만 받는다.
AGE_GROUPS = [
    ("10s", "10대"), ("20s", "20대"), ("30s", "30대"),
    ("40s", "40대"), ("50s", "50대"), ("60s_plus", "60대 이상"),
]
GENDERS = [("male", "남성"), ("female", "여성"), ("other", "기타")]
FAMILY_TYPES = [
    ("single", "1인"), ("couple", "커플"), ("family", "가족"), ("friends", "친구"),
]


def _child_pairs(category_code):
    node = next((c for c in SEARCH_CATEGORIES if c["code"] == category_code), None)
    return [(item["code"], item["label"]) for item in node["children"]] if node else []


# 관심 액티비티·선호 교통수단은 검색 트리의 코드/라벨을 그대로 쓴다(중복 정의 금지).
ACTIVITY_LABELS = _child_pairs("activity")       # [('harvest','수확체험'), ...]
TRANSPORT_LABELS = _child_pairs("transport")     # [('car','자가용'), ...]
ACTIVITY_OPTIONS = [code for code, _ in ACTIVITY_LABELS]
TRANSPORT_OPTIONS = [code for code, _ in TRANSPORT_LABELS]

# 검증용 코드 집합
AGE_GROUP_CODES = {code for code, _ in AGE_GROUPS}
GENDER_CODES = {code for code, _ in GENDERS}
FAMILY_TYPE_CODES = {code for code, _ in FAMILY_TYPES}
