from pathlib import Path


def _read_plugin_version() -> str:
    manifest_path = Path(__file__).resolve().parents[1] / "manifest.yaml"
    try:
        for line in manifest_path.read_text(encoding="utf-8").splitlines():
            if line.startswith("version:"):
                return line.split(":", 1)[1].strip().strip("'\"") or "unknown"
    except OSError:
        return "unknown"
    return "unknown"


MEM9_PLUGIN_USER_AGENT = f"mem9-plugin/dify/{_read_plugin_version()}"


def mem9_headers(
    api_key: str,
    agent_id: str,
    *,
    content_type_json: bool = False,
) -> dict[str, str]:
    headers = {
        "X-Mnemo-Agent-Id": agent_id,
        "X-API-Key": api_key,
        "User-Agent": MEM9_PLUGIN_USER_AGENT,
    }
    if content_type_json:
        headers["Content-Type"] = "application/json"
    return headers
