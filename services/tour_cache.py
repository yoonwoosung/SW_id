# services/tour_cache.py — 한국관광공사(KTO) 위치기반 조회 결과의 파일 캐시.
#
# 배경: AI 추천 페이지는 코스 카드마다 /api/experiences/<id>/course 를 부르고,
# 그 한 번이 KTO 를 2~4회 호출한다. KTO 일일 한도가 1,000건이라 금방 소진된다.
#
# 왜 파일인가: PythonAnywhere 는 워커 프로세스를 여러 개 띄울 수 있어서
# 프로세스 메모리 캐시는 워커마다 따로 쌓인다(효과가 워커 수만큼 나뉜다).
# 파일은 워커 수와 무관하게 하나를 공유하고, 앱 재시작 후에도 남는다.
#
# 왜 좌표를 반올림하나: 소수 2자리는 약 1.1km 다. 같은 농장의 체험 여러 건이나
# 인접 농장이 한 엔트리를 공유하게 된다. 후보 목록만 공유할 뿐
# course_builder._sorted_by_distance() 가 체험의 실제 좌표로 거리를 다시 계산하므로
# 코스 순서·선택 결과는 각 체험 기준으로 정확하다.
#
# 이 모듈은 절대 예외를 밖으로 내보내지 않는다. 캐시가 깨져도 호출부는
# 평소대로 KTO 를 부르면 되고, 서비스가 멈춰선 안 된다.
import hashlib
import json
import os
import tempfile
import time

from common.constants import (
    TOUR_CACHE_TTL_SEC,
    TOUR_CACHE_EMPTY_TTL_SEC,
    TOUR_CACHE_MAX_ENTRIES,
)

# 좌표 반올림 자릿수. 2 = 약 1.1km 격자.
# 격자라서 경계를 사이에 둔 두 좌표는 수십 m 차이여도 키가 갈린다
# (127.2943 → 127.29 / 127.2950 → 127.3). 그때는 캐시를 못 나눠 쓸 뿐이고
# 최악이 캐싱 전과 같은 동작이라 정확도 문제는 없다.
COORD_PRECISION = 2

_CACHE_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))), '.cache', 'tour')


def cache_dir():
    return _CACHE_DIR


def make_key(lat, lng, radius_m, content_type_id):
    """좌표를 반올림해 캐시 키를 만든다. 좌표가 없으면 None(캐시 미사용)."""
    try:
        rounded_lat = round(float(lat), COORD_PRECISION)
        rounded_lng = round(float(lng), COORD_PRECISION)
    except (TypeError, ValueError):
        return None
    raw = "%s|%s|%s|%s" % (rounded_lat, rounded_lng, radius_m, content_type_id)
    return hashlib.sha1(raw.encode('utf-8')).hexdigest()


def _path_for(key):
    return os.path.join(_CACHE_DIR, key + '.json')


def get(key):
    """살아있는 캐시면 장소 리스트, 없거나 만료·손상이면 None.

    빈 결과는 TTL 을 짧게 준다. KTO 일시 장애로 받은 [] 를 한 시간 물고 있으면
    API 가 1분 만에 복구돼도 화면은 한 시간 내내 '코스 생성 불가'로 굳는다.
    """
    if not key:
        return None
    try:
        with open(_path_for(key), encoding='utf-8') as f:
            entry = json.load(f)
        places = entry['places']
        saved_at = float(entry['saved_at'])
    except Exception:
        # 파일 없음·JSON 손상·키 누락 모두 '캐시 없음'으로 처리한다.
        return None

    ttl = TOUR_CACHE_EMPTY_TTL_SEC if not places else TOUR_CACHE_TTL_SEC
    if time.time() - saved_at > ttl:
        return None
    return places


def set(key, places):
    """캐시에 저장한다. 실패해도 조용히 넘어간다(호출부는 이미 결과를 갖고 있다)."""
    if not key:
        return
    try:
        os.makedirs(_CACHE_DIR, exist_ok=True)
        _evict_if_needed()
        entry = {'saved_at': time.time(), 'places': places}
        # 같은 키에 두 워커가 동시에 쓰면 반쯤 쓰인 JSON 을 남길 수 있다.
        # 임시 파일에 다 쓴 뒤 원자적으로 바꿔치기한다.
        fd, tmp = tempfile.mkstemp(dir=_CACHE_DIR, suffix='.tmp')
        try:
            with os.fdopen(fd, 'w', encoding='utf-8') as f:
                json.dump(entry, f, ensure_ascii=False)
            os.replace(tmp, _path_for(key))
        except Exception:
            _silent_remove(tmp)
            raise
    except Exception:
        return


def _evict_if_needed():
    """엔트리가 상한을 넘으면 오래된 것부터 지운다. 무한 증가 방지."""
    try:
        names = [n for n in os.listdir(_CACHE_DIR) if n.endswith('.json')]
        if len(names) < TOUR_CACHE_MAX_ENTRIES:
            return
        paths = [os.path.join(_CACHE_DIR, n) for n in names]
        paths.sort(key=lambda p: os.path.getmtime(p))
        # 상한의 10% 만큼 여유를 두고 비운다(매번 한 개씩 지우지 않게).
        for p in paths[:max(1, TOUR_CACHE_MAX_ENTRIES // 10)]:
            _silent_remove(p)
    except Exception:
        return


def _silent_remove(path):
    try:
        os.remove(path)
    except Exception:
        pass
