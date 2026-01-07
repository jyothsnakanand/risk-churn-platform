.PHONY: help install install-dev test lint format type-check pre-commit clean docker-build docker-up docker-down k8s-deploy

help:
	@echo "Available commands:"
	@echo "  make install          - Install production dependencies"
	@echo "  make install-dev      - Install development dependencies"
	@echo "  make test             - Run tests with coverage"
	@echo "  make lint             - Run linting checks"
	@echo "  make format           - Format code"
	@echo "  make type-check       - Run type checking"
	@echo "  make pre-commit       - Run all pre-commit hooks"
	@echo "  make clean            - Clean build artifacts"
	@echo "  make docker-build     - Build Docker image"
	@echo "  make docker-up        - Start Docker Compose services"
	@echo "  make docker-down      - Stop Docker Compose services"
	@echo "  make k8s-deploy       - Deploy to Kubernetes"

install:
	uv sync

install-dev:
	uv sync --all-extras
	pre-commit install

test:
	pytest tests/ -v --cov=src --cov-report=html --cov-report=term-missing

lint:
	ruff check src/ tests/

format:
	black src/ tests/
	isort src/ tests/

type-check:
	mypy src/

pre-commit:
	pre-commit run --all-files

clean:
	rm -rf .venv
	rm -rf build dist *.egg-info
	rm -rf .pytest_cache .coverage htmlcov
	rm -rf .mypy_cache .ruff_cache
	find . -type d -name __pycache__ -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete

docker-build:
	docker build -t risk-churn-platform:latest .

docker-up:
	docker-compose up -d

docker-down:
	docker-compose down -v

docker-logs:
	docker-compose logs -f

k8s-deploy:
	kubectl apply -f k8s/namespace.yaml
	kubectl apply -f k8s/kafka-deployment.yaml
	kubectl apply -f k8s/monitoring-deployment.yaml
	kubectl apply -f k8s/seldon-deployment-shadow.yaml
	kubectl apply -f k8s/drift-detector-deployment.yaml

k8s-status:
	kubectl get all -n ml-platform

k8s-clean:
	kubectl delete -f k8s/seldon-deployment-shadow.yaml
	kubectl delete -f k8s/drift-detector-deployment.yaml
	kubectl delete -f k8s/monitoring-deployment.yaml
	kubectl delete -f k8s/kafka-deployment.yaml
	kubectl delete namespace ml-platform
