from collections.abc import Generator
from typing import Any

import requests
from dify_plugin import Tool
from dify_plugin.entities.tool import ToolInvokeMessage


class MemorySearchTool(Tool):
    def _invoke(
        self, tool_parameters: dict[str, Any]
    ) -> Generator[ToolInvokeMessage, None, None]:
        base_url = (
            self.runtime.credentials.get("mem9_base_url") or "https://api.mem9.ai"
        ).rstrip("/")
        api_key = self.runtime.credentials.get("mem9_api_key", "")
        agent_id = self.runtime.credentials.get("mem9_agent_id", "") or "dify"

        query = tool_parameters.get("query", "").strip()
        if not query:
            yield self.create_json_message(
                {"ok": False, "error": "query is required", "memories": [], "total": 0}
            )
            return

        session_id = tool_parameters.get("session_id", "")
        try:
            limit = int(tool_parameters.get("limit", 10))
        except (TypeError, ValueError):
            limit = 10

        url = f"{base_url}/v1alpha2/mem9s/memories"
        headers: dict[str, str] = {
            "X-Mnemo-Agent-Id": agent_id,
            "X-API-Key": api_key,
        }

        params: dict[str, str] = {"q": query, "limit": str(limit)}
        if session_id:
            params["session_id"] = session_id

        try:
            resp = requests.get(url, headers=headers, params=params, timeout=30)
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
            raw_memories = data.get("memories", [])

            if not raw_memories:
                yield self.create_json_message(
                    {"ok": True, "memories": [], "total": 0, "session_id": session_id or None}
                )
                return

            memories: list[dict[str, Any]] = []
            for m in raw_memories:
                entry: dict[str, Any] = {"content": m.get("content", "").strip()}
                score = m.get("score")
                if score is not None:
                    try:
                        entry["score"] = float(score)
                    except (TypeError, ValueError):
                        entry["score"] = score
                if m.get("memory_type"):
                    entry["memory_type"] = m["memory_type"]
                if m.get("relative_age"):
                    entry["relative_age"] = m["relative_age"]
                memories.append(entry)

            yield self.create_json_message(
                {"ok": True, "memories": memories, "total": len(memories), "session_id": session_id or None}
            )
        except requests.RequestException as e:
            yield self.create_json_message(
                {"ok": False, "error": f"Failed to connect to mem9: {e}", "memories": [], "total": 0}
            )
