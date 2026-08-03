# services/segment_service.py — 회원정보 기반 'AI 자동 추천 세그먼트' 카드 로직.
# 로그인 사용자의 연령대·성별로 세그먼트 라벨을 만들고, 진입 즉시 보여줄 추천 묶음 3개를 제안한다.
from common.profile_options import AGE_GROUPS, GENDERS

_AGE_LABEL = dict(AGE_GROUPS)                                  # {'20s':'20대', ...}
_GENDER_LABEL = {code: label for code, label in GENDERS if code != 'other'}  # 기타는 라벨 생략


def user_segment_label(user):
    """'20대·남성'처럼 사용자 세그먼트 라벨. 프로필 없으면 None."""
    if user is None:
        return None
    parts = []
    if getattr(user, 'age_group', None) in _AGE_LABEL:
        parts.append(_AGE_LABEL[user.age_group])
    if getattr(user, 'gender', None) in _GENDER_LABEL:
        parts.append(_GENDER_LABEL[user.gender])
    return '·'.join(parts) if parts else None


def auto_segments(user):
    """진입 즉시 보여줄 자동 추천 세그먼트 카드 3개. key는 추천 API의 segment 파라미터로 쓰인다."""
    age = _AGE_LABEL.get(getattr(user, 'age_group', None)) if user is not None else None
    peers_title = (age + ' 인기 체험') if age else '요즘 인기 체험'
    return [
        {'key': 'peers', 'emoji': '🎯', 'title': peers_title, 'subtitle': '또래가 많이 봤어요'},
        {'key': 'active', 'emoji': '👥', 'title': '가볍게 즐기는 코스', 'subtitle': '부담 없는 하루'},
        {'key': 'esg', 'emoji': '🌱', 'title': 'ESG 친환경 코스', 'subtitle': '무농약·유기농'},
    ]
