# services/review_service.py — CLOVA 후기 분석 응답을 파싱해 {strengths, improvements} dict로 가공한다.
import json
import re

from external import clova_api


def analyze_review_with_clova(text):
    try:
        response = clova_api.request_review_analysis(text)
        response.raise_for_status()

        response_data = response.json()
        content_string = response_data['result']['message']['content']

        json_match = re.search(r'\{.*\}', content_string, re.DOTALL)

        if json_match:
            json_string = json_match.group(0)
            analysis_result = json.loads(json_string)
            return analysis_result
        else:
            print(f"응답에서 JSON을 찾을 수 없음: {content_string}")
            return None

    except Exception as e:
        print(f"--- CLOVA API 에러 발생 ---")
        print(f"에러 종류: {e}")
        if 'response' in locals() and hasattr(response, 'text'):
            print(f"서버 실제 응답 내용: {response.text}")
        print("--------------------------")
        return None
