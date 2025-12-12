.PHONY: help build up down logs clean test lint format

help: ## Show this help message
	@echo 'Usage: make [target]'
	@echo ''
	@echo 'Available targets:'
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "  %-15s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

build: ## Build all Docker images
	docker-compose build

up: ## Start all services
	docker-compose up -d

down: ## Stop all services
	docker-compose down

logs: ## Show logs from all services
	docker-compose logs -f

clean: ## Remove all containers, volumes, and images
	docker-compose down -v --rmi all

test: ## Run tests
	@echo "Running Python tests..."
	@for service in backend/*/; do \
		echo "Testing $$service"; \
		cd $$service && pytest || true && cd - > /dev/null; \
	done

test-integration: ## Run integration tests
	@echo "Running integration tests..."
	@docker-compose up -d
	@sleep 10
	@pytest tests/integration/ -v -m integration || true

test-e2e: ## Run E2E tests (requires frontend running)
	@echo "Running E2E tests..."
	@cd frontend/dashboard && npm run test:e2e || true

test-all: test test-integration ## Run all tests

lint: ## Run linters
	@echo "Linting Python code..."
	@for service in backend/*/; do \
		echo "Linting $$service"; \
		cd $$service && black --check . && isort --check-only . && flake8 . || true && cd - > /dev/null; \
	done
	@echo "Linting Frontend..."
	@cd frontend/dashboard && npm run lint

format: ## Format code
	@echo "Formatting Python code..."
	@for service in backend/*/; do \
		echo "Formatting $$service"; \
		cd $$service && black . && isort . && cd - > /dev/null; \
	done
	@echo "Formatting Frontend..."
	@cd frontend/dashboard && npm run format

install-pre-commit: ## Install pre-commit hooks
	pre-commit install

swagger-export: ## Export OpenAPI specs to docs/api
	mkdir -p docs/api
	@echo "Exporting gateway..."
	-@curl -s http://localhost:8000/openapi.json -o docs/api/gateway-openapi.json
	@echo "Exporting core-agent..."
	-@curl -s http://localhost:8001/openapi.json -o docs/api/core-agent-openapi.json
	@echo "Exporting spec-parser..."
	-@curl -s http://localhost:8002/openapi.json -o docs/api/spec-parser-openapi.json
	@echo "Exporting code-generator..."
	-@curl -s http://localhost:8003/openapi.json -o docs/api/code-generator-openapi.json
	@echo "Exporting test-optimizer..."
	-@curl -s http://localhost:8004/openapi.json -o docs/api/test-optimizer-openapi.json
	@echo "Exporting gitlab-integration..."
	-@curl -s http://localhost:8005/openapi.json -o docs/api/gitlab-integration-openapi.json
	@echo "Done. Check docs/api/*.json"

test-coverage: ## Run pytest with coverage for all backend services
	@for service in backend/*/; do \
		echo "==> Coverage $$service"; \
		cd $$service && pytest --maxfail=1 --disable-warnings --cov=app --cov-report=xml --cov-report=term || exit $$?; \
		cd - > /dev/null; \
	done
	@echo "Coverage reports generated (xml in each service dir)"

