# API документация — чек-лист публикации

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
- [ ] Gateway openapi экспортирован в docs/api
- [ ] Core agent openapi экспортирован
- [ ] Parser openapi экспортирован
- [ ] Code generator openapi экспортирован
- [ ] Optimizer openapi экспортирован
- [ ] GitLab integration openapi экспортирован
- [ ] docs/api/README.md обновлён ссылками

