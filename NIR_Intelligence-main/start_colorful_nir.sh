#!/bin/bash

# NIR Mistral Server Startup Script with Colorful UI/UX
# Usage: ./start_colorful_nir.sh [port]

PROJECT_DIR="/home/martin/Development/vsCode_Environment/NIR_Mistral/django_project"
PORT=${1:-8000}

echo "🚀 Starting NIR Mistral Server with Colorful UI/UX..."
echo "📁 Project Directory: $PROJECT_DIR"
echo "🌐 Port: $PORT"
echo ""

cd "$PROJECT_DIR"

# Check if port is available
if command -v fuser >/dev/null 2>&1; then
    if fuser -k $PORT/tcp 2>/dev/null; then
        echo "✅ Freed port $PORT"
    fi
fi

# Check if port is available
if python -c "import socket; s=socket.socket(); s.bind(('0.0.0.0',$PORT)); s.close()" 2>/dev/null; then
    echo "✅ Port $PORT is available"
else
    echo "❌ Port $PORT is in use, trying $((PORT+1))..."
    PORT=$((PORT+1))
fi

# Start Django server
echo "✅ Starting Django development server with Colorful UI..."
echo "🔗 Access the application at: http://localhost:$PORT"
echo "🔗 Colorful Dashboard: http://localhost:$PORT/dashboard/"
echo "🔗 Agents Page: http://localhost:$PORT/agents/"
echo "🔗 Spectra Page: http://localhost:$PORT/spectra/"
echo "🔗 Analysis Page: http://localhost:$PORT/analysis/"
echo "🔗 Jobs Page: http://localhost:$PORT/jobs/"
echo "🔗 Admin Panel: http://localhost:$PORT/admin/"
echo ""

python manage.py runserver 0.0.0.0:$PORT