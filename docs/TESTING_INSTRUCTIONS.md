# Инструкция по проверке работоспособности TestOps Copilot

> 📖 Вернуться к [главной документации](../../README.md)

## Подготовка

1. **Вход в систему:**
   - Откройте страницу `/login`
   - Введите:
     - **Key ID (IAM)** - ваш Cloud.ru IAM Key ID
     - **Key Secret (IAM)** - ваш Cloud.ru IAM Key Secret
     - **API Key (Cloud.ru Evolution Model)** - ваш API ключ для доступа к модели (не ограничен)
   - Нажмите "Войти"
   - После успешного входа вы будете перенаправлены на главную страницу

2. **Проверка парсера OpenAPI:**
   - Перейдите на страницу `/generate`
   - Загрузите файл OpenAPI спецификации (YAML или JSON)
   - Пример спецификации для Evolution Compute VMs находится в `docs/examples/openapi-evolution-compute-vms.yaml`
   - После загрузки вы должны увидеть:
     - Список эндпоинтов (например, `/vms`, `/vms/{vmId}`)
     - Методы HTTP (GET, POST, PUT, DELETE)
     - Параметры и схемы

## Проверка конвейера генерации тестов

### Шаг 1: Загрузка OpenAPI спецификации

1. На странице `/generate` загрузите файл `openapi-evolution-compute-vms.yaml`
2. Парсер должен извлечь:
   - Эндпоинты: `POST /vms`, `GET /vms/{vmId}`, `GET /vms`, `DELETE /vms/{vmId}`
   - Методы: POST, GET, DELETE
   - Схемы: `VMCreateRequest`, `VM`, `VMListResponse`

### Шаг 2: Генерация тест-кейсов

1. После успешного парсинга нажмите "Сгенерировать тесты"
2. Система создаст задачу генерации
3. Перейдите на страницу `/tasks` для отслеживания прогресса

### Шаг 3: Проверка результата

1. На странице `/tasks` вы увидите статус задачи:
   - `PENDING` - задача создана
   - `PROGRESS` - идет генерация (с прогрессом в %)
   - `SUCCESS` - тесты сгенерированы
   - `FAILURE` - произошла ошибка

2. После успешной генерации:
   - Нажмите "Скачать код" для получения Python файла с тестами
   - Нажмите "Скачать артефакты" для получения ZIP архива

## Что проверяется в конвейере

### 1. Парсер OpenAPI (`spec-parser-service`)
- ✅ Извлекает эндпоинты из спецификации
- ✅ Определяет HTTP методы
- ✅ Парсит параметры и схемы
- ✅ Валидирует формат OpenAPI

### 2. Формирование промпта (`core-agent-service`)
- ✅ Создает промпт для LLM на основе данных парсера
- ✅ Использует шаблон с паттерном AAA (Arrange-Act-Assert)
- ✅ Добавляет требования к декораторам Allure

### 3. Запрос к LLM (`core-agent-service`)
- ✅ Отправляет запрос в Cloud.ru Evolution Foundation Model
- ✅ Использует правильный endpoint: `https://foundation-models.api.cloud.ru/v1`
- ✅ Использует модель: `openai/gpt-oss-120b`
- ✅ Получает ответ с тест-кейсом

### 4. Генератор кода (`code-generator-service`)
- ✅ Проверяет наличие декораторов Allure
- ✅ Форматирует код с помощью `black`
- ✅ Сохраняет результат в файл

## Пример запроса к LLM

**Промпт для `POST /vms`:**
```
Ты — помощник QA-инженера. Сгенерируй один ручной тест-кейс в формате Allure TestOps as Code (Python) для POST /vms. Используй паттерн AAA (Arrange-Act-Assert). Обязательно добавь декораторы Allure: @allure.title, @allure.feature('VMs'), @allure.story('Create VM'), @allure.label('owner', 'qa-team'). В тесте используй фейковые данные для аутентификации и тестовых данных.
```

**Ожидаемый ответ (фрагмент):**
```python
import allure
import pytest
import requests

@allure.title("Создание виртуальной машины")
@allure.feature('VMs')
@allure.story('Create VM')
@allure.label('owner', 'qa-team')
def test_create_vm():
    # Arrange
    base_url = "https://api.cloud.ru/v1"
    headers = {"Authorization": "Bearer fake_token"}
    payload = {
        "name": "test-vm",
        "flavor": "small",
        "image": "ubuntu-20.04"
    }
    
    # Act
    response = requests.post(f"{base_url}/vms", json=payload, headers=headers)
    
    # Assert
    assert response.status_code == 201
    assert response.json()["name"] == "test-vm"
```

## Проверка UI-требований (Кейс 1)

Для проверки генерации тестов на основе текстового описания:

1. На странице `/generate` введите текстовое описание:
   ```
   Проверить, что при изменении слайдера 'vCPU' в конфигурации Compute, блок 'Итоговая стоимость' пересчитывается.
   ```

2. Система должна сгенерировать UI тест-кейс с использованием Playwright или Selenium

## Возможные проблемы

1. **Ошибка 401 при запросе к LLM:**
   - Проверьте, что API ключ модели введен правильно
   - Убедитесь, что ключ не истек

2. **Ошибка парсинга OpenAPI:**
   - Проверьте формат файла (должен быть валидный YAML или JSON)
   - Убедитесь, что файл соответствует OpenAPI 3.0 спецификации

3. **Задача не завершается:**
   - Проверьте логи Celery worker
   - Убедитесь, что Redis запущен и доступен

## Логи для отладки

Все сервисы логируют важные события:
- Парсинг спецификации
- Формирование промпта
- Запросы к LLM
- Генерация кода
- Ошибки на каждом этапе

Логи доступны в консоли каждого сервиса.

## Связанная документация

- [README.md](../../README.md) — Главная документация проекта
- [QUICK_TEST.md](../../QUICK_TEST.md) — Быстрая проверка работоспособности
- [QUICK_START.md](../../QUICK_START.md) — Быстрый старт
- [docs/USER_GUIDE.md](USER_GUIDE.md) — Пользовательское руководство

