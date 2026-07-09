from pathlib import Path

from tools.mem9_headers import MEM9_PLUGIN_USER_AGENT, mem9_headers


def _manifest_version() -> str:
    manifest_path = Path(__file__).resolve().parents[1] / "manifest.yaml"
    for line in manifest_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("version:"):
            return line.split(":", 1)[1].strip().strip("'\"")
    raise AssertionError("manifest version missing")


def test_mem9_headers_include_plugin_user_agent():
    expected_user_agent = f"mem9-plugin/dify/{_manifest_version()}"

    assert MEM9_PLUGIN_USER_AGENT == expected_user_agent
    assert mem9_headers("key-1", "dify") == {
        "X-Mnemo-Agent-Id": "dify",
        "X-API-Key": "key-1",
        "User-Agent": expected_user_agent,
    }


def test_mem9_headers_can_include_json_content_type():
    headers = mem9_headers("key-1", "dify", content_type_json=True)

    assert headers["Content-Type"] == "application/json"
    assert headers["User-Agent"] == MEM9_PLUGIN_USER_AGENT
