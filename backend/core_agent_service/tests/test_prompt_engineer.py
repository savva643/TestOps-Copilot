"""Tests for PromptEngineer."""

import pytest
from app.services.prompt_engineer import PromptEngineer, PromptValidationError


def test_validate_prompt_inputs_success():
    """Test successful validation."""
    PromptEngineer.validate_prompt_inputs(
        description="This is a valid test case description with enough content",
        test_type="manual",
        feature="User Management",
        story="User Registration",
    )


def test_validate_prompt_inputs_empty_description():
    """Test validation fails on empty description."""
    with pytest.raises(PromptValidationError, match="cannot be empty"):
        PromptEngineer.validate_prompt_inputs(
            description="",
            test_type="manual",
        )


def test_validate_prompt_inputs_short_description():
    """Test validation fails on too short description."""
    with pytest.raises(PromptValidationError, match="too short"):
        PromptEngineer.validate_prompt_inputs(
            description="Short",
            test_type="manual",
        )


def test_validate_prompt_inputs_long_description():
    """Test validation fails on too long description."""
    long_desc = "a" * 10001
    with pytest.raises(PromptValidationError, match="too long"):
        PromptEngineer.validate_prompt_inputs(
            description=long_desc,
            test_type="manual",
        )


def test_validate_prompt_inputs_invalid_test_type():
    """Test validation fails on invalid test type."""
    with pytest.raises(PromptValidationError, match="Invalid test_type"):
        PromptEngineer.validate_prompt_inputs(
            description="Valid description with enough content",
            test_type="invalid_type",
        )


def test_get_test_case_generation_prompt_manual():
    """Test prompt generation for manual tests."""
    system_prompt, user_prompt = PromptEngineer.get_test_case_generation_prompt(
        description="Test user registration",
        test_type="manual",
        feature="User Management",
    )
    
    assert "manual" in system_prompt.lower()
    assert "Test user registration" in user_prompt
    assert "User Management" in user_prompt
    assert len(system_prompt) > 0
    assert len(user_prompt) > 0


def test_get_test_case_generation_prompt_api():
    """Test prompt generation for API tests."""
    system_prompt, user_prompt = PromptEngineer.get_test_case_generation_prompt(
        description="Test API endpoint /api/v1/users",
        test_type="api",
    )
    
    assert "api" in system_prompt.lower()
    assert "/api/v1/users" in user_prompt
    assert "AAA" in system_prompt or "Arrange-Act-Assert" in system_prompt


def test_get_test_case_generation_prompt_ui():
    """Test prompt generation for UI tests."""
    system_prompt, user_prompt = PromptEngineer.get_test_case_generation_prompt(
        description="Test login page",
        test_type="ui",
    )
    
    assert "ui" in system_prompt.lower() or "playwright" in system_prompt.lower()
    assert "login page" in user_prompt.lower()


def test_get_test_case_generation_prompt_validation_error():
    """Test that prompt generation validates inputs."""
    with pytest.raises(PromptValidationError):
        PromptEngineer.get_test_case_generation_prompt(
            description="",  # Empty description
            test_type="manual",
        )

