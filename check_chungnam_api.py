#!/usr/bin/env python3
"""충남 올담 API 가 열렸는지 확인하고, 열렸으면 응답 구조를 보여준다.

서버가 "서비스 확대를 위한 작업 중"으로 닫혀 있던 동안 만들어 둔 점검 도구다.
열리면 external/chungnam_api.py 의 _to_place / _extract_items 만 채우면 된다.

사용:
    python check_chungnam_api.py            # 상태 + 구조 요약
    python check_chungnam_api.py --raw      # 원문도 함께 출력
"""
import json
import os
import sys

import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    from dotenv import load_dotenv
    load_dotenv(os.path.join(os.path.dirname(os.path.abspath(__file__)), '.env'))
except Exception:
    pass

URL = "https://alldam.chungnam.go.kr/api/getTrsmic/stdlist.do"
# WAF 가 requests 기본 UA 를 404 로 막는다. 브라우저 UA 가 필수다.
UA = ("Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
      "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")


def decode(response):
    if not response.encoding or response.encoding.lower() == 'iso-8859-1':
        response.encoding = response.apparent_encoding or 'utf-8'
    try:
        return response.text
    except Exception:
        return response.content.decode('utf-8', 'replace')


def strip_html(html):
    import re
    text = re.sub(r'<(script|style)[^>]*>.*?</\1>', '', html, flags=re.S | re.I)
    text = re.sub(r'<[^>]+>', ' ', text)
    return re.sub(r'\s+', ' ', text).strip()


def describe(value, depth=0, prefix=''):
    """응답 구조를 타입과 함께 트리로 출력한다."""
    pad = '   ' * depth
    if isinstance(value, dict):
        print(f"{pad}{prefix}{{}} ({len(value)} keys)")
        for k, v in list(value.items())[:25]:
            describe(v, depth + 1, f"{k}: ")
    elif isinstance(value, list):
        print(f"{pad}{prefix}[] ({len(value)} items)")
        if value:
            describe(value[0], depth + 1, '[0] ')
    else:
        shown = str(value)
        if len(shown) > 60:
            shown = shown[:60] + '…'
        print(f"{pad}{prefix}{type(value).__name__} = {shown!r}")


def main():
    show_raw = '--raw' in sys.argv
    key = os.environ.get('CHUNGNAM_API_KEY')
    print(f"  인증키: {'있음 (' + str(len(key)) + '자)' if key else '★없음 — .env 확인★'}")

    params = {'numOfRows': 3, 'pageNo': 1, 'type': 'json'}
    if key:
        params['serviceKey'] = key

    try:
        r = requests.get(URL, params=params, timeout=20,
                         headers={'User-Agent': UA, 'Accept': 'application/json, */*'})
    except Exception as exc:
        print(f"  ❌ 요청 실패: {exc}")
        return 2

    body = decode(r)
    ctype = r.headers.get('Content-Type', '')
    print(f"  HTTP {r.status_code} · {ctype} · {len(r.content):,}바이트")

    is_html = 'html' in ctype.lower() or body.lstrip()[:15].lower().startswith(('<!doctype', '<html'))
    if is_html:
        print(f"\n  ⏳ 아직 열리지 않았습니다.")
        print(f"     {strip_html(body)[:140]}")
        return 1

    print("\n  ✅ 데이터 응답으로 보입니다.\n")
    try:
        parsed = json.loads(body)
    except Exception:
        print("  JSON 파싱 실패 — XML 일 수 있습니다. 원문 앞부분:")
        print('  ' + body[:600])
        return 0

    print("  === 응답 구조 ===")
    describe(parsed)

    print("\n  === 다음 할 일 ===")
    print("     external/chungnam_api.py 의 _extract_items() 에 항목 리스트 경로를,")
    print("     _to_place() 에 name·address·lat·lng 매핑을 채우면 됩니다.")

    if show_raw:
        print("\n  === 원문 ===")
        print(json.dumps(parsed, ensure_ascii=False, indent=2)[:3000])
    return 0


if __name__ == '__main__':
    sys.exit(main())
