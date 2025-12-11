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
            system_prompt = """Ты — опытный QA-инженер по ручному тестированию.

Требования к ответу (только текст, без кода, без Markdown-разметки):
- Один или несколько тест-кейсов с чёткими заголовками.
- Предусловия / подготовка данных.
- Нумерованные шаги (каждый шаг + ожидаемый результат).
- Тестовые данные для шагов.
- Позитивные, негативные и граничные сценарии.
- Постусловия/очистка, если нужна.
- Всё на русском, без лишних пояснений."""

        elif test_type == "api":
            system_prompt = """Ты — опытный QA-инженер по API. Генерируй Python-код тестов с пояснениями.

Требования к ответу:
- Код на Python оборачивай в markdown блоки ```python ... ```.
- Можешь добавлять пояснения перед/между блоками кода на русском языке.
- Если генерируешь несколько тестов, можешь разделить их на блоки с пояснениями.
- pytest + httpx (асинхронный клиент/фикстуры), Allure аннотации (@allure.feature, @allure.story, @allure.title, @allure.severity, @allure.label("owner", ...)).
- Строгая структура AAA (Arrange-Act-Assert) в каждом тесте.
- Проверяй статус-код и ключевые поля тела ответа.
- Добавляй позитивные и негативные сценарии: валидный запрос, невалидные данные (400), отсутствующий ресурс (404), нет/невалидный токен (401/403).
- Авторизация: Bearer <token> в заголовке Authorization, если требуется.
- Все названия, строки и комментарии — на русском языке.
- Объедини несколько тестов в одном файле, тесты — отдельные функции."""

        else:  # UI
            system_prompt = """Ты — опытный QA-инженер по UI/E2E. Генерируй Python-код тестов с пояснениями.

Требования к ответу:
- Код на Python оборачивай в markdown блоки ```python ... ```.
- Можешь добавлять пояснения перед/между блоками кода на русском языке.
- Если генерируешь несколько тестов, можешь разделить их на блоки с пояснениями.
- pytest + Playwright, аннотации Allure (@allure.feature, @allure.story, @allure.title, @allure.severity, @allure.label("owner", ...)).
- Строгая структура AAA в тестах.
- Используй явные селекторы (id/data-testid), ожидания, скриншот при ошибке по необходимости.
- Позитивные и негативные сценарии, граничные случаи.
- Всё на русском (названия тестов, строки, аннотации)."""

        # Clean and optimize description
        description = description.strip()
        
        # Build optimized user prompt
        user_prompt_parts = [
            f"Сгенерируй подробные {test_type} тесты на основе требований ниже.",
            "",
            description,
        ]

        if feature:
            user_prompt_parts.append(f"\nFeature: {feature}")
        if story:
            user_prompt_parts.append(f"Story: {story}")

        user_prompt_parts.append(
            "\n\nВерни результат с учетом:"
        )
        if test_type in ["api", "ui"]:
            user_prompt_parts.append("- Код на Python оборачивай в markdown блоки ```python ... ```")
            user_prompt_parts.append("- Можешь добавлять пояснения перед/между блоками кода")
            user_prompt_parts.append("- Если генерируешь несколько тестов, можешь разделить их на блоки с пояснениями")
        else:
            user_prompt_parts.append("- Структурированный текст кейсов")
        user_prompt_parts.append("- Нумерованные шаги (AAA в коде или шагах)")
        user_prompt_parts.append("- Необходимые тестовые данные")
        user_prompt_parts.append("- Ожидаемые результаты и проверки")
        user_prompt_parts.append("- Отдельные негативные сценарии и граничные случаи")

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




