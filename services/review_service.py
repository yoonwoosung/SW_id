# services/review_service.py — 검증 완료된 Flash-Lite 기반 초고속 후기 분석 서비스
import os
import json
import re
import requests

# 💡 터미널 테스트로 200 OK 검증 완료된 고속 모델
PRIMARY_MODEL = "gemini-flash-lite-latest"
FALLBACK_MODEL = "gemini-3.5-flash-lite"


def _send_request(model_name: str, api_key: str, payload: dict) -> requests.Response:
    """단일 모델 대상 REST API 전송 헬퍼 (타임아웃 10초)"""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
    headers = {"Content-Type": "application/json"}
    return requests.post(url, headers=headers, json=payload, timeout=10)


def _call_gemini_api(prompt: str) -> dict:
    """Google Gemini REST API 호출 (1순위 실패 시 2순위 자동 전환)"""
    api_key = os.environ.get("GEMINI_API_KEY")
    if not api_key:
        print("[Gemini API] 오류: GEMINI_API_KEY 환경변수가 설정되지 않았습니다.")
        return None

    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
            "maxOutputTokens": 800
        }
    }

    response = None

    # 1. PRIMARY_MODEL 호출 시도
    try:
        response = _send_request(PRIMARY_MODEL, api_key, payload)
    except requests.exceptions.RequestException as e:
        print(f"[Gemini API] 1차 모델({PRIMARY_MODEL}) 요청 실패: {e}")

    # 2. 1차 호출 실패 또는 에러 발생 시 FALLBACK_MODEL로 즉시 전환
    if response is None or response.status_code != 200:
        err_msg = response.text if response is not None else "연결 불가"
        print(f"[Gemini API] {PRIMARY_MODEL} 실패 ({err_msg}) -> {FALLBACK_MODEL} 로 대체 요청")
        try:
            response = _send_request(FALLBACK_MODEL, api_key, payload)
        except requests.exceptions.RequestException as e:
            print(f"[Gemini API] 대체 모델({FALLBACK_MODEL}) 요청 실패: {e}")
            return None

    if response is None or response.status_code != 200:
        final_code = response.status_code if response is not None else "None"
        final_text = response.text if response is not None else "응답 없음"
        print(f"[Gemini API] 최종 호출 실패 ({final_code}): {final_text}")
        return None

    # 3. JSON 응답 안전 파싱
    try:
        res_json = response.json()
        raw_text = res_json['candidates'][0]['content']['parts'][0]['text']
        json_match = re.search(r'\{.*\}', raw_text, re.DOTALL)
        if json_match:
            return json.loads(json_match.group(0))
        return json.loads(raw_text)
    except Exception as e:
        print(f"[Gemini API] JSON 파싱 오류: {e}")
        return None


def analyze_review_with_clova(text):
    """
    [체험자 후기 등록 시 자동 실행]
    개별 후기 본문에서 긍정 키워드(strengths)와 개선 키워드(improvements)를 추출합니다.
    기존 라우트와의 호환성을 위해 함수명을 유지합니다.
    """
    if not text or len(text.strip()) < 3:
        return {"strengths": [], "improvements": []}

    prompt = f"""
    당신은 농촌 체험 리뷰 분석 AI입니다.
    아래 방문객의 체험 후기를 분석하여 긍정적인 평가 키워드(strengths)와 개선이 필요한 점 키워드(improvements)를 각각 1~3개씩 추출하세요.
    키워드는 명사 또는 짧은 구(예: "신선한 딸기", "친절한 설명", "주차장 협소")로 작성하세요.

    반드시 아래 JSON 포맷으로만 응답하세요:
    {{
        "strengths": ["키워드1", "키워드2"],
        "improvements": ["키워드1"]
    }}

    [체험 후기]
    "{text}"
    """

    try:
        result = _call_gemini_api(prompt)
        if result and isinstance(result, dict):
            return {
                "strengths": result.get("strengths", []),
                "improvements": result.get("improvements", [])
            }
    except Exception as e:
        print(f"[Gemini 후기 분석 오류]: {e}")

    return {"strengths": [], "improvements": []}


def analyze_farm_reviews_summary(reviews_list):
    """
    [농장주 간편모드: AI 분석 갱신 시 실행]
    해당 농장의 모든 실제 후기들을 묶어 종합 긍정 요약, 개선 피드백 요약, 만족도(%)를 생성합니다.
    """
    review_lines = []
    for r in reviews_list:
        content = getattr(r, 'content', None) or getattr(r, 'comment', '')
        rating = getattr(r, 'rating', None) or getattr(r, 'score', 5)
        if content:
            review_lines.append(f"- [별점 {rating}점] {content}")

    if not review_lines:
        return None

    corpus = "\n".join(review_lines)

    prompt = f"""
    당신은 농촌 체험 농장 전문 컨설턴트입니다.
    아래 농장의 실제 방문객 후기들을 객관적으로 분석하여 농장주를 위한 종합 요약 리포트를 작성하세요.

    반드시 아래 JSON 포맷으로만 응답하세요:
    {{
        "strengths_summary": "방문객들이 칭찬한 농장의 장점 요약 (친절하고 격려하는 어조로 2~3문장)",
        "improvements_summary": "방문객들이 지적한 개선 필요 사항 및 조언 (2~3문장, 불만이 없으면 칭찬/격려 문구)",
        "satisfaction_rate": 85
    }}
    * satisfaction_rate는 전체 리뷰의 긍정적 뉘앙스를 종합 평가한 0부터 100 사이의 정수여야 합니다.

    [방문객 후기 목록]
    {corpus}
    """

    result = _call_gemini_api(prompt)
    if result and isinstance(result, dict):
        rate = result.get("satisfaction_rate", 85)
        try:
            rate = int(rate)
        except (ValueError, TypeError):
            rate = 85
        return {
            "strengths_summary": result.get("strengths_summary", ""),
            "improvements_summary": result.get("improvements_summary", ""),
            "satisfaction_rate": rate
        }
    return None