# Multi-Galaxy-Note Development Makefile

.PHONY: help setup start stop clean test build

# Default target
help:
	@echo "Multi-Galaxy-Note Development Commands:"
	@echo "  setup     - Set up development environment"
	@echo "  start     - Start all services with Docker Compose"
	@echo "  stop      - Stop all services"
	@echo "  clean     - Clean up containers and volumes"
	@echo "  test      - Run all tests"
	@echo "  build     - Build all Docker images"
	@echo "  dev-be    - Start backend in development mode"
	@echo "  dev-fe    - Start frontend in development mode"

# Set up development environment
setup:
	@echo "🚀 Setting up development environment..."
	@./scripts/dev-setup.sh

# Start all services
start:
	@echo "🐳 Starting all services..."
	@docker-compose up -d

# Stop all services
stop:
	@echo "🛑 Stopping all services..."
	@docker-compose down

# Clean up everything
clean:
	@echo "🧹 Cleaning up containers and volumes..."
	@docker-compose down -v --remove-orphans
	@docker system prune -f

# Run tests
test:
	@echo "🧪 Running backend tests..."
	@cd backend && python -m pytest
	@echo "🧪 Running frontend tests..."
	@cd frontend && npm test -- --watchAll=false

# Build Docker images
build:
	@echo "🔨 Building Docker images..."
	@docker-compose build

# Development mode - backend only
dev-be:
	@echo "🚀 Starting backend in development mode..."
	@cd backend && uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Development mode - frontend only
dev-fe:
	@echo "🚀 Starting frontend in development mode..."
	@cd frontend && npm start

# Install dependencies
install:
	@echo "📦 Installing backend dependencies..."
	@cd backend && pip install -r requirements.txt
	@echo "📦 Installing frontend dependencies..."
	@cd frontend && npm install