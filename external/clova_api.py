# external/clova_api.py — CLOVA Studio 챗 API 호출(요청 구성 + POST). 응답 가공은 services/review_service.py.
import os

import requests


def request_review_analysis(text):
    """후기 분석을 CLOVA에 요청하고 응답 객체(requests.Response)를 그대로 반환한다."""
    api_key = os.environ.get('CLOVA_API_KEY')
    host = os.environ.get('CLOVA_HOST')
    endpoint = os.environ.get('CLOVA_ENDPOINT')
    url = host + endpoint
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    request_data = {
        "messages": [
            {
                "role": "system",
                "content": "너는 사용자 후기를 분석하여 긍정적인 점과 개선점을 추출하는 전문가야. 문장에 '좋은데', '아쉽지만', '하지만' 같은 연결어가 있어도 각 부분을 독립적으로 평가해서 키워드를 추출해야 해. 결과는 반드시 JSON 형식으로 \"strengths\"와 \"improvements\" 키를 사용해줘."
            },
            {
                "role": "user",
                "content": "거리가 가까워서 좋은데 체험이 좀 힘들었어요."
            },
            {
                "role": "assistant",
                "content": "```json\n{\n  \"strengths\": [\"가까운 거리\"],\n  \"improvements\": [\"체험 난이도 조절\"]\n}\n```"
            },
            {
                "role": "user",
                "content": "화장실이 아주 깨끗한 편은 아니었지만 이정도면 괜찮았구요."
            },
            {
                "role": "assistant",
                "content": "```json\n{\n  \"strengths\": [],\n  \"improvements\": [\"화장실 청결도\"]\n}\n```"
            },
            {
                "role": "user",
                "content": text
            }
        ],
        "temperature": 0.1,
        "stream": False
    }

    return requests.post(url, headers=headers, json=request_data)
