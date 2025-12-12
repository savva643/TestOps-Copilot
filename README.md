# TestOps Copilot

AI-ассистент для автоматизации рутинной работы QA-инженера. Система генерирует тест-кейсы и автотесты (UI/API), оптимизирует тестовое покрытие и проверяет соответствие стандартам, используя Cloud.ru Evolution Foundation Model.

## Архитектура

Проект построен на микросервисной архитектуре:

- **core-agent-service**: Главный оркестратор, взаимодействует с LLM API
- **spec-parser-service**: Парсит требования (OpenAPI 3.0, текстовые описания)
- **code-generator-service**: Генерирует код на основе шаблонов
- **test-optimizer-service**: Анализирует существующие тесты, вычисляет покрытие
- **frontend-dashboard**: Веб-интерфейс для управления агентом
- **integration-gateway**: Единая точка входа для API
- **task-queue-manager**: Обрабатывает асинхронные задачи (Celery + Redis)

## Технологический стек

### Backend
- Python 3.11+
- FastAPI
- PostgreSQL (метаданные, задачи, пользователи)
- Redis (кэш и брокер сообщений)
- Celery (асинхронные задачи)
- LangChain (оркестрация промптов)
- Jinja2 (шаблонизация кода)

### Frontend
- React 19+ с TypeScript
- Vite
- Snack UI Kit (snack-uikit)
- Zustand / TanStack Query
- Recharts (графики)

### Тестирование
- Pytest 7+
- Playwright (UI e2e тесты)
- Allure TestOps / Allure Report

## Быстрый старт

### Требования
- Docker и Docker Compose
- Python 3.11+ (для локальной разработки)
- Node.js 18+ (для frontend)

### Запуск через Docker Compose

```bash
git clone <repository-url>
cd testops-copilot
docker-compose up -d
docker-compose ps
```

Сервисы:
- Frontend Dashboard: http://localhost:3000
- Integration Gateway (API): http://localhost:8000
- Swagger UI (gateway): http://localhost:8000/docs

### Локальная разработка

Backend (пример для core-agent):
```bash
cd backend/core_agent_service
uv sync
uv run uvicorn app.main:app --reload --port 8001
```

Frontend:
```bash
cd frontend/dashboard
npm install
npm run dev
```

### Swagger/OpenAPI
Все сервисы на FastAPI, Swagger UI доступен по `/docs`, OpenAPI по `/openapi.json`.
- Gateway: https://testops.keep-pixel.ru/docs
- Core agent: http://localhost:8001/docs
- Spec parser: http://localhost:8002/docs
- Code generator: http://localhost:8003/docs
- Test optimizer: http://localhost:8004/docs
- GitLab integration: http://localhost:8005/docs

Экспорт схем: см. `docs/api/README.md`.

### Обязательные .env (создать вручную)
- `backend/core_agent_service/.env`
- `backend/integration_gateway/.env`
- `frontend/dashboard/.env`

Пример `backend/core_agent_service/.env`:
```
SERVICE_NAME=core-agent-service
DEBUG=false
POSTGRES_URL=postgresql://testops:testops_password@postgres:5432/testops_db
REDIS_URL=redis://redis:6379/0
CELERY_BROKER_URL=redis://redis:6379/0
CELERY_RESULT_BACKEND=redis://redis:6379/0
CLOUD_RU_LLM_API_KEY=changeme-llm-key
CLOUD_RU_LLM_API_URL=https://foundation-models.api.cloud.ru/v1
CLOUD_RU_LLM_MODEL=openai/gpt-oss-120b
SPEC_PARSER_URL=http://spec-parser-service:8000
CODE_GENERATOR_URL=http://code-generator-service:8000
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

Пример `backend/integration_gateway/.env`:
```
SERVICE_NAME=integration-gateway
DEBUG=false
API_KEY=testops-copilot-api-key-2024
CORE_AGENT_URL=http://core-agent-service:8000
SPEC_PARSER_URL=http://spec-parser-service:8000
CODE_GENERATOR_URL=http://code-generator-service:8000
TEST_OPTIMIZER_URL=http://test-optimizer-service:8000
GITLAB_INTEGRATION_URL=http://gitlab-integration-service:8000
CORS_ORIGINS=["http://localhost:3000","http://localhost:8000"]
```

Пример `frontend/dashboard/.env`:
```
VITE_API_URL=https://testops.keep-pixel.ru
VITE_API_KEY=testops-copilot-api-key-2024
```

Создание файлов через nano (на сервере, из корня репо):
```
nano backend/core_agent_service/.env
nano backend/integration_gateway/.env
nano frontend/dashboard/.env
```

## Структура проекта

```
testops-copilot/
├── docker-compose.yml
├── .gitlab-ci.yml
├── README.md
│
├── backend/
│   ├── core_agent_service/
│   ├── spec_parser_service/
│   ├── code_generator_service/
│   ├── test_optimizer_service/
│   └── integration_gateway/
│
├── frontend/
│   └── dashboard/
│
├── shared/
│   └── lib/
│
└── infra/
    ├── prometheus/
    ├── grafana/
    └── nginx/
```

## Документация и примеры
- Пользовательское руководство: `docs/USER_GUIDE.md`
- Демо-сценарий: `docs/DEMO_SCENARIO.md`
- План метрик: `docs/METRICS_PLAN.md`
- Swagger/OpenAPI чек-лист: `docs/API_DOCS_CHECKLIST.md`
- Архитектура: `docs/ARCHITECTURE.md`
- Демо-материалы: `demo_materials/` (UI/API/GitLab)

## Конфигурация

Настройки сервисов находятся в переменных окружения. Файлы `.env` уже созданы с базовыми настройками и API ключом.

### Обязательные переменные

- `CLOUD_RU_LLM_API_KEY` - API ключ для Cloud.ru Evolution Foundation Model (уже настроен)
- `POSTGRES_URL` - URL подключения к PostgreSQL
- `REDIS_URL` - URL подключения к Redis
- `API_KEY` - API ключ для Gateway (по умолчанию: `testops-copilot-api-key-2024`)

## Разработка

### Линтеры и форматтеры

```bash
# Python
black .
isort .
flake8 .

# Frontend
npm run lint
npm run format
```

### Тесты

```bash
# Backend
pytest --cov=app tests/

# Frontend
npm run test
```

## Лицензия

Proprietary - Cloud.ru




