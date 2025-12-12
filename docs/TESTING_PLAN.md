# План тестирования (фаза 5)

## Цели
- Unit покрытие backend сервисов ≥60%.
- Интеграционные прогоны основного флоу: загрузка спецификации → генерация → скачивание артефакта.
- E2E критические сценарии UI (авторизация, загрузка, запуск, просмотр задач, скачивание).

## Backend: покрытие и команды
- Запуск всех юнит-тестов по сервисам: `make test` или `pytest --maxfail=1 --disable-warnings --cov=app` внутри каждого сервиса.
- Собрать отчёты покрытия: `pytest --cov=app --cov-report=xml` в сервисе; сложить xml в `docs/metrics/` (например, `backend-coverage-<service>.xml`).
- Минимум по сервисам:
  - core_agent_service: задачи, LLM client, prompt_engineer.
  - spec_parser_service: openapi_parser текст/файлы.
  - code_generator_service: шаблоны, валидатор, end-to-end flow.
  - test_optimizer_service: ast_analyzer, coverage_analyzer, duplicate_finder.
  - gitlab_integration_service: gitlab_client + интеграционный мок.

## Интеграционные тесты
- Использовать docker-compose (см. `QUICK_TEST.md`) для поднятия стека.
- Сценарий: POST `/api/v1/parse/specification` → `/api/v1/generate/autotest` → `/api/v1/tasks/{id}` → скачивание артефакта.
- Проверить статус 200, SUCCESS, наличие артефактов.

## E2E (Frontend)
- Playwright: сценарии
  - login → dashboard → generate (загрузить `demo_materials/manual/ui-calculator-openapi.yaml`) → дождаться SUCCESS → открыть задачу.
  - tasks → открыть задачу с артефактом → скачать.
  - optimize (GitLab) — подключение токена и запуск анализа (при наличии test repo).
- Сохранять отчёты в `frontend/dashboard/playwright-report/` и публиковать как артефакты CI.

## Отчётность
- Сохранить `coverage.xml` (Cobertura) и Playwright HTML-report как артефакты CI.
- Добавить суммарные цифры в `docs/metrics/metrics.json` (coverage_backend, coverage_frontend, e2e_passed).

