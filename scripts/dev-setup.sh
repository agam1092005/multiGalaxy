#!/bin/bash

# Multi-Galaxy-Note Development Setup Script

echo "🚀 Setting up Multi-Galaxy-Note development environment..."

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker and try again."
    exit 1
fi

# Create environment file if it doesn't exist
if [ ! -f backend/.env ]; then
    echo "📝 Creating backend environment file..."
    cp backend/.env.example backend/.env
    echo "✅ Created backend/.env from template"
fi

# Start the development environment
echo "🐳 Starting Docker containers..."
docker-compose up -d postgres redis

echo "⏳ Waiting for services to be ready..."
sleep 10

# Check if services are healthy
echo "🔍 Checking service health..."
docker-compose ps

echo "✅ Development environment is ready!"
echo ""
echo "📋 Next steps:"
echo "  1. Start the backend: cd backend && pip install -r requirements.txt && uvicorn main:app --reload"
echo "  2. Start the frontend: cd frontend && npm start"
echo "  3. Or use Docker: docker-compose up"
echo ""
echo "🌐 Access points:"
echo "  - Frontend: http://localhost:3000"
echo "  - Backend API: http://localhost:8000"
echo "  - API Docs: http://localhost:8000/docs"
echo "  - PostgreSQL: localhost:5432"
echo "  - Redis: localhost:6379"