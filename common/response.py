# common/response.py — API 응답을 { success, data, error } 형식으로 통일하는 헬퍼.
from flask import jsonify


def success_response(data=None, status=200):
    """성공 응답: { "success": true, "data": ..., "error": null }"""
    return jsonify({"success": True, "data": data, "error": None}), status


def error_response(code, message, status=400):
    """실패 응답: { "success": false, "data": null, "error": {"code","message"} }"""
    return jsonify({
        "success": False,
        "data": None,
        "error": {"code": code, "message": message},
    }), status
