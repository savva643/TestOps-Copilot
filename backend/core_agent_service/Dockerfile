FROM python:3.11-slim

WORKDIR /app

# Установка uv для управления зависимостями
RUN pip install --no-cache-dir uv

# Копирование кода приложения (сначала код, потом зависимости)
# uv sync требует наличия директории пакета для сборки
COPY . .

# Установка зависимостей и пакета в editable mode
# Using uv sync without --frozen since uv.lock may not exist
RUN uv sync

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Запуск приложения
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]




