# План производительности и кэширования (фаза 5)

## Оптимизация LLM запросов
- Batch одинаковых промптов/шагов, где возможно.
- Ограничить размер промпта: обрезать контекст, использовать сжатие спецификации.
- Таймауты и retry с джиттером (уже в клиентах — проверить параметры по умолчанию).

## Кэширование
- Кэш Redis для:
  - результатов парсинга OpenAPI (ключ: hash(spec)).
  - LLM ответов для идентичных промптов (ключ: hash(prompt-template+inputs)).
- TTL: 1–6 часов для LLM ответов, 24 часа для парсинга.
- Инвалидация: по hash изменений входных данных.

## Мониторинг и алерты
- Экспорт метрик (Prometheus):
  - latency LLM (p50/p95), error_rate, retry_count.
  - queue_depth Celery/Redis.
  - task_success_rate (уже в UI — расширить для back).
- Алерты:
  - latency p95 > 5s,
  - error_rate > 5%,
  - queue_depth > 100.

## Следующие шаги
- Добавить метрики в gateway и сервисы (Prometheus FastAPI middleware).
- Подключить Grafana dashboards (LLM, Celery, API latency).
- Применить кэш Redis в parser/code-generator (на уровне сервисов).

