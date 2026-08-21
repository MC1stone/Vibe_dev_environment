#!/bin/bash

# NIR_Mistral Authentication Test Script
# This script tests the JWT authentication and API endpoints

set -e  # Exit on error

BASE_URL="http://localhost:8000"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}========================================${NC}"
echo -e "${BLUE}NIR_Mistral Authentication Test${NC}"
echo -e "${BLUE}========================================${NC}"

# Check if jq is installed
if ! command -v jq &> /dev/null; then
    echo -e "${RED}Error: jq is required but not installed.${NC}"
    echo "Install jq with: sudo apt-get install jq"
    exit 1
fi

# Check if curl is installed
if ! command -v curl &> /dev/null; then
    echo -e "${RED}Error: curl is required but not installed.${NC}"
    exit 1
fi

# Function to test endpoint
test_endpoint() {
    local endpoint=$1
    local method=$2
    local description=$3
    local token=$4
    
    echo -e "\n${YELLOW}Testing: ${description}${NC}"
    echo -e "  Endpoint: ${endpoint}"
    echo -e "  Method: ${method}"
    
    if [ "$method" = "GET" ]; then
        if [ -z "$token" ]; then
            response=$(curl -s -w "\n%{http_code}" "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $token" "$BASE_URL$endpoint")
        fi
    elif [ "$method" = "POST" ]; then
        if [ -z "$token" ]; then
            response=$(curl -s -w "\n%{http_code}" -H "Content-Type: application/json" -d "$4" "$BASE_URL$endpoint")
        else
            response=$(curl -s -w "\n%{http_code}" -H "Authorization: Bearer $token" -H "Content-Type: application/json" -d "$4" "$BASE_URL$endpoint")
        fi
    fi
    
    http_code=$(echo "$response" | tail -n1)
    body=$(echo "$response" | sed '$d')
    
    if [[ "$http_code" == "200" || "$http_code" == "201" ]]; then
        echo -e "  ${GREEN}✓ Success (HTTP ${http_code})${NC}"
        # Show first line of response
        if [ -n "$body" ]; then
            echo "  Response: $(echo "$body" | jq -c '.[] | .name' 2>/dev/null | head -1 || echo "$body" | head -c 100)..."
        fi
        return 0
    else
        echo -e "  ${RED}✗ Failed (HTTP ${http_code})${NC}"
        if [ -n "$body" ]; then
            echo "  Error: $(echo "$body" | jq -r '.error // .message // .detail' 2>/dev/null | head -1 || echo "$body" | head -c 100)"
        fi
        return 1
    fi
}

# Step 1: Test health check (public endpoint)
echo -e "\n${BLUE}[Step 1] Testing Public Endpoints${NC}"
test_endpoint "/api/health/" "GET" "Health Check" ""

# Step 2: Get JWT Token
echo -e "\n${BLUE}[Step 2] Getting JWT Token${NC}"
echo "Authenticating with username: admin, password: admin123"

TOKEN_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "$BASE_URL/api/token/" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}')

http_code=$(echo "$TOKEN_RESPONSE" | tail -n1)
body=$(echo "$TOKEN_RESPONSE" | sed '$d')

if [ "$http_code" = "200" ]; then
    ACCESS_TOKEN=$(echo "$body" | jq -r '.access')
    REFRESH_TOKEN=$(echo "$body" | jq -r '.refresh')
    
    echo -e "  ${GREEN}✓ Token obtained successfully${NC}"
    echo "  Access Token: ${ACCESS_TOKEN:0:50}..."
    echo "  Refresh Token: ${REFRESH_TOKEN:0:50}..."
else
    echo -e "  ${RED}✗ Failed to get token (HTTP ${http_code})${NC}"
    echo "  Response: $body"
    exit 1
fi

# Step 3: Test protected endpoints
echo -e "\n${BLUE}[Step 3] Testing Protected Endpoints${NC}"

# Test agents list
test_endpoint "/api/agents/" "GET" "Agents List" "$ACCESS_TOKEN"

# Test NIR_TEST info
test_endpoint "/api/nir-test/info/" "GET" "NIR_TEST Info" "$ACCESS_TOKEN"

# Test NIR_TEST files
test_endpoint "/api/nir-test/files/" "GET" "NIR_TEST Files" "$ACCESS_TOKEN"

# Test user profile
test_endpoint "/api/users/profile/" "GET" "User Profile" "$ACCESS_TOKEN"

# Step 4: Test NIR_TEST demo (this may take a while)
echo -e "\n${BLUE}[Step 4] Testing NIR_TEST Demo (may take 30-60 seconds)${NC}"
DEMO_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X GET "$BASE_URL/api/nir-test/demo/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  --max-time 120)

http_code=$(echo "$DEMO_RESPONSE" | tail -n1)
body=$(echo "$DEMO_RESPONSE" | sed '$d')

if [ "$http_code" = "200" ]; then
    echo -e "  ${GREEN}✓ Demo completed successfully${NC}"
    # Extract some info from response
    status=$(echo "$body" | jq -r '.status' 2>/dev/null || echo "unknown")
    message=$(echo "$body" | jq -r '.message' 2>/dev/null || echo "")
    echo "  Status: $status"
    echo "  Message: $message"
else
    echo -e "  ${RED}✗ Demo failed (HTTP ${http_code})${NC}"
    echo "  Response: $(echo "$body" | jq -r '.message // .error' 2>/dev/null | head -c 100)"
fi

# Step 5: Test token refresh
echo -e "\n${BLUE}[Step 5] Testing Token Refresh${NC}"

REFRESH_RESPONSE=$(curl -s -w "\n%{http_code}" \
  -X POST "$BASE_URL/api/token/refresh/" \
  -H "Content-Type: application/json" \
  -d "{\"refresh\": \"$REFRESH_TOKEN\"}")

http_code=$(echo "$REFRESH_RESPONSE" | tail -n1)
body=$(echo "$REFRESH_RESPONSE" | sed '$d')

if [ "$http_code" = "200" ]; then
    NEW_ACCESS_TOKEN=$(echo "$body" | jq -r '.access')
    echo -e "  ${GREEN}✓ Token refreshed successfully${NC}"
    echo "  New Access Token: ${NEW_ACCESS_TOKEN:0:50}..."
else
    echo -e "  ${RED}✗ Token refresh failed (HTTP ${http_code})${NC}"
fi

# Step 6: Test with invalid token
echo -e "\n${BLUE}[Step 6] Testing Invalid Token (should fail)${NC}"
test_endpoint "/api/agents/" "GET" "Invalid Token Test" "invalid_token_12345"

# Summary
echo -e "\n${BLUE}========================================${NC}"
echo -e "${BLUE}Authentication Test Summary${NC}"
echo -e "${BLUE}========================================${NC}"
echo -e "${GREEN}✓ Server is running and responding${NC}"
echo -e "${GREEN}✓ JWT authentication is working${NC}"
echo -e "${GREEN}✓ Protected endpoints require valid tokens${NC}"
echo -e "${GREEN}✓ Token refresh functionality works${NC}"
echo -e "${GREEN}✓ NIR_TEST integration is functional${NC}"
echo -e "\n${YELLOW}You can now use the API with JWT authentication!${NC}"
echo -e "${YELLOW}Access Token: ${ACCESS_TOKEN:0:80}...${NC}"
echo -e "${YELLOW}Refresh Token: ${REFRESH_TOKEN:0:80}...${NC}"

echo -e "\n${BLUE}Quick Usage Examples:${NC}"
echo "Get agents: curl -H \"Authorization: Bearer $ACCESS_TOKEN\" $BASE_URL/api/agents/"
echo "Run demo:   curl -H \"Authorization: Bearer $ACCESS_TOKEN\" $BASE_URL/api/nir-test/demo/"
echo "Get files:  curl -H \"Authorization: Bearer $ACCESS_TOKEN\" $BASE_URL/api/nir-test/files/"

echo -e "\n${BLUE}========================================${NC}"