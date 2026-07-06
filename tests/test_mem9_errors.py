import sys
import types

sys.modules.setdefault("requests", types.SimpleNamespace(Response=object))

from tools.mem9_errors import build_mem9_error_payload, format_provider_error


CLAIM_URL = "https://console.mem9.ai/console/claim?key=mem9_test"
BILLING_URL = "https://console.mem9.ai/console/billing/plan"


class FakeResponse:
    def __init__(self, status_code, payload, headers=None):
        self.status_code = status_code
        self._payload = payload
        self.text = str(payload)
        self.headers = headers or {}

    def json(self):
        return self._payload


def quota_payload(error, runtime_quota=None):
    details = {"errorCategory": "runtime_quota_denied"}
    if runtime_quota is not None:
        details["runtimeQuota"] = runtime_quota
    return {"error": error, "details": details}


def test_build_recall_quota_payload_preserves_claim_action():
    response = FakeResponse(
        402,
        quota_payload("Included quota is exhausted.", {
            "meter": "memory_recall_requests",
            "recommendedAction": {
                "type": "openUrl",
                "providerActionCode": "claimApiKey",
                "url": CLAIM_URL,
            },
        }),
    )

    payload = build_mem9_error_payload(response, "search memories")

    assert payload["code"] == "runtime_quota_denied"
    assert payload["action_url"] == CLAIM_URL
    assert payload["quota"]["meter"] == "memory_recall_requests"
    assert payload["quota"]["recommendedAction"] == {
        "type": "openUrl",
        "providerActionCode": "claimApiKey",
        "url": CLAIM_URL,
    }
    assert "Mem9 recall is temporarily unavailable" in payload["quota"]["user_message"]
    assert "mem9 cannot recall memories right now" in payload["quota"]["user_message"]
    assert "Include the link exactly as written" in payload["quota"]["user_message"]


def test_build_write_quota_payload_uses_spending_limit_action():
    response = FakeResponse(
        402,
        quota_payload("Spending limit is exhausted.", {
            "meter": "memory_write_requests",
            "recommendedAction": {
                "type": "openUrl",
                "providerActionCode": "increaseSpendingLimit",
                "url": BILLING_URL,
            },
        }),
    )

    payload = build_mem9_error_payload(response, "store memory")

    assert payload["action_url"] == BILLING_URL
    assert payload["quota"]["recommendedAction"]["providerActionCode"] == "increaseSpendingLimit"
    assert "Mem9 memory saving is temporarily unavailable" in payload["user_message"]
    assert "increase the mem9 spending limit" in payload["user_message"]


def test_build_recall_post_quota_rate_limit_payload_uses_generic_guidance_without_url():
    response = FakeResponse(
        429,
        quota_payload("Post-quota rate limit exceeded.", {
            "meter": "memory_recall_requests",
            "quotaGateResult": {
                "outcome": "rateLimited",
                "mode": "postQuota",
                "postQuotaRateLimit": {
                    "requestsPerMinute": 4,
                    "windowDurationSeconds": 60,
                    "scope": "apiKeyMeter",
                    "retryAfterSeconds": 23,
                },
            },
        }),
    )

    payload = build_mem9_error_payload(response, "search memories")

    assert payload["status_code"] == 429
    assert payload["code"] == "runtime_quota_denied"
    assert "action_url" not in payload
    assert payload["quota"]["retryAfterSeconds"] == 23
    assert "temporary request limit" in payload["user_message"]
    assert "quota/rate-limit check blocked this request" in payload["user_message"]
    assert "console/billing/plan" not in payload["user_message"]


def test_build_minimal_public_quota_payload_uses_stable_category():
    response = FakeResponse(402, quota_payload("Runtime access is blocked."))

    payload = build_mem9_error_payload(response, "search memories")

    assert payload["code"] == "runtime_quota_denied"
    assert payload["quota"]["code"] == "runtime_quota_denied"
    assert payload["error"] == "Runtime access is blocked."
    assert "action_url" not in payload
    assert "runtime quota check blocked this request" in payload["user_message"]


def test_build_write_post_quota_rate_limit_payload_keeps_server_action():
    response = FakeResponse(
        429,
        quota_payload("Post-quota rate limit exceeded.", {
            "meter": "memory_write_requests",
            "recommendedAction": {
                "type": "openUrl",
                "providerActionCode": "upgradePlan",
                "url": BILLING_URL,
            },
            "quotaGateResult": {
                "outcome": "rateLimited",
                "mode": "postQuota",
                "reason": "postQuotaRateLimitExceeded",
                "postQuotaRateLimit": {
                    "requestsPerMinute": 2,
                    "windowDurationSeconds": 60,
                    "scope": "apiKeyMeter",
                    "retryAfterSeconds": 1,
                },
            },
        }),
    )

    payload = build_mem9_error_payload(response, "store memory")

    assert payload["action_url"] == BILLING_URL
    assert payload["quota"]["retryAfterSeconds"] == 1
    assert "Mem9 memory saving is temporarily unavailable" in payload["user_message"]
    assert "upgrade their mem9 plan and get more included usage" in payload["user_message"]
    assert payload["user_message"].count(BILLING_URL) == 1


def test_build_recall_post_quota_rate_limit_payload_keeps_claim_action():
    response = FakeResponse(
        429,
        quota_payload("Post-quota rate limit exceeded.", {
            "meter": "memory_recall_requests",
            "recommendedAction": {
                "type": "openUrl",
                "providerActionCode": "claimApiKey",
                "url": CLAIM_URL,
            },
            "quotaGateResult": {
                "outcome": "rateLimited",
                "mode": "postQuota",
                "reason": "postQuotaRateLimitExceeded",
                "postQuotaRateLimit": {
                    "requestsPerMinute": 4,
                    "windowDurationSeconds": 60,
                    "scope": "apiKeyMeter",
                    "retryAfterSeconds": 23,
                },
            },
        }),
    )

    payload = build_mem9_error_payload(response, "search memories")

    assert payload["action_url"] == CLAIM_URL
    assert payload["quota"]["recommendedAction"]["providerActionCode"] == "claimApiKey"
    assert "temporary request limit" in payload["user_message"]
    assert "sign in or create a mem9 account and claim this API key" in payload["user_message"]
    assert "After claiming the key, they can upgrade their plan or set up billing" in payload["user_message"]
    assert "console/billing/plan" not in payload["user_message"]
    assert payload["user_message"].count(CLAIM_URL) == 1


def test_provider_error_uses_admin_wording_with_action_url():
    response = FakeResponse(
        402,
        quota_payload("Included quota is exhausted.", {
            "recommendedAction": {
                "type": "openUrl",
                "providerActionCode": "claimApiKey",
                "url": CLAIM_URL,
            },
        }),
    )

    message = format_provider_error(response)

    assert "mem9 returned HTTP 402" in message
    assert "Runtime quota denied for provider validation" in message
    assert CLAIM_URL in message
    assert "In your reply" not in message
    assert "Ask them" not in message
