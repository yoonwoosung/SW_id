"""services/thumbnail_service 단위 테스트 — 카드 대표 사진 폴백 규칙.

가짜 객체로 순수 로직만 검증한다(DB 불필요).
폴백 순서: 체험 사진 → 농장 사진(farmer.farm_image) → 기본 이미지.
"""
from services.thumbnail_service import (
    first_image_name,
    experience_thumbnail_url,
    DEFAULT_THUMBNAIL_URL,
    UPLOAD_URL_PREFIX,
)


class FakeFarmer:
    def __init__(self, farm_image=None):
        self.farm_image = farm_image


class FakeExperience:
    def __init__(self, images=None, farmer=None):
        self.images = images
        self.farmer = farmer


# ---- first_image_name: CSV 파싱 엣지케이스 ----

def test_first_image_plain():
    assert first_image_name(FakeExperience(images="a.jpg")) == "a.jpg"


def test_first_image_multiple():
    assert first_image_name(FakeExperience(images="a.jpg,b.jpg")) == "a.jpg"


def test_first_image_leading_comma():
    # ★기존 split(',')[0] 버그: 빈 문자열을 반환해 사진이 있는데도 카드가 비었다★
    assert first_image_name(FakeExperience(images=",a.jpg")) == "a.jpg"


def test_first_image_spaces():
    assert first_image_name(FakeExperience(images=" a.jpg , b.jpg")) == "a.jpg"


def test_first_image_only_commas():
    assert first_image_name(FakeExperience(images=",,,")) is None


def test_first_image_empty_and_none():
    assert first_image_name(FakeExperience(images="")) is None
    assert first_image_name(FakeExperience(images=None)) is None


# ---- experience_thumbnail_url: 폴백 3단계 ----

def test_thumbnail_prefers_experience_image():
    exp = FakeExperience(images="exp.jpg", farmer=FakeFarmer("farm.jpg"))
    assert experience_thumbnail_url(exp) == UPLOAD_URL_PREFIX + "exp.jpg"


def test_thumbnail_falls_back_to_farm_image():
    exp = FakeExperience(images=None, farmer=FakeFarmer("farm.jpg"))
    assert experience_thumbnail_url(exp) == UPLOAD_URL_PREFIX + "farm.jpg"


def test_thumbnail_falls_back_when_images_are_blank():
    # 체험 사진이 빈 항목뿐이면 농장 사진으로 넘어가야 한다
    exp = FakeExperience(images=" , ", farmer=FakeFarmer("farm.jpg"))
    assert experience_thumbnail_url(exp) == UPLOAD_URL_PREFIX + "farm.jpg"


def test_thumbnail_default_when_nothing():
    assert experience_thumbnail_url(FakeExperience()) == DEFAULT_THUMBNAIL_URL


def test_thumbnail_default_when_farm_image_blank():
    exp = FakeExperience(images=None, farmer=FakeFarmer("   "))
    assert experience_thumbnail_url(exp) == DEFAULT_THUMBNAIL_URL


def test_thumbnail_handles_missing_farmer():
    assert experience_thumbnail_url(FakeExperience(farmer=None)) == DEFAULT_THUMBNAIL_URL


def test_thumbnail_handles_none_experience():
    assert experience_thumbnail_url(None) == DEFAULT_THUMBNAIL_URL


# ---- 프론트 계약 ----

def test_contract_always_non_null_absolute_path():
    """thumbnail_url 은 항상 non-null 이고 /static/ 으로 시작하는 완전한 경로."""
    cases = [
        FakeExperience(images="a.jpg"),
        FakeExperience(images=None, farmer=FakeFarmer("f.jpg")),
        FakeExperience(),
        None,
    ]
    for exp in cases:
        url = experience_thumbnail_url(exp)
        assert url is not None
        assert url.startswith('/static/')
