# external/kakao_map.py — 카카오 로컬 API로 주소를 좌표(위도, 경도)로 변환(지오코딩).
import requests
from flask import current_app


def get_coords_from_address(address):
    KAKAO_API_KEY = current_app.config['KAKAO_API_KEY']
    url = f"https://dapi.kakao.com/v2/local/search/address.json?query={address}"
    headers = {"Authorization": f"KakaoAK {KAKAO_API_KEY}"}
    print(f"--- 지오코딩 요청: 주소='{address}' ---")
    try:
        response = requests.get(url, headers=headers)
        response.raise_for_status()
        data = response.json()
        print(f"--- 카카오 API 응답: {data} ---")
        if data['documents']:
            location = data['documents'][0]
            lat, lng = float(location['y']), float(location['x'])
            print(f"--- 변환된 좌표: ({lat}, {lng}) ---")
            return lat, lng
    except Exception as e:
        print(f"지오코딩 처리 중 오류 발생: {e}")
    
    print("--- 기본 좌표 반환 ---")
    return 36.8583, 127.2943
