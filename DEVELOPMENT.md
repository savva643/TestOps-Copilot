# Development Guide

## Локальная разработка

### Требования

- Python 3.11+
- Node.js 18+
- Docker и Docker Compose
- uv (для управления Python зависимостями) или poetry

### Настройка окружения

1. Клонируйте репозиторий:
```bash
git clone <repository-url>
cd testops-copilot
```

2. Установите pre-commit хуки:
```bash
make install-pre-commit
```

3. Скопируйте примеры .env файлов:
```bash
cp backend/core_agent_service/.env.example backend/core_agent_service/.env
cp backend/integration_gateway/.env.example backend/integration_gateway/.env
cp frontend/dashboard/.env.example frontend/dashboard/.env
```

4. Заполните необходимые переменные окружения (особенно `CLOUD_RU_LLM_API_KEY`)

### Запуск через Docker Compose

```bash
# Собрать и запустить все сервисы
make build
make up

# Просмотр логов
make logs

# Остановить сервисы
make down
```

### Локальная разработка (без Docker)

#### Backend сервисы

```bash
# Установить uv (если еще не установлен)
pip install uv

# Для каждого сервиса
cd backend/core_agent_service
uv sync
uv run uvicorn app.main:app --reload --port 8001
```

#### Frontend

```bash
cd frontend/dashboard
npm install
npm run dev
```

### Тестирование

```bash
# Запустить все тесты
make test

# Запустить линтеры
make lint

# Форматировать код
make format
```

## Структура проекта

### Backend сервисы

Каждый сервис следует структуре:
```
service_name/
├── app/
│   ├── api/          # FastAPI роутеры
│   ├── core/         # Конфигурация, security
│   ├── models/       # SQLAlchemy модели (если нужны)
│   ├── schemas/      # Pydantic схемы
│   ├── services/     # Бизнес-логика
│   └── tasks/        # Celery задачи
├── tests/            # Тесты
├── Dockerfile
└── pyproject.toml
```

### Frontend

```
dashboard/
├── src/
│   ├── components/   # React компоненты
│   ├── pages/        # Страницы приложения
│   ├── api/          # API клиенты
│   ├── stores/       # Zustand сторы
│   └── types/        # TypeScript типы
├── public/
└── package.json
```

## API Endpoints

### Integration Gateway (http://localhost:8000)

- `POST /api/v1/generate/test-case` - Генерация тест-кейса
- `GET /api/v1/tasks/{task_id}` - Статус задачи
- `POST /api/v1/parse/openapi` - Парсинг OpenAPI спецификации
- `POST /api/v1/generate/code` - Генерация кода теста
- `POST /api/v1/optimize/coverage` - Анализ покрытия

Все запросы требуют заголовок `X-API-Key`.

## Работа с LLM API

Для работы с Cloud.ru Evolution Foundation Model необходимо:

1. Получить API ключ
2. Установить переменную окружения `CLOUD_RU_LLM_API_KEY`
3. Убедиться, что URL API правильный (по умолчанию: `https://api.cloud.ru/v1/evolution/foundation`)

## Git Workflow

1. Создайте feature ветку от `main`
2. Внесите изменения
3. Запустите линтеры и тесты: `make lint && make test`
4. Создайте Merge Request в GitLab
5. После ревью и прохождения CI/CD - мердж в `main`

## Дополнительная документация

- [README.md](README.md) — Главная документация проекта
- [QUICK_START.md](QUICK_START.md) — Быстрый старт
- [PROJECT_PLAN.md](PROJECT_PLAN.md) — План разработки
- [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) — Архитектура системы

## Troubleshooting

### Проблемы с Docker

```bash
# Очистить все контейнеры и volumes
make clean

# Пересобрать образы
make build
```

### Проблемы с зависимостями

```bash
# Обновить Python зависимости
cd backend/<service>
uv sync --upgrade

# Обновить Node зависимости
cd frontend/dashboard
npm update
```

### Проблемы с базой данных

```bash
# Пересоздать базу данных
docker-compose down -v
docker-compose up -d postgres
```

