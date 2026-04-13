from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class MemoryStoreTool(Tool):
    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        base_url = (
            self.runtime.credentials.get("mem9_base_url") or "https://api.mem9.ai"
        ).rstrip("/")
        api_key = self.runtime.credentials.get("mem9_api_key", "")
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
                yield self.create_json_message(
                    {
                        "ok": False,
                        "error": "mem9 request failed",
                        "status_code": resp.status_code,
                        "detail": resp.text[:500],
                    }
                )
                return

            data = resp.json()
            yield self.create_json_message(
                {
                    "ok": True,
                    "status": data.get("status", "ok"),
                    "memories_changed": data.get("memories_changed", 0),
                    "insight_ids": data.get("insight_ids", []),
                    "session_id": session_id or None,
                }
            )
        except requests.RequestException as e:
            yield self.create_json_message(
                {"ok": False, "error": f"Failed to connect to mem9: {e}"}
            )
