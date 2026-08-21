# NIR_Mistral API Authentication Guide

## Overview

The NIR_Mistral Django API uses **JWT (JSON Web Token)** authentication via `djangorestframework-simplejwt`. This guide explains how to authenticate and use the API endpoints.

## 🔐 Authentication Flow

### 1. Get JWT Token

To access protected endpoints, you need to obtain a JWT token by authenticating with valid credentials.

**Endpoint:** `POST /api/token/`

**Request:**
```bash
curl -X POST http://localhost:8000/api/token/ \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}'
```

**Response:**
```json
{
  "refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...",
  "access": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
}
```

### 2. Use the Access Token

Include the access token in the `Authorization` header for all protected requests:

```bash
curl -X GET http://localhost:8000/api/agents/ \
  -H "Authorization: Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."
```

### 3. Refresh Token (when access token expires)

**Endpoint:** `POST /api/token/refresh/`

```bash
curl -X POST http://localhost:8000/api/token/refresh/ \
  -H "Content-Type: application/json" \
  -d '{"refresh": "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9..."}'
```

## 📋 Token Lifetimes

- **Access Token:** 1 hour (configurable)
- **Refresh Token:** 1 day (configurable)
- **Token Rotation:** Enabled (new refresh token issued on each refresh)

## 🔓 Public Endpoints (No Authentication Required)

These endpoints are accessible without authentication:

- `POST /api/token/` - Get JWT token
- `POST /api/token/refresh/` - Refresh JWT token
- `GET /api/health/` - Health check
- `POST /api/users/register/` - User registration

## 🔒 Protected Endpoints (Require JWT Authentication)

All other endpoints require a valid JWT access token in the `Authorization: Bearer <token>` header.

### Agent Endpoints
- `GET /api/agents/` - List all agents
- `GET /api/agents/{name}/` - Get agent details
- `POST /api/agents/{name}/execute/` - Execute an agent

### Spectrum Endpoints
- `GET /api/spectra/` - List user's spectra
- `POST /api/spectra/` - Upload new spectrum
- `GET /api/spectra/{id}/` - Get spectrum details

### Analysis Job Endpoints
- `GET /api/jobs/` - List user's analysis jobs
- `POST /api/jobs/` - Create new analysis job
- `GET /api/jobs/{id}/` - Get job details

### User Endpoints
- `GET /api/users/profile/` - Get user profile

### NIR_TEST Environment Endpoints
- `GET /api/nir-test/info/` - Get environment info
- `GET /api/nir-test/demo/` - Run demonstration
- `GET /api/nir-test/run/{test_name}/` - Run specific test
- `GET /api/nir-test/files/` - List test data files
- `GET /api/nir-test/report/` - Get test report
- `POST /api/nir-test/setup/` - Setup environment
- `POST /api/nir-test/clean/` - Clean environment

### Dashboard
- `GET /` or `GET /dashboard/` - Dashboard view

## 💻 Code Examples

### Python Example

```python
import requests
import json

# Base URL
BASE_URL = "http://localhost:8000"

# 1. Get JWT Token
auth_url = f"{BASE_URL}/api/token/"
auth_data = {
    "username": "admin",
    "password": "admin123"
}

response = requests.post(auth_url, json=auth_data)
tokens = response.json()

access_token = tokens["access"]
refresh_token = tokens["refresh"]

# 2. Use the token to access protected endpoints
headers = {
    "Authorization": f"Bearer {access_token}",
    "Content-Type": "application/json"
}

# Get agents list
agents_response = requests.get(f"{BASE_URL}/api/agents/", headers=headers)
print("Agents:", agents_response.json())

# Get NIR_TEST info
nir_test_response = requests.get(f"{BASE_URL}/api/nir-test/info/", headers=headers)
print("NIR_TEST Info:", nir_test_response.json())

# Run NIR_TEST demo
demo_response = requests.get(f"{BASE_URL}/api/nir-test/demo/", headers=headers)
print("Demo Results:", demo_response.json())
```

### JavaScript (Browser) Example

```javascript
// 1. Get JWT Token
async function getToken() {
    const response = await fetch('http://localhost:8000/api/token/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            username: 'admin',
            password: 'admin123'
        })
    });
    
    const tokens = await response.json();
    localStorage.setItem('access_token', tokens.access);
    localStorage.setItem('refresh_token', tokens.refresh);
    return tokens.access;
}

// 2. Use the token for authenticated requests
async function getAgents() {
    const accessToken = localStorage.getItem('access_token');
    
    const response = await fetch('http://localhost:8000/api/agents/', {
        method: 'GET',
        headers: {
            'Authorization': `Bearer ${accessToken}`,
            'Content-Type': 'application/json',
        }
    });
    
    return await response.json();
}

// 3. Refresh token when needed
async function refreshToken() {
    const refreshToken = localStorage.getItem('refresh_token');
    
    const response = await fetch('http://localhost:8000/api/token/refresh/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
        },
        body: JSON.stringify({
            refresh: refreshToken
        })
    });
    
    const tokens = await response.json();
    localStorage.setItem('access_token', tokens.access);
    return tokens.access;
}
```

## 🛠️ Testing Authentication

### Test Script

Create a test script to verify authentication:

```bash
#!/bin/bash

# Test authentication and API access
BASE_URL="http://localhost:8000"

# 1. Get token
echo "Getting JWT token..."
TOKEN_RESPONSE=$(curl -s -X POST "$BASE_URL/api/token/" \
  -H "Content-Type: application/json" \
  -d '{"username": "admin", "password": "admin123"}')

ACCESS_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.access')
REFRESH_TOKEN=$(echo $TOKEN_RESPONSE | jq -r '.refresh')

echo "Access Token: ${ACCESS_TOKEN:0:50}..."
echo "Refresh Token: ${REFRESH_TOKEN:0:50}..."

# 2. Test protected endpoint
echo -e "\nTesting protected endpoint..."
curl -s -X GET "$BASE_URL/api/agents/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" | jq '.[] | .name'

# 3. Test NIR_TEST endpoints
echo -e "\nTesting NIR_TEST info endpoint..."
curl -s -X GET "$BASE_URL/api/nir-test/info/" \
  -H "Authorization: Bearer $ACCESS_TOKEN" \
  -H "Content-Type: application/json" | jq '.status'

echo -e "\nAuthentication test completed!"
```

## 🔧 Troubleshooting

### 401 Unauthorized Error

**Cause:** Missing or invalid JWT token.

**Solutions:**
1. Ensure you have obtained a valid token from `/api/token/`
2. Check that the token is included in the `Authorization: Bearer <token>` header
3. Verify the token hasn't expired (access tokens last 1 hour)
4. If expired, refresh the token using `/api/token/refresh/`

### 403 Forbidden Error

**Cause:** Valid token but insufficient permissions.

**Solutions:**
1. Check that the user has the required permissions
2. Verify the token belongs to a valid user
3. Ensure the user is active (not disabled)

### Invalid Token Error

**Cause:** Malformed or tampered token.

**Solutions:**
1. Obtain a new token
2. Ensure the token is not modified
3. Check for proper encoding

## 📝 Default Credentials

- **Username:** `admin`
- **Password:** `admin123`

## 🔐 Security Notes

1. **Never expose tokens in client-side code** (except in trusted environments)
2. **Use HTTPS in production** to prevent token interception
3. **Store tokens securely** (HttpOnly cookies for web, secure storage for mobile)
4. **Rotate tokens regularly** (configured automatically in this setup)
5. **Invalidate tokens on logout** (implement token blacklisting)

## 🎯 Quick Start

1. **Start the server:**
   ```bash
   cd /home/martin/Development/vsCode_Environment/NIR_Mistral/django_project
   ./start.sh
   ```

2. **Get a token:**
   ```bash
   curl -X POST http://localhost:8000/api/token/ \
     -H "Content-Type: application/json" \
     -d '{"username": "admin", "password": "admin123"}'
   ```

3. **Access protected endpoints:**
   ```bash
   curl -X GET http://localhost:8000/api/agents/ \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

4. **Run NIR_TEST demo:**
   ```bash
   curl -X GET http://localhost:8000/api/nir-test/demo/ \
     -H "Authorization: Bearer YOUR_ACCESS_TOKEN"
   ```

## 📚 Additional Resources

- [Django REST Framework SimpleJWT Documentation](https://django-rest-framework-simplejwt.readthedocs.io/)
- [JWT.io Debugger](https://jwt.io/) - Inspect and debug JWT tokens
- [NIR_Mistral API Documentation](../README.md)