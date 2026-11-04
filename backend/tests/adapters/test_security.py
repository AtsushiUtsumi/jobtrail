import pytest
from fastapi.testclient import TestClient

HEADERS = {"Accept": "application/json, text/event-stream"}
BODY = {"jsonrpc": "2.0", "id": 1, "method": "tools/list"}


@pytest.mark.parametrize("host", ["localhost", "localhost:8080", "127.0.0.1", "127.0.0.1:80"])
def test_local_hosts_are_allowed(client: TestClient, host: str) -> None:
    assert client.get("/api/health", headers={"Host": host}).status_code == 200


@pytest.mark.parametrize("host", ["evil.example", "evil.example:80", "localhost.evil.example", ""])
def test_other_hosts_are_rejected(client: TestClient, host: str) -> None:
    response = client.get("/api/health", headers={"Host": host})
    assert response.status_code == 403
    assert response.json()["code"] == "FORBIDDEN_HOST"


@pytest.mark.parametrize("origin", ["http://localhost", "http://127.0.0.1:8080"])
def test_local_origins_are_allowed_on_mcp(client: TestClient, origin: str) -> None:
    response = client.post("/mcp", headers={**HEADERS, "Origin": origin}, json=BODY)
    assert response.status_code == 200


@pytest.mark.parametrize(
    "origin", ["https://evil.example", "null", "http://localhost.evil.example"]
)
def test_other_origins_are_rejected_on_mcp(client: TestClient, origin: str) -> None:
    response = client.post("/mcp", headers={**HEADERS, "Origin": origin}, json=BODY)
    assert response.status_code == 403


def test_missing_origin_is_allowed_for_native_clients(client: TestClient) -> None:
    assert client.post("/mcp", headers=HEADERS, json=BODY).status_code == 200
