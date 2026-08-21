/**
 * NIR_Mistral Framework - Main JavaScript
 * Core functionality for the Django frontend
 */

// Global variables
let NIR_MISTRAL = {
    version: '1.0.0',
    apiBaseUrl: '/api/',
    debug: true,
    csrfToken: ''
};

// Utility function for safe element access
function getElementSafely(id, parent = document) {
    const element = parent.getElementById(id);
    if (!element) {
        log(`Element with ID "${id}" not found`, 'warning');
        return null;
    }
    return element;
}

// Get CSRF token from meta tag
function getCSRFToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

// Logging function
function log(message, level = 'info') {
    if (!NIR_MISTRAL.debug) return;
    
    const levels = {
        debug: 'log',
        info: 'info',
        warning: 'warn',
        error: 'error'
    };
    
    const method = levels[level] || 'log';
    console[method](`[NIR_MISTRAL] ${message}`);
}

// DOM Ready function
document.addEventListener('DOMContentLoaded', function() {
    log('NIR_Mistral Framework initialized');
    
    // Get CSRF token
    NIR_MISTRAL.csrfToken = getCSRFToken();
    log('CSRF Token loaded: ' + (NIR_MISTRAL.csrfToken ? 'Yes' : 'No'));
    
    // Initialize all components
    initComponents();
    
    // Set up cleanup on page unload
    setupCleanup();
});

// Set up cleanup for page unload
function setupCleanup() {
    window.addEventListener('beforeunload', function() {
        // Clean up Bootstrap modals
        const modals = document.querySelectorAll('.modal.show');
        modals.forEach(modal => {
            const modalInstance = bootstrap.Modal.getInstance(modal);
            if (modalInstance) {
                modalInstance.dispose();
            }
        });
        
        // Clean up Bootstrap tooltips
        const tooltips = document.querySelectorAll('[data-bs-toggle="tooltip"]');
        tooltips.forEach(tooltip => {
            const tooltipInstance = bootstrap.Tooltip.getInstance(tooltip);
            if (tooltipInstance) {
                tooltipInstance.dispose();
            }
        });
        
        // Clean up Bootstrap popovers
        const popovers = document.querySelectorAll('[data-bs-toggle="popover"]');
        popovers.forEach(popover => {
            const popoverInstance = bootstrap.Popover.getInstance(popover);
            if (popoverInstance) {
                popoverInstance.dispose();
            }
        });
        
        log('Cleaned up Bootstrap components');
    });
}

// Initialize all components
function initComponents() {
    log('Initializing components');
    
    // Initialize tooltips
    initTooltips();
    
    // Initialize popovers
    initPopovers();
    
    // Initialize charts
    initCharts();
    
    // Initialize file upload handlers
    initFileUploads();
    
    // Initialize form handlers
    initForms();
}

// Initialize Bootstrap tooltips
function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

// Initialize Bootstrap popovers
function initPopovers() {
    const popoverTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="popover"]'));
    popoverTriggerList.map(function (popoverTriggerEl) {
        return new bootstrap.Popover(popoverTriggerEl);
    });
}

// Initialize Charts
function initCharts() {
    // Find all chart containers
    const chartContainers = document.querySelectorAll('.chart-container');
    
    chartContainers.forEach(container => {
        const chartType = container.dataset.chartType || 'line';
        const chartData = container.dataset.chartData ? JSON.parse(container.dataset.chartData) : null;
        
        if (chartData) {
            createChart(container, chartType, chartData);
        }
    });
}

// Create a chart
function createChart(container, type, data) {
    try {
        const ctx = container.querySelector('canvas') || document.createElement('canvas');
        
        if (!container.querySelector('canvas')) {
            container.appendChild(ctx);
        }
        
        const config = {
            type: type,
            data: data,
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        position: 'top',
                    },
                    tooltip: {
                        callbacks: {
                            label: function(context) {
                                return `${context.dataset.label}: ${context.parsed.y}`;
                            }
                        }
                    }
                }
            }
        };
        
        new Chart(ctx, config);
        log(`Created ${type} chart`);
        
    } catch (error) {
        log(`Error creating chart: ${error}`, 'error');
    }
}

// Initialize File Uploads
function initFileUploads() {
    const fileInputs = document.querySelectorAll('input[type="file"]');
    
    fileInputs.forEach(input => {
        // Add change event listener
        input.addEventListener('change', function(e) {
            const files = e.target.files;
            if (files.length > 0) {
                handleFileUpload(input, files);
            }
        });
        
        // Add drag and drop support
        const dropZone = input.closest('.drop-zone') || input.parentElement;
        if (dropZone) {
            setupDropZone(dropZone, input);
        }
    });
}

// Setup drag and drop zone
function setupDropZone(dropZone, fileInput) {
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        dropZone.classList.add('dragover');
    });
    
    dropZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        dropZone.classList.remove('dragover');
    });
    
    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        dropZone.classList.remove('dragover');
        
        const files = e.dataTransfer.files;
        if (files.length > 0) {
            fileInput.files = files;
            handleFileUpload(fileInput, files);
        }
    });
}

// Handle file upload
function handleFileUpload(input, files) {
    const form = input.closest('form');
    if (form) {
        // If it's part of a form, let the form handle it
        return;
    }
    
    // For standalone file uploads
    const file = files[0];
    const fileName = file.name;
    const fileSize = formatFileSize(file.size);
    const fileType = file.type || getFileExtension(fileName);
    
    log(`File selected: ${fileName} (${fileSize}, ${fileType})`);
    
    // Show file info
    const fileInfo = input.nextElementSibling;
    if (fileInfo && fileInfo.classList.contains('file-info')) {
        fileInfo.innerHTML = `
            <div class="d-flex align-items-center">
                <i class="bi bi-file-earmark me-2"></i>
                <div>
                    <div class="fw-bold">${fileName}</div>
                    <div class="small text-muted">${fileSize}, ${fileType.toUpperCase()}</div>
                </div>
            </div>
        `;
    }
    
    // Trigger upload if auto-upload is enabled
    if (input.dataset.autoUpload === 'true') {
        uploadFile(input, file);
    }
}

// Upload file via API
async function uploadFile(input, file) {
    const url = input.dataset.uploadUrl || '/api/spectra/upload/';
    const fieldName = input.name || 'file';
    
    try {
        const formData = new FormData();
        formData.append(fieldName, file);
        
        // Add additional data from data attributes
        const additionalData = input.dataset;
        for (let key in additionalData) {
            if (key.startsWith('data-')) {
                const fieldName = key.replace('data-', '');
                formData.append(fieldName, additionalData[key]);
            }
        }
        
        const response = await fetch(url, {
            method: 'POST',
            body: formData,
            headers: {
                'Authorization': `Bearer ${getAuthToken()}`
            }
        });
        
        if (!response.ok) {
            throw new Error(`Upload failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        log(`File uploaded successfully: ${result.message}`);
        
        // Trigger success event
        if (input.dataset.onSuccess) {
            window[input.dataset.onSuccess](result);
        }
        
        return result;
        
    } catch (error) {
        log(`File upload error: ${error}`, 'error');
        showNotification(`Upload failed: ${error.message}`, 'danger');
        
        // Trigger error event
        if (input.dataset.onError) {
            window[input.dataset.onError](error);
        }
        
        return null;
    }
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB', 'TB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Get file extension
function getFileExtension(filename) {
    return filename.slice((filename.lastIndexOf('.') - 1 >>> 0) + 2).toLowerCase();
}

// Initialize Forms
function initForms() {
    const forms = document.querySelectorAll('form[data-ajax="true"]');
    
    forms.forEach(form => {
        // Add client-side validation
        form.addEventListener('submit', function(e) {
            e.preventDefault();
            
            // Validate form before submission
            if (validateForm(form)) {
                submitFormAjax(form);
            }
        });
        
        // Add real-time validation on input change
        const inputs = form.querySelectorAll('input[required], select[required], textarea[required]');
        inputs.forEach(input => {
            input.addEventListener('blur', function() {
                validateInput(this);
            });
            
            input.addEventListener('input', function() {
                if (this.classList.contains('is-invalid')) {
                    validateInput(this);
                }
            });
        });
    });
}

// Validate entire form
function validateForm(form) {
    let isValid = true;
    const requiredInputs = form.querySelectorAll('input[required], select[required], textarea[required]');
    
    requiredInputs.forEach(input => {
        if (!validateInput(input)) {
            isValid = false;
        }
    });
    
    return isValid;
}

// Validate individual input
function validateInput(input) {
    const value = input.value.trim();
    const isRequired = input.hasAttribute('required');
    
    // Remove existing validation classes
    input.classList.remove('is-invalid', 'is-valid');
    
    // Remove existing error message
    const existingError = input.nextElementSibling;
    if (existingError && existingError.classList.contains('invalid-feedback')) {
        existingError.remove();
    }
    
    // Check required fields
    if (isRequired && !value) {
        input.classList.add('is-invalid');
        const error = document.createElement('div');
        error.className = 'invalid-feedback text-danger';
        error.textContent = 'This field is required';
        input.parentNode.insertBefore(error, input.nextSibling);
        return false;
    }
    
    // Check for custom validation patterns
    if (input.pattern && value && !new RegExp(input.pattern).test(value)) {
        input.classList.add('is-invalid');
        const error = document.createElement('div');
        error.className = 'invalid-feedback text-danger';
        error.textContent = input.title || 'Invalid format';
        input.parentNode.insertBefore(error, input.nextSibling);
        return false;
    }
    
    // Check for email validation
    if (input.type === 'email' && value && !/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(value)) {
        input.classList.add('is-invalid');
        const error = document.createElement('div');
        error.className = 'invalid-feedback text-danger';
        error.textContent = 'Please enter a valid email address';
        input.parentNode.insertBefore(error, input.nextSibling);
        return false;
    }
    
    // If valid, add valid class
    if (isRequired || input.pattern || input.type === 'email') {
        input.classList.add('is-valid');
    }
    
    return true;
}

// Submit form via AJAX
async function submitFormAjax(form) {
    const method = form.method.toUpperCase() || 'GET';
    const action = form.action || window.location.href;
    const formData = new FormData(form);
    
    try {
        // Show loading state
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = true;
            submitBtn.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Processing...';
        }
        
        const headers = {};
        if (!form.enctype || form.enctype === 'application/x-www-form-urlencoded') {
            headers['Content-Type'] = 'application/x-www-form-urlencoded';
        }
        
        const response = await fetch(action, {
            method: method,
            headers: headers,
            body: method === 'GET' ? null : formData,
            credentials: 'include'
        });
        
        if (!response.ok) {
            throw new Error(`Form submission failed: ${response.statusText}`);
        }
        
        const result = await response.json();
        
        // Handle success
        if (result.success !== false) {
            showNotification(result.message || 'Form submitted successfully', 'success');
            
            // Trigger success callback
            if (form.dataset.onSuccess) {
                window[form.dataset.onSuccess](result, form);
            }
            
            // Reset form if specified
            if (form.dataset.resetOnSuccess === 'true') {
                form.reset();
            }
            
            // Redirect if specified
            if (form.dataset.redirectOnSuccess) {
                window.location.href = form.dataset.redirectOnSuccess;
            }
            
        } else {
            showNotification(result.error || result.message || 'Form submission failed', 'danger');
        }
        
    } catch (error) {
        log(`Form submission error: ${error}`, 'error');
        showNotification(`Error: ${error.message}`, 'danger');
        
        // Trigger error callback
        if (form.dataset.onError) {
            window[form.dataset.onError](error, form);
        }
        
    } finally {
        // Restore submit button
        const submitBtn = form.querySelector('button[type="submit"]');
        if (submitBtn) {
            submitBtn.disabled = false;
            submitBtn.innerHTML = form.dataset.submitText || 'Submit';
        }
    }
}

// Show notification (already defined in base.html, but here for reference)
function showNotification(message, type = 'info') {
    const notification = document.createElement('div');
    notification.className = `alert alert-${type} alert-dismissible fade show`;
    notification.role = 'alert';
    notification.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert" aria-label="Close"></button>
    `;
    
    const container = document.querySelector('.container-fluid') || document.body;
    if (container) {
        container.insertBefore(notification, container.firstChild);
    } else {
        document.body.insertBefore(notification, document.body.firstChild);
    }
    
    setTimeout(() => {
        notification.classList.remove('show');
        setTimeout(() => notification.remove(), 150);
    }, 5000);
}

// Utility functions
function getAuthToken() {
    return localStorage.getItem('access_token');
}

function setAuthToken(token) {
    localStorage.setItem('access_token', token);
}

function logout() {
    localStorage.removeItem('access_token');
    localStorage.removeItem('refresh_token');
    window.location.href = '/login/';
}

// API request helper (already defined in base.html, but here for reference)
async function apiRequest(url, method = 'GET', data = null, headers = {}) {
    const token = getAuthToken();
    const defaultHeaders = {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...headers
    };
    
    const config = {
        method: method,
        headers: defaultHeaders
    };
    
    if (data) {
        config.body = JSON.stringify(data);
    }
    
    try {
        const response = await fetch(url, config);
        
        if (response.status === 401) {
            // Token expired, try to refresh
            const refreshToken = localStorage.getItem('refresh_token');
            if (refreshToken) {
                const refreshResponse = await fetch('/api/token/refresh/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({ refresh: refreshToken })
                });
                
                if (refreshResponse.ok) {
                    const refreshData = await refreshResponse.json();
                    setAuthToken(refreshData.access);
                    return apiRequest(url, method, data, headers);
                }
            }
            logout();
            return null;
        }
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(error.error || 'Request failed');
        }
        
        return await response.json();
    } catch (error) {
        console.error('API request error:', error);
        throw error;
    }
}

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = {
        NIR_MISTRAL,
        log,
        initComponents,
        initTooltips,
        initPopovers,
        initCharts,
        createChart,
        initFileUploads,
        setupDropZone,
        handleFileUpload,
        uploadFile,
        formatFileSize,
        getFileExtension,
        initForms,
        submitFormAjax,
        showNotification,
        getAuthToken,
        setAuthToken,
        logout,
        apiRequest
    };
}

// Set up Axios with CSRF token for Django
if (typeof axios !== 'undefined') {
    axios.defaults.headers.common['X-Requested-With'] = 'XMLHttpRequest';
    
    // Add CSRF token to requests if available
    if (NIR_MISTRAL.csrfToken) {
        axios.defaults.headers.common['X-CSRFToken'] = NIR_MISTRAL.csrfToken;
    }
    
    // Response interceptor for handling errors
    axios.interceptors.response.use(
        response => response,
        error => {
            if (error.response) {
                const status = error.response.status;
                
                if (status === 403) {
                    log('CSRF Token error - please refresh the page', 'error');
                    showNotification('Session expired. Please refresh the page.', 'error');
                } else if (status === 401) {
                    log('Authentication required', 'error');
                    showNotification('Please login to continue.', 'error');
                } else if (status >= 500) {
                    log('Server error: ' + status, 'error');
                    showNotification('Server error. Please try again later.', 'error');
                }
            }
            return Promise.reject(error);
        }
    );
    
    log('Axios configured with CSRF token support');
}