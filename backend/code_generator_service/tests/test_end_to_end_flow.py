import pytest

from app.services.template_engine import TemplateEngine
from app.services.code_validator import validate_allure_contract
from app.services.test_standard_validator import validate_test_standard


@pytest.mark.asyncio
async def test_end_to_end_api_strict_flow():
    """
    Simulates spec -> generation -> validation flow for API strict template.
    """
    spec = {
        "base_url": "https://api.example.com",
        "endpoint": "/api/v1/resource",
        "expected_status": 200,
        "payload": {"id": 1},
    }

    engine = TemplateEngine()
    code = await engine.generate(
        test_case="Validate API contract for /api/v1/resource",
        test_type="api",
        feature="Compute",
        story="Resource CRUD",
        priority="NORMAL",
        owner="QA Team",
        jira_link="https://jira.example.com/API-1",
        specification=spec,
        strict=True,
    )
    formatted = await engine.format_code(code)

    val_issues = validate_allure_contract(formatted or code)
    std_issues = validate_test_standard(formatted or code)

    assert val_issues == []
    assert std_issues == []

