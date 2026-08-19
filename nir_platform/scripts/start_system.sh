#!/bin/bash

# NIR Intelligence Platform Startup Script
# This script starts all components of the NIR Intelligence Platform

set -e

echo "=========================================="
echo "NIR Intelligence Platform Startup"
echo "=========================================="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Get the directory where this script is located
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
DOCKER_DIR="$PROJECT_ROOT/docker"
DJANGO_DIR="$PROJECT_ROOT/django_app"

echo "Project Root: $PROJECT_ROOT"
echo "Docker Directory: $DOCKER_DIR"
echo "Django Directory: $DJANGO_DIR"
echo ""

# Function to check if a command exists
command_exists() {
    command -v "$1" >/dev/null 2>&1
}

# Function to check if Docker is running
check_docker() {
    if command_exists docker; then
        if docker info >/dev/null 2>&1; then
            echo -e "${GREEN}✓ Docker is running${NC}"
            return 0
        else
            echo -e "${RED}✗ Docker is not running${NC}"
            return 1
        fi
    else
        echo -e "${RED}✗ Docker is not installed${NC}"
        return 1
    fi
}

# Function to check if docker-compose is available
check_docker_compose() {
    if command_exists docker-compose; then
        echo -e "${GREEN}✓ docker-compose is available${NC}"
        COMPOSE_CMD="docker-compose"
        return 0
    elif docker compose version >/dev/null 2>&1; then
        echo -e "${GREEN}✓ docker compose plugin is available${NC}"
        COMPOSE_CMD="docker compose"
        return 0
    else
        echo -e "${RED}✗ Neither docker-compose nor docker compose plugin is available${NC}"
        return 1
    fi
}

# Function to stop existing containers
stop_containers() {
    echo -e "${YELLOW}Stopping existing containers...${NC}"
    cd "$DOCKER_DIR"
    if [ -n "$COMPOSE_CMD" ]; then
        $COMPOSE_CMD down 2>/dev/null || true
    else
        docker stop nir_django nir_mcp nir_ollama nir_qdrant nir_postgres nir_n8n 2>/dev/null || true
        docker rm nir_django nir_mcp nir_ollama nir_qdrant nir_postgres nir_n8n 2>/dev/null || true
    fi
    echo -e "${GREEN}✓ Containers stopped${NC}"
}

# Function to pull latest images
pull_images() {
    echo -e "${YELLOW}Pulling latest Docker images...${NC}"
    cd "$DOCKER_DIR"
    if [ -n "$COMPOSE_CMD" ]; then
        $COMPOSE_CMD pull
    else
        echo "No compose command available, skipping image pull"
    fi
    echo -e "${GREEN}✓ Images pulled${NC}"
}

# Function to build and start containers
start_containers() {
    echo -e "${YELLOW}Building and starting containers...${NC}"
    cd "$DOCKER_DIR"
    if [ -n "$COMPOSE_CMD" ]; then
        $COMPOSE_CMD up -d --build
    else
        echo "No compose command available, cannot start containers"
        return 1
    fi
    echo -e "${GREEN}✓ Containers started${NC}"
}

# Function to wait for services to be ready
wait_for_services() {
    echo -e "${YELLOW}Waiting for services to initialize...${NC}"
    
    # Wait for PostgreSQL
    echo -n "Waiting for PostgreSQL..."
    for i in {1..30}; do
        if docker exec nir_postgres pg_isready -U postgres -d nir_db 2>/dev/null; then
            echo -e " ${GREEN}✓ PostgreSQL is ready${NC}"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    
    # Wait for Qdrant
    echo -n "Waiting for Qdrant..."
    for i in {1..30}; do
        if curl -s http://localhost:6333 >/dev/null 2>&1; then
            echo -e " ${GREEN}✓ Qdrant is ready${NC}"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    
    # Wait for Ollama
    echo -n "Waiting for Ollama..."
    for i in {1..30}; do
        if curl -s http://localhost:11435/api/tags >/dev/null 2>&1; then
            echo -e " ${GREEN}✓ Ollama is ready${NC}"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    
    # Wait for n8n
    echo -n "Waiting for n8n..."
    for i in {1..30}; do
        if curl -s http://localhost:5678 >/dev/null 2>&1; then
            echo -e " ${GREEN}✓ n8n is ready${NC}"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
    
    # Wait for Django
    echo -n "Waiting for Django..."
    for i in {1..30}; do
        if curl -s http://localhost:8000 >/dev/null 2>&1; then
            echo -e " ${GREEN}✓ Django is ready${NC}"
            break
        fi
        sleep 1
        echo -n "."
    done
    echo ""
}

# Function to run Django migrations
run_migrations() {
    echo -e "${YELLOW}Running Django migrations...${NC}"
    cd "$DJANGO_DIR"
    python3 manage.py migrate
    echo -e "${GREEN}✓ Migrations completed${NC}"
}

# Function to create superuser (optional)
create_superuser() {
    echo -e "${YELLOW}Creating Django superuser...${NC}"
    cd "$DJANGO_DIR"
    echo "from django.contrib.auth import get_user_model; User = get_user_model(); User.objects.create_superuser('admin', 'admin@nir.local', 'nir2024') if not User.objects.filter(username='admin').exists() else None" | python3 manage.py shell
    echo -e "${GREEN}✓ Superuser created or already exists${NC}"
}

# Function to pull Mistral model into Ollama
pull_mistral_model() {
    echo -e "${YELLOW}Pulling Mistral model into Ollama...${NC}"
    curl -X POST http://localhost:11435/api/pull -d '{"name": "mistral"}' -H "Content-Type: application/json"
    echo -e "${GREEN}✓ Mistral model pull initiated${NC}"
}

# Function to start Django development server
start_django() {
    echo -e "${YELLOW}Starting Django development server...${NC}"
    echo "Access Django at: http://localhost:8000"
    echo "Press Ctrl+C to stop the server"
    echo ""
    cd "$DJANGO_DIR"
    python3 manage.py runserver
}

# Function to show system status
show_status() {
    echo ""
    echo "=========================================="
    echo "System Status"
    echo "=========================================="
    echo ""
    
    if command_exists docker; then
        echo -e "${YELLOW}Docker Containers:${NC}"
        docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" --filter "name=nir_" 2>/dev/null || docker ps 2>/dev/null || echo "No containers running"
        echo ""
    fi
    
    echo -e "${YELLOW}Service URLs:${NC}"
    echo "  Django:      http://localhost:8000"
    echo "  Qdrant:      http://localhost:6333/dashboard"
    echo "  n8n:         http://localhost:5678"
    echo "  Ollama:      http://localhost:11435"
    echo "  MCP Server:  http://localhost:8001"
    echo ""
    
    echo -e "${YELLOW}Access Credentials:${NC}"
    echo "  PostgreSQL:  user=postgres, password=postgres, db=nir_db, port=5432"
    echo "  n8n:         user=admin, password=nir2024"
    echo "  Django:      user=admin, password=nir2024 (after superuser creation)"
    echo ""
}

# Main execution
main() {
    echo "Starting NIR Intelligence Platform..."
    echo ""
    
    # Check prerequisites
    echo -e "${YELLOW}Checking prerequisites...${NC}"
    check_docker || { echo "Please start Docker and try again."; exit 1; }
    check_docker_compose || { echo "Please install docker-compose and try again."; exit 1; }
    echo ""
    
    # Stop existing containers
    stop_containers
    echo ""
    
    # Pull latest images
    pull_images
    echo ""
    
    # Start containers
    start_containers
    echo ""
    
    # Wait for services
    wait_for_services
    echo ""
    
    # Run migrations
    run_migrations
    echo ""
    
    # Create superuser
    create_superuser
    echo ""
    
    # Pull Mistral model
    pull_mistral_model
    echo ""
    
    # Show status
    show_status
    
    # Start Django
    start_django
}

# Run main function
main "$@"
