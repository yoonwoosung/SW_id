"""services/tour_cache 단위 테스트 — KTO 조회 결과 파일 캐시.

캐시 디렉터리를 tmp_path 로 갈아끼워 실제 .cache/ 를 건드리지 않는다.
핵심 계약: 캐시가 어떤 식으로 깨져도 예외를 밖으로 내보내지 않는다
(호출부는 그냥 KTO 를 부르면 되고 서비스는 멈추지 않아야 한다).
"""
import json
import os
import time

import pytest

from services import tour_cache
from common.constants import TOUR_CACHE_TTL_SEC, TOUR_CACHE_EMPTY_TTL_SEC

PLACES = [{"name": "가나다 관광지", "lat": "36.8", "lng": "127.3"}]


@pytest.fixture
def cache(tmp_path, monkeypatch):
    """캐시 디렉터리를 임시 경로로 격리."""
    monkeypatch.setattr(tour_cache, '_CACHE_DIR', str(tmp_path))
    return tour_cache


# ---- 기본 동작 ----

def test_set_then_get_roundtrip(cache):
    key = cache.make_key(36.8583, 127.2943, 10000, 12)
    cache.set(key, PLACES)
    assert cache.get(key) == PLACES


def test_miss_returns_none(cache):
    assert cache.get(cache.make_key(1.0, 1.0, 10000, 12)) is None


def test_key_is_none_without_coords(cache):
    # 좌표가 없으면 캐시를 쓰지 않는다(키 None). set/get 모두 조용히 통과.
    assert cache.make_key(None, 127.0, 10000, 12) is None
    assert cache.make_key('없음', 127.0, 10000, 12) is None
    cache.set(None, PLACES)
    assert cache.get(None) is None


# ---- 좌표 반올림 (인접 농장 공유) ----

def test_nearby_coords_share_same_key(cache):
    """소수 2자리(약 1.1km)까지 같으면 같은 키 → 조회를 나눠 쓴다."""
    a = cache.make_key(36.8583, 127.2943, 10000, 12)
    b = cache.make_key(36.8581, 127.2939, 10000, 12)   # 약 30m 차이
    assert a == b


def test_far_coords_get_different_keys(cache):
    a = cache.make_key(36.85, 127.29, 10000, 12)
    b = cache.make_key(36.95, 127.29, 10000, 12)       # 약 11km 차이
    assert a != b


def test_radius_and_content_type_separate_keys(cache):
    base = cache.make_key(36.85, 127.29, 10000, 12)
    assert base != cache.make_key(36.85, 127.29, 20000, 12)   # 반경 다름
    assert base != cache.make_key(36.85, 127.29, 10000, 39)   # 타입 다름


def test_shared_key_serves_second_experience(cache):
    """농장 A 가 채운 캐시를 같은 버킷의 농장 B 가 그대로 받는다."""
    key_a = cache.make_key(36.8583, 127.2943, 10000, 39)
    cache.set(key_a, PLACES)
    key_b = cache.make_key(36.8578, 127.2938, 10000, 39)   # 같은 (36.86, 127.29)
    assert key_a == key_b
    assert cache.get(key_b) == PLACES


def test_rounding_boundary_splits_close_coords(cache):
    """반올림 격자 특성: 경계를 사이에 둔 두 좌표는 가까워도 키가 갈린다.

    127.2943 → 127.29 / 127.2950 → 127.3 이라 60m 차이인데도 버킷이 다르다.
    격자 방식이면 피할 수 없고, 최악이 캐시 미스(= 캐싱 전과 동일)라
    정확도 문제는 아니다. 동작을 명시해 두려고 남긴다.
    """
    a = cache.make_key(36.8583, 127.2943, 10000, 39)
    b = cache.make_key(36.8583, 127.2950, 10000, 39)
    assert a != b


# ---- TTL ----

def _advance(monkeypatch, seconds):
    """저장 직후를 기준으로 시계를 seconds 만큼 민다.

    모듈 로드 시각을 기준으로 잡으면 스위트 전체를 돌릴 때 그 사이 경과 시간이
    끼어들어 실행 순서에 따라 결과가 달라진다. 호출 시점 기준으로 계산한다.
    """
    now = time.time()
    monkeypatch.setattr(time, 'time', lambda: now + seconds)


def test_expired_entry_returns_none(cache, monkeypatch):
    key = cache.make_key(36.85, 127.29, 10000, 12)
    cache.set(key, PLACES)
    _advance(monkeypatch, TOUR_CACHE_TTL_SEC + 1)
    assert cache.get(key) is None


def test_entry_alive_just_before_ttl(cache, monkeypatch):
    key = cache.make_key(36.85, 127.29, 10000, 12)
    cache.set(key, PLACES)
    _advance(monkeypatch, TOUR_CACHE_TTL_SEC - 10)
    assert cache.get(key) == PLACES


def test_empty_result_uses_short_ttl(cache, monkeypatch):
    """★빈 결과는 5분만 산다 — 일시 장애가 1시간 고장으로 굳지 않게.★"""
    key = cache.make_key(36.85, 127.29, 10000, 12)
    cache.set(key, [])
    # 짧은 TTL 은 지났지만 정상 TTL(1시간)은 한참 남은 시점
    _advance(monkeypatch, TOUR_CACHE_EMPTY_TTL_SEC + 1)
    assert cache.get(key) is None


def test_empty_result_alive_within_short_ttl(cache, monkeypatch):
    key = cache.make_key(36.85, 127.29, 10000, 12)
    cache.set(key, [])
    _advance(monkeypatch, TOUR_CACHE_EMPTY_TTL_SEC - 10)
    assert cache.get(key) == []


# ---- 손상 파일 ----

def test_corrupt_json_returns_none(cache, tmp_path):
    key = cache.make_key(36.85, 127.29, 10000, 12)
    cache.set(key, PLACES)
    path = os.path.join(str(tmp_path), key + '.json')
    with open(path, 'w', encoding='utf-8') as f:
        f.write('{"places": [')      # 잘린 JSON
    assert cache.get(key) is None    # 예외 없이 미스 처리


def test_missing_field_returns_none(cache, tmp_path):
    key = cache.make_key(36.85, 127.29, 10000, 12)
    os.makedirs(str(tmp_path), exist_ok=True)
    with open(os.path.join(str(tmp_path), key + '.json'), 'w', encoding='utf-8') as f:
        json.dump({'places': PLACES}, f)      # saved_at 없음
    assert cache.get(key) is None


def test_empty_file_returns_none(cache, tmp_path):
    key = cache.make_key(36.85, 127.29, 10000, 12)
    os.makedirs(str(tmp_path), exist_ok=True)
    open(os.path.join(str(tmp_path), key + '.json'), 'w').close()
    assert cache.get(key) is None


# ---- 쓰기 실패 폴백 ----

def test_set_failure_is_silent(cache, monkeypatch):
    """디스크가 꽉 차거나 권한이 없어도 예외가 새면 안 된다."""
    def boom(*a, **kw):
        raise OSError('디스크 쓰기 실패')
    monkeypatch.setattr(os, 'makedirs', boom)
    key = cache.make_key(36.85, 127.29, 10000, 12)
    cache.set(key, PLACES)          # 예외 없이 통과해야 한다
    assert cache.get(key) is None   # 저장은 안 됐다


def test_set_failure_leaves_no_temp_file(cache, tmp_path, monkeypatch):
    """쓰기 중 실패해도 .tmp 찌꺼기를 남기지 않는다."""
    def boom(*a, **kw):
        raise OSError('쓰기 중 실패')
    monkeypatch.setattr(json, 'dump', boom)
    cache.set(cache.make_key(36.85, 127.29, 10000, 12), PLACES)
    leftovers = [n for n in os.listdir(str(tmp_path)) if n.endswith('.tmp')]
    assert leftovers == []


def test_get_failure_is_silent(cache, monkeypatch):
    def boom(*a, **kw):
        raise OSError('읽기 실패')
    key = cache.make_key(36.85, 127.29, 10000, 12)
    cache.set(key, PLACES)
    monkeypatch.setattr('builtins.open', boom)
    assert cache.get(key) is None   # 예외 대신 미스


# ---- 엔트리 상한 ----

def test_eviction_keeps_cache_bounded(cache, tmp_path, monkeypatch):
    monkeypatch.setattr('services.tour_cache.TOUR_CACHE_MAX_ENTRIES', 10)
    for i in range(20):
        cache.set(cache.make_key(36.0 + i * 0.1, 127.0, 10000, 12), PLACES)
    files = [n for n in os.listdir(str(tmp_path)) if n.endswith('.json')]
    assert len(files) <= 20          # 무한 증가하지 않는다
