#!/bin/bash

# Quick Start Script for NIR Intelligence Platform
# This script provides step-by-step instructions for starting the system

echo "=========================================="
echo "NIR Intelligence Platform - Quick Start Guide"
echo "=========================================="
echo ""

echo "This script will guide you through starting the NIR Intelligence Platform."
echo ""

# Check if we're in the right directory
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

if [ ! -f "$PROJECT_ROOT/docker/docker-compose.yml" ]; then
    echo "Error: Please run this script from the nir_platform directory or its parent."
    echo "Current directory: $(pwd)"
    echo "Expected: $PROJECT_ROOT"
    exit 1
fi

echo "Project directory: $PROJECT_ROOT"
echo ""

# Step 1: Check Docker
echo "Step 1: Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "  ✗ Docker is not installed."
    echo "  Please install Docker first:"
    echo "    sudo apt-get update"
    echo "    sudo apt-get install -y docker.io docker-compose"
    echo ""
    exit 1
fi

if ! docker info &> /dev/null; then
    echo "  ✗ Docker daemon is not running."
    echo "  Please start Docker:"
    echo "    sudo systemctl start docker"
    echo "  Or:"
    echo "    sudo service docker start"
    echo ""
    exit 1
fi

echo "  ✓ Docker is running"
echo ""

# Step 2: Check docker-compose
echo "Step 2: Checking docker-compose..."
if command -v docker-compose &> /dev/null; then
    COMPOSE_CMD="docker-compose"
    echo "  ✓ docker-compose is available"
elif docker compose version &> /dev/null; then
    COMPOSE_CMD="docker compose"
    echo "  ✓ docker compose plugin is available"
else
    echo "  ✗ docker-compose is not installed."
    echo "  Please install it:"
    echo "    sudo apt-get install -y docker-compose-plugin"
    echo "  Or use pip:"
    echo "    pip install docker-compose"
    echo ""
    exit 1
fi
echo ""

# Step 3: Stop existing containers
echo "Step 3: Stopping existing containers..."
cd "$PROJECT_ROOT/docker"
$COMPOSE_CMD down 2>/dev/null || true
echo "  ✓ Containers stopped"
echo ""

# Step 4: Pull latest changes
echo "Step 4: Pulling latest code changes..."
cd "$PROJECT_ROOT"
git pull origin main
echo "  ✓ Code updated"
echo ""

# Step 5: Start containers
echo "Step 5: Starting containers..."
cd "$PROJECT_ROOT/docker"
$COMPOSE_CMD up -d --build
echo ""
echo "  Containers are starting..."
echo ""

# Step 6: Wait and verify
echo "Step 6: Waiting for services to initialize (30 seconds)..."
sleep 30
echo ""

echo "Checking service status:"

# Check PostgreSQL
if docker exec nir_postgres pg_isready -U postgres -d nir_db 2>/dev/null; then
    echo "  ✓ PostgreSQL is ready"
else
    echo "  ✗ PostgreSQL is not ready yet"
fi

# Check Qdrant
if curl -s http://localhost:6333 >/dev/null 2>&1; then
    echo "  ✓ Qdrant is ready (http://localhost:6333/dashboard)"
else
    echo "  ✗ Qdrant is not ready yet"
fi

# Check Ollama
if curl -s http://localhost:11435/api/tags >/dev/null 2>&1; then
    echo "  ✓ Ollama is ready (http://localhost:11435)"
else
    echo "  ✗ Ollama is not ready yet"
fi

# Check n8n
if curl -s http://localhost:5678 >/dev/null 2>&1; then
    echo "  ✓ n8n is ready (http://localhost:5678)"
else
    echo "  ✗ n8n is not ready yet"
fi

echo ""

# Step 7: Run Django migrations
echo "Step 7: Running Django migrations..."
cd "$PROJECT_ROOT/django_app"
python3 manage.py migrate
echo "  ✓ Migrations completed"
echo ""

# Step 8: Create superuser
echo "Step 8: Creating Django superuser..."
echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@nir.local', 'nir2024') if not User.objects.filter(username='admin').exists() else None" | python3 manage.py shell
echo "  ✓ Superuser created (username: admin, password: nir2024)"
echo ""

# Step 9: Pull Mistral model
echo "Step 9: Pulling Mistral model into Ollama..."
curl -X POST http://localhost:11435/api/pull -d '{"name": "mistral"}' -H "Content-Type: application/json"
echo ""
echo "  ✓ Mistral model pull initiated (this may take a while)"
echo ""

# Final status
echo "=========================================="
echo "System is starting up!"
echo "=========================================="
echo ""
echo "Access the following services:"
echo "  Django:      http://localhost:8000"
echo "  Qdrant:      http://localhost:6333/dashboard"
echo "  n8n:         http://localhost:5678"
echo "  Ollama:      http://localhost:11435"
echo "  MCP Server:  http://localhost:8001"
echo ""
echo "To start Django development server:"
echo "  cd $PROJECT_ROOT/django_app"
echo "  python3 manage.py runserver"
echo ""
echo "Credentials:"
echo "  Django: admin / nir2024"
echo "  n8n:    admin / nir2024"
echo "  PostgreSQL: postgres / postgres"
echo ""
echo "Note: Ollama will continue pulling the Mistral model in the background."
echo "      You can check progress with: curl http://localhost:11435/api/tags"
echo ""
