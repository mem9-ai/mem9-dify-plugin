import sys
import types

sys.modules.setdefault("requests", types.SimpleNamespace(Response=object))

from tools.mem9_errors import build_mem9_error_payload, format_provider_error


CLAIM_URL = "https://console.mem9.ai/console/claim?key=mem9_test"
BILLING_URL = "https://console.mem9.ai/console/billing/plan"


class FakeResponse:
    def __init__(self, status_code, payload):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)

    def json(self):
        return self._payload


def test_build_recall_quota_payload_preserves_claim_action():
    response = FakeResponse(
        402,
        {
            "code": "quota_exhausted",
            "message": "Included quota is exhausted.",
            "details": {
                "mem9Code": "runtime_quota_denied",
                "meter": "memory_recall_requests",
                "recommendedAction": {
                    "bindingState": "unclaimed",
                    "type": "claimApiKey",
                    "url": CLAIM_URL,
                },
            },
        },
    )

    payload = build_mem9_error_payload(response, "search memories")

    assert payload["action_url"] == CLAIM_URL
    assert payload["quota"]["meter"] == "memory_recall_requests"
    assert "Mem9 recall is temporarily unavailable" in payload["quota"]["user_message"]
    assert "mem9 cannot recall memories right now" in payload["quota"]["user_message"]
    assert "Include the link exactly as written" in payload["quota"]["user_message"]


def test_build_write_quota_payload_uses_spending_limit_action():
    response = FakeResponse(
        402,
        {
            "code": "spending_limit_exceeded",
            "message": "Spending limit is exhausted.",
            "details": {
                "mem9Code": "runtime_quota_denied",
                "meter": "memory_write_requests",
                "recommendedAction": {
                    "bindingState": "claimed",
                    "type": "increaseSpendingLimit",
                    "url": BILLING_URL,
                },
            },
        },
    )

    payload = build_mem9_error_payload(response, "store memory")

    assert payload["action_url"] == BILLING_URL
    assert payload["quota"]["recommendedAction"]["type"] == "increaseSpendingLimit"
    assert "Mem9 memory saving is temporarily unavailable" in payload["user_message"]
    assert "increase the mem9 spending limit" in payload["user_message"]


def test_provider_error_includes_action_notice():
    response = FakeResponse(
        402,
        {
            "code": "quota_exhausted",
            "message": "Included quota is exhausted.",
            "details": {
                "mem9Code": "runtime_quota_denied",
                "recommendedAction": {
                    "type": "claimApiKey",
                    "url": CLAIM_URL,
                },
            },
        },
    )

    message = format_provider_error(response)

    assert "mem9 returned HTTP 402" in message
    assert CLAIM_URL in message
    assert "Include the link exactly as written" in message
