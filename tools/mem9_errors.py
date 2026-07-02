from typing import Any

import requests


QUOTA_CODES = {
    "quota_exhausted",
    "spending_limit_exceeded",
    "runtime_quota_denied",
}


def _as_dict(value: Any) -> dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _normalize_recommended_action(details: dict[str, Any]) -> dict[str, str] | None:
    nested = _as_dict(details.get("recommendedAction"))
    binding_state = str(nested.get("bindingState") or details.get("bindingState") or "").strip()
    action_type = str(nested.get("type") or details.get("upgradeAction") or "").strip()
    url = str(nested.get("url") or details.get("upgradeUrl") or "").strip()
    if not binding_state and not action_type and not url:
        return None

    action: dict[str, str] = {}
    if binding_state:
        action["bindingState"] = binding_state
    if action_type:
        action["type"] = action_type
    if url:
        action["url"] = url
    return action


def parse_runtime_quota_denied(payload: Any, status_code: int | None = None) -> dict[str, Any] | None:
    body = _as_dict(payload)
    if not body:
        return None

    details = _as_dict(body.get("details"))
    mem9_code = str(
        details.get("mem9Code") or details.get("mem9_code") or body.get("mem9_code") or ""
    ).strip()
    code = str(body.get("code") or "").strip()
    if mem9_code != "runtime_quota_denied" and code not in QUOTA_CODES:
        return None

    action = _normalize_recommended_action(details)
    result: dict[str, Any] = {
        "status_code": status_code,
        "code": code or "runtime_quota_denied",
        "message": str(body.get("message") or "runtime usage quota denied"),
        "meter": str(details.get("meter") or "").strip(),
    }
    if action:
        result["recommendedAction"] = action
    return result


def _quota_reason(quota: dict[str, Any]) -> str:
    action = _as_dict(quota.get("recommendedAction"))
    action_type = str(action.get("type") or "").strip()
    code = str(quota.get("code") or "").strip()
    if action_type == "claimApiKey":
        return "the included usage quota for this API key has been used up"
    if action_type == "increaseSpendingLimit" or code == "spending_limit_exceeded":
        return "the configured spending limit would be exceeded"
    if action_type == "enableOnDemand":
        return "the included usage quota has been used up and on-demand usage is not enabled"
    if action_type == "upgradePlan" or code == "quota_exhausted":
        return "the included usage quota for this mem9 account has been used up"
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


def _action_instruction(action: dict[str, Any] | None) -> str:
    action = _as_dict(action)
    action_type = str(action.get("type") or "").strip()
    action_url = str(action.get("url") or "").strip()
    if not action_url:
        return "Ask them to open the mem9 console to resolve the account or billing state."

    if action_type == "claimApiKey":
        return (
            "Ask them to open this link to sign in or create a mem9 account and "
            f"claim this API key: {action_url}. After claiming the key, they can "
            "upgrade their plan or set up billing to get more usage. Include the "
            "link exactly as written."
        )
    if action_type == "upgradePlan":
        return (
            "Ask them to open this link to upgrade their mem9 plan and get more "
            f"included usage: {action_url}. Include the link exactly as written."
        )
    if action_type == "increaseSpendingLimit":
        return (
            "Ask them to open this link to increase the mem9 spending limit or "
            f"adjust billing settings: {action_url}. Include the link exactly as written."
        )
    if action_type == "enableOnDemand":
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
        f"{_action_instruction(_as_dict(quota.get('recommendedAction')))}"
    )


def response_json(response: requests.Response) -> Any:
    try:
        return response.json()
    except ValueError:
        return None


def build_mem9_error_payload(response: requests.Response, operation: str = "mem9 request") -> dict[str, Any]:
    quota = parse_runtime_quota_denied(response_json(response), response.status_code)
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
    quota = parse_runtime_quota_denied(response_json(response), response.status_code)
    if quota:
        return f"mem9 returned HTTP {response.status_code}: {format_runtime_quota_notice(quota, 'search memories')}"

    return f"mem9 returned HTTP {response.status_code}: {response.text[:200]}"
