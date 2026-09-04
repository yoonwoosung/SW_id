# routes/album.py — 추억 앨범(일지) CRUD, 추억 광장(커뮤니티) 및 한국관광공사 사진 API 연동
import os
import re
import json
import math
import requests
from flask import render_template, request, jsonify, session, Response
from models import db, Album, User


# ==========================================
# 1. 페이지 라우트
# ==========================================

def community_page():
    """추억 광장(커뮤니티) 메인 페이지 — 비로그인 접근 가능"""
    return render_template('community.html')


# ==========================================
# 2. 한국관광공사 관광사진 API & 이미지 프록시 연동
# ==========================================

def proxy_image():
    """
    외부 관광공사 이미지의 CORS 차단 및 캔버스 오염(PDF 백지 현상)을 방지하는 이미지 프록시
    (GET /api/proxy-image?url=...)
    """
    image_url = request.args.get('url', '').strip()
    if not image_url:
        return jsonify({'error': 'URL이 필요합니다.'}), 400

    try:
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Referer': 'https://korean.visitkorea.or.kr/'
        }
        res = requests.get(image_url, headers=headers, timeout=10)
        content_type = res.headers.get('Content-Type', 'image/jpeg')
        return Response(res.content, status=res.status_code, headers={
            'Content-Type': content_type,
            'Access-Control-Allow-Origin': '*',
            'Cache-Control': 'public, max-age=86400'
        })
    except Exception as e:
        return jsonify({'error': str(e)}), 500


def get_tour_photos():
    """
    체험 농장 주소 또는 검색어를 받아 한국관광공사 포토코리아 사진을 조회하는 API
    (GET /api/tour-photos?keyword=...&address=...&pageNo=...&numOfRows=...)
    """
    keyword = request.args.get('keyword', '').strip()
    address = request.args.get('address', '').strip()
    page_no = request.args.get('pageNo', 1, type=int)
    num_of_rows = request.args.get('numOfRows', 40, type=int)

    # 1. 주소에서 핵심 지역 키워드 추출
    search_query = keyword
    if not search_query and address:
        eup_myeon = re.findall(r'([가-힣]+[읍면동])', address)
        si_gun = re.findall(r'([가-힣]+[시군구])', address)

        if eup_myeon:
            search_query = eup_myeon[0].replace('읍', '').replace('면', '').replace('동', '')
        elif si_gun:
            search_query = si_gun[0].replace('시', '').replace('군', '').replace('구', '')
        else:
            search_query = "천안"

    if not search_query:
        search_query = "천안"

    api_key = os.environ.get("KTO_PHOTO_API_KEY")
    if not api_key:
        return jsonify({"success": False, "error": "KTO_PHOTO_API_KEY가 설정되지 않았습니다."}), 500

    api_url = "https://apis.data.go.kr/B551011/PhotoGalleryService1/gallerySearchList1"
    params = {
        "serviceKey": api_key,
        "numOfRows": num_of_rows,
        "pageNo": page_no,
        "MobileOS": "ETC",
        "MobileApp": "FarmLink",
        "arrange": "A",
        "keyword": search_query,
        "_type": "json"
    }

    try:
        res = requests.get(api_url, params=params, timeout=5)
        data = res.json()

        body_data = data.get("response", {}).get("body", {})
        items_data = body_data.get("items", {})
        total_count = body_data.get("totalCount", 0)
        
        # 읍/면 단위 검색 결과가 없을 경우 '시/군' 단위로 2차 Fallback 검색
        if not items_data and address:
            si_gun = re.findall(r'([가-힣]+[시군구])', address)
            if si_gun:
                fallback_query = si_gun[0].replace('시', '').replace('군', '').replace('구', '')
                if fallback_query != search_query:
                    params["keyword"] = fallback_query
                    res = requests.get(api_url, params=params, timeout=5)
                    data = res.json()
                    body_data = data.get("response", {}).get("body", {})
                    items_data = body_data.get("items", {})
                    total_count = body_data.get("totalCount", 0)

        raw_item = items_data.get("item", []) if isinstance(items_data, dict) else []
        item_list = [raw_item] if isinstance(raw_item, dict) else raw_item

        photos = []
        for it in item_list:
            raw_url = it.get("galWebImageUrl", "")
            proxy_url = f"/api/proxy-image?url={requests.utils.quote(raw_url)}" if raw_url else ""
            photos.append({
                "title": it.get("galTitle", "관광 사진"),
                "imageUrl": proxy_url,
                "rawUrl": raw_url,
                "location": it.get("galPhotographyLocation", ""),
                "photographer": it.get("galPhotographer", "한국관광공사")
            })

        return jsonify({
            "success": True,
            "query": params["keyword"],
            "totalCount": total_count,
            "pageNo": page_no,
            "photos": photos
        }), 200

    except Exception as e:
        return jsonify({"success": False, "error": str(e)}), 500


# ==========================================
# 3. 개인 앨범 CRUD API (/api/albums)
# ==========================================

def get_albums():
    """내 앨범 목록 조회 (GET /api/albums)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    user_id = session['user_id']
    albums = Album.query.filter_by(user_id=user_id).order_by(Album.updated_at.desc()).all()
    return jsonify({
        'success': True,
        'albums': [album.to_dict(include_pages=False) for album in albums]
    }), 200


def create_album():
    """앨범 생성 (POST /api/albums)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    data = request.get_json() or {}
    pages_data = data.get('pages_data', [])
    pages_data_str = json.dumps(pages_data, ensure_ascii=False) if isinstance(pages_data, (list, dict)) else str(pages_data)

    new_album = Album(
        user_id=session['user_id'],
        title=data.get('title', '제목 없음'),
        shape_theme=data.get('shape_theme', 'shape-portrait'),
        cover_theme=data.get('cover_theme', 'cover-green'),
        paper_theme=data.get('paper_theme', 'paper-white'),
        inner_page_count=int(data.get('inner_page_count', 2)),
        pages_data=pages_data_str,
        category=data.get('category', 'all'),
        is_public=data.get('is_public', False)
    )

    db.session.add(new_album)
    db.session.commit()

    return jsonify({
        'success': True,
        'album_id': new_album.id
    }), 201


def get_album_detail(album_id):
    """앨범 단건 조회 — 편집 재개용 (GET /api/albums/<id>)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    album = Album.query.get(album_id)
    if not album or album.user_id != session['user_id']:
        return jsonify({'success': False, 'error': 'not_found'}), 404

    return jsonify({
        'success': True,
        'album': album.to_dict(include_pages=True)
    }), 200


def update_album(album_id):
    """앨범 수정/저장 (PUT /api/albums/<id>)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    album = Album.query.get(album_id)
    if not album:
        return jsonify({'success': False, 'error': 'not_found'}), 404
    if album.user_id != session['user_id']:
        return jsonify({'success': False, 'error': 'forbidden'}), 403

    data = request.get_json() or {}
    if 'title' in data:
        album.title = data['title']
    if 'shape_theme' in data:
        album.shape_theme = data['shape_theme']
    if 'cover_theme' in data:
        album.cover_theme = data['cover_theme']
    if 'paper_theme' in data:
        album.paper_theme = data['paper_theme']
    if 'inner_page_count' in data:
        album.inner_page_count = int(data['inner_page_count'])
    if 'pages_data' in data:
        pages_data = data['pages_data']
        album.pages_data = json.dumps(pages_data, ensure_ascii=False) if isinstance(pages_data, (list, dict)) else str(pages_data)
    if 'category' in data:
        album.category = data['category']
    if 'is_public' in data:
        album.is_public = data['is_public']

    db.session.commit()
    return jsonify({'success': True}), 200


def delete_album(album_id):
    """앨범 삭제 (DELETE /api/albums/<id>)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    album = Album.query.get(album_id)
    if not album:
        return jsonify({'success': False, 'error': 'not_found'}), 404
    if album.user_id != session['user_id']:
        return jsonify({'success': False, 'error': 'forbidden'}), 403

    db.session.delete(album)
    db.session.commit()
    return jsonify({'success': True}), 200


def update_album_visibility(album_id):
    """앨범 공개/비공개 전환 (PUT /api/albums/<id>/visibility)"""
    if 'user_id' not in session:
        return jsonify({'success': False, 'message': '로그인이 필요합니다.'}), 401

    album = Album.query.get(album_id)
    if not album:
        return jsonify({'success': False, 'error': 'not_found'}), 404
    if album.user_id != session['user_id']:
        return jsonify({'success': False, 'error': 'forbidden'}), 403

    data = request.get_json() or {}
    if 'is_public' in data:
        album.is_public = bool(data['is_public'])
    if 'category' in data:
        album.category = data['category']

    db.session.commit()
    return jsonify({'success': True}), 200


# ==========================================
# 4. 추억 광장(커뮤니티) 조회 API (/api/community/albums)
# ==========================================

def get_community_albums():
    """공개 앨범 목록 조회 (GET /api/community/albums) — 비로그인 가능"""
    category = request.args.get('category', 'all')
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 16, type=int)

    query = Album.query.filter_by(is_public=True)
    if category and category != 'all':
        query = query.filter_by(category=category)

    total = query.count()
    pages = math.ceil(total / per_page) if total > 0 else 1
    albums = query.order_by(Album.created_at.desc()).offset((page - 1) * per_page).limit(per_page).all()

    return jsonify({
        'success': True,
        'total': total,
        'page': page,
        'pages': pages,
        'albums': [album.to_dict(include_pages=False) for album in albums]
    }), 200


def get_community_album_detail(album_id):
    """공개 앨범 단건 조회 — 뷰어용 (GET /api/community/albums/<id>) — 비로그인 가능"""
    album = Album.query.filter_by(id=album_id, is_public=True).first()
    if not album:
        return jsonify({'success': False, 'error': 'not_found'}), 404

    return jsonify({
        'success': True,
        'album': album.to_dict(include_pages=True)
    }), 200


# ==========================================
# 라우트 등록 함수
# ==========================================

def register(app):
    # 페이지
    app.add_url_rule('/community', 'community_page', community_page)

    # 💡 한국관광공사 사진 API 및 이미지 프록시 등록
    app.add_url_rule('/api/proxy-image', 'proxy_image', proxy_image, methods=['GET'])
    app.add_url_rule('/api/tour-photos', 'get_tour_photos', get_tour_photos, methods=['GET'])

    # 앨범 CRUD API
    app.add_url_rule('/api/albums', 'get_albums', get_albums, methods=['GET'])
    app.add_url_rule('/api/albums', 'create_album', create_album, methods=['POST'])
    app.add_url_rule('/api/albums/<int:album_id>', 'get_album_detail', get_album_detail, methods=['GET'])
    app.add_url_rule('/api/albums/<int:album_id>', 'update_album', update_album, methods=['PUT'])
    app.add_url_rule('/api/albums/<int:album_id>', 'delete_album', delete_album, methods=['DELETE'])
    app.add_url_rule('/api/albums/<int:album_id>/visibility', 'update_album_visibility', update_album_visibility, methods=['PUT'])

    # 커뮤니티 API
    app.add_url_rule('/api/community/albums', 'get_community_albums', get_community_albums, methods=['GET'])
    app.add_url_rule('/api/community/albums/<int:album_id>', 'get_community_album_detail', get_community_album_detail, methods=['GET'])