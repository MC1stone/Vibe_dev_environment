#!/bin/bash

# NIR_MISTRAL Simple Docker Startup Script
# This script provides a simpler approach without requiring Docker to be running for initial checks

set -e

echo "🚀 Starting NIR_MISTRAL Docker Infrastructure (Simple Mode)"
echo "=========================================================="

# Get the directory where the script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "📁 Working directory: $(pwd)"
echo ""

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Copying .env.docker to .env..."
    cp .env.docker .env
    echo "✅ Created .env file from template."
    echo ""
    echo "💡 Please edit the .env file to configure your settings:"
    echo "   - DJANGO_SECRET_KEY (change from default)"
    echo "   - POSTGRES_PASSWORD (change from default)"
    echo "   - Other settings as needed"
    echo ""
    echo "Then run this script again."
    exit 0
else
    echo "✅ .env file found."
fi

# Load environment variables from .env file
echo "🔍 Loading environment variables from .env file..."
set -o allexport
source .env
set +o allexport
echo "✅ Environment variables loaded."
echo ""

# Check required environment variables
if [ -z "${DJANGO_SECRET_KEY:-}" ] || [ "${DJANGO_SECRET_KEY:-}" = "your-production-secret-key-change-me" ]; then
    echo "⚠️  DJANGO_SECRET_KEY is not set or is default."
    echo "💡 Please edit the .env file and set a proper DJANGO_SECRET_KEY."
    exit 1
fi

if [ -z "${POSTGRES_PASSWORD:-}" ] || [ "${POSTGRES_PASSWORD:-}" = "nir_password_2026" ]; then
    echo "⚠️  POSTGRES_PASSWORD is not set or is default."
    echo "💡 Please edit the .env file and set a proper POSTGRES_PASSWORD."
    exit 1
fi

echo "✅ Environment variables look good!"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo "❌ Docker is not running. Please start Docker first."
    echo ""
    echo "💡 On Linux: sudo systemctl start docker"
    echo "💡 On Mac: Open Docker Desktop"
    echo "💡 On Windows: Start Docker Desktop"
    exit 1
fi

echo "✅ Docker is running."
echo ""

# Default to development mode
MODE="development"
COMPOSE_FILE="docker-compose.yml"

# Parse command line arguments
while [[ $# -gt 0 ]]; do
    case "$1" in
        --production|-p)
            MODE="production"
            COMPOSE_FILE="docker-compose.prod.yml"
            shift
            ;;
        --help|-h)
            echo "Usage: $0 [--production|-p] [--help|-h]"
            echo ""
            echo "Options:"
            echo "  --production, -p   Start in production mode"
            echo "  --help, -h         Show this help message"
            exit 0
            ;;
        *)
            echo "❌ Unknown option: $1"
            exit 1
            ;;
    esac
done

echo "📋 Mode: $MODE"
echo "📄 Compose file: $COMPOSE_FILE"
echo ""

# Start Docker containers
echo "🐳 Starting Docker containers..."

if [ "$MODE" = "production" ]; then
    echo "🏭 Building production images..."
    docker-compose -f $COMPOSE_FILE build --no-cache
fi

echo "🚀 Starting containers..."
docker-compose -f $COMPOSE_FILE up -d

echo "✅ Containers started!"
echo ""

# Wait for database to be ready
echo "⏳ Waiting for PostgreSQL to be ready..."
MAX_RETRIES=30
RETRY_DELAY=5

for ((i=1; i<=$MAX_RETRIES; i++)); do
    if docker-compose -f $COMPOSE_FILE exec postgres pg_isready -U nir_user -d nir_mistral > /dev/null 2>&1; then
        echo "✅ PostgreSQL is ready!"
        break
    else
        echo "⏳ Attempt $i/$MAX_RETRIES: PostgreSQL not ready yet..."
        sleep $RETRY_DELAY
    fi
    
    if [ $i -eq $MAX_RETRIES ]; then
        echo "❌ PostgreSQL did not become ready after $MAX_RETRIES attempts."
        echo "💡 Check the PostgreSQL logs with: docker-compose -f $COMPOSE_FILE logs postgres"
        exit 1
    fi
done

echo ""

# Run Django migrations
echo "🔄 Running Django migrations..."
docker-compose -f $COMPOSE_FILE exec django_app python django_project/manage.py migrate --noinput

echo "✅ Migrations completed!"
echo ""

# Pull Mistral model for Ollama
echo "🤖 Checking Mistral model for Ollama..."
if docker-compose -f $COMPOSE_FILE exec ollama ollama list 2>/dev/null | grep -q mistral; then
    echo "✅ Mistral model already exists."
else
    echo "📥 Downloading Mistral model (this may take a while)..."
    docker-compose -f $COMPOSE_FILE exec ollama ollama pull mistral
    echo "✅ Mistral model downloaded!"
fi

echo ""

# Test services
echo "🧪 Testing services..."

# Test Django application
if curl -s -f http://localhost:8000/health/ > /dev/null 2>&1; then
    echo "✅ Django application is healthy"
else
    echo "⚠️  Django application health check failed"
fi

# Test Weaviate
if curl -s -f http://localhost:8080/v1/.well-known/ready > /dev/null 2>&1; then
    echo "✅ Weaviate is healthy"
else
    echo "⚠️  Weaviate health check failed"
fi

# Test Ollama
if curl -s -f http://localhost:11434/api/tags > /dev/null 2>&1; then
    echo "✅ Ollama is healthy"
else
    echo "⚠️  Ollama health check failed"
fi

# Test Redis
if docker-compose -f $COMPOSE_FILE exec redis redis-cli ping > /dev/null 2>&1; then
    echo "✅ Redis is healthy"
else
    echo "⚠️  Redis health check failed"
fi

echo ""
echo "🎉 NIR_MISTRAL Docker Infrastructure is ready!"
echo ""
echo "🌐 Access the application at:"
echo "   - Web Application: http://localhost:8000"
echo "   - Admin Panel: http://localhost:8000/admin"
echo "   - Weaviate: http://localhost:8080"
echo "   - Ollama: http://localhost:11434"
echo "   - Redis: http://localhost:6379"
echo "   - Flower Server: http://localhost:5555"
echo "   - Flower Management: http://localhost:5556"
echo ""

if [ "$MODE" = "production" ]; then
    echo "🏭 Production services:"
    echo "   - Prometheus: http://localhost:9090"
    echo "   - Grafana: http://localhost:3000 (admin/admin)"
    echo "   - Nginx: http://localhost:80"
    echo ""
fi

echo "📊 To view logs, run:"
echo "   docker-compose -f $COMPOSE_FILE logs -f"
echo ""
echo "🛑 To stop the containers, run:"
echo "   docker-compose -f $COMPOSE_FILE down"
echo ""

echo "✨ Setup complete! Enjoy using NIR_MISTRAL! 🚀"