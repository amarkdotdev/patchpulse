.PHONY: help lint test build docker-up docker-down helm-install helm-uninstall run clean

help:
	@echo "PatchPulse Makefile"
	@echo ""
	@echo "Targets:"
	@echo "  lint          - Lint all code"
	@echo "  test          - Run all tests"
	@echo "  build         - Build all containers"
	@echo "  docker-up     - Start docker-compose"
	@echo "  docker-down   - Stop docker-compose"
	@echo "  helm-install  - Install via Helm"
	@echo "  helm-uninstall - Uninstall from Helm"
	@echo "  run           - Run backend locally"
	@echo "  clean         - Clean build artifacts"

lint:
	@echo "Linting Python code..."
	@cd backend && python -m flake8 . --max-line-length=120 --ignore=E501,W503 || true
	@cd integrations/git && python -m flake8 . --max-line-length=120 --ignore=E501,W503 || true
	@cd integrations/slack && python -m flake8 . --max-line-length=120 --ignore=E501,W503 || true
	@echo "Linting Go code..."
	@cd agent && go fmt ./... && go vet ./... || true

test:
	@echo "Running Python tests..."
	@cd backend && python -m pytest tests/ -v || true
	@cd integrations/git && python -m pytest tests/ -v || true
	@echo "Running Go tests..."
	@cd agent && go test ./... -v || true

build:
	@echo "Building containers..."
	@docker build -t patchpulse-backend ./backend
	@docker build -t patchpulse-agent ./agent
	@docker build -t patchpulse-git-poller ./integrations/git

docker-up:
	@echo "Starting docker-compose..."
	@docker-compose up -d
	@echo "Services started. Backend: http://localhost:8000"

docker-down:
	@echo "Stopping docker-compose..."
	@docker-compose down

helm-install:
	@echo "Installing PatchPulse via Helm..."
	@helm install patchpulse-backend ./helm/backend
	@helm install patchpulse-agent ./helm/agent
	@echo "Installation complete"

helm-uninstall:
	@echo "Uninstalling PatchPulse..."
	@helm uninstall patchpulse-backend || true
	@helm uninstall patchpulse-agent || true
	@echo "Uninstallation complete"

run:
	@echo "Running backend locally..."
	@cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

clean:
	@echo "Cleaning build artifacts..."
	@find . -type d -name __pycache__ -exec rm -r {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@find . -type f -name "*.pyo" -delete 2>/dev/null || true
	@find . -type f -name "*.db" -delete 2>/dev/null || true
	@echo "Clean complete"

