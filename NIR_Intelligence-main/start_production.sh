#!/bin/bash

# NIR_Mistral Production Startup Script
# This script provides a unified interface for starting the NIR_Mistral platform
# in production mode with all required services.

set -e  # Exit on error
set -u  # Exit on undefined variable
set -o pipefail  # Exit on pipe failure

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
PURPLE='\033[0;35m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$SCRIPT_DIR"

# Default values
ACTION="start"
ENV_FILE="$PROJECT_ROOT/.env"
COMPOSE_FILES=("docker-compose.yml")
BUILD_CACHE=true
FORCE_RECREATE=false
SHOW_LOGS=false
DETACHED=true

# Functions
function print_banner() {
    echo -e "${BLUE}
============================================
    NIR_MISTRAL PRODUCTION STARTUP SCRIPT
============================================
Version: 1.0.0
Project: NIR Intelligence Platform
============================================${NC}"
}

function print_usage() {
    echo -e "${YELLOW}Usage: $0 [OPTIONS] [ACTION]${NC}"
    echo ""
    echo "Actions:"
    echo "  start       Start all services (default)"
    echo "  stop        Stop all services"
    echo "  restart     Restart all services"
    echo "  build       Build Docker images"
    echo "  logs        Show service logs"
    echo "  status      Show service status"
    echo "  migrate     Run database migrations"
    echo "  createsuperuser  Create Django superuser"
    echo "  collectstatic   Collect static files"
    echo "  healthcheck    Run health checks"
    echo "  cleanup       Clean up Docker resources"
    echo ""
    echo "Options:"
    echo "  -h, --help            Show this help message"
    echo "  -e, --env FILE        Specify environment file (default: .env)"
    echo "  --no-cache            Build images without cache"
    echo "  --force-recreate      Force recreation of containers"
    echo "  --no-detach           Run containers in foreground"
    echo "  -f, --file FILE       Additional compose file"
    echo "  -v, --verbose         Verbose output"
    echo ""
    echo "Examples:"
    echo "  $0 start"
    echo "  $0 start --no-cache --force-recreate"
    echo "  $0 stop"
    echo "  $0 restart"
    echo "  $0 logs"
    echo "  $0 status"
    echo "  $0 migrate"
    echo "  $0 healthcheck"
    echo "  $0 -e .env.production start"
}

function check_prerequisites() {
    echo -e "${BLUE}Checking prerequisites...${NC}"
    
    # Check Docker
    if ! command -v docker &> /dev/null; then
        echo -e "${RED}Error: Docker is not installed. Please install Docker first.${NC}"
        echo "See: https://docs.docker.com/get-docker/"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker: $(docker --version)${NC}"
    
    # Check Docker Compose
    if ! command -v docker-compose &> /dev/null; then
        echo -e "${RED}Error: Docker Compose is not installed. Please install Docker Compose.${NC}"
        echo "See: https://docs.docker.com/compose/install/"
        exit 1
    fi
    echo -e "${GREEN}✓ Docker Compose: $(docker-compose --version)${NC}"
    
    # Check if we're in the right directory
    if [ ! -f "$PROJECT_ROOT/docker-compose.yml" ]; then
        echo -e "${RED}Error: Not in NIR_Mistral project directory.${NC}"
        echo "Please run this script from the NIR_Mistral project root."
        exit 1
    fi
    
    # Check environment file
    if [ ! -f "$ENV_FILE" ]; then
        echo -e "${YELLOW}Warning: Environment file not found: $ENV_FILE${NC}"
        echo "Using default configuration."
    else
        echo -e "${GREEN}✓ Environment file: $ENV_FILE${NC}"
    fi
    
    echo -e "${GREEN}All prerequisites checked!${NC}"
}

function load_environment() {
    if [ -f "$ENV_FILE" ]; then
        echo -e "${BLUE}Loading environment variables from $ENV_FILE...${NC}"
        # Export all variables from .env file
        set -o allexport
        source "$ENV_FILE"
        set +o allexport
    fi
}

function start_services() {
    echo -e "${BLUE}Starting NIR_Mistral services...${NC}"
    
    # Build compose command
    local compose_cmd="docker-compose"
    
    # Add compose files
    for file in "${COMPOSE_FILES[@]}"; do
        if [ -f "$file" ]; then
            compose_cmd+=" -f $file"
        fi
    done
    
    # Add options
    if [ "$BUILD_CACHE" = false ]; then
        compose_cmd+=" --no-cache"
    fi
    
    if [ "$FORCE_RECREATE" = true ]; then
        compose_cmd+=" --force-recreate"
    fi
    
    if [ "$DETACHED" = true ]; then
        compose_cmd+=" -d"
    fi
    
    # Start services
    echo -e "${YELLOW}Executing: $compose_cmd up${NC}"
    
    if [ "$VERBOSE" = true ]; then
        $compose_cmd up
    else
        $compose_cmd up 2>&1 | grep -E "(Starting|Recreating|Attaching|Created|PULL|Downloading|Waiting)" || true
    fi
    
    echo -e "${GREEN}Services started successfully!${NC}"
    
    # Show service status
    show_status
    
    # Show access information
    show_access_info
}

function stop_services() {
    echo -e "${BLUE}Stopping NIR_Mistral services...${NC}"
    
    local compose_cmd="docker-compose"
    for file in "${COMPOSE_FILES[@]}"; do
        if [ -f "$file" ]; then
            compose_cmd+=" -f $file"
        fi
    done
    
    echo -e "${YELLOW}Executing: $compose_cmd down${NC}"
    $compose_cmd down
    
    echo -e "${GREEN}Services stopped successfully!${NC}"
}

function restart_services() {
    echo -e "${BLUE}Restarting NIR_Mistral services...${NC}"
    stop_services
    sleep 2
    start_services
}

function build_images() {
    echo -e "${BLUE}Building Docker images...${NC}"
    
    local compose_cmd="docker-compose"
    for file in "${COMPOSE_FILES[@]}"; do
        if [ -f "$file" ]; then
            compose_cmd+=" -f $file"
        fi
    done
    
    if [ "$BUILD_CACHE" = false ]; then
        compose_cmd+=" --no-cache"
    fi
    
    echo -e "${YELLOW}Executing: $compose_cmd build${NC}"
    $compose_cmd build
    
    echo -e "${GREEN}Images built successfully!${NC}"
}

function show_logs() {
    echo -e "${BLUE}Showing service logs...${NC}"
    echo -e "${YELLOW}Press Ctrl+C to stop viewing logs${NC}"
    
    local compose_cmd="docker-compose"
    for file in "${COMPOSE_FILES[@]}"; do
        if [ -f "$file" ]; then
            compose_cmd+=" -f $file"
        fi
    done
    
    $compose_cmd logs -f
}

function show_status() {
    echo -e "${BLUE}Service Status:${NC}"
    
    local compose_cmd="docker-compose"
    for file in "${COMPOSE_FILES[@]}"; do
        if [ -f "$file" ]; then
            compose_cmd+=" -f $file"
        fi
    done
    
    $compose_cmd ps
    
    # Show resource usage
    echo -e "${BLUE}Resource Usage:${NC}"
    docker stats --no-stream --format "table {{.Container}},{{.Name}},{{.CPUPerc}},{{.MemUsage}},{{.MemPerc}},{{.NetIO}},{{.BlockIO}},{{.PIDs}}"
}

function run_migrations() {
    echo -e "${BLUE}Running database migrations...${NC}"
    
    local compose_cmd="docker-compose"
    for file in "${COMPOSE_FILES[@]}"; do
        if [ -f "$file" ]; then
            compose_cmd+=" -f $file"
        fi
    done
    
    echo -e "${YELLOW}Running: $compose_cmd exec django_app python django_project/manage.py migrate${NC}"
    $compose_cmd exec django_app python django_project/manage.py migrate
    
    echo -e "${GREEN}Database migrations completed!${NC}"
}

function create_superuser() {
    echo -e "${BLUE}Creating Django superuser...${NC}"
    
    local compose_cmd="docker-compose"
    for file in "${COMPOSE_FILES[@]}"; do
        if [ -f "$file" ]; then
            compose_cmd+=" -f $file"
        fi
    done
    
    echo -e "${YELLOW}Running: $compose_cmd exec django_app python django_project/manage.py createsuperuser${NC}"
    $compose_cmd exec -it django_app python django_project/manage.py createsuperuser
}

function collect_static() {
    echo -e "${BLUE}Collecting static files...${NC}"
    
    local compose_cmd="docker-compose"
    for file in "${COMPOSE_FILES[@]}"; do
        if [ -f "$file" ]; then
            compose_cmd+=" -f $file"
        fi
    done
    
    echo -e "${YELLOW}Running: $compose_cmd exec django_app python django_project/manage.py collectstatic --noinput${NC}"
    $compose_cmd exec django_app python django_project/manage.py collectstatic --noinput
    
    echo -e "${GREEN}Static files collected!${NC}"
}

function run_healthcheck() {
    echo -e "${BLUE}Running health checks...${NC}"
    
    local compose_cmd="docker-compose"
    for file in "${COMPOSE_FILES[@]}"; do
        if [ -f "$file" ]; then
            compose_cmd+=" -f $file"
        fi
    done
    
    # Check Django
    echo -e "${YELLOW}Checking Django...${NC}"
    $compose_cmd exec django_app python django_project/manage.py check --deploy || echo "Django health check failed"
    
    # Check PostgreSQL
    echo -e "${YELLOW}Checking PostgreSQL...${NC}"
    $compose_cmd exec postgresql pg_isready -U nir_user -d nir_metadata || echo "PostgreSQL health check failed"
    
    # Check Weaviate
    echo -e "${YELLOW}Checking Weaviate...${NC}"
    $compose_cmd exec weaviate curl -X GET http://localhost:8080/v1/.well-known/ready || echo "Weaviate health check failed"
    
    # Check Ollama
    echo -e "${YELLOW}Checking Ollama...${NC}"
    $compose_cmd exec ollama curl -X GET http://localhost:11434/api/tags || echo "Ollama health check failed"
    
    # Check Redis
    echo -e "${YELLOW}Checking Redis...${NC}"
    $compose_cmd exec redis redis-cli ping || echo "Redis health check failed"
    
    echo -e "${GREEN}Health checks completed!${NC}"
}

function cleanup_resources() {
    echo -e "${BLUE}Cleaning up Docker resources...${NC}"
    
    # Stop services first
    stop_services
    
    # Remove containers, networks, and volumes
    echo -e "${YELLOW}Removing stopped containers, unused networks, and dangling images...${NC}"
    docker system prune -f
    
    # Remove volumes (commented out by default for safety)
    # echo -e "${YELLOW}Removing unused volumes...${NC}"
    # docker volume prune -f
    
    echo -e "${GREEN}Cleanup completed!${NC}"
}

function show_access_info() {
    echo -e "${PURPLE}"
    echo "============================================"
    echo "    NIR_MISTRAL ACCESS INFORMATION"
    echo "============================================"
    echo ""
    echo "🌐 Web Interface:"
    echo "   - Dashboard: http://localhost:8000/dashboard/"
    echo "   - Admin:     http://localhost:8000/admin/"
    echo "   - API:       http://localhost:8000/api/"
    echo ""
    echo "🔌 Service Ports:"
    echo "   - Django:    8000"
    echo "   - PostgreSQL: 5432"
    echo "   - Weaviate:  8080"
    echo "   - FAISS:     8081"
    echo "   - Ollama:    11434"
    echo "   - Redis:     6379"
    echo "   - Quarto:    8083"
    echo "   - Flower:    5555-5556"
    echo ""
    echo "📝 Service Management:"
    echo "   - Start:    ./start_production.sh start"
    echo "   - Stop:     ./start_production.sh stop"
    echo "   - Restart:  ./start_production.sh restart"
    echo "   - Logs:     ./start_production.sh logs"
    echo "   - Status:   ./start_production.sh status"
    echo ""
    echo "💾 Data Directories:"
    echo "   - Media:     ./data/media/"
    echo "   - Reports:   ./reports/"
    echo "   - Uploads:   ./data/uploads/"
    echo "   - Logs:     ./logs/"
    echo ""
    echo "============================================${NC}"
}

function main() {
    print_banner
    
    # Parse command line arguments
    while [[ $# -gt 0 ]]; do
        case $1 in
            start)
                ACTION="start"
                shift
                ;;
            stop)
                ACTION="stop"
                shift
                ;;
            restart)
                ACTION="restart"
                shift
                ;;
            build)
                ACTION="build"
                shift
                ;;
            logs)
                ACTION="logs"
                shift
                ;;
            status)
                ACTION="status"
                shift
                ;;
            migrate)
                ACTION="migrate"
                shift
                ;;
            createsuperuser)
                ACTION="createsuperuser"
                shift
                ;;
            collectstatic)
                ACTION="collectstatic"
                shift
                ;;
            healthcheck)
                ACTION="healthcheck"
                shift
                ;;
            cleanup)
                ACTION="cleanup"
                shift
                ;;
            -h|--help)
                print_usage
                exit 0
                ;;
            -e|--env)
                ENV_FILE="$2"
                shift 2
                ;;
            -f|--file)
                COMPOSE_FILES+=("$2")
                shift 2
                ;;
            --no-cache)
                BUILD_CACHE=false
                shift
                ;;
            --force-recreate)
                FORCE_RECREATE=true
                shift
                ;;
            --no-detach)
                DETACHED=false
                shift
                ;;
            -v|--verbose)
                VERBOSE=true
                shift
                ;;
            *)
                echo -e "${RED}Unknown option: $1${NC}"
                print_usage
                exit 1
                ;;
        esac
    done
    
    # Check prerequisites
    check_prerequisites
    
    # Load environment
    load_environment
    
    # Execute action
    case "$ACTION" in
        start)
            start_services
            ;;
        stop)
            stop_services
            ;;
        restart)
            restart_services
            ;;
        build)
            build_images
            ;;
        logs)
            show_logs
            ;;
        status)
            show_status
            ;;
        migrate)
            run_migrations
            ;;
        createsuperuser)
            create_superuser
            ;;
        collectstatic)
            collect_static
            ;;
        healthcheck)
            run_healthcheck
            ;;
        cleanup)
            cleanup_resources
            ;;
        *)
            echo -e "${RED}Unknown action: $ACTION${NC}"
            print_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"

# Show access info if we started services
if [ "$ACTION" = "start" ] || [ "$ACTION" = "restart" ]; then
    show_access_info
fi