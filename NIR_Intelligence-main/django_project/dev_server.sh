#!/bin/bash

# NIR Mistral Stable Development Server
# Usage: ./dev_server.sh [start|stop|restart|status]
# This script runs Django with Gunicorn for stable development

PROJECT_DIR="/home/martin/Development/vsCode_Environment/NIR_Mistral/django_project"
PORT=8000
PID_FILE="/tmp/nir_dev_server.pid"
LOG_FILE="/tmp/nir_dev_server.log"

action=${1:-start}

case $action in
    start)
        echo "🚀 Starting NIR Mistral Development Server..."
        echo "📁 Project: $PROJECT_DIR"
        echo "🌐 Port: $PORT"
        echo "📝 Log: $LOG_FILE"
        echo ""
        
        # Kill any existing server
        if [ -f "$PID_FILE" ]; then
            echo "🛑 Found existing server (PID: $(cat $PID_FILE)), killing..."
            kill -9 $(cat $PID_FILE) 2>/dev/null
            rm -f "$PID_FILE"
            sleep 1
        fi
        
        # Start Gunicorn server
        cd "$PROJECT_DIR"
        nohup gunicorn --bind 0.0.0.0:$PORT --workers 4 --reload --timeout 120 --log-level debug nir_web.wsgi:application > "$LOG_FILE" 2>&1 &
        echo $! > "$PID_FILE"
        
        sleep 3
        if ps -p $! > /dev/null; then
            echo "✅ Server started successfully!"
            echo "🔗 Access at: http://localhost:$PORT/dashboard/"
            echo "📝 Logs: tail -f $LOG_FILE"
            echo "🛑 To stop: ./dev_server.sh stop"
        else
            echo "❌ Server failed to start. Check logs:"
            tail -20 "$LOG_FILE"
        fi
        ;;
    
    stop)
        echo "🛑 Stopping NIR Mistral Development Server..."
        if [ -f "$PID_FILE" ]; then
            kill -9 $(cat $PID_FILE) 2>/dev/null
            rm -f "$PID_FILE"
            echo "✅ Server stopped"
        else
            echo "⚠️  No server PID file found"
        fi
        ;;
    
    restart)
        ./dev_server.sh stop
        sleep 2
        ./dev_server.sh start
        ;;
    
    status)
        if [ -f "$PID_FILE" ]; then
            PID=$(cat $PID_FILE)
            if ps -p $PID > /dev/null; then
                echo "✅ Server is running (PID: $PID)"
                echo "📝 Log file: $LOG_FILE"
                echo "🌐 Port: $PORT"
            else
                echo "❌ Server is not running (PID: $PID)"
            fi
        else
            echo "❌ No server running"
        fi
        ;;
    
    *)
        echo "Usage: ./dev_server.sh [start|stop|restart|status]"
        exit 1
        ;;
esac