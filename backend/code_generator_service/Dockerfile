FROM python:3.11-slim

WORKDIR /app

RUN pip install --no-cache-dir uv

# Copy code first - uv sync needs the package directory to build
COPY . .

# Install dependencies and the package in editable mode
# Using uv sync without --frozen since uv.lock may not exist
RUN uv sync

ENV PYTHONPATH=/app
ENV PYTHONUNBUFFERED=1

CMD ["uv", "run", "uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]




