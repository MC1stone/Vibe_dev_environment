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

    // CSRF-Header jetzt nachziehen: das Axios-Default-Setup am Ende dieser
    // Datei laeuft beim PARSEN - vor DOMContentLoaded und damit mit leerem
    // Token ('' -> if schlug fehl, Header nie gesetzt, 403 'CSRF token
    // missing' auf allen Default-basierten Requests, Vorfall 2026-10-16).
    if (typeof axios !== 'undefined' && NIR_MISTRAL.csrfToken) {
        axios.defaults.headers.common['X-CSRFToken'] = NIR_MISTRAL.csrfToken;
    }
    
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
// OP63 Stufe 1/2 (Fusion-Analyse-Zweig): Comparable Spektren aus anderen
// Projekten -> Angebot rendern, Preview laden, Nutzer entscheidet ob der
// Zweig geoeffnet und die Zusammenfuehrung ausgefuehrt wird (nie automatisch).
window.nirBuildFusionOfferHtml = function (offer, context) {
    if (!offer || !offer.available) return '';
    let html = '<div class="border rounded p-2 bg-light mt-2" id="fusionOfferBox">';
    html += `<h6><i class="bi bi-diagram-3 me-1"></i>${nirGettext('Analyse-Zweig: Datenfusion anderer Projekte')}</h6>`;
    html += `<p class="mb-2 small">${nirGettext(offer.explanation || '')}</p>`;
    if (offer.candidates && offer.candidates.length) {
        html += '<table class="table table-sm mb-2"><thead><tr>' +
            `<th>${nirGettext('Spektrum')}</th><th>${nirGettext('Ähnlichkeit')}</th><th>${nirGettext('Projekt')}</th></tr></thead><tbody>`;
        offer.candidates.forEach(c => {
            html += '<tr>' +
                `<td>${c.file_name}</td>` +
                `<td>${c.similarity !== null && c.similarity !== undefined ? (100 * c.similarity).toFixed(1) + ' %' : '—'}</td>` +
                `<td>${c.project_id ? `<a href="/projects/${c.project_id}/">${c.project_name || nirGettext('Projekt öffnen')}</a>` : nirGettext('kein Projekt')}</td></tr>`;
        });
        html += '</tbody></table>';
    }
    const pids = offer.project_ids || [];
    html += `<button type="button" class="btn btn-sm btn-primary me-2" id="fusionPreviewBtn" onclick="nirFusionPreview(this.dataset.pids)" data-pids='${JSON.stringify(pids)}'>` +
        `<i class="bi bi-eye me-1"></i>${nirGettext('Zweig öffnen: Metadaten-Abgleich ansehen')}</button>`;
    html += `<button type="button" class="btn btn-sm btn-outline-secondary" onclick="document.getElementById('fusionOfferBox').style.display='none'">` +
        `${nirGettext('Nein, nicht öffnen')}</button>`;
    html += '<div id="fusionPreviewResult" class="mt-2"></div></div>';
    return html;
};

window.nirFusionPreview = function (projectIds) {
    const box = document.getElementById('fusionPreviewResult');
    if (!box) return;
    if (typeof projectIds === 'string') {
        try { projectIds = JSON.parse(projectIds); } catch (e) { projectIds = []; }
    }
    if (!Array.isArray(projectIds) || projectIds.length < 2) {
        box.innerHTML = `<div class="alert alert-warning py-2 mb-0">${nirGettext('Es konnten nicht beide Projekte identifiziert werden - bitte Seite neu laden.')}</div>`;
        return;
    }
    box.innerHTML = `<p class="mb-0 text-muted small">${nirGettext('Metadaten-Abgleich wird geladen …')}</p>`;
    axios.post('/projects/fusion/preview/', { project_ids: projectIds })
        .then(resp => {
            const data = resp.data || {};
            if (!data.success) { throw new Error(data.error || 'preview failed'); }
            let html = `<h6 class="mt-2">${nirGettext('Metadaten-Abgleich')}</h6>`;
            (data.projects || []).forEach(p => {
                html += `<p class="mb-1 small"><strong>${p.project_name}</strong> — ${p.usable_datasets} ${nirGettext('verwendbare Datensätze')}</p>`;
                const diff = p.metadata_diff_vs_first;
                if (diff && diff.fields && diff.fields.length) {
                    html += '<table class="table table-sm mb-2"><thead><tr>' +
                        `<th>${nirGettext('Feld')}</th><th>${nirGettext('Projekt A')}</th><th>${nirGettext('Projekt B')}</th><th>${nirGettext('Status')}</th></tr></thead><tbody>`;
                    diff.fields.forEach(f => {
                        html += '<tr>' +
                            `<td>${f.label}</td>` +
                            `<td>${f.a || '—'}</td><td>${f.b || '—'}</td>` +
                            `<td>${f.missing ? '—' : (f.equal ? '<i class="bi bi-check-lg text-success"></i>' : `<span class="text-warning"><i class="bi bi-exclamation-triangle me-1"></i>${nirGettext('unterschiedlich')}</span>`)}</td></tr>`;
                    });
                    html += '</tbody></table>';
                }
            });
            html += `<div class="d-flex gap-2 flex-wrap mt-2">` +
                `<button type="button" class="btn btn-sm btn-success" onclick="nirFusionExecute(this.dataset.pids)" data-pids='${JSON.stringify(projectIds)}'>` +
                `<i class="bi bi-boxes me-1"></i>${nirGettext('Zusammenführung durchführen (neues Projekt)')}</button>` +
                `<span class="small text-muted align-self-center">${nirGettext('Die Original-Projekte bleiben unangetastet.')}</span></div>`;
            box.innerHTML = html;
        })
        .catch(err => {
            box.innerHTML = `<div class="alert alert-danger py-2 mb-0">${nirGettext('Metadaten-Abgleich fehlgeschlagen:')} ${err.message || err}</div>`;
        });
};

window.nirFusionExecute = function (projectIds) {
    const box = document.getElementById('fusionPreviewResult');
    if (!box) return;
    if (typeof projectIds === 'string') {
        try { projectIds = JSON.parse(projectIds); } catch (e) { projectIds = []; }
    }
    if (!Array.isArray(projectIds) || projectIds.length < 2) {
        box.innerHTML = `<div class="alert alert-warning py-2 mb-0">${nirGettext('Es konnten nicht beide Projekte identifiziert werden - bitte Seite neu laden.')}</div>`;
        return;
    }
    if (!window.confirm(nirGettext('Zusammenführung in ein neues Fusionsprojekt durchführen? Die Original-Projekte bleiben unangetastet.'))) return;
    axios.post('/projects/fusion/execute/', { project_ids: projectIds })
        .then(resp => {
            const data = resp.data || {};
            if (!data.success) { throw new Error(data.error || 'execute failed'); }
            box.innerHTML = `<div class="alert alert-success py-2 mb-0">${nirGettext('Fusionsprojekt angelegt. Aufbereitung läuft im Hintergrund.')} ` +
                `<a href="${data.detail_url}">${nirGettext('Zum Fusionsprojekt')}</a></div>`;
        })
        .catch(err => {
            box.innerHTML = `<div class="alert alert-danger py-2 mb-0">${nirGettext('Zusammenführung fehlgeschlagen:')} ${err.message || err}</div>`;
        });
};

// OP63 Stufe 3: vergleichende Kalibration des Fusion-Zweigs - Button im
// Fusionsprojekt-Report laedt die drei Kalibrationen + Signifikanz-Test.
window.nirFusionCalibration = function (projectId) {
    const box = document.getElementById('fusionCalibrationResult');
    if (!box) return;
    box.innerHTML = `<p class="mb-0 text-muted small">${nirGettext('Kalibrationsvergleich wird gerechnet (PLS, Kreuzvalidierung) …')}</p>`;
    axios.get(`/api/projects/${projectId}/fusion/calibration/`)
        .then(resp => {
            const data = resp.data || {};
            if (!data.success) { throw new Error(data.error || 'comparison failed'); }
            const cals = data.calibrations || {};
            const labels = Object.keys(cals);
            if (!labels.length) {
                box.innerHTML = `<p class="mb-0 small text-muted">${nirGettext('Keine kalibrierbaren Datensätze (Referenzwerte fehlen).')}</p>`;
                return;
            }
            // OP65 UI-Redesign: eine Zeile je Datensatz, alle Kennzahlen
            // nebeneinander - vorhergesagte vs. tatsächliche Brix je
            // Messung (Trefferquote), MAE, RPD, R2/CV.
            let html = '<div class="table-responsive"><table class="table table-sm table-striped mb-2 align-middle"><thead><tr>' +
                `<th rowspan="2">${nirGettext('Datensatz')}</th><th rowspan="2">n</th>` +
                `<th colspan="2">${nirGettext('Trefferquote: |vorhergesagt − tatsächl. Brix| ≤ Toleranz')}</th>` +
                `<th rowspan="2">MAE</th><th rowspan="2">RMSE</th><th rowspan="2">R² (CV)</th><th rowspan="2">RPD</th><th rowspan="2">${nirGettext('Status')}</th></tr><tr>`;
            const anyPvr = labels.some(l => cals[l].predicted_vs_reference);
            if (anyPvr) {
                const firstPvr = cals[labels.find(l => cals[l].predicted_vs_reference)].predicted_vs_reference;
                Object.keys(firstPvr.hits_within_tolerance).forEach(k => {
                    html += `<th>±${firstPvr.hits_within_tolerance[k].tolerance}</th>`;
                });
            } else {
                html += '<th>—</th>';
            }
            html += '</tr></thead><tbody>';
            labels.forEach(label => {
                const c = cals[label];
                const pvr = c.predicted_vs_reference;
                const tolCells = pvr
                    ? Object.keys(pvr.hits_within_tolerance).map(k => {
                        const h = pvr.hits_within_tolerance[k];
                        const pct = (100 * h.ratio).toFixed(0);
                        const cls = h.ratio >= 0.8 ? 'text-success' : (h.ratio >= 0.5 ? 'text-warning' : 'text-danger');
                        return `<td class="${cls}"><strong>${h.n_within}/${pvr.n}</strong> (${pct} %)</td>`;
                    }).join('')
                    : '<td class="text-muted">—</td>';
                const status = c.status === 'ok'
                    ? '<span class="badge bg-success"><i class="bi bi-check-lg"></i></span>'
                    : `<span class="badge bg-secondary">${nirGettext('nicht kalibrierbar')}</span>`;
                html += '<tr>' +
                    `<td><strong>${label}</strong></td>` +
                    `<td>${c.n_samples ?? '—'}</td>` +
                    tolCells +
                    `<td>${pvr ? Number(pvr.mae).toFixed(3) : (c.rmse_cv != null ? Number(c.rmse_cv).toFixed(3) : '—')}</td>` +
                    `<td>${pvr ? Number(pvr.rmse).toFixed(3) : '—'}</td>` +
                    `<td>${c.mean_r2 != null ? (100 * c.mean_r2).toFixed(1) + ' %' : '—'}</td>` +
                    `<td>${c.rpd != null ? Number(c.rpd).toFixed(1) : '—'}</td>` +
                    `<td>${status}</td></tr>`;
            });
            html += '</tbody></table></div>';
            const sig = data.significance || {};
            if (sig.performed) {
                const sigBadge = (ok, textOk, textBad) =>
                    `<span class="badge ${ok ? 'bg-success' : 'bg-warning text-dark'}">${ok ? textOk : textBad}</span>`;
                html += `<div class="border rounded p-2 bg-light mb-2 small">` +
                    `<strong>${nirGettext('Signifikanz-Test')}</strong> ` +
                    `${nirGettext('Varianz gleich')} ${sigBadge(sig.levene.variance_equal, 'p=' + Number(sig.levene.p_value).toFixed(3), 'p=' + Number(sig.levene.p_value).toFixed(3))}` +
                    ` · ${nirGettext('Mittelwert gleich')} ${sigBadge(sig.welch_t.means_equal, 'p=' + Number(sig.welch_t.p_value).toFixed(3), 'p=' + Number(sig.welch_t.p_value).toFixed(3))}` +
                    `</div>`;
                if (sig.interpretation) {
                    html += `<p class="small mb-2">${nirGettext(sig.interpretation)}</p>`;
                }
            }
            // OP70: Brix-Band-Matrix (gemessen x geschaetzt) je Kalibration
            // + am Fusions-Datensatz pro Quell-Datensatz getrennt
            labels.forEach(label => {
                const c = cals[label];
                const pvr = c.predicted_vs_reference || {};
                const bm = pvr.brix_band_matrix;
                const chartUrl = c.band_matrix_chart;
                if (!bm || !bm.matrix) return;
                const renderMx = (m, title) => {
                    let h = `<h6 class="mt-2 mb-1"><i class="bi bi-grid-3x3-gap me-1"></i>${nirGettext('Konfusionsmatrix (Brix-Bänder)')}: ${title}</h6>`;
                    h += '<div class="table-responsive"><table class="table table-sm table-bordered mb-2 small text-center" style="width:auto;"><thead><tr><th>' +
                        nirGettext('gemessen \ geschaetzt') + '</th>' + bm.labels.map(l => `<th class="small">${l}</th>`).join('') + '</tr></thead><tbody>';
                    m.forEach((row, i) => {
                        h += `<tr><th class="small">${bm.labels[i]}</th>` + row.map(v => {
                            const cls = v === 0 ? 'table-light text-muted' : (bm.labels[i] === bm.labels[row.indexOf(v)] && false ? '' : '');
                            return `<td class="${v > 0 ? 'table-primary' : 'table-light'}">${v}</td>`;
                        }).join('') + '</tr>';
                    });
                    h += '</tbody></table></div>';
                    if (chartUrl) h += `<img src="${chartUrl}" alt="${nirGettext('Brix-Band-Matrix')} ${title}" class="img-fluid border rounded mt-1" style="max-height:380px;">`;
                    return h;
                };
                html += renderMx(bm.matrix, label);
                const perSrc = c.band_matrix_charts_sources || {};
                Object.keys(perSrc).forEach(src => {
                    if (perSrc[src]) html += `<img src="${perSrc[src]}" alt="${nirGettext('Brix-Band-Matrix')} ${src}" class="img-fluid border rounded mt-1" style="max-height:380px;">`;
                });
            });
            // OP66: Brix-Vorhersage vs. gemessene Brix des Fusionsprojekts
            // als EIN kombinierter Datensatz - Streudiagramm (Base64-PNG)
            // inkl. aufklappbarer Erklaerung unter der Grafik.
            const fusedName = (data.fusion_project_name || '').trim();
            const fusedCal = (fusedName && cals[fusedName]) || null;
            const pvrChart = fusedCal && fusedCal.pvr_chart;
            if (pvrChart) {
                html += `<div class="mt-2"><h6 class="mb-1"><i class="bi bi-graph-up me-1"></i>` +
                    nirGettext('Vorhersage vs. Messwert (kombinierter Datensatz)') + `</h6>` +
                    `<img src="${pvrChart}" alt="${nirGettext('Vorhersage vs. Messwert')}" class="img-fluid border rounded" style="max-height:420px;">`;
                const expl = (window.NIR_CHART_EXPLANATIONS && window.NIR_CHART_EXPLANATIONS.predicted_vs_measured) ||
                    nirGettext('Vorhergesagte gegen gemessene Referenzwerte; Punkte auf der Diagonalen bedeuten perfekte Vorhersage.');
                html += `<details class="small text-muted mt-1"><summary>${nirGettext('Was zeigt dieses Diagramm?')}</summary>${expl}</details></div>`;
            }
            // OP68: Sensor-Vergleich (alle Details) + Korrekturvarianten
            const cmp = data.sensor_comparison;
            if (cmp && cmp.performed) {
                html += `<h6 class="mt-2 mb-1"><i class="bi bi-cpu me-1"></i>${nirGettext('Sensor-Vergleich der Quellen')}</h6>`;
                html += '<div class="table-responsive"><table class="table table-sm table-striped mb-1 small align-middle"><thead><tr>' +
                    `<th>${nirGettext('Kanal')}</th><th>Med. A</th><th>Med. B</th><th>B/A</th><th>CV A %</th><th>CV B %</th></tr></thead><tbody>`;
                (cmp.channels || []).forEach(c => {
                    const r = c.ratio_b_over_a;
                    const cls = r == null ? '' : (r > 1.5 || r < 0.67 ? 'text-danger fw-bold' : (r > 1.2 || r < 0.83 ? 'text-warning' : ''));
                    html += `<tr><td>${c.name}</td><td>${c.median_a?.toFixed?.(0) ?? c.median_a}</td><td>${c.median_b?.toFixed?.(0) ?? c.median_b}</td>` +
                        `<td class="${cls}">${r != null ? r.toFixed(3) : '—'}</td><td>${c.cv_a_percent != null ? c.cv_a_percent.toFixed(1) : '—'}</td><td>${c.cv_b_percent != null ? c.cv_b_percent.toFixed(1) : '—'}</td></tr>`;
                });
                html += '</tbody></table></div>';
                if (cmp.correlation_structure) {
                    html += `<p class="small mb-1">${nirGettext('Korrelationsstruktur-Differenz (Sensor-Signatur)')}: ` +
                        `Ø |Δ| ${cmp.correlation_structure.mean_abs_diff?.toFixed(3)}, max ${cmp.correlation_structure.max_abs_diff?.toFixed(3)} ` +
                        `${nirGettext('bei')} ${cmp.correlation_structure.max_channel}. ${nirGettext('Signifikant unterschiedliche Kanäle (p<0.001)')}: ${cmp.n_significant_channels}/18.</p>`;
                }
                if (cmp.confounding) {
                    html += `<div class="alert ${cmp.confounding.median_iqr > 0.5 ? 'alert-warning' : 'alert-success'} py-2 small mb-2">${nirGettext(cmp.confounding.interpretation)} ` +
                        `(IQR max ${cmp.confounding.max_iqr?.toFixed(2)} ${nirGettext('bei')} ${cmp.confounding.max_iqr_channel})</div>`;
                }
            }
            const gcr = data.gain_curve_report;
            if (gcr) {
                if (gcr.estimable) {
                    html += `<div class="alert alert-success py-2 small mb-2"><i class="bi bi-check-circle me-1"></i>` +
                        nirGettext('Gain-Kurve aus Dark/White-Referenzen geschätzt (sensoragnostisch)') +
                        ` — ${nirGettext(gcr.confidence_note || '')}</div>`;
                } else {
                    html += `<div class="alert alert-secondary py-2 small mb-2"><i class="bi bi-info-circle me-1"></i>` +
                        `${nirGettext('Gain-Kurve nicht schätzbar:')} ${nirGettext(gcr.reason || '')} ` +
                        `${nirGettext('Vertrag: Dark/White-Abgleich mit ≥ 50 Wiederholungen je Quelle, als Referenzmessung deklariert (nur Fusionsprojekte).')}</div>`;
                }
            }
            const cv = data.correction_variants || {};
            const cvNames = Object.keys(cv);
            if (cvNames.length) {
                html += `<h6 class="mt-2 mb-1"><i class="bi bi-sliders me-1"></i>${nirGettext('Korrekturvarianten (Bewertung auf Basis korrigierter Zahlen)')}</h6>`;
                html += '<div class="table-responsive"><table class="table table-sm table-striped mb-2 small align-middle"><thead><tr>' +
                    `<th>${nirGettext('Variante')}</th><th>n</th><th>RMSE</th><th>MAE</th><th>${nirGettext('Treffer ±0,5')}</th><th>${nirGettext('Treffer ±1,0')}</th></tr></thead><tbody>`;
                cvNames.forEach(name => {
                    const pvr = cv[name].predicted_vs_reference || {};
                    const hits = pvr.hits_within_tolerance || {};
                    const first = Object.values(hits)[0];
                    const last = Object.values(hits)[Object.values(hits).length - 1];
                    html += `<tr><td><strong>${name}</strong></td><td>${pvr.n ?? '—'}</td><td>${pvr.rmse != null ? Number(pvr.rmse).toFixed(3) : '—'}</td>` +
                        `<td>${pvr.mae != null ? Number(pvr.mae).toFixed(3) : '—'}</td>` +
                        `<td>${first ? (100 * first.ratio).toFixed(0) + ' %' : '—'}</td><td>${last ? (100 * last.ratio).toFixed(0) + ' %' : '—'}</td></tr>`;
                });
                html += '</tbody></table></div>';
                if (data.corrected_verdict) {
                    html += `<div class="alert alert-info py-2 mb-2 small"><strong>${nirGettext('Korrigiertes Fazit:')}</strong> ${nirGettext(data.corrected_verdict)}</div>`;
                }
            }
            if (data.conclusion) {
                html += `<div class="alert alert-info py-2 mb-0 small"><strong>${nirGettext('Fazit:')}</strong> ${nirGettext(data.conclusion)}</div>`;
            }
            box.innerHTML = html;
            if (data.discussion_summary && window.nirChatbotContext) {
                let ds = data.discussion_summary;
                if (data.corrected_verdict) ds += ' Korrigierte Bewertung: ' + data.corrected_verdict;
                if (data.sensor_comparison && data.sensor_comparison.performed) {
                    const c = data.sensor_comparison;
                    ds += ' Sensor-Vergleich: ' + (c.n_significant_channels ?? '?') + ' von ' + (c.channels || []).length + ' Kanaelen signifikant verschieden (p<0.001)';
                    if (c.correlation_structure) ds += '; Korrelationsstruktur-Differenz max ' + (c.correlation_structure.max_abs_diff ?? '?') + ' bei ' + (c.correlation_structure.max_channel ?? '?');
                    if (c.confounding) ds += '; ' + c.confounding.interpretation;
                }
                if (data.gain_curve_report) {
                    ds += data.gain_curve_report.estimable
                        ? '; Gain-Kurve aus Dark/White-Referenzen geschätzt.'
                        : '; Gain-Kurve nicht schätzbar: ' + (data.gain_curve_report.reason || '');
                }
                window.nirChatbotContext.fusion_discussion = ds;
            }
        })
        .catch(err => {
            box.innerHTML = `<div class="alert alert-danger py-2 mb-0">${nirGettext('Kalibrationsvergleich fehlgeschlagen:')} ${err.message || err}</div>`;
        });
};

window.nirFusionMetadataSuggestions = function (projectId) {
    const box = document.getElementById('fusionMetaSuggestionsResult');
    if (!box) return;
    box.innerHTML = `<p class="mb-0 text-muted small">${nirGettext('Vorschläge werden geladen …')}</p>`;
    axios.get(`/api/projects/${projectId}/fusion/metadata-suggestions/`)
        .then(resp => {
            const data = resp.data || {};
            if (!data.success) { throw new Error(data.error || 'suggestions failed'); }
            if (!data.available || !data.suggestions || !data.suggestions.length) {
                box.innerHTML = `<p class="mb-0 small text-muted">${nirGettext('Keine Übernahme-Vorschläge: entweder alle Datensätze tragen bereits Metadaten, oder die Quellen haben keine verwertbaren Felder.')}</p>`;
                return;
            }
            let html = '';
            data.suggestions.forEach(s => {
                html += `<h6 class="mt-2 mb-1"><i class="bi bi-file-earmark-text me-1"></i>${s.file_name}</h6>`;
                html += '<table class="table table-sm mb-2"><thead><tr>' +
                    `<th>${nirGettext('Feld')}</th><th>${nirGettext('Vorgeschlagener Wert')}</th><th>${nirGettext('Aus Datensatz')}</th><th></th></tr></thead><tbody>`;
                s.proposals.forEach(pr => {
                    html += '<tr>' +
                        `<td><code>${pr.field}</code></td>` +
                        `<td>${pr.value}</td>` +
                        `<td class="small text-muted">${pr.source_file}</td>` +
                        `<td><button type="button" class="btn btn-sm btn-outline-primary py-0" onclick="nirApplyMetadataSuggestion('${projectId}', '${s.file_id || ''}', '${pr.field}', '${String(pr.value).replace(/'/g, "\\'")}')">` +
                        `${nirGettext('Übernehmen')}</button></td></tr>`;
                });
                html += '</tbody></table>';
            });
            html += `<p class="small text-muted mb-0">${nirGettext('Übernommene Werte landen im Metadaten-Editor unten – endgültig speichern dort.')}</p>`;
            box.innerHTML = html;
        })
        .catch(err => {
            box.innerHTML = `<div class="alert alert-danger py-2 mb-0">${nirGettext('Vorschläge fehlgeschlagen:')} ${err.message || err}</div>`;
        });
};

// Vorschlag in das Metadaten-Editor-Feld uebernehmen (Input fuellen,
// Speichern bleibt Nutzer-Entscheidung im Editor).
window.nirApplyMetadataSuggestion = function (projectId, fileId, field, value) {
    document.querySelectorAll('[data-file-id]').forEach(container => {
        if (container.dataset.fileId !== fileId) return;
        const input = container.querySelector(`[name="meta_${field}"]`);
        if (input) { input.value = value; input.classList.add('is-warning'); }
    });
};
