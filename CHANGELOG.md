# Changelog

> 📖 Вернуться к [главной документации](README.md)

## [0.1.0] - 2025-12-11

### Added
- Полная структура микросервисной архитектуры
- Core Agent Service с интеграцией Cloud.ru Evolution Foundation Model
- Spec Parser Service для парсинга OpenAPI спецификаций
- Code Generator Service с Jinja2 шаблонами
- Test Optimizer Service (базовая структура)
- Integration Gateway как единая точка входа
- Frontend Dashboard на React + TypeScript
- Docker Compose конфигурация для всех сервисов
- CI/CD пайплайн для GitLab
- Документация (README, DEVELOPMENT, QUICK_START)

### Features
- Генерация тест-кейсов через LLM API
- Парсинг OpenAPI 3.0 спецификаций
- Генерация кода в формате Allure TestOps as Code
- Асинхронная обработка задач через Celery
- Веб-интерфейс для управления генерацией
- Отслеживание статуса задач
- Загрузка и парсинг OpenAPI файлов

### Technical
- Python 3.11+ с FastAPI
- React 19 + TypeScript + Vite
- PostgreSQL для метаданных
- Redis для кэша и брокера сообщений
- Celery для фоновых задач
- Docker контейнеризация

### Configuration
- API ключ для Cloud.ru Evolution Foundation Model настроен
- Базовые .env файлы созданы
- Docker Compose готов к запуску

## [1.1] - 2025-12-12

- Анализ покрытия тестов
- Поиск дубликатов тестов
- Интеграция с GitLab API
- Расширенная аналитика

## Связанная документация

- [README.md](README.md) — Главная документация проекта
- [PROJECT_PLAN.md](PROJECT_PLAN.md) — План разработки

