"""Prompt engineering service for constructing LLM prompts."""

from typing import Optional, Dict, Any
import structlog
import re

from app.core.exceptions import PromptValidationError

logger = structlog.get_logger()


class PromptEngineer:
    """Service for constructing prompts for LLM."""

    @staticmethod
    def validate_prompt_inputs(
        description: str,
        test_type: str,
        feature: Optional[str] = None,
        story: Optional[str] = None,
    ) -> None:
        """
        Validate prompt inputs.

        Args:
            description: Test case description
            test_type: Type of test
            feature: Feature name (optional)
            story: Story name (optional)

        Raises:
            PromptValidationError: If validation fails
        """
        if not description or not description.strip():
            raise PromptValidationError("Description cannot be empty")

        if len(description) < 10:
            raise PromptValidationError("Description is too short (minimum 10 characters)")

        if len(description) > 10000:
            raise PromptValidationError("Description is too long (maximum 10000 characters)")

        valid_test_types = ["manual", "api", "ui"]
        if test_type not in valid_test_types:
            raise PromptValidationError(
                f"Invalid test_type: {test_type}. Must be one of {valid_test_types}"
            )

        if feature and len(feature) > 200:
            raise PromptValidationError("Feature name is too long (maximum 200 characters)")

        if story and len(story) > 200:
            raise PromptValidationError("Story name is too long (maximum 200 characters)")

    @staticmethod
    def get_test_case_generation_prompt(
        description: str,
        test_type: str = "manual",
        feature: Optional[str] = None,
        story: Optional[str] = None,
    ) -> tuple[str, str]:
        """
        Generate system and user prompts for test case generation.

        Returns:
            Tuple of (system_prompt, user_prompt)

        Raises:
            PromptValidationError: If inputs are invalid
        """
        # Validate inputs
        PromptEngineer.validate_prompt_inputs(description, test_type, feature, story)

        # Optimized system prompts for different test types
        if test_type == "manual":
            system_prompt = """You are an expert QA engineer specializing in creating comprehensive manual test cases.

Your task is to generate well-structured, detailed manual test cases based on requirements.

Requirements:
1. Break down the requirement into clear, numbered test steps
2. Each step should be specific and actionable
3. Identify required test data for each step
4. Specify expected results clearly
5. Consider positive, negative, and edge case scenarios
6. Include preconditions and postconditions
7. Format output as structured text that can be easily converted to Allure TestOps format

Output format:
- Test Case Title: [Clear, descriptive title]
- Preconditions: [What needs to be set up]
- Test Steps:
  1. [Step description]
     Expected: [Expected result]
  2. [Step description]
     Expected: [Expected result]
- Test Data: [Required data]
- Postconditions: [Cleanup if needed]"""

        elif test_type == "api":
            system_prompt = """You are an expert QA engineer specializing in API testing.

Your task is to generate comprehensive API test cases following best practices.

Requirements:
1. Follow AAA pattern (Arrange-Act-Assert) structure
2. Include endpoint URL, HTTP method, and request details
3. Specify request headers, body, and parameters
4. Define expected response status codes
5. Validate response schema and data
6. Include error handling scenarios
7. Consider authentication requirements
8. Format for pytest + httpx with Allure annotations

Output format:
- Test Case Title: [API endpoint test]
- Endpoint: [HTTP method] [URL]
- Request: [Headers, body, parameters]
- Expected Response: [Status code, schema]
- Test Steps: [Arrange, Act, Assert breakdown]"""

        else:  # UI
            system_prompt = """You are an expert QA engineer specializing in UI/E2E testing.

Your task is to generate comprehensive UI test cases for web applications.

Requirements:
1. Follow AAA pattern (Arrange-Act-Assert)
2. Include page navigation and element interactions
3. Specify UI elements with selectors (ID, class, data attributes)
4. Include wait conditions and timeouts
5. Consider different screen sizes and browsers
6. Include screenshot capture points
7. Format for pytest + Playwright with Allure annotations

Output format:
- Test Case Title: [UI test scenario]
- Page/URL: [Starting page]
- Test Steps:
  1. Navigate to [page]
  2. Click on [element]
  3. Fill [field] with [value]
  4. Verify [expected state]
- Screenshots: [When to capture]"""

        # Clean and optimize description
        description = description.strip()
        
        # Build optimized user prompt
        user_prompt_parts = [
            f"Generate a comprehensive {test_type} test case based on the following requirements:",
            "",
            description,
        ]

        if feature:
            user_prompt_parts.append(f"\nFeature: {feature}")
        if story:
            user_prompt_parts.append(f"Story: {story}")

        user_prompt_parts.append(
            "\n\nProvide a detailed, well-structured test case with:"
        )
        user_prompt_parts.append("- Clear, numbered test steps")
        user_prompt_parts.append("- Required test data")
        user_prompt_parts.append("- Expected results for each step")
        user_prompt_parts.append("- Edge cases and error scenarios")

        user_prompt = "\n".join(user_prompt_parts)

        logger.info(
            "Generated prompt",
            test_type=test_type,
            description_length=len(description),
            has_feature=bool(feature),
            has_story=bool(story),
        )

        return system_prompt, user_prompt

    @staticmethod
    def get_code_generation_prompt(
        test_case: str,
        specification: Optional[Dict[str, Any]] = None,
        test_type: str = "api",
    ) -> tuple[str, str]:
        """
        Generate system and user prompts for code generation.

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system_prompt = """You are an expert Python developer specializing in writing automated tests.
Your task is to generate Python test code following best practices:

1. Use pytest framework
2. Follow AAA pattern (Arrange-Act-Assert)
3. Include Allure annotations:
   - @allure.feature()
   - @allure.story()
   - @allure.title()
   - @allure.label("owner", ...)
   - @allure.label("priority", ...)
   - @allure.tag(...)
4. Use proper type hints
5. Include docstrings
6. Handle errors appropriately

For API tests:
- Use httpx or requests for HTTP calls
- Validate response status codes
- Validate response schemas

For UI tests:
- Use Playwright for browser automation
- Include page object pattern where appropriate
- Take screenshots on failures"""

        user_prompt = f"""Generate Python test code for the following {test_type} test case:

{test_case}
"""

        if specification:
            user_prompt += f"\n\nAPI Specification:\n{specification}"

        user_prompt += "\n\nGenerate complete, runnable Python test code with all necessary imports and setup."

        return system_prompt, user_prompt

    @staticmethod
    def get_code_analysis_prompt(code: str) -> tuple[str, str]:
        """
        Generate system and user prompts for code analysis.

        Returns:
            Tuple of (system_prompt, user_prompt)
        """
        system_prompt = """You are a code quality expert specializing in test code analysis.
Analyze the provided test code and check for:
1. Compliance with AAA pattern (Arrange-Act-Assert)
2. Proper Allure annotations
3. Code quality and best practices
4. Potential issues or improvements
5. Test coverage completeness

Provide a structured analysis with specific recommendations."""

        user_prompt = f"""Analyze the following test code:

```python
{code}
```

Provide a detailed analysis with recommendations for improvement."""

        return system_prompt, user_prompt




