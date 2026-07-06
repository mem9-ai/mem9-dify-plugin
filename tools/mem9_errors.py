from typing import Any

import requests


QUOTA_CODES = {
    "quota_exhausted",
    "post_quota_rate_limited",
    "spending_limit_exceeded",
    "runtime_access_blocked",
    "runtime_quota_denied",
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _positive_int(value: Any) -> int | None:
    if isinstance(value, int) and value > 0:
        return value
    return None


def _retry_after_header(value: str | None) -> int | None:
    if not value:
        return None
    try:
        retry_after = int(value.strip())
    except ValueError:
        return None
    return retry_after if retry_after > 0 else None


def _normalize_recommended_action(runtime_quota: dict[str, Any]) -> dict[str, str] | None:
    nested = _as_dict(runtime_quota.get("recommendedAction"))
    action_type = str(nested.get("type") or "").strip()
    provider_action_code = str(nested.get("providerActionCode") or "").strip()
    severity = str(nested.get("severity") or "").strip()
    url = str(nested.get("url") or "").strip()

    legacy_action = str(runtime_quota.get("upgradeAction") or "").strip()
    if not provider_action_code and action_type and action_type != "openUrl":
        provider_action_code = action_type
        action_type = "openUrl" if url else ""
    if not provider_action_code and legacy_action:
        provider_action_code = legacy_action
        action_type = "openUrl" if url else ""
    if not url:
        url = str(runtime_quota.get("upgradeUrl") or "").strip()

    if not action_type and not provider_action_code and not severity and not url:
        return None

    action: dict[str, str] = {}
    if action_type:
        action["type"] = action_type
    if provider_action_code:
        action["providerActionCode"] = provider_action_code
    if severity:
        action["severity"] = severity
    if url:
        action["url"] = url
    return action


def _quota_gate_reason(details: dict[str, Any]) -> str:
    quota_gate_result = _as_dict(details.get("quotaGateResult"))
    return str(quota_gate_result.get("reason") or "").strip()


def _retry_after_seconds(details: dict[str, Any], retry_after: str | None = None) -> int | None:
    direct = _positive_int(details.get("retryAfterSeconds"))
    if direct is not None:
        return direct

    quota_gate_result = _as_dict(details.get("quotaGateResult"))
    post_quota_rate_limit = _as_dict(quota_gate_result.get("postQuotaRateLimit"))
    nested = _positive_int(post_quota_rate_limit.get("retryAfterSeconds"))
    if nested is not None:
        return nested

    return _retry_after_header(retry_after)


def parse_runtime_quota_denied(
    payload: Any,
    status_code: int | None = None,
    retry_after: str | None = None,
) -> dict[str, Any] | None:
    body = _as_dict(payload)
    if not body:
        return None

    details = _as_dict(body.get("details"))
    public_category = str(details.get("errorCategory") or "").strip()
    if public_category == "runtime_quota_denied":
        runtime_quota = _as_dict(details.get("runtimeQuota"))
        message = str(body.get("error") or "Runtime usage quota denied.")
    else:
        mem9_code = str(
            details.get("mem9Code") or details.get("mem9_code") or body.get("mem9_code") or ""
        ).strip()
        legacy_code = str(body.get("code") or "").strip()
        if mem9_code != "runtime_quota_denied" and legacy_code not in QUOTA_CODES:
            return None
        runtime_quota = details
        message = str(body.get("message") or body.get("error") or "Runtime usage quota denied.")

    if not isinstance(status_code, int):
        return None

    action = _normalize_recommended_action(runtime_quota)
    result: dict[str, Any] = {
        "status_code": status_code,
        "code": "runtime_quota_denied",
        "message": message,
        "meter": str(runtime_quota.get("meter") or "").strip(),
    }
    if action:
        result["recommendedAction"] = action
    quota_gate_reason = _quota_gate_reason(runtime_quota)
    if quota_gate_reason:
        result["quotaGateReason"] = quota_gate_reason
    retry_after_seconds = _retry_after_seconds(runtime_quota, retry_after)
    if retry_after_seconds is not None:
        result["retryAfterSeconds"] = retry_after_seconds
    return result


def _is_post_quota_rate_limited(quota: dict[str, Any]) -> bool:
    return (
        quota.get("status_code") == 429
        or quota.get("code") == "post_quota_rate_limited"
        or quota.get("quotaGateReason") == "postQuotaRateLimitExceeded"
    )


def _quota_reason(quota: dict[str, Any]) -> str:
    if _is_post_quota_rate_limited(quota):
        return "this API key has reached the temporary request limit for this memory feature"
    action = _as_dict(quota.get("recommendedAction"))
    provider_action_code = str(action.get("providerActionCode") or "").strip()
    if provider_action_code == "claimApiKey":
        return "the included usage quota for this API key has been used up"
    if provider_action_code == "increaseSpendingLimit":
        return "the configured spending limit would be exceeded"
    if provider_action_code == "enableOnDemand":
        return "the included usage quota has been used up and on-demand usage is not enabled"
    if provider_action_code == "upgradePlan":
        return "the included usage quota for this mem9 account has been used up"
    if provider_action_code == "resolveAccountState":
        return "the current account or billing state blocks runtime memory access"
    return "the runtime quota check blocked this request"


def _quota_notice_subject(quota: dict[str, Any], operation: str) -> dict[str, str]:
    meter = str(quota.get("meter") or "").strip()
    if meter == "memory_write_requests":
        return {
            "headline": "Mem9 memory saving is temporarily unavailable",
            "user_state": "mem9 cannot save new memories right now",
        }
    if meter == "memory_recall_requests":
        return {
            "headline": "Mem9 recall is temporarily unavailable",
            "user_state": "mem9 cannot recall memories right now",
        }

    operation_text = operation.lower()
    if any(word in operation_text for word in ("ingest", "save", "store", "write")):
        return {
            "headline": "Mem9 memory saving is temporarily unavailable",
            "user_state": "mem9 cannot save new memories right now",
        }
    if any(word in operation_text for word in ("recall", "search")):
        return {
            "headline": "Mem9 recall is temporarily unavailable",
            "user_state": "mem9 cannot recall memories right now",
        }
    return {
        "headline": "Mem9 memory is temporarily unavailable",
        "user_state": "mem9 cannot complete the memory request right now",
    }


def _action_instruction(quota: dict[str, Any]) -> str:
    action = _as_dict(quota.get("recommendedAction"))
    provider_action_code = str(action.get("providerActionCode") or "").strip()
    action_url = str(action.get("url") or "").strip()
    if _is_post_quota_rate_limited(quota) and not action_url:
        return (
            "Tell them that the quota/rate-limit check blocked this request "
            "and to retry later or open the mem9 console to review account and billing settings."
        )
    if not action_url:
        return "Ask them to open the mem9 console to resolve the account or billing state."

    if provider_action_code == "claimApiKey":
        return (
            "Ask them to open this link to sign in or create a mem9 account and "
            f"claim this API key: {action_url}. After claiming the key, they can "
            "upgrade their plan or set up billing to get more usage. Include the "
            "link exactly as written."
        )
    if provider_action_code == "upgradePlan":
        return (
            "Ask them to open this link to upgrade their mem9 plan and get more "
            f"included usage: {action_url}. Include the link exactly as written."
        )
    if provider_action_code == "increaseSpendingLimit":
        return (
            "Ask them to open this link to increase the mem9 spending limit or "
            f"adjust billing settings: {action_url}. Include the link exactly as written."
        )
    if provider_action_code == "enableOnDemand":
        return (
            "Ask them to open this link to enable billing or on-demand usage for "
            f"mem9: {action_url}. Include the link exactly as written."
        )
    return (
        "Ask them to open this mem9 link to resolve the account or billing state: "
        f"{action_url}. Include the link exactly as written."
    )


def format_runtime_quota_notice(quota: dict[str, Any], operation: str) -> str:
    subject = _quota_notice_subject(quota, operation)
    return (
        f"{subject['headline']} because {_quota_reason(quota)}. "
        f"In your reply, briefly tell the user that {subject['user_state']}. "
        f"{_action_instruction(quota)}"
    )


def response_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def build_mem9_error_payload(response: requests.Response, operation: str = "mem9 request") -> dict[str, Any]:
    retry_after = getattr(response, "headers", {}).get("Retry-After")
    quota = parse_runtime_quota_denied(response_json(response), response.status_code, retry_after)
    if quota:
        user_message = format_runtime_quota_notice(quota, operation)
        payload: dict[str, Any] = {
            "ok": False,
            "error": quota["message"],
            "user_message": user_message,
            "status_code": response.status_code,
            "code": quota["code"],
            "quota": {
                "code": quota["code"],
                "message": quota["message"],
                "user_message": user_message,
            },
        }
        if quota.get("meter"):
            payload["quota"]["meter"] = quota["meter"]
        if quota.get("retryAfterSeconds"):
            payload["quota"]["retryAfterSeconds"] = quota["retryAfterSeconds"]
        action = quota.get("recommendedAction")
        if isinstance(action, dict):
            payload["quota"]["recommendedAction"] = action
            if action.get("url"):
                payload["action_url"] = action["url"]
        return payload

    return {
        "ok": False,
        "error": "mem9 request failed",
        "status_code": response.status_code,
        "detail": response.text[:500],
    }


def format_provider_error(response: requests.Response) -> str:
    retry_after = getattr(response, "headers", {}).get("Retry-After")
    quota = parse_runtime_quota_denied(response_json(response), response.status_code, retry_after)
    if quota:
        action = _as_dict(quota.get("recommendedAction"))
        action_url = str(action.get("url") or "").strip()
        suffix = f" Open this mem9 action URL to resolve it: {action_url}" if action_url else ""
        return (
            f"mem9 returned HTTP {response.status_code}: {quota['message']}. "
            f"Runtime quota denied for provider validation.{suffix}"
        )

    return f"mem9 returned HTTP {response.status_code}: {response.text[:200]}"
