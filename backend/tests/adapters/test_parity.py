"""registry の全ユースケースが REST と MCP の両方に存在することを検証する。"""

from typing import Any

from fastapi.testclient import TestClient

from jobtrail.adapters.mcp.descriptions import GUIDANCE
from jobtrail.config import get_settings
from jobtrail.main import create_app
from jobtrail.usecase.context import AppContext
from jobtrail.usecase.registry import USE_CASES

SPEC_TOOLS = """
register_company update_company delete_company restore_company find_companies get_company
save_company_source get_company_sources get_company_source update_company_source_summary
find_stale_company_sources
add_application update_application apply close_application reopen_application
find_applications get_application advance_stage record_stage_result reschedule_stage
update_stage_memo save_job_posting get_job_postings get_job_posting update_job_posting_summary
create_document add_document_version get_document list_documents attach_document_to_application
get_skill_profile update_skill_profile_basic
add_career update_career remove_career add_project update_project remove_project
add_skill update_skill remove_skill add_qualification update_qualification remove_qualification
import_skill_profile record_submission list_submissions get_submission
get_pipeline get_stats get_next_actions ping
""".split()

MCP_HEADERS = {"Accept": "application/json, text/event-stream"}


def unused_context() -> AppContext:
    def fail() -> Any:
        raise AssertionError("このテストは DB に触れない")

    return AppContext(uow_factory=fail, settings=get_settings())


def rest_operations() -> set[str]:
    schema = create_app(unused_context()).openapi()
    return {
        operation["operationId"] for path in schema["paths"].values() for operation in path.values()
    }


def mcp_tool_names() -> set[str]:
    with TestClient(create_app(unused_context()), base_url="http://localhost") as client:
        response = client.post(
            "/mcp",
            headers=MCP_HEADERS,
            json={"jsonrpc": "2.0", "id": 1, "method": "tools/list"},
        )
    assert response.status_code == 200, response.text
    return {tool["name"] for tool in response.json()["result"]["tools"]}


def test_every_use_case_is_exposed_on_rest_and_mcp() -> None:
    names = {use_case.name for use_case in USE_CASES}
    assert rest_operations() == names
    assert mcp_tool_names() == names


def test_every_tool_listed_in_the_spec_exists() -> None:
    assert {use_case.name for use_case in USE_CASES} == set(SPEC_TOOLS)


def test_no_physical_delete_or_interview_log_tools() -> None:
    names = {use_case.name for use_case in USE_CASES}
    assert not [name for name in names if "interview_log" in name or name.startswith("purge")]


def test_every_use_case_has_a_description() -> None:
    assert all(use_case.description for use_case in USE_CASES)


def test_guidance_only_refers_to_existing_tools() -> None:
    assert set(GUIDANCE) <= {use_case.name for use_case in USE_CASES}
