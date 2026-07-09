MEM9_PLUGIN_USER_AGENT = "mem9-plugin/dify/0.0.4"


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
