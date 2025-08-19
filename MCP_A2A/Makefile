# MCP A2A Trading System - Makefile
# Provides convenient commands for development, testing, and deployment

.PHONY: help install install-dev clean test test-unit test-integration lint format check run run-services stop-services docs build deploy

# Default target
help:
	@echo "MCP A2A Trading System - Available Commands:"
	@echo ""
	@echo "Setup and Installation:"
	@echo "  install          Install production dependencies"
	@echo "  install-dev      Install development dependencies"
	@echo "  install-all      Install all dependencies (dev, docs, monitoring)"
	@echo "  clean            Clean build artifacts and cache files"
	@echo ""
	@echo "Development:"
	@echo "  format           Format code with black and isort"
	@echo "  lint             Run linting with flake8 and mypy"
	@echo "  check            Run all code quality checks"
	@echo "  pre-commit       Install pre-commit hooks"
	@echo ""
	@echo "Testing:"
	@echo "  test             Run all tests"
	@echo "  test-unit        Run unit tests only"
	@echo "  test-integration Run integration tests only"
	@echo "  test-smoke       Run smoke tests only"
	@echo "  test-coverage    Run tests with coverage report"
	@echo ""
	@echo "Services:"
	@echo "  run              Start the complete trading system"
	@echo "  run-services     Start all services in background"
	@echo "  stop-services    Stop all running services"
	@echo "  health-check     Check health of all services"
	@echo ""
	@echo "Documentation:"
	@echo "  docs             Generate documentation"
	@echo "  docs-serve       Serve documentation locally"
	@echo ""
	@echo "Build and Deploy:"
	@echo "  build            Build distribution packages"
	@echo "  deploy           Deploy to production (requires configuration)"
	@echo ""

# =============================================================================
# SETUP AND INSTALLATION
# =============================================================================

install:
	pip install -e .

install-dev:
	pip install -e ".[dev,test]"

install-all:
	pip install -e ".[dev,test,docs,monitoring,all]"

clean:
	@echo "Cleaning build artifacts and cache files..."
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info/
	rm -rf .pytest_cache/
	rm -rf .coverage
	rm -rf htmlcov/
	rm -rf .mypy_cache/
	rm -rf __pycache__/
	find . -type d -name "__pycache__" -exec rm -rf {} +
	find . -type f -name "*.pyc" -delete
	find . -type f -name "*.pyo" -delete
	@echo "✓ Cleanup completed"

# =============================================================================
# DEVELOPMENT
# =============================================================================

format:
	@echo "Formatting code..."
	black MCP_A2A/ tests/
	isort MCP_A2A/ tests/
	@echo "✓ Code formatting completed"

lint:
	@echo "Running linting..."
	flake8 MCP_A2A/ tests/
	mypy MCP_A2A/
	@echo "✓ Linting completed"

check: format lint
	@echo "✓ All code quality checks passed"

pre-commit:
	@echo "Installing pre-commit hooks..."
	pre-commit install
	@echo "✓ Pre-commit hooks installed"

# =============================================================================
# TESTING
# =============================================================================

test:
	@echo "Running all tests..."
	python -m pytest tests/ -v --tb=short

test-unit:
	@echo "Running unit tests..."
	python -m pytest tests/ -v --tb=short -k "not integration"

test-integration:
	@echo "Running integration tests..."
	python MCP_A2A/tests/run_integration_tests.py

test-smoke:
	@echo "Running smoke tests..."
	python -m pytest MCP_A2A/tests/test_smoke.py -v

test-coverage:
	@echo "Running tests with coverage..."
	python -m pytest tests/ --cov=MCP_A2A --cov-report=html --cov-report=term-missing
	@echo "✓ Coverage report generated in htmlcov/"

# =============================================================================
# SERVICES
# =============================================================================

run:
	@echo "Starting MCP A2A Trading System..."
	python -m MCP_A2A.main

run-services:
	@echo "Starting all services in background..."
	@echo "Starting MCP Servers..."
	python -m MCP_A2A.mcp_servers.market_data_server &
	python -m MCP_A2A.mcp_servers.technical_analysis_server &
	python -m MCP_A2A.mcp_servers.trading_execution_server &
	@echo "Starting Agent Services..."
	python -m MCP_A2A.agents.fundamental_analyst_agent &
	python -m MCP_A2A.agents.technical_analyst_agent &
	python -m MCP_A2A.agents.risk_manager_agent &
	python -m MCP_A2A.agents.trade_executor_agent &
	python -m MCP_A2A.agents.portfolio_manager_agent &
	@echo "✓ All services started in background"
	@echo "Use 'make stop-services' to stop all services"

stop-services:
	@echo "Stopping all services..."
	pkill -f "market_data_server" || true
	pkill -f "technical_analysis_server" || true
	pkill -f "trading_execution_server" || true
	pkill -f "fundamental_analyst_agent" || true
	pkill -f "technical_analyst_agent" || true
	pkill -f "risk_manager_agent" || true
	pkill -f "trade_executor_agent" || true
	pkill -f "portfolio_manager_agent" || true
	@echo "✓ All services stopped"

health-check:
	@echo "Checking health of all services..."
	python -c "import asyncio; from MCP_A2A.utils.health_check import HealthChecker; asyncio.run(HealthChecker().check_all_services())"

# =============================================================================
# DOCUMENTATION
# =============================================================================

docs:
	@echo "Generating documentation..."
	sphinx-build -b html docs/ docs/_build/html/
	@echo "✓ Documentation generated in docs/_build/html/"

docs-serve:
	@echo "Serving documentation locally..."
	cd docs/_build/html && python -m http.server 8080
	@echo "Documentation available at http://localhost:8080"

# =============================================================================
# BUILD AND DEPLOY
# =============================================================================

build: clean
	@echo "Building distribution packages..."
	python setup.py sdist bdist_wheel
	@echo "✓ Distribution packages built in dist/"

deploy:
	@echo "Deploying to production..."
	@echo "⚠️  This is a placeholder - configure your deployment process"
	@echo "Consider using Docker, Kubernetes, or your preferred deployment method"

# =============================================================================
# DOCKER SUPPORT
# =============================================================================

docker-build:
	@echo "Building Docker image..."
	docker build -t mcp-a2a-trading:latest .
	@echo "✓ Docker image built"

docker-run:
	@echo "Running Docker container..."
	docker run -p 8000:8000 -p 9000:9000 -p 9001:9001 -p 9002:9002 mcp-a2a-trading:latest

docker-compose-up:
	@echo "Starting services with Docker Compose..."
	docker-compose up -d
	@echo "✓ Services started with Docker Compose"

docker-compose-down:
	@echo "Stopping Docker Compose services..."
	docker-compose down
	@echo "✓ Docker Compose services stopped"

# =============================================================================
# MONITORING AND DEBUGGING
# =============================================================================

logs:
	@echo "Showing recent logs..."
	tail -f logs/mcp_a2a_trading.log

monitor:
	@echo "Starting monitoring dashboard..."
	@echo "⚠️  Configure your monitoring solution (Prometheus, Grafana, etc.)"

profile:
	@echo "Running performance profiling..."
	python -m cProfile -o profile_output.prof -m MCP_A2A.main
	@echo "✓ Profile saved to profile_output.prof"

# =============================================================================
# DATABASE AND MIGRATIONS (Future)
# =============================================================================

db-init:
	@echo "⚠️  Database initialization not implemented yet"
	@echo "This system currently uses in-memory storage"

db-migrate:
	@echo "⚠️  Database migrations not implemented yet"
	@echo "This system currently uses in-memory storage"

# =============================================================================
# SECURITY
# =============================================================================

security-check:
	@echo "Running security checks..."
	pip-audit
	bandit -r MCP_A2A/
	@echo "✓ Security checks completed"

# =============================================================================
# UTILITIES
# =============================================================================

requirements-update:
	@echo "Updating requirements.txt..."
	pip-compile requirements.in
	@echo "✓ Requirements updated"

env-setup:
	@echo "Setting up environment..."
	cp .env.example .env
	@echo "✓ Environment file created - please customize .env"

version:
	@echo "MCP A2A Trading System v1.0.0"
	@python -c "import MCP_A2A; print(f'Python package version: {MCP_A2A.__version__ if hasattr(MCP_A2A, \"__version__\") else \"1.0.0\"}')"

# =============================================================================
# QUICK START
# =============================================================================

quickstart: install-dev env-setup
	@echo ""
	@echo "🚀 Quick Start Setup Complete!"
	@echo ""
	@echo "Next steps:"
	@echo "1. Customize your .env file if needed"
	@echo "2. Run 'make test-smoke' to verify installation"
	@echo "3. Run 'make run' to start the trading system"
	@echo "4. Visit http://localhost:8000/docs for API documentation"
	@echo ""