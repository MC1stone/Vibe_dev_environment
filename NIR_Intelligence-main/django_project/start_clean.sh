#!/bin/bash

# NIR_Mistral Django Server - Clean Startup Script
# This script ensures a clean start by killing any existing processes on the port

set -e  # Exit on error

PORT=8000
PROJECT_DIR="/home/martin/Development/vsCode_Environment/NIR_Mistral/django_project"

echo "=========================================="
echo "NIR_Mistral Django Server - Clean Startup"
echo "=========================================="

# Function to kill processes on a specific port
kill_port_processes() {
    local port=$1
    echo "Checking for processes on port $port..."
    
    # Try fuser first
    if command -v fuser &> /dev/null; then
        fuser -k $port/tcp 2>/dev/null || true
        sleep 1
    fi
    
    # Try lsof
    if command -v lsof &> /dev/null; then
        lsof -ti:$port | grep -v "COMMAND" | awk '{print $2}' | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    
    # Try ss
    if command -v ss &> /dev/null; then
        ss -tulnp | grep ":$port " | grep -v grep | awk '{print $7}' | cut -d',' -f2 | xargs kill -9 2>/dev/null || true
        sleep 1
    fi
    
    # Fallback: kill all python processes containing manage.py
    ps aux | grep -E "(manage\.py|runserver)" | grep -v grep | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    sleep 1
    
    echo "Port $port should now be free"
}

# Kill any existing processes
kill_port_processes $PORT

# Change to project directory
cd "$PROJECT_DIR"

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Check if port is still in use
if ss -tulnp 2>/dev/null | grep -q ":$PORT " || lsof -i:$PORT 2>/dev/null | grep -q LISTEN; then
    echo "Port $PORT is still in use. Trying to force kill..."
    kill_port_processes $PORT
    sleep 2
fi

# Start Django server
echo "Starting Django server on port $PORT..."
echo "=========================================="
echo "Server will be available at: http://localhost:$PORT/"
echo "Admin panel at: http://localhost:$PORT/admin/"
echo "Username: admin"
echo "Password: admin123"
echo "=========================================="
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
python manage.py runserver 0.0.0.0:$PORT