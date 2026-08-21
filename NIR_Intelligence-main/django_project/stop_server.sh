#!/bin/bash

# NIR_Mistral Django Server - Stop Script

echo "=========================================="
echo "Stopping NIR_Mistral Django Server"
echo "=========================================="

PORT=8000

# Method 1: Try fuser
if command -v fuser &> /dev/null; then
    echo "Using fuser to kill processes on port $PORT..."
    fuser -k $PORT/tcp 2>/dev/null || true
    sleep 1
fi

# Method 2: Kill all Django processes
if ps aux | grep -E "(manage\.py|runserver)" | grep -v grep | grep -v code > /dev/null; then
    echo "Killing Django server processes..."
    ps aux | grep -E "(manage\.py|runserver)" | grep -v grep | grep -v code | awk '{print $2}' | xargs kill -9 2>/dev/null || true
    sleep 1
fi

# Method 3: Kill all python processes in the project directory
PIDS=$(ps aux | grep -E "python.*manage\.py" | grep -v grep | grep -v code | awk '{print $2}')
if [ -n "$PIDS" ]; then
    echo "Killing Python processes: $PIDS"
    kill -9 $PIDS 2>/dev/null || true
    sleep 1
fi

# Verify processes are killed
if ps aux | grep -E "(manage\.py|runserver)" | grep -v grep | grep -v code > /dev/null; then
    echo "⚠️  Some processes may still be running. Try again or use:"
    echo "   pkill -9 -f 'python manage.py'"
else
    echo "✓ All Django server processes have been stopped"
fi

echo ""
echo "=========================================="
echo "Server stopped. Port $PORT should now be free."
echo "To start the server again, run: ./start_clean.sh"
echo "=========================================="