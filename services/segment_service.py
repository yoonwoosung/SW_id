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


# 성별 코드 → (버튼 표기어, 아이콘). 'peers'는 성별+나이대 기반이라 나이·성별 버튼 모두 'peers'로 연결한다.
_GENDER_BUTTON = {'male': ('남자', '👬'), 'female': ('여자', '👭')}
# 프로필이 없을 때 채울 기본 버튼(순서대로 부족분을 채움).
_FALLBACK_BUTTONS = [
    {'label': '요즘 인기 있는 곳', 'icon': '🔥', 'segment': 'peers'},
    {'label': '친환경으로 즐기기', 'icon': '🌱', 'segment': 'esg'},
]


def segment_buttons(user):
    """회원 성별·나이대로 인적사항 단축 버튼 2개(라벨·아이콘·세그먼트 코드)를 만든다.
    프로필이 부족하면 기본(인기·친환경) 버튼으로 채운다. segment는 추천 API의 segment 파라미터."""
    age = _AGE_LABEL.get(getattr(user, 'age_group', None)) if user is not None else None
    gender = getattr(user, 'gender', None) if user is not None else None
    buttons = []
    if age:
        buttons.append({'label': age + ' 놀러가기 좋은 곳', 'icon': '🌿', 'segment': 'peers'})
    if gender in _GENDER_BUTTON:
        word, icon = _GENDER_BUTTON[gender]
        buttons.append({'label': word + '끼리 가기 좋은 곳', 'icon': icon, 'segment': 'peers'})
    for fallback in _FALLBACK_BUTTONS:      # 프로필 정보가 부족하면 기본 버튼으로 2개를 채운다.
        if len(buttons) >= 2:
            break
        buttons.append(dict(fallback))
    return buttons[:2]
