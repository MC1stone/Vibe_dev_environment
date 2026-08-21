/**
 * NIR_Mistral Framework - Authentication JavaScript
 * Handles login, registration, and integration with FlowerAI and ILIAS
 */

// Get CSRF token from cookie
function getCookie(name) {
    let cookieValue = null;
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

const csrftoken = getCookie('csrftoken');

// Authentication API endpoints
const AUTH_API = {
    login: '/api/token/',
    register: '/api/users/register/',
    refresh: '/api/token/refresh/',
    logout: '/logout/',
    profile: '/api/users/profile/',
    flowerai: '/api/auth/flowerai/',
    ilias: '/api/auth/ilias/',
    federated: '/api/auth/federated/'
};

// Default headers with CSRF token for POST requests
function getHeaders(contentType = 'application/json') {
    const headers = {
        'Content-Type': contentType,
    };
    if (csrftoken) {
        headers['X-CSRFToken'] = csrftoken;
    }
    return headers;
}

// FlowerAI Configuration
const FLOWERAI_CONFIG = {
    serverUrl: 'http://flower_server:5555',
    clientId: 'nir_mistral_client',
    enabled: true,
    federatedLearning: true
};

// ILIAS Configuration
const ILIAS_CONFIG = {
    apiUrl: 'https://ilias.hswt.de',
    clientId: 'nir_mistral_client',
    enabled: true,
    synchronization: true
};

/**
 * Login user with username/email and password
 */
async function loginUser(username, password, remember = false) {
    try {
        const response = await fetch(AUTH_API.login, {
            method: 'POST',
            headers: getHeaders(),
            credentials: 'include',
            body: JSON.stringify({
                username: username,
                password: password
            })
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.detail || 'Login failed');
        }
        
        const data = await response.json();
        
        // Store tokens
        localStorage.setItem('access_token', data.access);
        localStorage.setItem('refresh_token', data.refresh);
        
        // Store user info
        if (data.user) {
            localStorage.setItem('user_info', JSON.stringify(data.user));
        }
        
        // If remember me, store in sessionStorage as well
        if (remember) {
            sessionStorage.setItem('access_token', data.access);
            sessionStorage.setItem('refresh_token', data.refresh);
        }
        
        // Initialize FlowerAI and ILIAS integration
        await initializeIntegrations();
        
        return {
            success: true,
            tokens: data,
            message: 'Login successful'
        };
        
    } catch (error) {
        console.error('Login error:', error);
        return {
            success: false,
            error: error.message,
            message: 'Login failed'
        };
    }
}

/**
 * Register new user
 */
async function registerUser(userData) {
    try {
        const response = await fetch(AUTH_API.register, {
            method: 'POST',
            headers: getHeaders(),
            credentials: 'include',
            body: JSON.stringify(userData)
        });
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Registration failed');
        }
        
        const data = await response.json();
        
        // Auto-login after registration
        if (data.user) {
            await loginUser(userData.username || userData.email, userData.password);
        }
        
        return {
            success: true,
            user: data.user,
            message: 'Registration successful'
        };
        
    } catch (error) {
        console.error('Registration error:', error);
        return {
            success: false,
            error: error.message,
            message: 'Registration failed'
        };
    }
}

/**
 * Logout user
 */
async function logoutUser() {
    try {
        // Clear local storage
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_info');
        localStorage.removeItem('flowerai_config');
        localStorage.removeItem('ilias_config');
        
        // Clear session storage
        sessionStorage.removeItem('access_token');
        sessionStorage.removeItem('refresh_token');
        
        // Call logout endpoint
        const response = await fetch(AUTH_API.logout, {
            method: 'POST',
            headers: getHeaders(),
            credentials: 'include'
        });
        
        // Redirect to home page
        window.location.href = '/';
        
        return { success: true, message: 'Logout successful' };
        
    } catch (error) {
        console.error('Logout error:', error);
        // Still clear tokens and redirect even if API call fails
        localStorage.removeItem('access_token');
        localStorage.removeItem('refresh_token');
        localStorage.removeItem('user_info');
        window.location.href = '/';
        return { success: true, message: 'Logout successful' };
    }
}

/**
 * Refresh access token
 */
async function refreshToken() {
    try {
        const refreshToken = localStorage.getItem('refresh_token');
        
        if (!refreshToken) {
            throw new Error('No refresh token available');
        }
        
        const response = await fetch(AUTH_API.refresh, {
            method: 'POST',
            headers: getHeaders(),
            credentials: 'include',
            body: JSON.stringify({
                refresh: refreshToken
            })
        });
        
        if (!response.ok) {
            throw new Error('Token refresh failed');
        }
        
        const data = await response.json();
        
        // Store new access token
        localStorage.setItem('access_token', data.access);
        
        return data.access;
        
    } catch (error) {
        console.error('Token refresh error:', error);
        // Clear tokens and redirect to login
        logoutUser();
        return null;
    }
}

/**
 * Get current user info
 */
async function getCurrentUser() {
    try {
        const token = localStorage.getItem('access_token');
        
        if (!token) {
            return null;
        }
        
        const response = await fetch(AUTH_API.profile, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
            }
        });
        
        if (!response.ok) {
            // Try to refresh token
            const newToken = await refreshToken();
            if (newToken) {
                const retryResponse = await fetch(AUTH_API.profile, {
                    method: 'GET',
                    headers: {
                        'Authorization': `Bearer ${newToken}`,
                        'Content-Type': 'application/json',
                    }
                });
                
                if (retryResponse.ok) {
                    return await retryResponse.json();
                }
            }
            return null;
        }
        
        return await response.json();
        
    } catch (error) {
        console.error('Get user error:', error);
        return null;
    }
}

/**
 * Initialize FlowerAI and ILIAS integrations
 */
async function initializeIntegrations() {
    try {
        const token = localStorage.getItem('access_token');
        if (!token) return;
        
        // Get FlowerAI configuration
        const floweraiResponse = await fetch(AUTH_API.flowerai, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            credentials: 'include'
        });
        
        if (floweraiResponse.ok) {
            const floweraiData = await floweraiResponse.json();
            localStorage.setItem('flowerai_config', JSON.stringify(floweraiData.flowerai_config));
            FLOWERAI_CONFIG.enabled = floweraiData.flowerai_config.enabled;
            FLOWERAI_CONFIG.federatedLearning = floweraiData.flowerai_config.federated_learning;
        }
        
        // Get ILIAS configuration
        const iliasResponse = await fetch(AUTH_API.ilias, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            credentials: 'include'
        });
        
        if (iliasResponse.ok) {
            const iliasData = await iliasResponse.json();
            localStorage.setItem('ilias_config', JSON.stringify(iliasData.ilias_config));
            ILIAS_CONFIG.enabled = iliasData.ilias_config.enabled;
            ILIAS_CONFIG.synchronization = iliasData.ilias_config.synchronization_enabled;
        }
        
        // Get federated learning configuration
        const federatedResponse = await fetch(AUTH_API.federated, {
            method: 'GET',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            credentials: 'include'
        });
        
        if (federatedResponse.ok) {
            const federatedData = await federatedResponse.json();
            localStorage.setItem('federated_config', JSON.stringify(federatedData.federated_learning));
        }
        
    } catch (error) {
        console.error('Integration initialization error:', error);
    }
}

/**
 * Update FlowerAI settings
 */
async function updateFlowerAISettings(settings) {
    try {
        const token = localStorage.getItem('access_token');
        
        const response = await fetch(AUTH_API.flowerai, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            credentials: 'include',
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) {
            throw new Error('Failed to update FlowerAI settings');
        }
        
        const data = await response.json();
        localStorage.setItem('flowerai_config', JSON.stringify(data));
        
        return {
            success: true,
            config: data,
            message: 'FlowerAI settings updated successfully'
        };
        
    } catch (error) {
        console.error('Update FlowerAI settings error:', error);
        return {
            success: false,
            error: error.message,
            message: 'Failed to update FlowerAI settings'
        };
    }
}

/**
 * Update ILIAS settings
 */
async function updateILIASSettings(settings) {
    try {
        const token = localStorage.getItem('access_token');
        
        const response = await fetch(AUTH_API.ilias, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            credentials: 'include',
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) {
            throw new Error('Failed to update ILIAS settings');
        }
        
        const data = await response.json();
        localStorage.setItem('ilias_config', JSON.stringify(data));
        
        return {
            success: true,
            config: data,
            message: 'ILIAS settings updated successfully'
        };
        
    } catch (error) {
        console.error('Update ILIAS settings error:', error);
        return {
            success: false,
            error: error.message,
            message: 'Failed to update ILIAS settings'
        };
    }
}

/**
 * Update Federated Learning settings
 */
async function updateFederatedLearningSettings(settings) {
    try {
        const token = localStorage.getItem('access_token');
        
        const response = await fetch(AUTH_API.federated, {
            method: 'POST',
            headers: {
                'Authorization': `Bearer ${token}`,
                'Content-Type': 'application/json',
                'X-CSRFToken': csrftoken
            },
            credentials: 'include',
            body: JSON.stringify(settings)
        });
        
        if (!response.ok) {
            throw new Error('Failed to update federated learning settings');
        }
        
        const data = await response.json();
        localStorage.setItem('federated_config', JSON.stringify(data.preferences));
        
        return {
            success: true,
            preferences: data.preferences,
            message: 'Federated learning settings updated successfully'
        };
        
    } catch (error) {
        console.error('Update federated learning settings error:', error);
        return {
            success: false,
            error: error.message,
            message: 'Failed to update federated learning settings'
        };
    }
}

/**
 * Connect to FlowerAI server
 */
async function connectToFlowerAI() {
    try {
        const config = JSON.parse(localStorage.getItem('flowerai_config') || '{}');
        
        // Check if FlowerAI is enabled
        if (!config.enabled) {
            throw new Error('FlowerAI integration is disabled');
        }
        
        // Here you would implement the actual FlowerAI connection logic
        // This is a placeholder for the actual implementation
        
        console.log('Connecting to FlowerAI server:', config.server_url);
        
        // Simulate connection (replace with actual FlowerAI client connection)
        const response = await fetch(config.server_url + '/api/health', {
            method: 'GET',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        if (response.ok) {
            return {
                success: true,
                message: 'Connected to FlowerAI server successfully',
                server: config.server_url
            };
        } else {
            throw new Error('Failed to connect to FlowerAI server');
        }
        
    } catch (error) {
        console.error('FlowerAI connection error:', error);
        return {
            success: false,
            error: error.message,
            message: 'Failed to connect to FlowerAI'
        };
    }
}

/**
 * Connect to ILIAS platform
 */
async function connectToILIAS() {
    try {
        const config = JSON.parse(localStorage.getItem('ilias_config') || '{}');
        
        // Check if ILIAS is enabled
        if (!config.enabled) {
            throw new Error('ILIAS integration is disabled');
        }
        
        // Here you would implement the actual ILIAS OAuth connection
        // This is a placeholder for the actual implementation
        
        console.log('Connecting to ILIAS platform:', config.api_url);
        
        // Simulate OAuth flow (replace with actual ILIAS OAuth implementation)
        const authUrl = `${config.api_url}/oauth2/authorize?` +
            `client_id=${ILIAS_CONFIG.clientId}&` +
            `response_type=code&` +
            `redirect_uri=${encodeURIComponent(window.location.origin + '/ilias/callback/')}&` +
            `scope=read write`;
        
        // For now, just return the auth URL
        // In a real implementation, you would redirect to this URL
        return {
            success: true,
            auth_url: authUrl,
            message: 'Ready to connect to ILIAS'
        };
        
    } catch (error) {
        console.error('ILIAS connection error:', error);
        return {
            success: false,
            error: error.message,
            message: 'Failed to connect to ILIAS'
        };
    }
}

/**
 * Check if user is authenticated
 */
function isAuthenticated() {
    const token = localStorage.getItem('access_token');
    return !!token;
}

/**
 * Get authentication token for API requests
 */
function getAuthToken() {
    return localStorage.getItem('access_token');
}

/**
 * Make authenticated API request
 */
async function authApiRequest(url, method = 'GET', data = null) {
    try {
        const token = getAuthToken();
        
        if (!token) {
            throw new Error('Not authenticated');
        }
        
        const headers = {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        };
        
        const config = {
            method: method,
            headers: headers
        };
        
        if (data) {
            config.body = JSON.stringify(data);
        }
        
        const response = await fetch(url, config);
        
        // Handle token expiration
        if (response.status === 401) {
            const newToken = await refreshToken();
            if (newToken) {
                headers.Authorization = `Bearer ${newToken}`;
                const retryResponse = await fetch(url, {
                    method: method,
                    headers: headers,
                    body: data ? JSON.stringify(data) : null
                });
                return await retryResponse.json();
            }
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'API request failed');
        }
        
        return await response.json();
        
    } catch (error) {
        console.error('API request error:', error);
        throw error;
    }
}

// Export functions for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        loginUser,
        registerUser,
        logoutUser,
        refreshToken,
        getCurrentUser,
        initializeIntegrations,
        updateFlowerAISettings,
        updateILIASSettings,
        updateFederatedLearningSettings,
        connectToFlowerAI,
        connectToILIAS,
        isAuthenticated,
        getAuthToken,
        authApiRequest,
        AUTH_API,
        FLOWERAI_CONFIG,
        ILIAS_CONFIG
    };
}