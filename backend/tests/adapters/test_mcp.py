import json
from typing import Any

from fastapi.testclient import TestClient

HEADERS = {"Accept": "application/json, text/event-stream"}


def rpc(client: TestClient, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
    response = client.post(
        "/mcp",
        headers=HEADERS,
        json={"jsonrpc": "2.0", "id": 1, "method": method, "params": params or {}},
    )
    assert response.status_code == 200, response.text
    result: dict[str, Any] = response.json()["result"]
    return result


def call(client: TestClient, tool: str, /, **arguments: Any) -> tuple[bool, dict[str, Any]]:
    result = rpc(client, "tools/call", {"name": tool, "arguments": arguments})
    return result.get("isError", False), json.loads(result["content"][0]["text"])


def test_ping(client: TestClient) -> None:
    is_error, body = call(client, "ping")
    assert (is_error, body["status"]) == (False, "ok")


def test_tools_list_contains_guidance_and_schema(client: TestClient) -> None:
    tools = {tool["name"]: tool for tool in rpc(client, "tools/list")["tools"]}
    assert "find_companies" in tools["add_application"]["description"]
    assert "company_id" in tools["add_application"]["inputSchema"]["properties"]
    assert tools["get_stats"]["annotations"]["readOnlyHint"] is True


def test_domain_error_has_same_body_as_rest(client: TestClient) -> None:
    call(client, "register_company", name="アクメ")
    is_error, body = call(client, "register_company", name="アクメ")
    rest = client.post("/api/companies", json={"name": "アクメ"}).json()
    assert is_error is True
    assert body == rest


def test_expected_version_is_optional_on_mcp(client: TestClient) -> None:
    _, created = call(client, "register_company", name="アクメ")
    is_error, updated = call(client, "update_company", company_id=created["id"], memo="x")
    assert is_error is False
    assert updated["version"] == created["version"] + 1
    is_error, body = call(
        client,
        "update_company",
        company_id=created["id"],
        memo="y",
        expected_version=created["version"],
    )
    assert is_error is True
    assert body["code"] == "CONFLICT"


def test_validation_error_is_structured(client: TestClient) -> None:
    is_error, body = call(client, "register_company", nmae="typo")
    assert is_error is True
    assert body["code"] == "VALIDATION_ERROR"
    fields = {e["field"] for e in body["details"]["errors"]}
    assert {"name", "nmae"} <= fields


def test_unknown_tool_is_reported(client: TestClient) -> None:
    is_error, body = call(client, "does_not_exist")
    assert is_error is True
    assert body["code"] == "NOT_FOUND"


def test_data_written_over_mcp_is_visible_over_rest(client: TestClient) -> None:
    call(client, "add_application", new_company={"name": "アクメ"}, position="SWE")
    assert client.get("/api/applications").json()["items"][0]["company_name"] == "アクメ"
