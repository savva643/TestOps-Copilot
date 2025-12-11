# Формат UI тестов

## Обзор

UI тесты генерируются в формате **Allure TestOps as Code** с использованием:
- **pytest** - фреймворк для тестирования
- **Playwright** - библиотека для автоматизации браузера
- **Allure** - декораторы для метаданных тестов

## Структура UI теста

### Базовый формат

```python
import pytest
from playwright.sync_api import Page, expect
import allure

@allure.label("owner", "qa-team")
@allure.feature("Название фичи")
@allure.story("Название истории")
@allure.suite("ui")
@allure.tag("NORMAL")
@allure.label("priority", "NORMAL")
@allure.title("Название теста")
def test_example(page: Page):
    # Arrange - подготовка
    page.goto("https://example.com")
    
    # Act - выполнение действия
    button = page.locator('[data-testid="submit-button"]')
    button.click()
    
    # Assert - проверка результата
    expect(page).toHaveURL("https://example.com/success")
```

## Обязательные Allure декораторы

Каждый UI тест должен содержать:

1. **@allure.label("owner", owner)** - владелец теста
2. **@allure.feature(feature)** - название фичи (если указано)
3. **@allure.story(story)** - название истории (если указано)
4. **@allure.suite("ui")** - всегда "ui" для UI тестов
5. **@allure.tag(priority)** - приоритет: "CRITICAL", "NORMAL" или "LOW"
6. **@allure.label("priority", priority)** - дублирование приоритета
7. **@allure.title("Название теста")** - краткое название теста
8. **@allure.link(jira_link, name="JIRA")** - ссылка на JIRA (если есть)

## Структура AAA (Arrange-Act-Assert)

Каждый тест должен следовать паттерну AAA:

```python
def test_example(page: Page):
    # Arrange - подготовка данных и окружения
    page.goto("https://example.com/calculator")
    
    # Act - выполнение действия
    vcpu_slider = page.locator('[data-testid="vcpu-slider"]')
    vcpu_slider.fill("16")
    
    # Assert - проверка результата
    price = page.locator('[data-testid="total-price"]')
    expect(price).toContainText("₽")
```

## Работа с Playwright

### Фикстура `page`

Playwright предоставляет фикстуру `page` автоматически через плагин `pytest-playwright`. Не нужно создавать её вручную:

```python
# ✅ Правильно
def test_example(page: Page):
    page.goto("https://example.com")

# ❌ Неправильно - не создавайте фикстуру вручную
@pytest.fixture
def page(browser):
    page = browser.new_page()
    yield page
    page.close()
```

### Селекторы

Используйте явные селекторы:

```python
# ✅ Хорошо - data-testid
button = page.locator('[data-testid="add-service-button"]')

# ✅ Хорошо - id
button = page.locator('#submit-button')

# ⚠️ Избегайте - CSS селекторы без data-testid
button = page.locator('.btn-primary')  # Может сломаться при изменении стилей
```

### Ожидания (expect)

Используйте `expect` для проверок:

```python
from playwright.sync_api import expect

# Проверка видимости
expect(button).toBeVisible()

# Проверка текста
expect(page.locator('h1')).toContainText("Калькулятор цен")

# Проверка URL
expect(page).toHaveURL("https://example.com/success")

# Проверка атрибутов
expect(input).toHaveAttribute("value", "test")
```

### Взаимодействие с элементами

```python
# Клик
button.click()

# Ввод текста
input.fill("текст")

# Выбор из выпадающего списка
select.select_option("Москва")

# Перетаскивание слайдера
slider.fill("16")  # или set_value
```

## Скриншоты при ошибках

Playwright автоматически делает скриншоты при падении теста. Для ручного скриншота:

```python
import allure

# Скриншот в Allure
screenshot = page.screenshot()
allure.attach(
    screenshot,
    name="Page Screenshot",
    attachment_type=allure.attachment_type.PNG,
)
```

## Пример полного UI теста

```python
import pytest
from playwright.sync_api import Page, expect
import allure

@allure.label("owner", "qa-team")
@allure.feature("Price Calculator")
@allure.story("Динамический расчет цены при изменении конфигурации")
@allure.suite("ui")
@allure.tag("NORMAL")
@allure.label("priority", "NORMAL")

class TestPriceCalculatorDynamicPrice:
    
    @pytest.fixture(scope="function", autouse=True)
    def setup(self, page: Page):
        """Предусловия: открыть калькулятор."""
        page.goto("https://cloud.ru/calculator")
        expect(page.locator('[data-testid="calculator-title"]')).toBeVisible()
        yield
    
    @allure.title("Изменение количества vCPU должно пересчитывать итоговую стоимость")
    def test_change_vcpu_updates_price(self, page: Page):
        """
        Позитивный сценарий: изменение vCPU динамически меняет цену.
        Шаги:
        1. Добавить сервис Compute.
        2. На странице конфигурации изменить vCPU.
        3. Проверить, что блок с ценой обновился.
        """
        with allure.step("1. Добавить сервис Compute в конфигурацию"):
            add_service_button = page.locator('[data-testid="btn-add-service"]')
            expect(add_service_button).toBeVisible()
            add_service_button.click()
            
            compute_card = page.locator('[data-testid="product-card-compute"]')
            expect(compute_card).toBeVisible()
            compute_card.click()
            
            configure_button = page.locator('[data-testid="btn-configure-compute"]')
            configure_button.click()
        
        with allure.step("2. Запомнить начальную цену и увеличить vCPU"):
            price_locator = page.locator('[data-testid="total-price-value"]')
            initial_price = price_locator.text_content()
            allure.attach(initial_price, name="Начальная цена", attachment_type=allure.attachment_type.TEXT)
            
            vcpu_slider = page.locator('[data-testid="slider-vcpu"]')
            vcpu_slider.fill("4")
        
        with allure.step("3. Проверить, что цена изменилась"):
            page.wait_for_timeout(500)
            new_price = price_locator.text_content()
            allure.attach(new_price, name="Новая цена", attachment_type=allure.attachment_type.TEXT)
            
            assert new_price != initial_price, f"Цена не изменилась после изменения vCPU. Было: {initial_price}, Осталось: {new_price}"
        
        with allure.step("4. Прикрепить скриншот результата"):
            allure.attach(
                page.screenshot(),
                name="calculator_configuration",
                attachment_type=allure.attachment_type.PNG
            )
    
    @allure.title("Проверка ограничения в 99 экземпляров")
    def test_max_instance_limit(self, page: Page):
        """Негативный сценарий: проверка ограничения в 99 экземпляров."""
        with allure.step("1. Перейти к полю ввода количества экземпляров"):
            instance_input = page.locator('[data-testid="input-instance-count"]')
        
        with allure.step("2. Попытаться ввести значение 100"):
            instance_input.fill("100")
        
        with allure.step("3. Проверить, что значение сбросилось к 99 или появилось сообщение об ошибке"):
            actual_value = instance_input.input_value()
            assert actual_value == "99", f"Ограничение на максимум 99 экземпляров не сработало. Значение: {actual_value}"
            
            error_message = page.locator('[data-testid="error-max-instances"]')
            expect(error_message).toContainText("Максимум 99 экземпляров")
```

## Настройки для запуска UI тестов

### Требуемые зависимости

```txt
pytest
pytest-playwright
playwright
allure-pytest
```

### Установка браузеров

После установки `playwright` нужно установить браузеры:

```bash
playwright install
```

Или для конкретного браузера:

```bash
playwright install chromium
playwright install firefox
playwright install webkit
```

### Конфигурация pytest (pytest.ini или pyproject.toml)

```ini
[pytest]
# Использовать pytest-playwright
addopts = --browser chromium --headed=false
markers =
    ui: UI тесты
```

### Запуск тестов

```bash
# Запуск всех UI тестов
pytest -m ui

# Запуск с видимым браузером (для отладки)
pytest --headed

# Запуск конкретного браузера
pytest --browser chromium
pytest --browser firefox
pytest --browser webkit

# Генерация Allure отчета
pytest --alluredir=./allure-results
allure serve ./allure-results
```

## Структура в JSON

```json
{
  "test_case": {
    "files": [
      {
        "description": "Основные тесты для калькулятора цен.",
        "code": "import pytest...",
        "filename": "test_price_calculator_dynamic.py"
      },
      {
        "description": "Фикстуры и вспомогательные функции для UI тестов.",
        "code": "import pytest...",
        "filename": "conftest.py"
      }
    ],
    "raw_response": "[оригинальный ответ LLM с markdown]"
  }
}
```

## Лучшие практики

1. **Используйте классы** для группировки тестов (`class TestFeatureName`)
2. **Используйте фикстуры** для setup/teardown (`@pytest.fixture`)
3. **Используйте allure.step()** для группировки шагов внутри теста
4. **Используйте data-testid** для стабильных селекторов
5. **Ждите элементы** перед взаимодействием (Playwright делает это автоматически)
6. **Используйте expect** вместо assert для лучших сообщений об ошибках
7. **Делайте скриншоты** при важных проверках через `allure.attach()`
8. **Следуйте AAA** паттерну в каждом тесте
9. **Группируйте тесты** по фичам и историям через Allure декораторы
10. **Используйте русский язык** для названий тестов, комментариев и docstrings

## Типичные проблемы

### Проблема: Элемент не найден

```python
# ❌ Плохо - может упасть если элемент не загрузился
button = page.locator('[data-testid="button"]')
button.click()

# ✅ Хорошо - Playwright ждет автоматически, но можно явно
button = page.locator('[data-testid="button"]')
expect(button).toBeVisible()
button.click()
```

### Проблема: Динамический контент

```python
# ❌ Плохо - может не успеть загрузиться
price = page.locator('[data-testid="price"]').inner_text()

# ✅ Хорошо - ждем изменения
price = page.locator('[data-testid="price"]')
expect(price).not.toContainText("0 ₽")
```

### Проблема: Асинхронные действия

```python
# ❌ Плохо - может не дождаться пересчета
vcpu_slider.fill("16")
price = page.locator('[data-testid="price"]').inner_text()

# ✅ Хорошо - ждем изменения
vcpu_slider.fill("16")
price = page.locator('[data-testid="price"]')
expect(price).not.toContainText("0 ₽")  # Ждем пока цена изменится
```

