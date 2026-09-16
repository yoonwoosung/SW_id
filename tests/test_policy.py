"""services/policy_service 단위 테스트 — 예약 상세 '알아두어야 할 사항' 정책 3종 구조."""
from services.policy_service import booking_policies


def test_three_policies_with_required_keys():
    policies = booking_policies()
    assert [p["key"] for p in policies] == ["refund", "rules", "safety"]
    for p in policies:
        assert p["title"] and p["summary"]            # 요약(첫 화면 노출)
        assert p["details"] and len(p["details"]) >= 2  # 자세히(펼침 목록)
        assert p["icon"]
