#!/bin/bash

# NIR Mistral Server Stop Script

echo "🛑 Stopping NIR Mistral Django Server..."

# Method 1: Try graceful kill first
echo "🔍 Looking for Django server processes..."
PIDS=$(ps aux | grep "manage.py runserver" | grep -v grep | awk '{print $2}')

if [ -z "$PIDS" ]; then
    echo "✅ No Django server processes found"
else
    echo "📋 Found Django server processes: $PIDS"
    echo "💀 Killing processes..."
    kill $PIDS
    sleep 2
    
    # Check if any processes are still running
    REMAINING=$(ps aux | grep "manage.py runserver" | grep -v grep | awk '{print $2}')
    if [ -z "$REMAINING" ]; then
        echo "✅ All Django servers stopped successfully"
    else
        echo "⚠️  Some processes didn't stop gracefully, forcing kill..."
        kill -9 $REMAINING
        echo "✅ Forced kill completed"
    fi
fi

# Method 2: Try to free up common ports
echo "🔌 Freeing up common Django ports..."
for port in 8000 8001 8080 8888 9000; do
    if fuser -k $port/tcp 2>/dev/null; then
        echo "🔗 Freed port $port"
    fi
done

echo "✅ Server stop completed"