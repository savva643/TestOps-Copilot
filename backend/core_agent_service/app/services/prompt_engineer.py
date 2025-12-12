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
        
        valid_priorities = ["CRITICAL", "NORMAL", "LOW"]
        # priority валидируется в get_test_case_generation_prompt, но здесь тоже можно проверить

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
        priority: str = "NORMAL",
        owner: Optional[str] = None,
        jira_link: Optional[str] = None,
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
        
        # Validate priority
        valid_priorities = ["CRITICAL", "NORMAL", "LOW"]
        if priority not in valid_priorities:
            raise PromptValidationError(
                f"Invalid priority: {priority}. Must be one of {valid_priorities}"
            )

        # Optimized system prompts for different test types
        if test_type == "manual":
            system_prompt = """Ты — опытный QA-инженер по ручному тестированию. Твоя ЕДИНСТВЕННАЯ задача — вернуть готовый тест-кейс в формате Markdown.

КРИТИЧЕСКИ ВАЖНО:
- Твой ответ ДОЛЖЕН начинаться СРАЗУ с "# ТЕСТ-КЕЙС:" (без единого символа перед ним)
- ЗАПРЕЩЕНО писать: 'We need to...', 'We must...', 'Let's create...', 'I'll generate...', 'Here is...'
- ЗАПРЕЩЕНО писать планы действий или описания того, что ты собираешься сделать
- ЗАПРЕЩЕНО начинать ответ с английского текста
- Пиши ТОЛЬКО готовый тест-кейс в формате Markdown

СТРОГИЙ ФОРМАТ ОТВЕТА (начинай сразу с этого):

# ТЕСТ-КЕЙС: [Название сценария]

**ID:** TC-001
**Приоритет:** CRITICAL | NORMAL | LOW
**Feature:** [Название фичи, если указано]
**Story:** [Название истории, если указано]
**Владелец:** [owner из запроса]

## 1. ПРЕДУСЛОВИЯ
- [Список условий, которые должны быть выполнены перед тестом]

## 2. ТЕСТОВЫЕ ДАННЫЕ
- [Данные, которые будут использоваться в тесте]

## 3. ШАГИ ТЕСТИРОВАНИЯ (позитивный сценарий)

| № | Действие (ACT) | Ожидаемый результат (ASSERT) |
|---|----------------|------------------------------|
| 1 | [Действие] | [Ожидаемый результат] |
| 2 | [Действие] | [Ожидаемый результат] |

## 4. НЕГАТИВНЫЕ / ГРАНИЧНЫЕ СЦЕНАРИИ
- **ГС-1 (Граничный):** [Описание]. *Ожидаемо:* [Результат]
- **НС-1 (Негативный):** [Описание]. *Ожидаемо:* [Результат]

## 5. ПОСТУСЛОВИЯ
- [Действия для очистки после теста]

ТРЕБОВАНИЯ:
- Используй таблицу для шагов тестирования
- Каждый шаг должен иметь четкое действие и ожидаемый результат
- Включи негативные и граничные сценарии
- Всё на русском языке
- НИКАКИХ объяснений перед тест-кейсом. НИКАКИХ планов. ТОЛЬКО ГОТОВЫЙ ТЕСТ-КЕЙС."""

        elif test_type == "api":
            system_prompt = """Ты — генератор Python-кода тестов в формате Allure TestOps as Code. Твоя задача — вернуть готовый код.

СТРОГО ЗАПРЕЩЕНО:
- Писать текстовые пояснения типа "We need to produce...", "Let's create...", "I'll generate..."
- Писать планы действий или описания того, что ты собираешься сделать
- Начинать ответ с английского текста

ОБЯЗАТЕЛЬНО:
- Твой ответ ДОЛЖЕН начинаться СРАЗУ с ```python (без пробелов и текста перед ним)
- Внутри блока — полный готовый код на Python
- Закрой блок ```
- Если нужно несколько файлов — используй несколько блоков ```python ... ```
- Можешь добавлять пояснения МЕЖДУ блоками кода (перед следующим блоком ```python)

Формат ответа (СТРОГО):
```python
import pytest
import httpx
import allure
# ... код ...
```

Если нужно несколько файлов:
```python
# Первый файл
import pytest
# ... код первого файла ...
```

Пояснение ко второму файлу (если нужно).

```python
# Второй файл
import pytest
# ... код второго файла ...
```

Требования к коду (формат Allure TestOps as Code):
- pytest + httpx AsyncClient (фикстуры для клиента)
- ОБЯЗАТЕЛЬНЫЕ Allure декораторы в каждом тесте:
  * @allure.label("owner", owner) - owner из запроса
  * @allure.feature(feature) - feature из запроса (если указан)
  * @allure.story(story) - story из запроса (если указан)
  * @allure.suite("api") - всегда "api" для API тестов
  * @allure.tag(priority) - приоритет: "CRITICAL", "NORMAL" или "LOW" (НЕ severity!)
  * @allure.label("priority", priority) - дублирование приоритета в label
  * @allure.title("Название теста") - краткое название теста
  * @allure.link(jira_link, name="JIRA") - если есть jira_link
- Структура AAA (Arrange-Act-Assert) в каждом тесте с комментариями # Arrange, # Act, # Assert
- Проверка статус-кодов и полей ответа
- Позитивные и негативные сценарии (200, 400, 401, 403, 404)
- Авторизация через Bearer token в заголовке Authorization (если требуется)
- Все названия тестов, строки, комментарии — на русском языке
- Несколько тестов в одном файле — отдельные функции

ПРИМЕР ПРАВИЛЬНОГО ОТВЕТА:
```python
import pytest
import httpx
import allure

BASE_URL = "http://api.example.com"

@pytest.fixture
async def client():
    async with httpx.AsyncClient(base_url=BASE_URL) as ac:
        yield ac

@allure.label("owner", "qa-team")
@allure.feature("Example Feature")
@allure.story("Example Story")
@allure.suite("api")
@allure.tag("CRITICAL")
@allure.label("priority", "CRITICAL")
@allure.title("Успешный запрос")
@pytest.mark.asyncio
async def test_example_success(client):
    # Arrange - подготовка данных
    headers = {"Authorization": "Bearer valid-token"}
    payload = {"key": "value"}
    # Act - выполнение действия
    response = await client.post("/endpoint", json=payload, headers=headers)
    # Assert - проверка результата
    assert response.status_code == 200
    data = response.json()
    assert data.get("id") is not None
```"""

        else:  # UI
            system_prompt = """Ты — генератор Python-кода UI тестов в формате Allure TestOps as Code. Твоя ЕДИНСТВЕННАЯ задача — вернуть готовый код.

СТРОГО ЗАПРЕЩЕНО:
- Писать текстовые пояснения типа "We need to produce...", "Let's create...", "I'll generate..."
- Писать планы действий или описания того, что ты собираешься сделать
- Начинать ответ с английского текста

ОБЯЗАТЕЛЬНО:
- Твой ответ ДОЛЖЕН начинаться СРАЗУ с ```python (без пробелов и текста перед ним)
- Внутри блока — полный готовый код на Python
- Закрой блок ```
- Если нужно несколько файлов — используй несколько блоков ```python ... ```
- Можешь добавлять пояснения МЕЖДУ блоками кода (перед следующим блоком ```python)

Формат ответа (СТРОГО):
```python
import pytest
from playwright.sync_api import Page, expect
import allure
# ... код ...
```

Требования к коду (формат Allure TestOps as Code):
- pytest + Playwright для браузерной автоматизации
- ОБЯЗАТЕЛЬНЫЕ Allure декораторы в каждом тесте:
  * @allure.label("owner", owner) - owner из запроса
  * @allure.feature(feature) - feature из запроса (если указан)
  * @allure.story(story) - story из запроса (если указано)
  * @allure.suite("ui") - всегда "ui" для UI тестов
  * @allure.tag(priority) - приоритет: "CRITICAL", "NORMAL" или "LOW" (НЕ severity!)
  * @allure.label("priority", priority) - дублирование приоритета в label
  * @allure.title("Название теста") - краткое название теста
  * @allure.link(jira_link, name="JIRA") - если есть jira_link
- Используй классы для группировки тестов (class TestFeatureName)
- Используй фикстуры @pytest.fixture для setup/teardown
- Используй allure.step() для группировки шагов внутри теста
- Структура AAA (Arrange-Act-Assert) с комментариями # Arrange, # Act, # Assert
- Используй явные селекторы (id/data-testid), ожидания через expect()
- Делай скриншоты и вложения через allure.attach()
- Позитивные и негативные сценарии, граничные случаи
- Всё на русском (названия тестов, строки, комментарии, docstrings)

ПРИМЕР ПРАВИЛЬНОГО ОТВЕТА:
```python
import pytest
from playwright.sync_api import Page, expect
import allure

@allure.label("owner", "qa-team")
@allure.feature("Price Calculator")
@allure.story("Динамический расчет цены")
@allure.suite("ui")
@allure.tag("NORMAL")
@allure.label("priority", "NORMAL")

class TestPriceCalculatorDynamicPrice:
    
    @pytest.fixture(scope="function", autouse=True)
    def setup(self, page: Page):
        '''Предусловия: открыть калькулятор.'''
        page.goto("https://cloud.ru/calculator")
        expect(page.locator('[data-testid="calculator-title"]')).toBeVisible()
        yield
    
    @allure.title("Изменение vCPU должно пересчитывать цену")
    def test_change_vcpu_updates_price(self, page: Page):
        '''Позитивный сценарий: изменение vCPU динамически меняет цену.'''
        with allure.step("1. Добавить сервис Compute"):
            add_service_button = page.locator('[data-testid="btn-add-service"]')
            add_service_button.click()
            compute_card = page.locator('[data-testid="product-card-compute"]')
            compute_card.click()
        
        with allure.step("2. Изменить vCPU и проверить цену"):
            vcpu_slider = page.locator('[data-testid="slider-vcpu"]')
            initial_price = page.locator('[data-testid="total-price"]').text_content()
            vcpu_slider.fill("4")
            page.wait_for_timeout(500)
            new_price = page.locator('[data-testid="total-price"]').text_content()
            assert new_price != initial_price, f"Цена не изменилась"
        
        with allure.step("3. Прикрепить скриншот"):
            allure.attach(
                page.screenshot(),
                name="calculator_configuration",
                attachment_type=allure.attachment_type.PNG
            )
```

Примечание: Фикстура `page` предоставляется плагином pytest-playwright автоматически. Используй классы для группировки тестов и allure.step() для шагов."""

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

        if test_type in ["api", "ui"]:
            user_prompt_parts.append("\n\nСТРОГОЕ ТРЕБОВАНИЕ:")
            user_prompt_parts.append("Начни ответ СРАЗУ с ```python (без единого символа перед ним)")
            user_prompt_parts.append("НЕ пиши: 'We need to...', 'Let's create...', 'I'll generate...'")
            user_prompt_parts.append("НЕ пиши планы или описания перед первым блоком кода")
            user_prompt_parts.append("Если нужно несколько файлов — используй несколько блоков ```python ... ```")
            user_prompt_parts.append("Можешь добавлять пояснения МЕЖДУ блоками кода (перед следующим ```python)")
            
            user_prompt_parts.append("\nОБЯЗАТЕЛЬНЫЕ Allure декораторы для каждого теста:")
            if owner:
                user_prompt_parts.append(f"- @allure.label(\"owner\", \"{owner}\")")
            else:
                user_prompt_parts.append("- @allure.label(\"owner\", \"qa-team\")")
            if feature:
                user_prompt_parts.append(f"- @allure.feature(\"{feature}\")")
            if story:
                user_prompt_parts.append(f"- @allure.story(\"{story}\")")
            user_prompt_parts.append(f"- @allure.suite(\"{test_type}\")")
            user_prompt_parts.append(f"- @allure.tag(\"{priority}\")")
            user_prompt_parts.append(f"- @allure.label(\"priority\", \"{priority}\")")
            user_prompt_parts.append("- @allure.title(\"Название теста\")")
            if jira_link:
                user_prompt_parts.append(f"- @allure.link(\"{jira_link}\", name=\"JIRA\")")
            
            user_prompt_parts.append("\nТребования к коду:")
            user_prompt_parts.append("- Полный готовый код с импортами, фикстурами, тестами")
            user_prompt_parts.append("- Используй классы для группировки тестов (class TestFeatureName)")
            user_prompt_parts.append("- Используй фикстуры @pytest.fixture для setup/teardown")
            user_prompt_parts.append("- Используй allure.step() для группировки шагов внутри теста")
            user_prompt_parts.append("- Структура AAA в каждом тесте с комментариями # Arrange, # Act, # Assert")
            user_prompt_parts.append("- Делай скриншоты через allure.attach() для важных проверок")
            user_prompt_parts.append("- Позитивные и негативные сценарии")
            user_prompt_parts.append("- Все на русском языке (названия, комментарии, docstrings)")
        else:  # manual
            user_prompt_parts.append("\n\nСТРОГОЕ ТРЕБОВАНИЕ:")
            user_prompt_parts.append("Начни ответ СРАЗУ с \"# ТЕСТ-КЕЙС:\" (без единого символа перед ним)")
            user_prompt_parts.append("НЕ пиши: 'We need to...', 'Let's create...', 'I'll generate...', 'Here is...'")
            user_prompt_parts.append("НЕ пиши планы действий или описания того, что ты собираешься сделать")
            user_prompt_parts.append("НЕ пиши на английском языке перед тест-кейсом")
            user_prompt_parts.append("Пиши ТОЛЬКО готовый тест-кейс в формате Markdown")
            
            user_prompt_parts.append("\nВерни структурированный тест-кейс в формате Markdown:")
            user_prompt_parts.append("- Заголовок: # ТЕСТ-КЕЙС: [Название]")
            user_prompt_parts.append("- Метаданные: ID, Приоритет, Feature, Story, Владелец")
            user_prompt_parts.append("- Раздел 1: ПРЕДУСЛОВИЯ (список условий)")
            user_prompt_parts.append("- Раздел 2: ТЕСТОВЫЕ ДАННЫЕ (данные для теста)")
            user_prompt_parts.append("- Раздел 3: ШАГИ ТЕСТИРОВАНИЯ (таблица с колонками: №, Действие, Ожидаемый результат)")
            user_prompt_parts.append("- Раздел 4: НЕГАТИВНЫЕ / ГРАНИЧНЫЕ СЦЕНАРИИ (список с ГС-1, НС-1 и т.д.)")
            user_prompt_parts.append("- Раздел 5: ПОСТУСЛОВИЯ (действия для очистки)")
            if priority:
                user_prompt_parts.append(f"\nПриоритет теста: {priority}")
            if owner:
                user_prompt_parts.append(f"Владелец теста: {owner}")
            if feature:
                user_prompt_parts.append(f"Feature: {feature}")
            if story:
                user_prompt_parts.append(f"Story: {story}")

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




