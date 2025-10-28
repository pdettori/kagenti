import json

from lib import build_utils


def test_plain_value():
    content = "MCP_URL=http://weather-tool:8080/mcp\n"
    res = build_utils.parse_env_file(content)
    assert isinstance(res, list)
    assert res == [{"name": "MCP_URL", "value": "http://weather-tool:8080/mcp"}]


def test_valuefrom_json():
    content = (
        "SECRET_KEY="
        + "'"
        + json.dumps(
            {"valueFrom": {"secretKeyRef": {"name": "openai-secret", "key": "apikey"}}}
        )
        + "'\n"
    )
    res = build_utils.parse_env_file(content)
    assert len(res) == 1
    entry = res[0]
    assert "valueFrom" in entry
    assert entry["valueFrom"]["secretKeyRef"]["name"] == "openai-secret"


def test_shorthand_secretkeyref():
    content = (
        "SECRET_KEY="
        + "'"
        + json.dumps({"secretKeyRef": {"name": "openai-secret", "key": "apikey"}})
        + "'\n"
    )
    res = build_utils.parse_env_file(content)
    assert len(res) == 1
    entry = res[0]
    assert "valueFrom" in entry
    assert entry["valueFrom"]["secretKeyRef"]["key"] == "apikey"


def test_invalid_json_kept_as_string():
    # missing closing brace
    content = (
        "API_KEY="
        + "'"
        + '{"valueFrom": {"secretKeyRef": {"name": "foo", "key": "bar"}}'
        + "'\n"
    )
    res = build_utils.parse_env_file(content)
    assert len(res) == 1
    entry = res[0]
    assert "value" in entry
    assert entry["value"].startswith('{"valueFrom')
