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

