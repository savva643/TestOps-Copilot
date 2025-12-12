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

