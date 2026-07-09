from tools.mem9_headers import mem9_headers


def test_mem9_headers_include_plugin_user_agent():
    assert mem9_headers("key-1", "dify") == {
        "X-Mnemo-Agent-Id": "dify",
        "X-API-Key": "key-1",
        "User-Agent": "mem9-plugin/dify/0.0.4",
    }


def test_mem9_headers_can_include_json_content_type():
    headers = mem9_headers("key-1", "dify", content_type_json=True)

    assert headers["Content-Type"] == "application/json"
    assert headers["User-Agent"] == "mem9-plugin/dify/0.0.4"
