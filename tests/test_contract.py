from __future__ import annotations

import sys
import types
from types import SimpleNamespace
from unittest.mock import patch


def install_dify_stubs() -> type[Exception]:
    dify_plugin = types.ModuleType("dify_plugin")
    entities = types.ModuleType("dify_plugin.entities")
    tool_entities = types.ModuleType("dify_plugin.entities.tool")
    errors = types.ModuleType("dify_plugin.errors")
    tool_errors = types.ModuleType("dify_plugin.errors.tool")

    class ToolInvokeMessage(dict):
        pass

    class Tool:
        def create_json_message(self, payload):
            return payload

    class ToolProvider:
        pass

    class ToolProviderCredentialValidationError(Exception):
        pass

    dify_plugin.Tool = Tool
    dify_plugin.ToolProvider = ToolProvider
    tool_entities.ToolInvokeMessage = ToolInvokeMessage
    tool_errors.ToolProviderCredentialValidationError = ToolProviderCredentialValidationError
    sys.modules["dify_plugin"] = dify_plugin
    sys.modules["dify_plugin.entities"] = entities
    sys.modules["dify_plugin.entities.tool"] = tool_entities
    sys.modules["dify_plugin.errors"] = errors
    sys.modules["dify_plugin.errors.tool"] = tool_errors
    return ToolProviderCredentialValidationError


CredentialError = install_dify_stubs()

from provider.mem9 import Mem9Provider  # noqa: E402
from tools.memory_search import MemorySearchTool  # noqa: E402
from tools.memory_store import MemoryStoreTool  # noqa: E402


class Response:
    def __init__(self, status_code=200, payload=None, text=""):
        self.status_code = status_code
        self._payload = payload or {}
        self.text = text

    def json(self):
        return self._payload


def invoke(tool, credentials, params):
    tool.runtime = SimpleNamespace(credentials=credentials)
    return list(tool._invoke(params))[0]


def test_provider_validates_single_space_credentials():
    credentials = {
        "auth_mode": "single_space",
        "mem9_base_url": "https://mem9.test",
        "mem9_api_key": "tenant-1",
        "mem9_agent_id": "compat-dify",
    }

    with patch("provider.mem9.requests.get", return_value=Response(payload={"memories": [], "total": 0})) as get:
        Mem9Provider()._validate_credentials(credentials)

    assert get.call_args.kwargs["headers"]["X-API-Key"] == "tenant-1"
    assert get.call_args.kwargs["headers"]["X-Mnemo-Agent-Id"] == "compat-dify"
    assert get.call_args.kwargs["params"] == {"limit": "1"}


def test_provider_requires_single_space_api_key():
    credentials = {
        "auth_mode": "single_space",
        "mem9_base_url": "https://mem9.test",
    }

    try:
        Mem9Provider()._validate_credentials(credentials)
    except CredentialError as exc:
        assert "API Key is required" in str(exc)
    else:
        raise AssertionError("expected credential validation failure")


def test_multi_space_search_requires_node_api_key():
    result = invoke(
        MemorySearchTool(),
        {"auth_mode": "multi_space", "mem9_base_url": "https://mem9.test"},
        {"query": "project convention"},
    )

    assert result["ok"] is False
    assert "Multi-space mode requires the API Key" in result["error"]
    assert result["memories"] == []


def test_search_sends_expected_headers_and_params():
    credentials = {
        "auth_mode": "single_space",
        "mem9_base_url": "https://mem9.test",
        "mem9_api_key": "tenant-1",
        "mem9_agent_id": "compat-dify",
    }

    with patch(
        "tools.memory_search.requests.get",
        return_value=Response(
            payload={
                "memories": [
                    {
                        "content": "fact",
                        "confidence": 90,
                        "score": 0.8,
                        "relative_age": "2h ago",
                    },
                ],
                "total": 1,
            },
        ),
    ) as get:
        result = invoke(
            MemorySearchTool(),
            credentials,
            {
                "query": "fact",
                "limit": 2,
                "session_id": "session-1",
                "scanAll": "true",
            },
        )

    assert result["ok"] is True
    assert result["memories"][0]["content"] == "fact"
    kwargs = get.call_args.kwargs
    assert kwargs["headers"]["X-API-Key"] == "tenant-1"
    assert kwargs["headers"]["X-Mnemo-Agent-Id"] == "compat-dify"
    assert kwargs["params"]["q"] == "fact"
    assert kwargs["params"]["limit"] == "6"
    assert kwargs["params"]["session_id"] == "session-1"
    assert kwargs["params"]["scanAll"] == "true"


def test_store_sends_smart_messages_body():
    credentials = {
        "auth_mode": "single_space",
        "mem9_base_url": "https://mem9.test",
        "mem9_api_key": "tenant-1",
        "mem9_agent_id": "compat-dify",
    }

    with patch("tools.memory_store.requests.post", return_value=Response(payload={"status": "accepted"})) as post:
        result = invoke(
            MemoryStoreTool(),
            credentials,
            {"content": "remember this", "session_id": "session-2"},
        )

    assert result["ok"] is True
    assert result["accepted"] is True
    assert result["session_id"] == "session-2"
    kwargs = post.call_args.kwargs
    assert kwargs["headers"]["X-API-Key"] == "tenant-1"
    assert kwargs["headers"]["X-Mnemo-Agent-Id"] == "compat-dify"
    assert kwargs["json"]["messages"] == [{"role": "user", "content": "remember this"}]
    assert kwargs["json"]["agent_id"] == "compat-dify"
    assert kwargs["json"]["mode"] == "smart"
    assert kwargs["json"]["session_id"] == "session-2"
