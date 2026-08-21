#!/bin/bash

echo "Starting Mock ILIAS Server..."
echo "=========================================="

# Start the mock ILIAS server in the background
cd /home/martin/Development/vsCode_Environment/NIR_Mistral/nir_test_env/server
python3 mock_ilias_server.py &

# Store the process ID
MOCK_ILIAS_PID=$!
echo "Mock ILIAS Server started with PID: $MOCK_ILIAS_PID"
echo "Server URL: http://localhost:8081"

# Wait a moment for the server to start
sleep 2

# Test if the server is running
echo "Testing Mock ILIAS Server..."
curl -s http://localhost:8081/api/health > /dev/null
if [ $? -eq 0 ]; then
    echo "✓ Mock ILIAS Server is running successfully"
    echo "✓ Health check passed"
    
    # Test some endpoints
    echo "Testing endpoints..."
    
    # Test courses endpoint
    response=$(curl -s http://localhost:8081/api/courses)
    if echo "$response" | grep -q "NIR_101"; then
        echo "✓ Courses endpoint working"
    else
        echo "✗ Courses endpoint failed"
    fi
    
    # Test users endpoint
    response=$(curl -s http://localhost:8081/api/users)
    if echo "$response" | grep -q "users"; then
        echo "✓ Users endpoint working"
    else
        echo "✗ Users endpoint failed"
    fi
    
    # Test analytics endpoint
    response=$(curl -s http://localhost:8081/api/analytics)
    if echo "$response" | grep -q "analytics"; then
        echo "✓ Analytics endpoint working"
    else
        echo "✗ Analytics endpoint failed"
    fi
    
    echo ""
    echo "Mock ILIAS Server is ready!"
    echo "Available endpoints:"
    echo "  http://localhost:8081/api/health - Health check"
    echo "  http://localhost:8081/api/users - List users"
    echo "  http://localhost:8081/api/courses - List courses"
    echo "  http://localhost:8081/api/messages - List messages"
    echo "  http://localhost:8081/api/analytics - Get analytics"
    echo ""
    echo "To stop the server:"
    echo "  kill $MOCK_ILIAS_PID"
    
else
    echo "✗ Mock ILIAS Server failed to start"
    kill $MOCK_ILIAS_PID
    exit 1
fi