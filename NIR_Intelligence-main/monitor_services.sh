#!/bin/bash

# NIR_MISTRAL Service Monitoring Script
# This script monitors all Docker services and verifies they're available at their designated ports

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if a port is open
check_port() {
    local host=$1
    local port=$2
    local service_name=$3
    
    if nc -z "$host" "$port" 2>/dev/null; then
        echo -e "${GREEN}✅${NC} $service_name is available at $host:$port"
        return 0
    else
        echo -e "${RED}❌${NC} $service_name is NOT available at $host:$port"
        return 1
    fi
}

# Function to check HTTP endpoint
check_http() {
    local url=$1
    local service_name=$2
    
    if curl -s -f "$url" > /dev/null 2>&1; then
        echo -e "${GREEN}✅${NC} $service_name HTTP endpoint $url is responding"
        return 0
    else
        echo -e "${RED}❌${NC} $service_name HTTP endpoint $url is NOT responding"
        return 1
    fi
}

# Function to check Docker container status
check_container() {
    local container_name=$1
    local service_name=$2
    
    if docker ps --format '{{.Names}}' | grep -q "^${container_name}$"; then
        local status=$(docker ps --format '{{.Status}}' --filter "name=^/${container_name}$" | head -1)
        if echo "$status" | grep -q "Up"; then
            echo -e "${GREEN}✅${NC} $service_name container is running ($status)"
            return 0
        else
            echo -e "${RED}❌${NC} $service_name container is not running ($status)"
            return 1
        fi
    else
        echo -e "${RED}❌${NC} $service_name container is not running"
        return 1
    fi
}

echo "🚀 NIR_MISTRAL Service Monitoring"
echo "================================"
echo ""

# Check if Docker is running
if ! docker info > /dev/null 2>&1; then
    echo -e "${RED}❌ Docker is not running. Please start Docker first.${NC}"
    echo ""
    echo "💡 On Linux: sudo systemctl start docker"
    echo "💡 On Mac: Open Docker Desktop"
    echo "💡 On Windows: Start Docker Desktop"
    exit 1
fi

echo -e "${GREEN}✅ Docker is running${NC}"
echo ""

# Determine which compose file to use
if [ -f "docker-compose.prod.yml" ] && [ "$1" = "--production" ] || [ "$1" = "-p" ]; then
    COMPOSE_FILE="docker-compose.prod.yml"
    MODE="production"
else
    COMPOSE_FILE="docker-compose.yml"
    MODE="development"
fi

echo "📋 Mode: $MODE"
echo "📄 Compose file: $COMPOSE_FILE"
echo ""

# Check if containers are running
echo "🐳 Checking Docker containers..."
echo "--------------------------------"

# Define services to check
declare -A SERVICES=(
    ["django_app"]="Django Web Application"
    ["web"]="Django Web Application"
    ["postgresql"]="PostgreSQL Database"
    ["postgres"]="PostgreSQL Database"
    ["weaviate"]="Weaviate Vector Database"
    ["faiss"]="Faiss Similarity Search"
    ["ollama"]="Ollama AI Service"
    ["redis"]="Redis Cache"
    ["flower_server"]="Flower Federated Learning"
    ["celery_worker"]="Celery Worker"
    ["celery_beat"]="Celery Beat"
    ["nginx"]="Nginx Reverse Proxy"
    ["prometheus"]="Prometheus Monitoring"
    ["grafana"]="Grafana Dashboards"
)

# Check all containers
running_containers=0
total_containers=0

for container in "${!SERVICES[@]}"; do
    if check_container "$container" "${SERVICES[$container]}"; then
        ((running_containers++))
    fi
    ((total_containers++))
done

echo ""
echo "📊 Container Summary: $running_containers/$total_containers containers running"
echo ""

# Check ports
echo "🌐 Checking service ports..."
echo "----------------------------"

# Define ports to check
declare -A PORTS=(
    ["8000"]="Django Web Application"
    ["5432"]="PostgreSQL Database"
    ["8080"]="Weaviate Vector Database"
    ["8081"]="Faiss Similarity Search"
    ["11434"]="Ollama AI Service"
    ["6379"]="Redis Cache"
    ["5555"]="Flower Federated Learning"
    ["5556"]="Flower Management API"
    ["9090"]="Prometheus Monitoring"
    ["3000"]="Grafana Dashboards"
    ["80"]="Nginx HTTP"
    ["443"]="Nginx HTTPS"
)

# Check all ports
open_ports=0
total_ports=0

for port in "${!PORTS[@]}"; do
    if check_port "localhost" "$port" "${PORTS[$port]}"; then
        ((open_ports++))
    fi
    ((total_ports++))
done

echo ""
echo "📊 Port Summary: $open_ports/$total_ports ports open"
echo ""

# Check HTTP endpoints
echo "🔗 Checking HTTP endpoints..."
echo "-----------------------------"

# Define HTTP endpoints to check
declare -A ENDPOINTS=(
    ["http://localhost:8000/health/"]="Django Health Check"
    ["http://localhost:8080/v1/.well-known/ready"]="Weaviate Health"
    ["http://localhost:11434/api/tags"]="Ollama API"
    ["http://localhost:8081/health"]="Faiss Health"
    ["http://localhost:5556/health"]="Flower Management"
    ["http://localhost:9090/"]="Prometheus"
    ["http://localhost:3000/"]="Grafana"
    ["http://localhost:80/"]="Nginx"
)

# Check all endpoints
working_endpoints=0
total_endpoints=0

for endpoint in "${!ENDPOINTS[@]}"; do
    if check_http "$endpoint" "${ENDPOINTS[$endpoint]}"; then
        ((working_endpoints++))
    fi
    ((total_endpoints++))
done

echo ""
echo "📊 HTTP Endpoint Summary: $working_endpoints/$total_endpoints endpoints responding"
echo ""

# Detailed service information
echo "📋 Detailed Service Information"
echo "=============================="

# Django Application
if check_port "localhost" "8000" "Django"; then
    echo -e "${BLUE}🔹 Django Application:${NC}"
    echo "   URL: http://localhost:8000"
    echo "   Admin: http://localhost:8000/admin"
    echo "   Health: http://localhost:8000/health/"
    echo ""
fi

# Database
if check_port "localhost" "5432" "PostgreSQL"; then
    echo -e "${BLUE}🔹 PostgreSQL Database:${NC}"
    echo "   Host: localhost"
    echo "   Port: 5432"
    echo "   Database: nir_mistral"
    echo "   User: nir_user"
    echo ""
fi

# AI Services
if check_port "localhost" "8080" "Weaviate"; then
    echo -e "${BLUE}🔹 Weaviate:${NC}"
    echo "   URL: http://localhost:8080"
    echo "   Health: http://localhost:8080/v1/.well-known/ready"
    echo ""
fi

if check_port "localhost" "11434" "Ollama"; then
    echo -e "${BLUE}🔹 Ollama:${NC}"
    echo "   URL: http://localhost:11434"
    echo "   API: http://localhost:11434/api/tags"
    echo ""
fi

if check_port "localhost" "8081" "Faiss"; then
    echo -e "${BLUE}🔹 Faiss:${NC}"
    echo "   URL: http://localhost:8081"
    echo "   Health: http://localhost:8081/health"
    echo ""
fi

# Monitoring
if check_port "localhost" "9090" "Prometheus"; then
    echo -e "${BLUE}🔹 Prometheus:${NC}"
    echo "   URL: http://localhost:9090"
    echo ""
fi

if check_port "localhost" "3000" "Grafana"; then
    echo -e "${BLUE}🔹 Grafana:${NC}"
    echo "   URL: http://localhost:3000"
    echo "   Credentials: admin/admin"
    echo ""
fi

# Federated Learning
if check_port "localhost" "5555" "Flower"; then
    echo -e "${BLUE}🔹 Flower Server:${NC}"
    echo "   URL: http://localhost:5555"
    echo ""
fi

if check_port "localhost" "5556" "Flower Management"; then
    echo -e "${BLUE}🔹 Flower Management:${NC}"
    echo "   URL: http://localhost:5556"
    echo "   Health: http://localhost:5556/health"
    echo ""
fi

# Final summary
echo "🎯 Final Status Summary"
echo "======================"

if [ $running_containers -eq $total_containers ] && [ $open_ports -eq $total_ports ] && [ $working_endpoints -eq $total_endpoints ]; then
    echo -e "${GREEN}🎉 ALL SERVICES ARE RUNNING CORRECTLY! 🎉${NC}"
    echo ""
    echo "You can now access:"
    echo "  - Web Application: http://localhost:8000"
    echo "  - Admin Panel: http://localhost:8000/admin"
    echo "  - All AI services at their respective ports"
    exit 0
else
    echo -e "${YELLOW}⚠️  Some services are not running correctly${NC}"
    echo ""
    echo "💡 Troubleshooting tips:"
    echo "  1. Check Docker logs: docker-compose -f $COMPOSE_FILE logs"
    echo "  2. Check specific service logs: docker-compose -f $COMPOSE_FILE logs [service_name]"
    echo "  3. Restart services: docker-compose -f $COMPOSE_FILE restart"
    echo "  4. Check resource usage: docker stats"
    exit 1
fi