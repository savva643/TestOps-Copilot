import pytest

from app.services.template_engine import TemplateEngine
from app.services.code_validator import validate_allure_contract


@pytest.mark.asyncio
@pytest.mark.parametrize("test_type", ["manual", "api", "ui", "contract"])
async def test_templates_have_no_validation_issues(test_type: str):
    engine = TemplateEngine()
    for strict in (False, True):
        code = await engine.generate(
            test_case="Sample test case steps",
            test_type=test_type,
            feature="Feature",
            story="Story",
            priority="NORMAL",
            owner="QA",
            jira_link="https://jira.example.com/TEST-1",
            specification={"endpoint": "/api/v1/sample"},
            strict=strict,
        )
        formatted = await engine.format_code(code)
        issues = validate_allure_contract(formatted or code)
        assert issues == []

