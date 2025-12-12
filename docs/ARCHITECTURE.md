# Архитектура TestOps Copilot

> 📖 Вернуться к [главной документации](../../README.md)

## Микросервисы
- **integration-gateway** — единая точка входа API, авторизация, rate limiting, метрики.
- **core-agent-service** — оркестратор LLM запросов, постановка задач в очередь.
- **spec-parser-service** — парсит OpenAPI 3.0 и текстовые спецификации.
- **code-generator-service** — Jinja2 + LLM для генерации тестов (pytest/Playwright/manual).
- **test-optimizer-service** — анализ покрытия, поиск дубликатов, рекомендации.
- **gitlab-integration-service** — доступ к репозиториям/пайплайнам GitLab.
- **frontend/dashboard** — UI (React + Snack UI Kit).
- **infra** — Redis/PG/Celery, Prometheus/Grafana (для мониторинга).

## Поток
1) Пользователь отправляет задачу через gateway (UI или API).
2) Core agent создаёт задачу и ставит в очередь Celery.
3) Parser/Generator/Optimizer обрабатывают задачу и сохраняют результаты.
4) Gateway/Frontend выдают статусы, артефакты и метрики.

## Порты (по умолчанию)
- Gateway: 8000
- Core agent: 8001
- Spec parser: 8002
- Code generator: 8003
- Test optimizer: 8004
- GitLab integration: 8005
- Frontend: 3000

## Связанная документация

- [README.md](../../README.md) — Главная документация проекта
- [DEVELOPMENT.md](../../DEVELOPMENT.md) — Руководство для разработчиков
- [docs/api/README.md](api/README.md) — API документация

