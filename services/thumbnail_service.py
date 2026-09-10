# services/thumbnail_service.py — 카드용 대표 사진 한 장을 고르는 규칙을 한곳에 모은다.
#
# 배경: images 는 콤마로 이어붙인 파일명 문자열이라 ",a.jpg" 나 "a.jpg, " 처럼
# 빈 항목·공백이 섞여 들어온다. split(',')[0] 만 쓰면 사진이 있는데도 빈 문자열이
# 나와 카드가 비어 보였다. 파싱을 이 모듈로 모아 그 경우를 없앤다.

# 프론트가 경로를 덧붙이지 않아도 되도록 완전한 경로를 돌려준다.
UPLOAD_URL_PREFIX = '/static/uploads/'
DEFAULT_THUMBNAIL_URL = '/static/images/no_image.svg'


def first_image_name(experience):
    """체험 사진 CSV에서 첫 유효 파일명. 없으면 None.

    빈 항목과 앞뒤 공백을 걸러내므로 ",a.jpg" 는 "a.jpg" 가 된다.
    """
    images = getattr(experience, 'images', None)
    if not images:
        return None
    names = [name.strip() for name in images.split(',') if name.strip()]
    return names[0] if names else None


def _farm_image_name(experience):
    """농장 사진 파일명. 농장 사진은 farm 이 아니라 farmer(User) 에 있다.

    farm 테이블에는 인증서 스캔(organic_cert_image)만 있고 농장 사진 컬럼이 없다.
    """
    farmer = getattr(experience, 'farmer', None)
    if farmer is None:
        return None
    farm_image = getattr(farmer, 'farm_image', None)
    if not farm_image or not farm_image.strip():
        return None
    return farm_image.strip()


def experience_thumbnail_url(experience):
    """카드 대표 사진 URL. 체험 사진 → 농장 사진 → 기본 이미지 순.

    항상 non-null 인 완전한 경로를 돌려준다(프론트 계약).
    """
    if experience is None:
        return DEFAULT_THUMBNAIL_URL

    name = first_image_name(experience)
    if name:
        return UPLOAD_URL_PREFIX + name

    farm_image = _farm_image_name(experience)
    if farm_image:
        return UPLOAD_URL_PREFIX + farm_image

    return DEFAULT_THUMBNAIL_URL
