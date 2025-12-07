FROM python:3.11-slim

WORKDIR /app

# Установка uv для управления зависимостями
RUN pip install --no-cache-dir uv

# Копирование файлов зависимостей
COPY pyproject.toml uv.lock* ./

# Установка зависимостей
# Using uv sync without --frozen since uv.lock may not exist
RUN uv sync

# Копирование кода приложения
COPY . .

# Переменные окружения
ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

# Запуск приложения
CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]




