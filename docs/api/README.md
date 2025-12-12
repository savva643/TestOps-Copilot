# API схемы и Swagger UI

> 📖 Вернуться к [главной документации](../../README.md)

Все сервисы — FastAPI, Swagger UI доступен по `/docs`, схема — `/openapi.json`.

## Локальные URL (по умолчанию)
- Gateway: http://localhost:8000/docs
- Core agent: http://localhost:8001/docs
- Spec parser: http://localhost:8002/docs
- Code generator: http://localhost:8003/docs
- Test optimizer: http://localhost:8004/docs
- GitLab integration: http://localhost:8005/docs

## Экспорт OpenAPI в репозиторий
Скачать схемы и положить в `docs/api/`:
```bash
mkdir -p docs/api
curl -s http://localhost:8000/openapi.json -o docs/api/gateway-openapi.json
curl -s http://localhost:8001/openapi.json -o docs/api/core-agent-openapi.json
curl -s http://localhost:8002/openapi.json -o docs/api/spec-parser-openapi.json
curl -s http://localhost:8003/openapi.json -o docs/api/code-generator-openapi.json
curl -s http://localhost:8004/openapi.json -o docs/api/test-optimizer-openapi.json
curl -s http://localhost:8005/openapi.json -o docs/api/gitlab-integration-openapi.json
```

## Публикация в UI
- В Dashboard можно добавить ссылку/iframe на gateway Swagger UI (`/docs`).
- Для внешней публикации используйте Redoc/Swagger UI хостинг, указывая сохранённые схемы из `docs/api/`.

## Связанная документация

- [README.md](../../README.md) — Главная документация проекта
- [docs/API_DOCS_CHECKLIST.md](../API_DOCS_CHECKLIST.md) — Чек-лист публикации API
- [docs/ARCHITECTURE.md](../ARCHITECTURE.md) — Архитектура системы

