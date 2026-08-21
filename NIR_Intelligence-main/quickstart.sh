#!/bin/bash

# NIR Mistral Quick Start Script
# Usage: ./quickstart.sh [port]
# Example: ./quickstart.sh 8001

PROJECT_DIR="/home/martin/Development/vsCode_Environment/NIR_Mistral/django_project"
PORT=${1:-8001}

echo "🚀 NIR Mistral Quick Start"
echo "=========================="
echo ""

# Stop any existing servers
echo "🛑 Stopping any existing servers..."
pkill -f "manage.py runserver" 2>/dev/null
sleep 1

# Free up the port
if command -v fuser >/dev/null 2>&1; then
    fuser -k $PORT/tcp 2>/dev/null
fi

# Check if port is available
if python -c "import socket; s=socket.socket(); s.bind(('0.0.0.0',$PORT)); s.close()" 2>/dev/null; then
    echo "✅ Port $PORT is available"
else
    echo "❌ Port $PORT is in use, trying $((PORT+1))..."
    PORT=$((PORT+1))
fi

echo ""
echo "📁 Changing to project directory: $PROJECT_DIR"
cd "$PROJECT_DIR"

echo ""
echo "🎨 Starting NIR Mistral with Colorful UI/UX..."
echo "🌐 Server will be available at: http://localhost:$PORT"
echo ""
echo "🔗 Access these pages after startup:"
echo "   • Dashboard: http://localhost:$PORT/dashboard/"
echo "   • Agents: http://localhost:$PORT/agents/"
echo "   • Spectra: http://localhost:$PORT/spectra/"
echo "   • Analysis: http://localhost:$PORT/analysis/"
echo "   • Jobs: http://localhost:$PORT/jobs/"
echo "   • Admin: http://localhost:$PORT/admin/"
echo ""
echo "💡 Press Ctrl+C to stop the server"
echo ""

# Start the server in the foreground
python manage.py runserver 0.0.0.0:$PORT