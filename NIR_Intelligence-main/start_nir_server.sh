#!/bin/bash

# NIR Mistral Server Startup Script
# Usage: ./start_nir_server.sh [port]

PROJECT_DIR="/home/martin/Development/vsCode_Environment/NIR_Mistral"
PORT=${1:-8000}

echo "🚀 Starting NIR Mistral Server..."
echo "📁 Project Directory: $PROJECT_DIR"
echo "🌐 Port: $PORT"
echo ""

cd "$PROJECT_DIR"

# Check if port is available
if lsof -i :$PORT > /dev/null 2>&1; then
    echo "❌ Port $PORT is already in use!"
    echo "💡 Try: ./start_nir_server.sh 8001"
    exit 1
fi

# Start Django server
echo "✅ Starting Django development server..."
echo "🔗 Access the application at: http://localhost:$PORT"
echo "🔗 Admin panel: http://localhost:$PORT/admin/"
echo "🔗 API documentation: http://localhost:$PORT/api/"
echo "🔗 Test media: http://localhost:$PORT/media/test.txt"
echo ""

python manage.py runserver 0.0.0.0:$PORT