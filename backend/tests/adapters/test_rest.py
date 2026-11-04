from typing import Any

from fastapi.testclient import TestClient


def company(client: TestClient, name: str = "アクメ") -> dict[str, Any]:
    response = client.post("/api/companies", json={"name": name})
    assert response.status_code == 201, response.text
    body: dict[str, Any] = response.json()
    return body


def test_health(client: TestClient) -> None:
    assert client.get("/api/health").json()["status"] == "ok"


def test_error_body_carries_code_message_and_hint(client: TestClient) -> None:
    first = company(client)
    response = client.post("/api/companies", json={"name": "アクメ"})
    assert response.status_code == 409
    body = response.json()
    assert body["code"] == "DUPLICATE_COMPANY"
    assert body["hint"]
    assert body["details"]["existing_id"] == first["id"]


def test_not_found_is_404(client: TestClient) -> None:
    response = client.get("/api/companies/00000000-0000-0000-0000-000000000000")
    assert response.status_code == 404
    assert response.json()["code"] == "NOT_FOUND"


def test_validation_error_is_422_with_same_shape(client: TestClient) -> None:
    response = client.post("/api/companies", json={"name": ""})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"
    assert response.json()["details"]["errors"]


def test_model_validator_failure_is_422(client: TestClient) -> None:
    response = client.post("/api/applications", json={"position": "SWE"})
    assert response.status_code == 422
    assert response.json()["code"] == "VALIDATION_ERROR"


def test_too_large_is_413(client: TestClient) -> None:
    created = company(client)
    response = client.post(
        f"/api/companies/{created['id']}/sources",
        json={"source_type": "about", "url": "https://a.example", "raw_text": "あ" * 50_001},
    )
    assert response.status_code == 413
    assert response.json()["code"] == "CONTENT_TOO_LARGE"


def test_expected_version_is_required_on_rest(client: TestClient) -> None:
    created = company(client)
    url = f"/api/companies/{created['id']}"
    assert client.patch(url, json={"memo": "x"}).status_code == 422
    assert client.delete(url).status_code == 422


def test_stale_version_is_409(client: TestClient) -> None:
    created = company(client)
    url = f"/api/companies/{created['id']}"
    version = created["version"]
    updated = client.patch(url, json={"memo": "x", "expected_version": version})
    assert updated.status_code == 200
    assert updated.json()["version"] == version + 1
    stale = client.patch(url, json={"memo": "y", "expected_version": version})
    assert stale.status_code == 409
    assert stale.json()["code"] == "CONFLICT"
    assert stale.json()["details"]["current_version"] == version + 1


def test_partial_update_preserves_omitted_fields(client: TestClient) -> None:
    created = client.post("/api/companies", json={"name": "A", "url": "https://a.example"}).json()
    url = f"/api/companies/{created['id']}"
    response = client.patch(url, json={"memo": "x", "expected_version": created["version"]})
    assert response.json()["url"] == "https://a.example"


def test_delete_and_restore_over_rest(client: TestClient) -> None:
    created = company(client)
    url = f"/api/companies/{created['id']}"
    deleted = client.delete(url, params={"expected_version": created["version"]})
    assert deleted.json()["deleted_at"] is not None
    restored = client.post(f"{url}/restore", json={"expected_version": deleted.json()["version"]})
    assert restored.json()["deleted_at"] is None


def test_query_parameters_reach_the_use_case(client: TestClient) -> None:
    company(client, "アクメ")
    company(client, "ベータ")
    body = client.get("/api/companies", params={"query": "ベータ", "limit": 10}).json()
    assert body["total"] == 1
    assert body["limit"] == 10
    assert client.get("/api/companies", params={"limit": 201}).status_code == 422


def test_full_application_flow_over_rest(client: TestClient) -> None:
    created = client.post(
        "/api/applications", json={"new_company": {"name": "アクメ"}, "position": "SWE"}
    ).json()
    url = f"/api/applications/{created['id']}"
    version = created["version"]

    blocked = client.post(f"{url}/stages", json={"type": "document", "expected_version": version})
    assert blocked.status_code == 409
    assert blocked.json()["code"] == "NOT_APPLIED_YET"

    applied = client.post(
        f"{url}/apply",
        json={"applied_at": "2026-01-01T00:00:00+09:00", "expected_version": version},
    ).json()
    assert applied["status"] == "document"
    staged = client.post(
        f"{url}/stages", json={"type": "document", "expected_version": applied["version"]}
    )
    assert staged.status_code == 201
    stage_id = staged.json()["stages"][0]["id"]
    result = client.post(
        f"{url}/stages/{stage_id}/result",
        json={"result": "rejected", "expected_version": staged.json()["version"]},
    )
    assert result.json()["outcome"] == "rejected"
    assert client.get("/api/analytics/pipeline").json()["total"] == 1


def test_openapi_schema_is_generated(client: TestClient) -> None:
    schema = client.get("/api/openapi.json").json()
    operations = {
        operation["operationId"] for path in schema["paths"].values() for operation in path.values()
    }
    assert "advance_stage" in operations
    body = schema["paths"]["/api/companies/{company_id}"]["patch"]["requestBody"]
    reference = body["content"]["application/json"]["schema"]["$ref"].rsplit("/", 1)[-1]
    assert "expected_version" in schema["components"]["schemas"][reference]["required"]
