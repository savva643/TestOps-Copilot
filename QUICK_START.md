# Быстрый старт TestOps Copilot

## Запуск через Docker Compose

1. **Клонируйте репозиторий** (если еще не сделано):
```bash
git clone <repository-url>
cd testops-copilot
```

2. **Запустите все сервисы**:
```bash
docker-compose up -d
```

3. **Проверьте статус**:
```bash
docker-compose ps
```

4. **Откройте в браузере**:
   - Frontend: http://localhost:3000
   - API Gateway: http://localhost:8000
   - API Docs: http://localhost:8000/docs

## Первое использование

### 1. Генерация тест-кейса

1. Откройте http://localhost:3000
2. Перейдите на страницу "Generate Tests"
3. Заполните форму:
   - Выберите тип теста (Manual, API, или UI)
   - Введите описание или загрузите OpenAPI файл
   - Укажите дополнительные параметры (опционально)
4. Нажмите "Generate Test Case"
5. Получите Task ID для отслеживания

### 2. Проверка статуса задачи

1. Перейдите на страницу "Tasks"
2. Введите Task ID
3. Нажмите "Check Status"
4. Дождитесь завершения (статус обновляется автоматически)
5. Скачайте сгенерированный код

## Примеры использования

### Генерация из OpenAPI спецификации

1. Подготовьте OpenAPI файл (YAML или JSON)
2. На странице Generate Tests загрузите файл
3. Система автоматически распарсит спецификацию
4. Описание заполнится автоматически
5. Нажмите "Generate Test Case"

### Генерация из текстового описания

Пример описания:
```
Создать тест для регистрации пользователя:
- Пользователь вводит email и пароль
- Система проверяет валидность email
- Пароль должен быть минимум 8 символов
- При успешной регистрации отправляется письмо
```

## API Endpoints

### Через Gateway (http://localhost:8000)

Все запросы требуют заголовок `X-API-Key: testops-copilot-api-key-2024`

- `POST /api/v1/generate/test-case` - Генерация тест-кейса
- `GET /api/v1/tasks/{task_id}` - Статус задачи
- `POST /api/v1/parse/openapi` - Парсинг OpenAPI
- `POST /api/v1/generate/code` - Генерация кода

### Прямой доступ к сервисам

- Core Agent: http://localhost:8001/docs
- Spec Parser: http://localhost:8002/docs
- Code Generator: http://localhost:8003/docs
- Test Optimizer: http://localhost:8004/docs

## Troubleshooting

### Сервисы не запускаются

```bash
# Проверьте логи
docker-compose logs

# Пересоздайте контейнеры
docker-compose down
docker-compose up -d --build
```

### Ошибки подключения к API

1. Проверьте, что все сервисы запущены: `docker-compose ps`
2. Проверьте переменные окружения в `.env` файлах
3. Убедитесь, что API ключ правильный

### Проблемы с базой данных

```bash
# Пересоздать базу данных
docker-compose down -v
docker-compose up -d postgres
```

## Следующие шаги

- Прочитайте [DEVELOPMENT.md](DEVELOPMENT.md) для разработки
- Изучите [PROJECT_PLAN.md](PROJECT_PLAN.md) для плана развития
- См. [README.md](README.md) для полной документации

