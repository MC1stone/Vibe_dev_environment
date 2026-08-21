#!/bin/bash

# NIR Mistral Background Start Script
# Usage: ./start_bg.sh [port]
# Example: ./start_bg.sh 8001
# Server runs in background - use ./stop_nir_server.sh to stop

PROJECT_DIR="/home/martin/Development/vsCode_Environment/NIR_Mistral/django_project"
PORT=${1:-8001}
LOG_FILE="/tmp/nir_mistral_$PORT.log"

echo "🚀 Starting NIR Mistral in Background Mode"
echo "=========================================="
echo ""

# Stop any existing servers
echo "🛑 Stopping any existing servers..."
./stop_nir_server.sh > /dev/null 2>&1
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
    LOG_FILE="/tmp/nir_mistral_$PORT.log"
fi

echo ""
echo "📁 Project: $PROJECT_DIR"
echo "🌐 Port: $PORT"
echo "📝 Log: $LOG_FILE"
echo ""

cd "$PROJECT_DIR"

# Start server in background
echo "🎨 Starting NIR Mistral with Colorful UI/UX in background..."
nohup python manage.py runserver 0.0.0.0:$PORT > "$LOG_FILE" 2>&1 &

# Wait a moment for server to start
sleep 3

# Check if server started successfully
if ps aux | grep "manage.py runserver" | grep -v grep > /dev/null; then
    echo "✅ Server started successfully!"
    echo ""
    echo "🌐 Access your platform at:"
    echo "   Main: http://localhost:$PORT/"
    echo "   Dashboard: http://localhost:$PORT/dashboard/"
    echo "   Agents: http://localhost:$PORT/agents/"
    echo "   Spectra: http://localhost:$PORT/spectra/"
    echo "   Analysis: http://localhost:$PORT/analysis/"
    echo "   Jobs: http://localhost:$PORT/jobs/"
    echo "   Admin: http://localhost:$PORT/admin/"
    echo ""
    echo "📝 Server logs: tail -f $LOG_FILE"
    echo "🛑 To stop: ./stop_nir_server.sh"
    echo ""
    echo "✨ Your colorful NIR Mistral platform is ready!"
else
    echo "❌ Server failed to start. Check log file:"
    echo "   $LOG_FILE"
    tail -20 "$LOG_FILE"
fi