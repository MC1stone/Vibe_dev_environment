#!/bin/bash

# NIR Intelligence Platform Setup Script
# This script handles all setup requirements including:
# - Docker container startup
# - Python virtual environment creation
# - Dependency installation
# - Database setup

set -e

echo "=========================================="
echo "NIR Intelligence Platform Setup"
echo "=========================================="
echo ""

# Check if running as root
if [ "$EUID" -eq 0 ]; then
    echo "WARNING: Running as root is not recommended."
    echo "Please run this script as a regular user."
    exit 1
fi

# Step 1: Check Docker
 echo "Step 1: Checking Docker..."
if ! command -v docker &> /dev/null; then
    echo "ERROR: Docker is not installed."
    echo "Please install Docker first:"
    echo "  sudo apt-get update"
    echo "  sudo apt-get install docker.io docker-compose"
    echo "  sudo systemctl enable --now docker"
    echo "  sudo usermod -aG docker $USER"
    echo "Then log out and back in."
    exit 1
fi

if ! command -v docker-compose &> /dev/null; then
    echo "ERROR: docker-compose is not installed."
    echo "Please install docker-compose:"
    echo "  sudo apt-get install docker-compose-plugin"
    exit 1
fi

echo "✓ Docker is installed"
echo ""

# Step 2: Start Docker Containers
echo "Step 2: Starting Docker containers..."
cd "$(dirname "$0")"

# Pull images first (this may take a while)
echo "Pulling Docker images..."
docker compose -f docker/docker-compose.yml pull

# Start containers
echo "Starting containers..."
docker compose -f docker/docker-compose.yml up -d

# Wait for services to be ready
echo "Waiting for services to initialize..."
sleep 10

# Check if containers are running
echo "Checking container status..."
docker ps --filter "name=nir_*" --format "{{.Names}}: {{.Status}}"

echo "✓ Docker containers started"
echo ""

# Step 3: Set up Python Virtual Environment
echo "Step 3: Setting up Python virtual environment..."

# Check if python3 is available
if ! command -v python3 &> /dev/null; then
    echo "ERROR: Python3 is not installed."
    echo "Please install Python3:"
    echo "  sudo apt-get install python3 python3-venv python3-pip"
    exit 1
fi

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip

# Install Python dependencies
echo "Installing Python dependencies..."
pip install -r requirements.txt

echo "✓ Python environment set up"
echo ""

# Step 4: Set up Django
echo "Step 4: Setting up Django application..."
cd django_app

# Create necessary directories
mkdir -p uploads reports static media

# Run migrations
echo "Running database migrations..."
python manage.py migrate

echo "✓ Django setup complete"
echo ""

# Step 5: Pull Mistral model in Ollama
echo "Step 5: Pulling Mistral model in Ollama..."
# This may take a while depending on your internet connection
curl -X POST http://localhost:11434/api/pull -d '{"name": "mistral"}' \
    -H "Content-Type: application/json" \
    --progress-bar

echo "✓ Mistral model pulled"
echo ""

# Step 6: Display Setup Summary
echo "=========================================="
echo "Setup Complete!"
echo "=========================================="
echo ""
echo "Services running:"
echo "  Django:      http://localhost:8000"
echo "  n8n:         http://localhost:5678"
echo "  Ollama:      http://localhost:11434"
echo "  PostgreSQL:  localhost:5432"
echo "  Qdrant:      http://localhost:6333"
echo ""
echo "To start the Django server:"
echo "  cd django_app"
echo "  source ../venv/bin/activate"
echo "  python manage.py runserver"
echo ""
echo "To stop all services:"
echo "  docker compose -f docker/docker-compose.yml down"
echo ""
echo "Note: The first run may take a few minutes for all services to fully initialize."
echo ""
