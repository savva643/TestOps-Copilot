import requests
import json

API_URL = "https://foundation-models.api.cloud.ru/v1/chat/completions"
API_KEY = "ZWI0ZDcwMDUtYmJhMS00OWUyLWEwNWYtZTYxNjliZjZlNTVh.0db2e453d4aa678fba26ea79fcbaa469"

# System prompt для API тестов (из prompt_engineer.py)
system_prompt = """Ты — опытный QA-инженер по API-тестированию. Верни только готовый код на Python.

Требования к ответу:
- Только код на Python, без Markdown и без комментариев-пояснений.
- pytest + httpx (AsyncClient), аннотации Allure (@allure.feature, @allure.story, @allure.title, @allure.severity, @allure.label("owner", ...)).
- Строгая структура AAA в тестах (Arrange-Act-Assert).
- Проверка статус-кодов и ключевых полей в ответе.
- Позитивные и негативные сценарии, граничные случаи.
- Всё на русском (названия тестов, строки, аннотации).
- Начинай ответ с import pytest (или from ... import ...); никаких префиксов вроде "The user asks" или пояснений."""

# User prompt с примером описания
user_prompt = """Сгенерируй подробные api тесты на основе требований ниже.

Эндпоинты:
GET /vms - Получение списка виртуальных машин
POST /vms - Создание виртуальной машины
GET /vms/{vmId} - Получение информации о виртуальной машине

Верни строго (без Markdown) подходящий результат с учетом:
- Если тест_type=api/ui — только готовый Python-код тестов
- Нумерованные шаги (AAA в коде или шагах)
- Необходимые тестовые данные
- Ожидаемые результаты и проверки
- Отдельные негативные сценарии и граничные случаи
- Ответ строго начинается с import pytest (или from ... import ...), без преамбулы, без Markdown"""

payload = {
    "model": "openai/gpt-oss-120b",
    "messages": [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": user_prompt}
    ],
    "temperature": 0.2,
    "max_tokens": 3000,  # Увеличил для полного кода
}

print("Отправляю запрос к LLM API...")
resp = requests.post(
    API_URL,
    headers={"Authorization": f"Bearer {API_KEY}", "Content-Type": "application/json"},
    json=payload,
    timeout=120,
)

resp.raise_for_status()
data = resp.json()

print("\n=== Полный ответ API ===")
print(json.dumps(data, ensure_ascii=False, indent=2))

print("\n=== Извлечённый текст ===")
if "choices" in data and len(data["choices"]) > 0:
    message = data["choices"][0].get("message", {})
    content = message.get("content", "")
    print(content)
    
    # Проверка, начинается ли с import/from
    stripped = content.lstrip()
    if stripped.startswith("import ") or stripped.startswith("from "):
        print("\n✓ Ответ начинается с import/from - ОК!")
    else:
        print("\n✗ Ответ НЕ начинается с import/from - проблема!")
        # Попробуем найти код в ответе
        if "import" in content.lower():
            import_idx = content.lower().find("import")
            print(f"\nНайдено 'import' на позиции {import_idx}, вырезаем с этого места:")
            print(content[import_idx:])
else:
    print("Нет choices в ответе!")



