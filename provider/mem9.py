from typing import Any

import requests
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError


class Mem9Provider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        base_url = (credentials.get("mem9_base_url") or "https://api.mem9.ai").rstrip("/")
        api_key = credentials.get("mem9_api_key", "")
        if not api_key:
            raise ToolProviderCredentialValidationError("mem9 API Key is required.")

        agent_id = credentials.get("mem9_agent_id", "") or "dify"

        url = f"{base_url}/v1alpha2/mem9s/memories"
        headers: dict[str, str] = {
            "X-Mnemo-Agent-Id": agent_id,
            "X-API-Key": api_key,
        }

        try:
            resp = requests.get(url, headers=headers, params={"limit": "1"}, timeout=15)
            if resp.status_code >= 400:
                body = resp.text[:200]
                raise ToolProviderCredentialValidationError(
                    f"mem9 returned HTTP {resp.status_code}: {body}"
                )
        except requests.RequestException as e:
            raise ToolProviderCredentialValidationError(
                f"Failed to connect to mem9: {e}"
            ) from e
