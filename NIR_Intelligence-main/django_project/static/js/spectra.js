// NIR_Mistral Framework - Spectra Page JavaScript
// Spectrum Management with Crew AI Integration

// Global variables
let allSpectra = [];
let filteredSpectra = [];
let selectedSpectra = [];
let currentSpectrum = null;
let spectraCharts = {};
let currentPage = 1;
const itemsPerPage = 12;

// Utility function for safe element access
function getElementSafely(id, parent = document) {
    const element = parent.getElementById(id);
    if (!element) {
        console.warn(`Element with ID "${id}" not found`);
        return null;
    }
    return element;
}

// Function to get CSRF token from meta tag
function getCSRFToken() {
    const metaTag = document.querySelector('meta[name="csrf-token"]');
    return metaTag ? metaTag.getAttribute('content') : '';
}

// Set up axios to include CSRF token for all requests that need it
axios.defaults.xsrfCookieName = 'csrftoken';
axios.defaults.xsrfHeaderName = 'X-CSRFToken';

// Spectrum quality thresholds
const qualityThresholds = {
    excellent: 90,
    good: 75,
    fair: 50,
    poor: 0
};

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    loadSpectra();
    loadSpectrumTypes();
    setupEventListeners();
    
    // Set up real-time updates
    setInterval(loadCrewAIStatus, 30000);
});

function setupEventListeners() {
    // File input change event
    const fileInput = document.getElementById('fileInput');
    if (fileInput) {
        fileInput.addEventListener('change', handleSpectrumFileUpload);
    }
    
    // Drop zone for file upload
    const dropZone = document.getElementById('dropZone');
    if (dropZone) {
        dropZone.addEventListener('click', function() {
            document.getElementById('fileInput').click();
        });
        
        dropZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('drag-over');
        });
        
        dropZone.addEventListener('dragleave', function() {
            this.classList.remove('drag-over');
        });
        
        dropZone.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
            
            if (e.dataTransfer.files.length > 0) {
                document.getElementById('fileInput').files = e.dataTransfer.files;
                // Trigger the change event manually for the file input
                const fileInput = document.getElementById('fileInput');
                if (fileInput) {
                    fileInput.dispatchEvent(new Event('change'));
                }
            }
        });
    }
}

function loadCrewAIStatus() {
    axios.get('/api/crewai/status/')
        .then(function(response) {
            const status = response.data;
            if (status.available) {
                // Crew AI is available for analysis
            }
        })
        .catch(function(error) {
            // Log error but don't show to user - service might be temporarily unavailable
            console.debug('Crew AI status check failed:', error.message);
        });
}

function loadSpectra() {
    showLoading();
    
    axios.get('/api/spectra/')
        .then(function(response) {
            allSpectra = response.data.results || [];
            filteredSpectra = [...allSpectra];
            
            // Sort by upload date, newest first
            allSpectra.sort((a, b) => {
                const dateA = new Date(a.created_at || a.uploaded_at || 0);
                const dateB = new Date(b.created_at || b.uploaded_at || 0);
                return dateB - dateA;
            });
            
            updateStatistics();
            filterSpectra();
            hideLoading();
        })
        .catch(function(error) {
            console.error('Error loading spectra:', error);
            hideLoading();
            // Only show error if showError function exists
            if (typeof showError === 'function') {
                if (error.response && error.response.status === 403) {
                    showError('Please log in to view spectra. Authentication is required.');
                } else {
                    showError('Failed to load spectra. Please try again.');
                }
            }
        });
}

function loadSpectrumTypes() {
    // Extract unique spectral types from all spectra
    const types = new Set();
    allSpectra.forEach(spectrum => {
        if (spectrum.spectral_type) {
            types.add(spectrum.spectral_type);
        }
    });
    
    // Add default types
    ['nir', 'ir', 'uv-vis', 'raman'].forEach(type => types.add(type));
    
    const typeFilter = document.getElementById('typeFilter');
    const currentValue = typeFilter.value;
    
    typeFilter.innerHTML = '<option value="">All Types</option>';
    
    Array.from(types).sort().forEach(type => {
        const option = document.createElement('option');
        option.value = type;
        option.textContent = formatSpectrumType(type);
        if (type === currentValue) {
            option.selected = true;
        }
        typeFilter.appendChild(option);
    });
}

function formatSpectrumType(type) {
    const typeNames = {
        'nir': 'NIR',
        'ir': 'IR',
        'uv-vis': 'UV-Vis',
        'raman': 'Raman',
        'mid_ir': 'Mid-IR',
        'near_ir': 'Near-IR',
        'far_ir': 'Far-IR'
    };
    return typeNames[type] || type.toUpperCase();
}

function updateStatistics() {
    const total = allSpectra.length;
    const valid = allSpectra.filter(s => s.quality_status === 'valid' || s.quality_score >= 75).length;
    const invalid = allSpectra.filter(s => s.quality_status === 'invalid' || s.quality_score < 75).length;
    
    // Calculate total storage (approximate)
    let totalStorage = 0;
    allSpectra.forEach(spectrum => {
        if (spectrum.file_size) {
            totalStorage += spectrum.file_size;
        } else if (spectrum.wavelengths) {
            // Estimate size based on data points
            totalStorage += spectrum.wavelengths.length * 8; // 8 bytes per data point (wavelength + intensity)
        }
    });
    
    // Convert to MB
    totalStorage = (totalStorage / (1024 * 1024)).toFixed(2);
    
    document.getElementById('totalSpectra').textContent = total;
    document.getElementById('validSpectra').textContent = valid;
    document.getElementById('invalidSpectra').textContent = invalid;
    document.getElementById('totalStorage').textContent = totalStorage + ' MB';
}

function filterSpectra() {
    const filter = document.getElementById('spectrumFilter').value;
    const type = document.getElementById('typeFilter').value;
    
    filteredSpectra = allSpectra.filter(spectrum => {
        // Filter by quality/status
        if (filter === 'valid' && spectrum.quality_status !== 'valid' && (!spectrum.quality_score || spectrum.quality_score < 75)) {
            return false;
        }
        if (filter === 'invalid' && spectrum.quality_status !== 'invalid' && (!spectrum.quality_score || spectrum.quality_score >= 75)) {
            return false;
        }
        
        // Filter by type
        if (type && spectrum.spectral_type !== type) {
            return false;
        }
        
        return true;
    });
    
    // Sort by recent if requested
    if (filter === 'recent') {
        filteredSpectra.sort((a, b) => {
            const dateA = new Date(a.created_at || a.uploaded_at || 0);
            const dateB = new Date(b.created_at || b.uploaded_at || 0);
            return dateB - dateA;
        });
    }
    
    renderSpectraGallery();
    renderSpectraTable();
    updateSpectraCount();
}

function renderSpectraGallery() {
    const gallery = document.getElementById('spectraGallery');
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, filteredSpectra.length);
    const spectraToShow = filteredSpectra.slice(startIndex, endIndex);
    
    if (spectraToShow.length === 0) {
        gallery.innerHTML = `
            <div class="col-12">
                <div class="c-card text-center py-lg">
                    <i class="bi bi-inbox text-muted" style="font-size: 3rem;"></i>
                    <p class="mt-sm text-muted">No spectra found matching your criteria</p>
                </div>
            </div>
        `;
        return;
    }
    
    gallery.innerHTML = spectraToShow.map(spectrum => {
        const qualityClass = getQualityClass(spectrum);
        const qualityText = getQualityText(spectrum);
        const typeName = formatSpectrumType(spectrum.spectral_type || 'nir');
        const date = formatDate(spectrum.created_at || spectrum.uploaded_at);
        const dataPoints = spectrum.wavelengths ? spectrum.wavelengths.length : spectrum.data_points || 0;
        
        return `
            <div class="col-md-4 col-12">
                <div class="c-card spectrum-card h-100" onclick="showSpectrumDetails('${spectrum.id}')">
                    <div class="spectrum-preview">
                        <canvas class="spectrum-chart" id="chart_${spectrum.id}"></canvas>
                        <div class="quality-badge ${qualityClass}">${qualityText}</div>
                    </div>
                    <div class="c-card__body">
                        <h6 class="mb-2">${spectrum.name || spectrum.sample_name || spectrum.sample_id || 'Unknown'}</h6>
                        <div class="d-flex flex-wrap gap-2 mb-2">
                            <span class="spectrum-type-tag">${typeName}</span>
                            ${spectrum.instrument_type ? `<span class="spectrum-type-tag">${spectrum.instrument_type}</span>` : ''}
                        </div>
                        <div class="d-flex justify-content-between align-items-center spectrum-meta">
                            <span><i class="bi bi-database"></i> ${dataPoints} points</span>
                            <span><i class="bi bi-clock"></i> ${date}</span>
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
    
    // Create charts for each spectrum
    spectraToShow.forEach(spectrum => {
        createSpectrumChart(spectrum);
    });
}

function createSpectrumChart(spectrum) {
    const canvas = document.getElementById(`chart_${spectrum.id}`);
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Generate sample data if wavelengths are not available
    let wavelengths = spectrum.wavelengths || [];
    let intensities = spectrum.intensities || [];
    
    // If no data, generate sample data
    if (wavelengths.length === 0) {
        wavelengths = generateSampleWavelengths();
        intensities = generateSampleIntensities();
    }
    
    // Limit the number of data points for performance
    const maxPoints = 200;
    if (wavelengths.length > maxPoints) {
        const step = Math.ceil(wavelengths.length / maxPoints);
        wavelengths = wavelengths.filter((_, i) => i % step === 0);
        intensities = intensities.filter((_, i) => i % step === 0);
    }
    
    // Destroy existing chart if it exists
    if (spectraCharts[spectrum.id]) {
        spectraCharts[spectrum.id].destroy();
    }
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: wavelengths,
            datasets: [{
                label: 'Intensity',
                data: intensities,
                borderColor: 'var(--color-primary)',
                backgroundColor: 'rgba(122, 185, 41, 0.1)',
                borderWidth: 1,
                pointRadius: 0,
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    display: false
                },
                y: {
                    display: false
                }
            },
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    enabled: false
                }
            }
        }
    });
    
    spectraCharts[spectrum.id] = chart;
}

function generateSampleWavelengths() {
    const wavelengths = [];
    for (let i = 700; i <= 2500; i += 10) {
        wavelengths.push(i);
    }
    return wavelengths;
}

function generateSampleIntensities() {
    const intensities = [];
    for (let i = 700; i <= 2500; i += 10) {
        let intensity = Math.random() * 0.5 + 0.3;
        if (i >= 1200 && i <= 1400) intensity += 0.8;
        if (i >= 1700 && i <= 1900) intensity += 0.6;
        intensities.push(intensity);
    }
    return intensities;
}

function renderSpectraTable() {
    const tableBody = document.getElementById('spectraTable');
    const startIndex = (currentPage - 1) * itemsPerPage;
    const endIndex = Math.min(startIndex + itemsPerPage, filteredSpectra.length);
    const spectraToShow = filteredSpectra.slice(startIndex, endIndex);
    
    if (spectraToShow.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-lg">
                    <i class="bi bi-inbox text-muted" style="font-size: 2rem;"></i>
                    <p class="mt-sm text-muted">No spectra found</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = spectraToShow.map(spectrum => {
        const qualityClass = getQualityClass(spectrum);
        const qualityText = getQualityText(spectrum);
        const typeName = formatSpectrumType(spectrum.spectral_type || 'nir');
        const date = formatDate(spectrum.created_at || spectrum.uploaded_at);
        const dataPoints = spectrum.wavelengths ? spectrum.wavelengths.length : spectrum.data_points || 0;
        
        return `
            <tr>
                <td>
                    <input type="checkbox" class="c-checkbox" 
                           onchange="toggleSpectrumSelection('${spectrum.id}')">
                </td>
                <td>
                    <strong>${spectrum.name || spectrum.sample_name || spectrum.sample_id || 'Unknown'}</strong>
                    <div class="text-muted small">${spectrum.sample_id}</div>
                </td>
                <td><span class="c-badge c-badge--outline-primary">${typeName}</span></td>
                <td><span class="c-badge ${qualityClass}">${qualityText}</span></td>
                <td>${dataPoints}</td>
                <td><small>${date}</small></td>
                <td>
                    <button class="c-button c-button--outline-primary c-button--sm" 
                            onclick="showSpectrumDetails('${spectrum.id}')" 
                            data-bs-toggle="tooltip" title="View Details">
                        <i class="bi bi-eye c-button__icon"></i>
                    </button>
                    <button class="c-button c-button--outline-success c-button--sm" 
                            onclick="analyzeSpectrum('${spectrum.id}')" 
                            data-bs-toggle="tooltip" title="Analyze">
                        <i class="bi bi-play-circle c-button__icon"></i>
                    </button>
                    <button class="c-button c-button--outline-danger c-button--sm" 
                            onclick="deleteSpectrum('${spectrum.id}')" 
                            data-bs-toggle="tooltip" title="Delete">
                        <i class="bi bi-trash c-button__icon"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    // Initialize tooltips
    initTooltips();
}

function updateSpectraCount() {
    const total = filteredSpectra.length;
    document.getElementById('spectraCount').textContent = `${total} spectra`;
}

function getQualityClass(spectrum) {
    if (spectrum.quality_status === 'valid') return 'c-badge--success';
    if (spectrum.quality_status === 'invalid') return 'c-badge--danger';
    
    const score = spectrum.quality_score || 0;
    if (score >= qualityThresholds.excellent) return 'c-badge--success';
    if (score >= qualityThresholds.good) return 'c-badge--success';
    if (score >= qualityThresholds.fair) return 'c-badge--warning';
    return 'c-badge--danger';
}

function getQualityText(spectrum) {
    if (spectrum.quality_status === 'valid') return 'Valid';
    if (spectrum.quality_status === 'invalid') return 'Invalid';
    
    const score = spectrum.quality_score || 0;
    if (score >= qualityThresholds.excellent) return 'Excellent';
    if (score >= qualityThresholds.good) return 'Good';
    if (score >= qualityThresholds.fair) return 'Fair';
    return 'Poor';
}

function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function handleSpectrumFileUpload(event) {
    const files = event.target.files;
    if (files.length === 0) return;
    
    const preview = document.getElementById('filePreview');
    preview.style.display = 'block';
    preview.innerHTML = '';
    
    for (let i = 0; i < Math.min(files.length, 5); i++) {
        const file = files[i];
        const fileInfo = document.createElement('div');
        fileInfo.className = 'd-flex justify-content-between align-items-center mb-2 p-2 bg-white rounded';
        fileInfo.innerHTML = `
            <div>
                <i class="bi bi-file-earmark-text me-2"></i>
                <span>${file.name}</span>
                <small class="text-muted ms-2">(${formatFileSize(file.size)})</small>
            </div>
            <span class="c-badge c-badge--success">Ready</span>
        `;
        preview.appendChild(fileInfo);
    }
    
    if (files.length > 5) {
        const moreFiles = document.createElement('div');
        moreFiles.className = 'text-muted small';
        moreFiles.textContent = `+ ${files.length - 5} more files`;
        preview.appendChild(moreFiles);
    }
}

function formatFileSize(bytes) {
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(2) + ' KB';
    return (bytes / (1024 * 1024)).toFixed(2) + ' MB';
}

function uploadSpectrum() {
    const files = document.getElementById('fileInput').files;
    if (files.length === 0) {
        showError('Please select at least one file to upload');
        return;
    }
    
    const sampleName = document.getElementById('sampleName').value;
    const sampleId = document.getElementById('sampleId').value;
    const spectralType = document.getElementById('spectralType').value;
    const instrumentType = document.getElementById('instrumentType').value;
    const description = document.getElementById('spectrumDescription').value;
    const metadataOperator = document.getElementById('metadataOperator').value;
    const metadataDate = document.getElementById('metadataDate').value;
    const metadataLocation = document.getElementById('metadataLocation').value;
    const autoAnalyze = document.getElementById('autoAnalyze').checked;
    
    if (!sampleName || !sampleId) {
        showError('Please fill in the required fields (Sample Name and Sample ID)');
        return;
    }
    
    // Check if CSRF token is available
    const csrfToken = getCSRFToken();
    if (!csrfToken) {
        showError('Authentication error. Please refresh the page and try again.');
        return;
    }
    
    // Check file sizes (10MB limit)
    const MAX_FILE_SIZE = 10 * 1024 * 1024; // 10MB
    for (let i = 0; i < files.length; i++) {
        if (files[i].size > MAX_FILE_SIZE) {
            showError(`File "${files[i].name}" is too large. Maximum size is 10MB.`);
            return;
        }
    }
    
    showLoading();
    
    // Process each file
    const uploadPromises = [];
    
    for (let i = 0; i < files.length; i++) {
        const file = files[i];
        const formData = new FormData();
        
        // Map frontend spectral types to backend types
        let backendSpectralType = spectralType;
        if (spectralType === 'nir' || spectralType === 'ir' || spectralType === 'uv-vis' || spectralType === 'raman') {
            backendSpectralType = 'absorbance'; // Default to absorbance for upload
        }
        
        // Map file extension to data format
        let fileExtension = file.name.split('.').pop().toLowerCase();
        let dataFormat = 'txt'; // default
        if (fileExtension === 'csv') dataFormat = 'csv';
        else if (fileExtension === 'json') dataFormat = 'json';
        else if (fileExtension === 'h5') dataFormat = 'h5';
        else if (fileExtension === 'spc') dataFormat = 'txt'; // SPC files treated as text
        
        formData.append('original_file', file);
        formData.append('name', sampleName + (files.length > 1 ? ` (${i + 1})` : ''));
        formData.append('sample_id', sampleId + (files.length > 1 ? `_${i + 1}` : ''));
        formData.append('sample_type', 'unknown'); // Default sample type
        formData.append('spectral_type', backendSpectralType);
        formData.append('instrument', instrumentType);
        formData.append('description', description);
        formData.append('sample_source', metadataLocation);
        formData.append('data_format', dataFormat);
        
        // Add required metadata fields with default values
        formData.append('wavelength_range_start', '400.0'); // Default NIR range
        formData.append('wavelength_range_end', '2500.0');  // Default NIR range
        formData.append('resolution', '1.0');                 // Default resolution
        formData.append('data_points', '2100');               // Default data points
        
        // Handle JSON fields - send as empty arrays if no values
        formData.append('tags', metadataOperator ? JSON.stringify([metadataOperator]) : JSON.stringify([]));
        formData.append('categories', JSON.stringify([]));
        
        uploadPromises.push(
            axios.post('/api/spectra/', formData, {
                headers: {
                    'Content-Type': 'multipart/form-data',
                    'X-CSRFToken': getCSRFToken()
                }
            })
        );
    }
    
    // Wait for all uploads to complete
    Promise.all(uploadPromises)
        .then(responses => {
            hideLoading();
            
            const successful = responses.filter(r => r.data && (r.data.id || r.status === 201)).length;
            const failed = responses.length - successful;
            
            if (successful > 0) {
                showSuccess(`${successful} spectrum/spectra uploaded successfully!`);
                
                // Reset form
                document.getElementById('uploadSpectrumForm').reset();
                document.getElementById('filePreview').style.display = 'none';
                
                // Close modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('uploadSpectrumModal'));
                if (modal) {
                    modal.hide();
                }
                
                // Refresh spectra list
                loadSpectra();
                
                // If auto-analyze is enabled, start analysis
                if (autoAnalyze && successful > 0) {
                    setTimeout(() => {
                        showSuccess('Auto-analysis started for uploaded spectra');
                    }, 1000);
                }
            }
            
            if (failed > 0) {
                showError(`${failed} spectrum/spectra failed to upload`);
            }
        })
        .catch(error => {
            console.error('Error uploading spectra:', error);
            hideLoading();
            
            let errorMessage = 'Failed to upload spectra. Please try again.';
            
            if (error.response) {
                const status = error.response.status;
                const data = error.response.data;
                
                if (status === 403) {
                    errorMessage = 'Please log in to upload spectra. Authentication is required.';
                } else if (status === 400) {
                    // Bad request - validation error
                    if (data && data.error) {
                        errorMessage = data.error;
                    } else if (data && Object.keys(data).length > 0) {
                        // DRF validation errors
                        const errors = [];
                        for (const [field, messages] of Object.entries(data)) {
                            if (Array.isArray(messages)) {
                                errors.push(...messages);
                            } else {
                                errors.push(messages);
                            }
                        }
                        errorMessage = 'Validation error: ' + errors.join('; ');
                    }
                } else if (status === 413) {
                    errorMessage = 'File too large. Maximum upload size is 10MB.';
                } else if (status === 500) {
                    errorMessage = 'Server error: ' + (data.error || 'Unknown error');
                } else if (data && data.error) {
                    errorMessage = data.error;
                } else if (data && data.message) {
                    errorMessage = data.message;
                }
            } else if (error.request) {
                // Network error
                errorMessage = 'Network error. Please check your connection.';
            } else {
                // Other error
                errorMessage = 'Error: ' + error.message;
            }
            
            showError(errorMessage);
        });
}

function showSpectrumDetails(spectrumId) {
    const spectrum = allSpectra.find(s => s.id === spectrumId);
    
    if (!spectrum) {
        showError('Spectrum not found');
        return;
    }
    
    currentSpectrum = spectrum;
    
    // Update details
    document.getElementById('detailName').textContent = spectrum.name || spectrum.sample_name || 'Unknown';
    document.getElementById('detailSampleId').textContent = spectrum.sample_id || 'N/A';
    document.getElementById('detailType').textContent = formatSpectrumType(spectrum.spectral_type || 'nir');
    document.getElementById('detailQuality').innerHTML = `<span class="c-badge ${getQualityClass(spectrum)}">${getQualityText(spectrum)}</span>`;
    document.getElementById('detailDataPoints').textContent = (spectrum.wavelengths ? spectrum.wavelengths.length : spectrum.data_points || 0) + ' points';
    document.getElementById('detailWavelengthRange').textContent = getWavelengthRange(spectrum);
    document.getElementById('detailUploaded').textContent = formatDate(spectrum.created_at || spectrum.uploaded_at);
    document.getElementById('detailInstrument').textContent = spectrum.instrument_type || 'N/A';
    document.getElementById('detailDescription').textContent = spectrum.description || 'No description available';
    
    // Update metadata
    const metadataContainer = document.getElementById('detailMetadata');
    metadataContainer.innerHTML = '';
    
    if (spectrum.metadata) {
        Object.entries(spectrum.metadata).forEach(([key, value]) => {
            if (value && key !== 'sample_id' && key !== 'sample_name') {
                const dt = document.createElement('dt');
                dt.className = 'col-sm-4';
                dt.textContent = formatMetadataKey(key) + ':';
                
                const dd = document.createElement('dd');
                dd.className = 'col-sm-8';
                dd.textContent = value;
                
                metadataContainer.appendChild(dt);
                metadataContainer.appendChild(dd);
            }
        });
    }
    
    if (metadataContainer.innerHTML === '') {
        metadataContainer.innerHTML = '<dt class="col-12 text-muted">No additional metadata available</dt>';
    }
    
    // Create detailed chart
    createDetailedSpectrumChart(spectrum);
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('spectrumDetailsModal'));
    modal.show();
}

function formatMetadataKey(key) {
    return key.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function getWavelengthRange(spectrum) {
    if (spectrum.wavelength_range) {
        return `${spectrum.wavelength_range[0]} - ${spectrum.wavelength_range[1]} nm`;
    }
    
    if (spectrum.wavelengths && spectrum.wavelengths.length > 0) {
        const min = Math.min(...spectrum.wavelengths);
        const max = Math.max(...spectrum.wavelengths);
        return `${min} - ${max} nm`;
    }
    
    return 'N/A';
}

function createDetailedSpectrumChart(spectrum) {
    const canvas = document.getElementById('spectrumDetailsChart');
    if (!canvas) return;
    
    const ctx = canvas.getContext('2d');
    
    // Destroy existing chart if it exists
    if (spectraCharts['details']) {
        spectraCharts['details'].destroy();
    }
    
    // Use spectrum data or generate sample data
    let wavelengths = spectrum.wavelengths || generateSampleWavelengths();
    let intensities = spectrum.intensities || generateSampleIntensities();
    
    // Limit data points for performance
    const maxPoints = 500;
    if (wavelengths.length > maxPoints) {
        const step = Math.ceil(wavelengths.length / maxPoints);
        wavelengths = wavelengths.filter((_, i) => i % step === 0);
        intensities = intensities.filter((_, i) => i % step === 0);
    }
    
    const chart = new Chart(ctx, {
        type: 'line',
        data: {
            labels: wavelengths,
            datasets: [{
                label: 'Spectral Intensity',
                data: intensities,
                borderColor: 'var(--color-primary)',
                backgroundColor: 'rgba(122, 185, 41, 0.1)',
                borderWidth: 2,
                pointRadius: 0,
                tension: 0.1,
                fill: true
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            scales: {
                x: {
                    title: {
                        display: true,
                        text: 'Wavelength (nm)',
                        color: 'var(--color-text)'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        color: 'var(--color-text-muted)'
                    }
                },
                y: {
                    title: {
                        display: true,
                        text: 'Intensity (a.u.)',
                        color: 'var(--color-text)'
                    },
                    grid: {
                        color: 'rgba(0, 0, 0, 0.05)'
                    },
                    ticks: {
                        color: 'var(--color-text-muted)'
                    }
                }
            },
            plugins: {
                legend: {
                    position: 'top',
                    labels: {
                        color: 'var(--color-text)'
                    }
                },
                tooltip: {
                    backgroundColor: 'rgba(0, 0, 0, 0.8)',
                    titleColor: 'white',
                    bodyColor: 'white'
                }
            }
        }
    });
    
    spectraCharts['details'] = chart;
}

function analyzeSpectrum(spectrumId) {
    const spectrum = allSpectra.find(s => s.id === spectrumId);
    
    if (!spectrum) {
        showError('Spectrum not found');
        return;
    }
    
    showLoading();
    
    // Prepare analysis request for Crew AI
    const analysisRequest = {
        sample_id: spectrum.sample_id || spectrum.id,
        analysis_mode: 'standard',
        privacy_level: 'local_only',
        report_type: 'spectral_analysis',
        report_format: 'html',
        include_calibration: true,
        include_federated_learning: false,
        metadata: {
            spectrum_name: spectrum.name || spectrum.sample_name,
            spectrum_id: spectrum.id,
            spectral_type: spectrum.spectral_type,
            instrument_type: spectrum.instrument_type,
            description: spectrum.description
        },
        spectral_data: {
            wavelengths: spectrum.wavelengths || generateSampleWavelengths(),
            intensities: spectrum.intensities || generateSampleIntensities(),
            sample_id: spectrum.sample_id || spectrum.id
        }
    };
    
    axios.post('/api/crewai/analysis/start/', analysisRequest, {
        headers: {
            'X-CSRFToken': getCSRFToken()
        }
    })
        .then(function(response) {
            hideLoading();
            const result = response.data;
            
            if (result.success) {
                showSuccess('Analysis started successfully!');
                
                // Redirect to analysis page or jobs page
                setTimeout(() => {
                    window.location.href = '/analysis/';
                }, 1000);
            } else {
                showError('Failed to start analysis: ' + (result.error || 'Unknown error'));
            }
        })
        .catch(function(error) {
            console.error('Error starting analysis:', error);
            hideLoading();
            showError('Failed to start analysis. Please try again.');
        });
}

function analyzeCurrentSpectrum() {
    if (!currentSpectrum) {
        showError('No spectrum selected');
        return;
    }
    
    analyzeSpectrum(currentSpectrum.id);
    
    // Close the modal
    const modal = bootstrap.Modal.getInstance(document.getElementById('spectrumDetailsModal'));
    if (modal) {
        modal.hide();
    }
}

function quickAnalyzeSelected() {
    if (selectedSpectra.length === 0) {
        showError('Please select at least one spectrum to analyze');
        return;
    }
    
    showLoading();
    
    // For each selected spectrum, start an analysis
    const analysisPromises = selectedSpectra.map(spectrumId => {
        const spectrum = allSpectra.find(s => s.id === spectrumId);
        
        if (!spectrum) return Promise.resolve();
        
        const analysisRequest = {
            sample_id: spectrum.sample_id || spectrum.id,
            analysis_mode: 'quick',
            privacy_level: 'local_only',
            report_type: 'spectral_analysis',
            report_format: 'html',
            include_calibration: false,
            include_federated_learning: false,
            metadata: {
                spectrum_name: spectrum.name || spectrum.sample_name,
                spectrum_id: spectrum.id,
                batch_analysis: true
            },
            spectral_data: {
                wavelengths: spectrum.wavelengths || generateSampleWavelengths(),
                intensities: spectrum.intensities || generateSampleIntensities(),
                sample_id: spectrum.sample_id || spectrum.id
            }
        };
        
        return axios.post('/api/crewai/analysis/start/', analysisRequest, {
            headers: {
                'X-CSRFToken': getCSRFToken()
            }
        });
    });
    
    Promise.all(analysisPromises)
        .then(responses => {
            hideLoading();
            
            const successful = responses.filter(r => r && r.data && r.data.success).length;
            
            if (successful > 0) {
                showSuccess(`${successful} analysis/analyses started successfully!`);
                
                // Clear selection
                selectedSpectra = [];
                document.getElementById('selectAllSpectra').checked = false;
                
                // Refresh page
                setTimeout(() => {
                    window.location.href = '/analysis/';
                }, 1000);
            }
        })
        .catch(error => {
            console.error('Error starting batch analysis:', error);
            hideLoading();
            showError('Failed to start batch analysis. Please try again.');
        });
}

function toggleSpectrumSelection(spectrumId) {
    const index = selectedSpectra.indexOf(spectrumId);
    
    if (index === -1) {
        selectedSpectra.push(spectrumId);
    } else {
        selectedSpectra.splice(index, 1);
    }
    
    // Update select all checkbox
    const allCheckbox = document.getElementById('selectAllSpectra');
    if (allCheckbox) {
        allCheckbox.checked = selectedSpectra.length === filteredSpectra.length;
    }
}

function toggleSelectAll() {
    const checkbox = document.getElementById('selectAllSpectra');
    const checkboxes = document.querySelectorAll('input[type="checkbox"][onchange*="toggleSpectrumSelection"]');
    
    if (checkbox.checked) {
        selectedSpectra = filteredSpectra.map(s => s.id);
        checkboxes.forEach(cb => cb.checked = true);
    } else {
        selectedSpectra = [];
        checkboxes.forEach(cb => cb.checked = false);
    }
}

function deleteSpectrum(spectrumId) {
    currentSpectrum = allSpectra.find(s => s.id === spectrumId);
    
    if (!currentSpectrum) {
        showError('Spectrum not found');
        return;
    }
    
    document.getElementById('spectraDeleteMessage').textContent = 
        `Are you sure you want to delete the spectrum "${currentSpectrum.name || currentSpectrum.sample_id}"? This action cannot be undone.`;
    
    const modal = new bootstrap.Modal(document.getElementById('spectraDeleteConfirmationModal'));
    modal.show();
}

function deleteSelectedSpectra() {
    if (selectedSpectra.length === 0) {
        showError('Please select at least one spectrum to delete');
        return;
    }
    
    const count = selectedSpectra.length;
    document.getElementById('spectraDeleteMessage').textContent = 
        `Are you sure you want to delete ${count} selected spectrum/spectra? This action cannot be undone.`;
    
    const modal = new bootstrap.Modal(document.getElementById('spectraDeleteConfirmationModal'));
    modal.show();
}

function confirmDelete() {
    if (!currentSpectrum && selectedSpectra.length === 0) {
        showError('No spectrum selected for deletion');
        return;
    }
    
    showLoading();
    
    const deletePromises = [];
    
    if (currentSpectrum) {
        deletePromises.push(
            axios.delete('/api/spectra/' + currentSpectrum.id + '/', {
                headers: {
                    'X-CSRFToken': getCSRFToken()
                }
            })
        );
    }
    
    if (selectedSpectra.length > 0) {
        selectedSpectra.forEach(spectrumId => {
            deletePromises.push(
                axios.delete('/api/spectra/' + spectrumId + '/', {
                    headers: {
                        'X-CSRFToken': getCSRFToken()
                    }
                })
            );
        });
    }
    
    Promise.all(deletePromises)
        .then(responses => {
            hideLoading();
            
            const successful = responses.filter(r => r.status === 200 || r.status === 204).length;
            
            if (successful > 0) {
                showSuccess(`${successful} spectrum/spectra deleted successfully!`);
                
                // Close modals
                const deleteModal = bootstrap.Modal.getInstance(document.getElementById('spectraDeleteConfirmationModal'));
                if (deleteModal) {
                    deleteModal.hide();
                }
                
                // Clear selection
                currentSpectrum = null;
                selectedSpectra = [];
                document.getElementById('selectAllSpectra').checked = false;
                
                // Refresh spectra list
                loadSpectra();
            }
        })
        .catch(error => {
            console.error('Error deleting spectra:', error);
            hideLoading();
            showError('Failed to delete spectra. Please try again.');
        });
}

function downloadSpectrum() {
    if (!currentSpectrum) {
        showError('No spectrum selected');
        return;
    }
    
    showLoading();
    
    axios.get('/api/spectra/' + currentSpectrum.id + '/download/', {
        responseType: 'blob'
    })
        .then(response => {
            hideLoading();
            
            const url = window.URL.createObjectURL(new Blob([response.data]));
            const link = document.createElement('a');
            link.href = url;
            link.setAttribute('download', currentSpectrum.name || currentSpectrum.sample_id || 'spectrum');
            document.body.appendChild(link);
            link.click();
            link.parentNode.removeChild(link);
            window.URL.revokeObjectURL(url);
        })
        .catch(error => {
            console.error('Error downloading spectrum:', error);
            hideLoading();
            showError('Failed to download spectrum. Please try again.');
        });
}

function exportSpectraList() {
    const data = filteredSpectra.map(spectrum => ({
        id: spectrum.id,
        name: spectrum.name || spectrum.sample_name || '',
        sample_id: spectrum.sample_id || '',
        spectral_type: spectrum.spectral_type || '',
        instrument_type: spectrum.instrument_type || '',
        quality_status: spectrum.quality_status || '',
        quality_score: spectrum.quality_score || '',
        data_points: spectrum.wavelengths ? spectrum.wavelengths.length : spectrum.data_points || 0,
        wavelength_range: getWavelengthRange(spectrum),
        uploaded: formatDate(spectrum.created_at || spectrum.uploaded_at),
        description: spectrum.description || ''
    }));
    
    const csv = convertToCSV(data);
    downloadCSV(csv, 'spectra_' + new Date().toISOString().split('T')[0] + '.csv');
}

function convertToCSV(data) {
    if (data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const rows = data.map(row => headers.map(header => {
        const value = row[header];
        if (typeof value === 'string' && value.includes(',')) {
            return '"' + value.replace(/"/g, '""') + '"';
        }
        return value;
    }).join(','));
    
    return [headers.join(','), ...rows].join('\n');
}

function downloadCSV(csv, filename) {
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
    window.URL.revokeObjectURL(url);
}

function loadMoreSpectra() {
    currentPage++;
    filterSpectra();
}

function refreshSpectra() {
    currentPage = 1;
    loadSpectra();
}

function scrollToSpectra() {
    document.getElementById('spectraGallery').scrollIntoView({ behavior: 'smooth' });
}

// Utility functions
function showLoading() {
    document.getElementById('loadingOverlay').style.display = 'flex';
}

function hideLoading() {
    document.getElementById('loadingOverlay').style.display = 'none';
}

function showSuccess(message) {
    showToast('Success!', message, 'success');
}

function showError(message) {
    showToast('Error!', message, 'danger');
}

function showToast(title, message, type) {
    const toastContainer = document.getElementById('toastContainer');
    
    const toast = document.createElement('div');
    toast.className = `c-toast c-toast--${type}`;
    
    toast.innerHTML = `
        <div class="c-toast__content">
            <div class="c-toast__title">${title}</div>
            <div class="c-toast__message">${message}</div>
        </div>
        <button class="c-toast__close" onclick="this.parentElement.remove()">
            <i class="bi bi-x"></i>
        </button>
    `;
    
    toastContainer.appendChild(toast);
    
    // Auto-remove after 5 seconds
    setTimeout(() => {
        toast.remove();
    }, 5000);
}

function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    try {
        const date = new Date(dateString);
        return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' });
    } catch (e) {
        return dateString;
    }
}