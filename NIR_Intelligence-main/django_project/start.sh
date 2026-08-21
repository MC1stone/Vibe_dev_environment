#!/bin/bash

# Simple NIR_Mistral Django Server Start Script
# Usage: ./start.sh [port]

cd "$(dirname "$0")"

# Kill any existing processes on the port
PORT="${1:-8000}"
echo "Checking for existing processes on port $PORT..."
fuser -k $PORT/tcp 2>/dev/null || true
ps aux | grep -E "(manage\.py|runserver)" | grep -v grep | grep -v code | awk '{print $2}' | xargs kill -9 2>/dev/null || true
sleep 1

# Use virtual environment Python
PYTHON="$(pwd)/venv/bin/python"

echo "Starting NIR_Mistral Django Server on port $PORT..."
echo "Access the application at: http://localhost:$PORT/"
echo "Admin panel at: http://localhost:$PORT/admin/"
echo "Username: admin, Password: admin123"
echo "Press Ctrl+C to stop the server"
echo ""

# Start the server
$PYTHON manage.py runserver 0.0.0.0:$PORT