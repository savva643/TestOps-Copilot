# API документация — чек-лист публикации

> 📖 Вернуться к [главной документации](../../README.md)

Цель: собрать и опубликовать Swagger/OpenAPI для gateway и всех микросервисов.

## Шаги
1) Gateway (`backend/integration_gateway`):
   - Убедиться, что OpenAPI доступен по `/openapi.json`.
   - Экспортировать файл в `docs/api/gateway-openapi.json`.
   - Добавить ссылку в README/UI (swagger-ui или redoc).
2) Core agent, parser, code generator, optimizer, gitlab integration:
   - Для каждого сервиса собрать OpenAPI (`/openapi.json`) и сохранить в `docs/api/<service>-openapi.json`.
   - Если сервис FastAPI — можно запустить `uvicorn app.main:app` и скачать схему.
3) Сборка единого каталога:
   - Сформировать `docs/api/README.md` с ссылками на все схемы.
   - (Опционально) собрать агрегированный spec для gateway, который проксирует методы.
4) Публикация:
   - Добавить swagger-ui/static в Dashboard (линк на gateway swagger).
   - В CI добавить job, который проверяет актуальность схем (сравнивает с сохранёнными).

## Текущее состояние
- [x] Gateway openapi экспортирован в docs/api
- [x] Core agent openapi экспортирован
- [x] Parser openapi экспортирован
- [x] Code generator openapi экспортирован
- [x] Optimizer openapi экспортирован
- [x] GitLab integration openapi экспортирован
- [x] docs/api/README.md обновлён ссылками

## Связанная документация

- [README.md](../../README.md) — Главная документация проекта
- [docs/api/README.md](api/README.md) — API схемы и Swagger UI
- [docs/ARCHITECTURE.md](ARCHITECTURE.md) — Архитектура системы

