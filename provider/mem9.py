from typing import Any

import requests
from dify_plugin import ToolProvider
from dify_plugin.errors.tool import ToolProviderCredentialValidationError

from tools.mem9_errors import format_provider_error
from tools.mem9_headers import mem9_headers


class Mem9Provider(ToolProvider):
    def _validate_credentials(self, credentials: dict[str, Any]) -> None:
        # Default to single_space so a credential dict that somehow lacks
        # auth_mode (e.g. older saved state) still validates predictably.
        auth_mode = credentials.get("auth_mode") or "single_space"
        base_url = (credentials.get("mem9_base_url") or "https://api.mem9.ai").rstrip("/")

        if auth_mode == "multi_space":
            # Without an API Key here we cannot exercise an authenticated
            # endpoint, so just sanity-check the base URL.
            if not (base_url.startswith("http://") or base_url.startswith("https://")):
                raise ToolProviderCredentialValidationError(
                    "mem9 API Base URL must start with http:// or https://."
                )
            return

        api_key = credentials.get("mem9_api_key", "")
        if not api_key:
            raise ToolProviderCredentialValidationError(
                "mem9 API Key is required in Single space mode. "
                "Switch Authorization Mode to Multi-space to configure it per workflow node instead."
            )

        agent_id = credentials.get("mem9_agent_id", "") or "dify"

        url = f"{base_url}/v1alpha2/mem9s/memories"
        headers = mem9_headers(api_key, agent_id)

        try:
            resp = requests.get(url, headers=headers, params={"limit": "1"}, timeout=15)
            if resp.status_code >= 400:
                raise ToolProviderCredentialValidationError(format_provider_error(resp))
        except requests.RequestException as e:
            raise ToolProviderCredentialValidationError(
                f"Failed to connect to mem9: {e}"
            ) from e
