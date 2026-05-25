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
                        "memories": [],
                        "total": 0,
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
                        "memories": [],
                        "total": 0,
                    }
                )
                return
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
        limit = max(1, min(limit, 20))
        upstream_limit = min(max(limit * 3, limit), 100)

        url = f"{base_url}/v1alpha2/mem9s/memories"
        headers: dict[str, str] = {
            "X-Mnemo-Agent-Id": agent_id,
            "X-API-Key": api_key,
        }

        params: dict[str, str] = {"q": query, "limit": str(upstream_limit)}
        if session_id:
            params["session_id"] = session_id
        if is_truthy(tool_parameters.get("scanAll")):
            params["scanAll"] = "true"

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
            session_scoped = bool(session_id)

            base_result: dict[str, Any] = {
                "ok": True,
                "effective_query": query,
                "session_scoped": session_scoped,
                "available_result_count": len(raw_memories),
                "session_id": session_id or None,
            }

            if not raw_memories:
                base_result["memories"] = []
                base_result["total"] = 0
                base_result["retry_hint"] = (
                    "No memories matched. Possible fixes: "
                    "(1) rephrase as a short declarative statement instead of a question "
                    "(e.g. 'user prefers Python' rather than 'what language does the user like?'); "
                    "(2) try broader or different keywords."
                )
                yield self.create_json_message(base_result)
                return

            raw_memories = sorted(
                raw_memories,
                key=lambda memory: (
                    numeric_value(memory.get("confidence")),
                    numeric_value(memory.get("score")),
                ),
                reverse=True,
            )

            memories: list[dict[str, Any]] = []
            max_score: float | None = None
            for m in raw_memories[:limit]:
                entry: dict[str, Any] = {"content": m.get("content", "").strip()}
                confidence = m.get("confidence")
                if confidence is not None:
                    try:
                        entry["confidence"] = int(confidence)
                    except (TypeError, ValueError):
                        entry["confidence"] = confidence
                score = m.get("score")
                if score is not None:
                    try:
                        score_f = float(score)
                        entry["score"] = score_f
                        if max_score is None or score_f > max_score:
                            max_score = score_f
                    except (TypeError, ValueError):
                        entry["score"] = score
                if m.get("memory_type"):
                    entry["memory_type"] = m["memory_type"]
                if m.get("relative_age"):
                    entry["relative_age"] = m["relative_age"]
                memories.append(entry)

            base_result["memories"] = memories
            base_result["result_count"] = len(memories)
            base_result["total"] = len(memories)

            # All matches below 0.3 likely means the query phrasing doesn't
            # align with how facts were stored; nudge FC model to rephrase.
            if max_score is not None and max_score < 0.3:
                base_result["retry_hint"] = (
                    "All matches have low confidence. The query may not align "
                    "with how facts were stored. Consider rephrasing as a "
                    "declarative statement or using more specific keywords."
                )

            yield self.create_json_message(base_result)
        except requests.RequestException as e:
            yield self.create_json_message(
                {"ok": False, "error": f"Failed to connect to mem9: {e}", "memories": [], "total": 0}
            )


def is_truthy(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        return value.strip().lower() in {"1", "true", "yes", "on"}
    return False


def numeric_value(value: Any) -> float:
    try:
        return float(value)
    except (TypeError, ValueError):
        return -1.0
