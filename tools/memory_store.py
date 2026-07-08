from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage

from tools.mem9_errors import build_mem9_error_payload, fetch_runtime_state_notice


class MemoryStoreTool(Tool):
    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        base_url = (
            self.runtime.credentials.get("mem9_base_url") or "https://api.mem9.ai"
        ).rstrip("/")
        # Default single_space so any credential dict missing this field
        # still routes deterministically.
        auth_mode = self.runtime.credentials.get("auth_mode") or "single_space"
        if auth_mode == "multi_space":
            api_key = (tool_parameters.get("api_key") or "").strip()
            if not api_key:
                yield self.create_json_message(
                    {
                        "ok": False,
                        "error": (
                            "Multi-space mode requires the API Key on this "
                            "node. Configure it on the workflow node, or "
                            "switch the plugin to Single space mode."
                        ),
                    }
                )
                return
        else:
            api_key = self.runtime.credentials.get("mem9_api_key", "")
            if not api_key:
                yield self.create_json_message(
                    {
                        "ok": False,
                        "error": (
                            "Single space mode requires the API Key in "
                            "plugin authorization."
                        ),
                    }
                )
                return
        agent_id = self.runtime.credentials.get("mem9_agent_id", "") or "dify"

        content = tool_parameters.get("content", "").strip()
        if not content:
            yield self.create_json_message(
                {"ok": False, "error": "content is required"}
            )
            return

        session_id = tool_parameters.get("session_id", "")

        url = f"{base_url}/v1alpha2/mem9s/memories"
        headers: dict[str, str] = {
            "Content-Type": "application/json",
            "X-Mnemo-Agent-Id": agent_id,
            "X-API-Key": api_key,
        }
        runtime_state_notice = fetch_runtime_state_notice(base_url, api_key, agent_id)

        body: dict[str, Any] = {
            "messages": [{"role": "user", "content": content}],
            "agent_id": agent_id,
            "mode": "smart",
        }
        if session_id:
            body["session_id"] = session_id

        try:
            resp = requests.post(url, headers=headers, json=body, timeout=120)
            if resp.status_code >= 400:
                yield self.create_json_message(build_mem9_error_payload(resp, "store memory"))
                return

            data = resp.json()
            # Server contract: HTTP body emits only "ok" (sync) or "accepted" (async).
            # Revisit `is_async` if other statuses (failed/partial) ever appear here.
            status = data.get("status", "accepted")
            is_async = status != "ok"
            result: dict[str, Any] = {
                "ok": True,
                "status": status,
                "accepted": True,
                "searchable_now": not is_async,
                "session_id": session_id or None,
            }
            if runtime_state_notice:
                result["runtime_state_notice"] = runtime_state_notice
            if is_async:
                result["hint"] = (
                    "Stored asynchronously. Smart extraction is in progress "
                    "and this memory is not yet searchable. Do not call "
                    "memory_search for this content in the next turn."
                )
            yield self.create_json_message(result)
        except requests.RequestException as e:
            yield self.create_json_message(
                {"ok": False, "error": f"Failed to connect to mem9: {e}"}
            )
