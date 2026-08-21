#!/bin/bash

# NIR_Mistral Server Status Check Script

echo "=========================================="
echo "NIR_Mistral Server Status Check"
echo "=========================================="

# Check if any Django server is running
if ps aux | grep -E "(manage\.py|runserver)" | grep -v grep | grep -v code > /dev/null; then
    echo "✓ Django server processes found:"
    ps aux | grep -E "(manage\.py|runserver)" | grep -v grep | grep -v code
    echo ""
else
    echo "✗ No Django server processes found"
fi

# Check port 8000
if command -v ss &> /dev/null; then
    if ss -tulnp | grep -q ":8000 "; then
        echo "✓ Port 8000 is in use"
        ss -tulnp | grep ":8000 "
    else
        echo "✗ Port 8000 is free"
    fi
elif command -v netstat &> /dev/null; then
    if netstat -tulnp | grep -q ":8000 "; then
        echo "✓ Port 8000 is in use"
        netstat -tulnp | grep ":8000 "
    else
        echo "✗ Port 8000 is free"
    fi
else
    echo "ℹ Cannot check port status (no ss or netstat available)"
fi

# Try to test the server
if curl -s -f -o /dev/null http://localhost:8000/api/health/; then
    echo "✓ Server is responding to requests"
    echo ""
    echo "Server Status:"
    curl -s http://localhost:8000/api/health/ | python3 -m json.tool 2>/dev/null || echo "Health check successful"
else
    echo "✗ Server is not responding to requests"
fi

echo ""
echo "=========================================="
echo "To start the server, run: ./start_clean.sh"
echo "To stop the server, press Ctrl+C or run: pkill -f 'python manage.py'"
echo "=========================================="