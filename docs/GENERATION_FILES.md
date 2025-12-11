# Файлы генерации тестов

## Основные файлы

### 1. Формирование промптов

**Файл:** `backend/core_agent_service/app/services/prompt_engineer.py`

**Что делает:**
- Валидирует входные данные (description, test_type, feature, story)
- Формирует system и user промпты для LLM
- Адаптирует промпты под тип теста (manual/api/ui)

**Ключевые методы:**
- `validate_prompt_inputs()` — валидация входных данных
- `get_test_case_generation_prompt()` — создание промптов для генерации тестов
- `get_code_generation_prompt()` — создание промптов для генерации кода (не используется в основном flow)
- `get_code_analysis_prompt()` — создание промптов для анализа кода (не используется в основном flow)

### 2. Генерация и парсинг ответа

**Файл:** `backend/core_agent_service/app/tasks/test_generation.py`

**Что делает:**
- Celery задача для асинхронной генерации тестов
- Вызывает LLM через LLMClient
- Парсит ответ LLM и извлекает код/текст
- Обрабатывает несколько файлов и описания
- Сохраняет промпт в результат для отладки

**Ключевые функции:**
- `generate_test_case_task()` — основная Celery задача
- `extract_code_blocks_from_markdown()` — извлечение блоков кода из markdown
- `extract_code_from_text()` — универсальное извлечение кода
- `has_code()` — проверка наличия кода в ответе

**Структура результата:**
```python
{
  "test_case": {
    "files": [
      {
        "description": "Описание или None",
        "code": "import pytest\n...",
        "filename": "test_1.py"
      }
    ],
    "raw_response": "Оригинальный ответ LLM"
  },
  "test_type": "api",
  "prompt": "System Prompt:\n...\n\nUser Prompt:\n..."
}
```

### 3. Клиент LLM

**Файл:** `backend/core_agent_service/app/services/llm_client.py`

**Что делает:**
- Отправляет запросы к LLM API (Cloud.ru Foundation Models)
- Обрабатывает ответы разных форматов
- Ретраи при ошибках
- Rate limiting

**Ключевые методы:**
- `generate()` — генерация текста через LLM
- `extract_content()` — извлечение контента из ответа (поддержка разных форматов)

## Поток данных

```
1. Frontend → POST /api/v1/generate/test-case
   ↓
2. Gateway → Proxy → Core Agent Service
   ↓
3. Core Agent Service → Celery Task (generate_test_case_task)
   ↓
4. PromptEngineer → Формирование промптов
   ↓
5. LLMClient → Запрос к LLM API
   ↓
6. LLM → Ответ (код или текст)
   ↓
7. test_generation.py → Парсинг ответа
   ↓
8. Результат → Сохранение в БД
   ↓
9. WebSocket → Отправка обновлений фронтенду
   ↓
10. Frontend → Отображение файлов с кнопками скачать
```

## Изменения в последней версии

### Улучшения промпта для API тестов

1. **Более строгие инструкции:**
   - Запрет на текстовые пояснения типа "We need to..."
   - Обязательное начало с ```python
   - Пример правильного ответа в system prompt

2. **Поддержка нескольких файлов:**
   - Парсинг нескольких блоков ```python ... ```
   - Извлечение описаний между блоками
   - Генерация уникальных имен файлов

3. **Сохранение промпта:**
   - Промпт сохраняется в `result.prompt`
   - Отображается в артефактах для отладки

4. **Улучшенная обработка ошибок:**
   - Повторный запрос с усиленным промптом при отсутствии кода
   - Логирование preview ответа для отладки

## Как работает парсинг

### Сценарий 1: Markdown блоки

**Вход:**
```
Описание первого файла.

```python
import pytest
# код
```

Описание второго файла.

```python
import pytest
# код
```
```

**Выход:**
```python
[
  {
    "description": "Описание первого файла.",
    "code": "import pytest\n# код",
    "filename": "test_1.py"
  },
  {
    "description": "Описание второго файла.",
    "code": "import pytest\n# код",
    "filename": "test_2.py"
  }
]
```

### Сценарий 2: Чистый код без markdown

**Вход:**
```
import pytest
import httpx
# код
```

**Выход:**
```python
[
  {
    "description": None,
    "code": "import pytest\nimport httpx\n# код",
    "filename": "test.py"
  }
]
```

### Сценарий 3: Текст без кода (manual тесты)

**Вход:**
```
Тест-кейс 1: Проверка логина

Шаги:
1. Открыть страницу
2. Ввести логин
...
```

**Выход:**
```python
[
  {
    "description": None,
    "code": "Тест-кейс 1: Проверка логина\n\nШаги:\n1. Открыть страницу\n...",
    "filename": "test_case.txt"
  }
]
```

## Отладка

### Логи для отладки

1. **Preview ответа LLM:**
   ```
   LLM response doesn't contain code blocks or import statements
   preview='We need to produce...'
   ```

2. **Количество извлеченных файлов:**
   ```
   Extracted code files from LLM response
   files_count=3
   ```

3. **Промпт в артефактах:**
   - Скачай артефакты → увидишь полный промпт
   - Позволяет понять, что отправлялось в LLM

### Типичные проблемы

1. **LLM возвращает текст вместо кода:**
   - Проверь system prompt (должен быть строгим)
   - Проверь user prompt (должен требовать ```python)
   - Усиль промпт примерами

2. **Несколько файлов не парсятся:**
   - Проверь regex в `extract_code_blocks_from_markdown()`
   - Убедись, что блоки закрыты правильно

3. **Описания теряются:**
   - Проверь логику извлечения текста между блоками
   - Убедись, что текст добавляется к `description`

