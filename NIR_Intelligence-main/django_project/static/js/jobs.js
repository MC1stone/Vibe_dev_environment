// NIR_Mistral Framework - Jobs Page JavaScript
// Crew AI Job Management with Real-time Updates

// Global variables
let allJobs = [];
let filteredJobs = [];
let selectedJobs = [];
let currentJob = null;
let availableSpectra = [];
let currentStatusFilter = '';
let currentSortOrder = 'newest';

// Utility function for safe element access
function getElementSafely(id, parent = document) {
    const element = parent.getElementById(id);
    if (!element) {
        console.warn(`Element with ID "${id}" not found`);
        return null;
    }
    return element;
}

// Job status definitions
const jobStatuses = {
    'pending': { name: 'Pending', color: 'var(--color-warning)', badge: 'c-badge--warning', icon: 'bi-clock' },
    'running': { name: 'Running', color: 'var(--color-info)', badge: 'c-badge--info', icon: 'bi-play-circle' },
    'completed': { name: 'Completed', color: 'var(--color-success)', badge: 'c-badge--success', icon: 'bi-check-circle' },
    'failed': { name: 'Failed', color: 'var(--color-danger)', badge: 'c-badge--danger', icon: 'bi-exclamation-circle' },
    'cancelled': { name: 'Cancelled', color: 'var(--color-secondary)', badge: 'c-badge--secondary', icon: 'bi-stop-circle' }
};

// Agent information
const agentInfo = {
    'SpectralAnalysisAgent': { name: 'Spectral Analysis Agent', icon: 'bi-graph-up', color: 'var(--color-primary)' },
    'MetadataQualityAgent': { name: 'Metadata Quality Agent', icon: 'bi-check-circle', color: 'var(--color-primary-dark)' },
    'CalibrationAgent': { name: 'Calibration Agent', icon: 'bi-tools', color: 'var(--color-primary-light)' },
    'ReportingAgent': { name: 'Reporting Agent', icon: 'bi-file-earmark-text', color: '#5a8a3f' },
    'FlowerAgent': { name: 'Flower Federated Learning Agent', icon: 'bi-cloud', color: '#007bff' }
};

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    loadJobs();
    loadSpectra();
    setupEventListeners();
    
    // Set up real-time updates
    setInterval(refreshActiveJobs, 10000);
    setInterval(loadCrewAIStatus, 30000);
});

function setupEventListeners() {
    // Set up status filter styling
    document.querySelectorAll('.status-filter-badge').forEach(badge => {
        badge.addEventListener('click', function() {
            document.querySelectorAll('.status-filter-badge').forEach(b => b.classList.remove('active'));
            this.classList.add('active');
        });
    });
}

function loadCrewAIStatus() {
    axios.get('/api/crewai/status/')
        .then(function(response) {
            const status = response.data;
            if (status.available) {
                // Crew AI is available
            }
        })
        .catch(function(error) {
            // Log error but don't show to user - service might be temporarily unavailable
            console.debug('Crew AI status check failed:', error.message);
        });
}

function loadJobs() {
    showLoading();
    
    // Load jobs from both Crew AI and regular API
    const promises = [
        axios.get('/api/jobs/'),
        axios.get('/api/crewai/analysis/history/?limit=50')
    ];
    
    Promise.all(promises)
        .then(responses => {
            allJobs = [];
            
            // Process regular jobs
            if (responses[0].data && responses[0].data.results) {
                allJobs = allJobs.concat(responses[0].data.results);
            }
            
            // Process Crew AI jobs
            if (responses[1].data && responses[1].data.history) {
                responses[1].data.history.forEach(crewaiJob => {
                    // Convert Crew AI job to standard format
                    const job = {
                        id: crewaiJob.request_id,
                        name: crewaiJob.sample_id || 'Crew AI Analysis',
                        analysis_type: crewaiJob.report_type || 'spectral_analysis',
                        agent: 'CrewAI',
                        status: crewaiJob.status || 'completed',
                        progress: crewaiJob.progress || 100,
                        created_at: crewaiJob.timestamp,
                        completed_at: crewaiJob.completed_at,
                        duration: crewaiJob.processing_time || 0,
                        description: crewaiJob.summary || 'Crew AI analysis job',
                        sample_id: crewaiJob.sample_id,
                        is_crewai: true,
                        crewai_data: crewaiJob
                    };
                    allJobs.push(job);
                });
            }
            
            // Sort by creation date, newest first
            allJobs.sort((a, b) => {
                const dateA = new Date(a.created_at || 0);
                const dateB = new Date(b.created_at || 0);
                return dateB - dateA;
            });
            
            filteredJobs = [...allJobs];
            filterByStatus(currentStatusFilter);
            sortJobs();
            updateStatistics();
            hideLoading();
        })
        .catch(error => {
            console.error('Error loading jobs:', error);
            hideLoading();
            showError('Failed to load jobs. Please try again.');
        });
}

function loadSpectra() {
    axios.get('/api/spectra/')
        .then(function(response) {
            availableSpectra = response.data.results || [];
            
            // Update spectra selection in create job modal
            updateSpectraSelection();
        })
        .catch(function(error) {
            console.error('Error loading spectra:', error);
            availableSpectra = [];
        });
}

function updateSpectraSelection() {
    const container = document.getElementById('jobSpectraSelection');
    if (!container) return;
    
    container.innerHTML = '';
    
    if (availableSpectra.length > 0) {
        availableSpectra.forEach(spectrum => {
            const div = document.createElement('div');
            div.className = 'col-md-6';
            div.innerHTML = `
                <div class="c-form-check">
                    <input class="c-checkbox" type="checkbox" 
                           name="spectrum_ids" value="${spectrum.id}" id="job_spectrum_${spectrum.id}">
                    <label class="c-checkbox__label" for="job_spectrum_${spectrum.id}">
                        ${spectrum.name || spectrum.sample_name || spectrum.sample_id || spectrum.id}
                    </label>
                </div>
            `;
            container.appendChild(div);
        });
    } else {
        container.innerHTML = '<div class="col-12"><p class="text-muted small">No spectra available. Upload spectra first.</p></div>';
    }
}

function updateStatistics() {
    const total = allJobs.length;
    const completed = allJobs.filter(j => j.status === 'completed').length;
    const running = allJobs.filter(j => j.status === 'running').length;
    const pending = allJobs.filter(j => j.status === 'pending').length;
    const active = running + pending;
    
    document.getElementById('totalJobs').textContent = total;
    document.getElementById('completedJobs').textContent = completed;
    document.getElementById('runningJobs').textContent = running;
    document.getElementById('pendingJobs').textContent = pending;
    document.getElementById('activeJobsCount').textContent = active;
}

function filterByStatus(status) {
    currentStatusFilter = status;
    
    if (status === '') {
        filteredJobs = [...allJobs];
    } else {
        filteredJobs = allJobs.filter(job => job.status === status);
    }
    
    sortJobs();
    renderActiveJobs();
    renderJobsTable();
    updateJobsCount();
}

function sortJobs() {
    const sortOrder = document.getElementById('sortOrder').value;
    currentSortOrder = sortOrder;
    
    switch (sortOrder) {
        case 'newest':
            filteredJobs.sort((a, b) => {
                const dateA = new Date(a.created_at || 0);
                const dateB = new Date(b.created_at || 0);
                return dateB - dateA;
            });
            break;
        case 'oldest':
            filteredJobs.sort((a, b) => {
                const dateA = new Date(a.created_at || 0);
                const dateB = new Date(b.created_at || 0);
                return dateA - dateB;
            });
            break;
        case 'fastest':
            filteredJobs.sort((a, b) => (a.duration || 0) - (b.duration || 0));
            break;
        case 'slowest':
            filteredJobs.sort((a, b) => (b.duration || 0) - (a.duration || 0));
            break;
    }
    
    renderActiveJobs();
    renderJobsTable();
}

function renderActiveJobs() {
    const grid = document.getElementById('activeJobsGrid');
    const activeJobs = filteredJobs.filter(job => job.status === 'running' || job.status === 'pending');
    
    if (activeJobs.length === 0) {
        grid.innerHTML = `
            <div class="col-12">
                <div class="c-card text-center py-lg">
                    <i class="bi bi-inbox text-muted" style="font-size: 3rem;"></i>
                    <p class="mt-sm text-muted">No active jobs</p>
                </div>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = activeJobs.map(job => {
        const statusInfo = jobStatuses[job.status] || jobStatuses.pending;
        const agentInfoData = agentInfo[job.agent] || { name: job.agent, icon: 'bi-robot', color: 'var(--color-primary)' };
        const progress = job.progress || 0;
        
        return `
            <div class="col-md-4 col-12">
                <div class="c-card job-card h-100" onclick="showJobDetails('${job.id}')">
                    <div class="c-card__body">
                        <div class="d-flex justify-content-between align-items-start mb-3">
                            <div>
                                <h6 class="mb-1">${job.name || job.id || 'Unknown'}</h6>
                                <p class="text-muted small mb-0">${job.id}</p>
                            </div>
                            <span class="c-badge ${statusInfo.badge}">${statusInfo.name}</span>
                        </div>
                        
                        <div class="d-flex align-items-center mb-3">
                            <div class="job-agent-avatar" style="background: ${agentInfoData.color};">
                                <i class="bi ${agentInfoData.icon}"></i>
                            </div>
                            <div>
                                <strong>${agentInfoData.name}</strong>
                                <div class="text-muted small">${job.analysis_type || 'Analysis'}</div>
                            </div>
                        </div>
                        
                        <div class="job-progress">
                            <div class="job-progress-bar bg-primary" style="width: ${progress}%;"></div>
                        </div>
                        
                        <div class="d-flex justify-content-between align-items-center text-muted small">
                            <span><i class="bi bi-clock me-1"></i> ${formatDuration(job.duration)}</span>
                            <span><i class="bi bi-calendar me-1"></i> ${formatDate(job.created_at)}</span>
                        </div>
                        
                        ${job.sample_id ? `
                        <div class="mt-3 pt-3 border-top">
                            <div class="text-muted small">Sample</div>
                            <div class="fw-bold">${job.sample_id}</div>
                        </div>
                        ` : ''}
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function renderJobsTable() {
    const tableBody = document.getElementById('jobsTable');
    const startIndex = 0;
    const endIndex = Math.min(20, filteredJobs.length); // Show first 20 jobs
    const jobsToShow = filteredJobs.slice(startIndex, endIndex);
    
    if (jobsToShow.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="8" class="text-center py-lg">
                    <i class="bi bi-inbox text-muted" style="font-size: 2rem;"></i>
                    <p class="mt-sm text-muted">No jobs found</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = jobsToShow.map(job => {
        const statusInfo = jobStatuses[job.status] || jobStatuses.pending;
        const agentInfoData = agentInfo[job.agent] || { name: job.agent, icon: 'bi-robot', color: 'var(--color-primary)' };
        const progress = job.progress || 0;
        
        return `
            <tr>
                <td>
                    <input type="checkbox" class="c-checkbox" 
                           onchange="toggleJobSelection('${job.id}')">
                </td>
                <td>
                    <strong>${job.name || job.id || 'Unknown'}</strong>
                    <div class="text-muted small">${job.id}</div>
                </td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="job-agent-avatar" style="background: ${agentInfoData.color}; width: 24px; height: 24px; font-size: 0.7rem;">
                            <i class="bi ${agentInfoData.icon}"></i>
                        </div>
                        <span class="small">${agentInfoData.name}</span>
                    </div>
                </td>
                <td><span class="c-badge ${statusInfo.badge}">${statusInfo.name}</span></td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress" style="height: 8px; width: 60px; margin-right: 8px;">
                            <div class="progress-bar bg-primary" 
                                 style="width: ${progress}%" 
                                 role="progressbar" 
                                 aria-valuenow="${progress}" aria-valuemin="0" aria-valuemax="100">
                            </div>
                        </div>
                        <span class="small">${progress}%</span>
                    </div>
                </td>
                <td><small>${formatDuration(job.duration)}</small></td>
                <td><small>${formatDate(job.created_at)}</small></td>
                <td>
                    <button class="c-button c-button--outline-primary c-button--sm" 
                            onclick="showJobDetails('${job.id}')" 
                            data-bs-toggle="tooltip" title="View Details">
                        <i class="bi bi-eye c-button__icon"></i>
                    </button>
                    ${job.status === 'failed' ? `
                    <button class="c-button c-button--outline-success c-button--sm" 
                            onclick="retryJob('${job.id}')" 
                            data-bs-toggle="tooltip" title="Retry">
                        <i class="bi bi-arrow-clockwise c-button__icon"></i>
                    </button>
                    ` : ''}
                    ${job.status === 'running' || job.status === 'pending' ? `
                    <button class="c-button c-button--outline-danger c-button--sm" 
                            onclick="cancelJob('${job.id}')" 
                            data-bs-toggle="tooltip" title="Cancel">
                        <i class="bi bi-stop c-button__icon"></i>
                    </button>
                    ` : ''}
                    <button class="c-button c-button--outline-secondary c-button--sm" 
                            onclick="viewJobReport('${job.id}')" 
                            data-bs-toggle="tooltip" title="View Report">
                        <i class="bi bi-file-earmark-text c-button__icon"></i>
                    </button>
                </td>
            </tr>
        `;
    }).join('');
    
    // Initialize tooltips
    initTooltips();
}

function updateJobsCount() {
    const total = filteredJobs.length;
    document.getElementById('jobsCount').textContent = `${total} jobs`;
}

function initTooltips() {
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function showJobDetails(jobId) {
    const job = allJobs.find(j => j.id === jobId);
    
    if (!job) {
        showError('Job not found');
        return;
    }
    
    currentJob = job;
    
    // Update job information
    document.getElementById('detailJobId').textContent = job.id || 'N/A';
    document.getElementById('detailJobName').textContent = job.name || 'N/A';
    document.getElementById('detailJobStatus').innerHTML = getStatusBadge(job.status);
    document.getElementById('detailJobProgress').textContent = (job.progress || 0) + '%';
    document.getElementById('detailJobAgent').textContent = agentInfo[job.agent] ? agentInfo[job.agent].name : job.agent;
    document.getElementById('detailAnalysisType').textContent = job.analysis_type || 'N/A';
    document.getElementById('detailJobSample').textContent = job.sample_id || 'N/A';
    document.getElementById('detailJobCreated').textContent = formatDate(job.created_at);
    document.getElementById('detailJobCompleted').textContent = formatDate(job.completed_at);
    document.getElementById('detailJobDuration').textContent = formatDuration(job.duration);
    document.getElementById('detailJobDescription').textContent = job.description || 'No description available';
    
    // Update timeline
    const timeline = document.getElementById('detailJobTimeline');
    timeline.innerHTML = getJobTimeline(job);
    
    // Update results
    const resultsContainer = document.getElementById('detailJobResults');
    resultsContainer.innerHTML = getJobResults(job);
    
    // Update logs
    const logsContainer = document.getElementById('detailJobLogs');
    logsContainer.textContent = job.logs || job.error || 'No logs available';
    
    // Update button visibility
    const retryBtn = document.getElementById('retryJobBtn');
    const cancelBtn = document.getElementById('cancelJobBtn');
    
    if (retryBtn) {
        retryBtn.style.display = (job.status === 'failed' || job.status === 'cancelled') ? 'inline-flex' : 'none';
    }
    
    if (cancelBtn) {
        cancelBtn.style.display = (job.status === 'running' || job.status === 'pending') ? 'inline-flex' : 'none';
    }
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('jobDetailsModal'));
    modal.show();
}

function getStatusBadge(status) {
    const statusInfo = jobStatuses[status] || jobStatuses.pending;
    return `<span class="c-badge ${statusInfo.badge}">${statusInfo.name}</span>`;
}

function getJobTimeline(job) {
    const statusInfo = jobStatuses[job.status] || jobStatuses.pending;
    const createdDate = new Date(job.created_at || 0);
    const completedDate = new Date(job.completed_at || 0);
    
    let html = '';
    
    // Job created
    html += `
        <div class="job-timeline-item">
            <div class="d-flex align-items-center">
                <i class="bi bi-plus-circle me-2" style="color: var(--color-primary);"></i>
                <div>
                    <strong>Job Created</strong>
                    <div class="job-timeline-time">${formatDateTime(createdDate)}</div>
                </div>
            </div>
        </div>
    `;
    
    // Job started (if different from created)
    if (job.started_at && new Date(job.started_at) > createdDate) {
        const startedDate = new Date(job.started_at);
        html += `
            <div class="job-timeline-item">
                <div class="d-flex align-items-center">
                    <i class="bi bi-play-circle me-2" style="color: var(--color-info);"></i>
                    <div>
                        <strong>Job Started</strong>
                        <div class="job-timeline-time">${formatDateTime(startedDate)}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Job completed or failed
    if (job.status === 'completed' || job.status === 'failed' || job.status === 'cancelled') {
        const endDate = job.completed_at ? new Date(job.completed_at) : completedDate;
        const statusIcon = job.status === 'completed' ? 'bi-check-circle' : 
                         job.status === 'failed' ? 'bi-exclamation-circle' : 'bi-stop-circle';
        const statusColor = job.status === 'completed' ? 'var(--color-success)' : 
                           job.status === 'failed' ? 'var(--color-danger)' : 'var(--color-secondary)';
        const statusText = job.status === 'completed' ? 'Job Completed' : 
                          job.status === 'failed' ? 'Job Failed' : 'Job Cancelled';
        
        html += `
            <div class="job-timeline-item">
                <div class="d-flex align-items-center">
                    <i class="bi ${statusIcon} me-2" style="color: ${statusColor};"></i>
                    <div>
                        <strong>${statusText}</strong>
                        <div class="job-timeline-time">${formatDateTime(endDate)}</div>
                    </div>
                </div>
            </div>
        `;
    }
    
    return html;
}

function getJobResults(job) {
    if (!job.is_crewai || !job.crewai_data) {
        return '<p class="text-muted small">No results available</p>';
    }
    
    const crewaiData = job.crewai_data;
    let html = '';
    
    // Overall quality score
    if (crewaiData.overall_quality_score) {
        html += `
            <div class="row g-3 mb-4">
                <div class="col-md-6">
                    <div class="c-stat-card h-100">
                        <div class="c-stat-card__icon c-stat-card__icon--primary">
                            <i class="bi bi-star"></i>
                        </div>
                        <div class="c-stat-card__number">${crewaiData.overall_quality_score.toFixed(2)}</div>
                        <div class="c-stat-card__label">Overall Quality Score</div>
                    </div>
                </div>
        `;
    }
    
    // Spectral analysis results
    if (crewaiData.spectral_analysis) {
        const sa = crewaiData.spectral_analysis;
        html += `
                <div class="col-md-6">
                    <div class="c-stat-card h-100">
                        <div class="c-stat-card__icon c-stat-card__icon--success">
                            <i class="bi bi-graph-up"></i>
                        </div>
                        <div class="c-stat-card__number">${sa.quality_score.toFixed(2)}</div>
                        <div class="c-stat-card__label">Spectral Quality</div>
                    </div>
                </div>
            </div>
            
            <div class="c-card mb-3">
                <div class="c-card__header">
                    <h6 class="mb-0">Spectral Analysis Results</h6>
                </div>
                <div class="c-card__body">
                    <div class="table-responsive">
                        <table class="c-table c-table--bordered c-table--sm">
                            <tr><th>Quality Score:</th><td>${sa.quality_score.toFixed(2)}</td></tr>
                            <tr><th>Quality Grade:</th><td>${sa.quality_grade}</td></tr>
                            <tr><th>Wavelength Range:</th><td>${sa.wavelength_range[0]} - ${sa.wavelength_range[1]} nm</td></tr>
                            <tr><th>Data Points:</th><td>${sa.data_points}</td></tr>
                            <tr><th>Noise Level:</th><td>${sa.noise_level.toFixed(4)}</td></tr>
                            <tr><th>Signal to Noise Ratio:</th><td>${sa.signal_to_noise_ratio.toFixed(2)}</td></tr>
                            <tr><th>Shift Detected:</th><td>${sa.shift_detected ? 'Yes' : 'No'}</td></tr>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Metadata quality results
    if (crewaiData.metadata_quality) {
        const mq = crewaiData.metadata_quality;
        html += `
            <div class="c-card mb-3">
                <div class="c-card__header">
                    <h6 class="mb-0">Metadata Quality Results</h6>
                </div>
                <div class="c-card__body">
                    <div class="table-responsive">
                        <table class="c-table c-table--bordered c-table--sm">
                            <tr><th>Overall Score:</th><td>${mq.overall_quality_score.toFixed(2)}</td></tr>
                            <tr><th>Quality Grade:</th><td>${mq.overall_quality_grade}</td></tr>
                            <tr><th>Completeness Score:</th><td>${mq.completeness_score.toFixed(2)}</td></tr>
                            <tr><th>Accuracy Score:</th><td>${mq.accuracy_score.toFixed(2)}</td></tr>
                            <tr><th>Consistency Score:</th><td>${mq.consistency_score.toFixed(2)}</td></tr>
                        </table>
                    </div>
                </div>
            </div>
        `;
    }
    
    // Summary
    if (crewaiData.summary) {
        html += `
            <div class="c-card">
                <div class="c-card__header">
                    <h6 class="mb-0">Summary</h6>
                </div>
                <div class="c-card__body">
                    <p>${crewaiData.summary}</p>
                </div>
            </div>
        `;
    }
    
    return html || '<p class="text-muted small">No results available</p>';
}

function createNewJob() {
    // Load spectra for selection
    updateSpectraSelection();
    
    // Set default values
    document.getElementById('jobName').value = 'Analysis Job ' + new Date().toLocaleTimeString();
    document.getElementById('jobDescription').value = '';
    document.getElementById('jobAnalysisType').value = 'spectral_analysis';
    document.getElementById('jobAgent').value = 'SpectralAnalysisAgent';
    document.getElementById('jobPriority').value = 'normal';
    document.getElementById('jobNotifyOnComplete').checked = true;
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('createJobModal'));
    modal.show();
}

function createJob() {
    const jobName = document.getElementById('jobName').value;
    const analysisType = document.getElementById('jobAnalysisType').value;
    const agent = document.getElementById('jobAgent').value;
    const priority = document.getElementById('jobPriority').value;
    const description = document.getElementById('jobDescription').value;
    const notifyOnComplete = document.getElementById('jobNotifyOnComplete').checked;
    
    if (!jobName || !analysisType || !agent) {
        showError('Please fill in all required fields');
        return;
    }
    
    // Get selected spectra
    const selectedSpectra = [];
    const spectrumCheckboxes = document.querySelectorAll('input[name="spectrum_ids"]:checked');
    spectrumCheckboxes.forEach(checkbox => {
        selectedSpectra.push(checkbox.value);
    });
    
    if (selectedSpectra.length === 0) {
        showError('Please select at least one spectrum');
        return;
    }
    
    showLoading();
    
    // For Crew AI agents, use the Crew AI API
    if (agent.startsWith('CrewAI') || Object.keys(agentInfo).includes(agent)) {
        // Create a job for each selected spectrum
        const jobPromises = selectedSpectra.map(spectrumId => {
            const spectrum = availableSpectra.find(s => s.id === spectrumId);
            
            if (!spectrum) return Promise.resolve();
            
            const crewaiRequest = {
                sample_id: spectrum.sample_id || spectrum.id,
                analysis_mode: priority === 'high' ? 'comprehensive' : 'standard',
                privacy_level: 'local_only',
                report_type: analysisType,
                report_format: 'html',
                include_calibration: true,
                include_federated_learning: false,
                metadata: {
                    job_name: jobName,
                    job_id: 'job_' + Date.now(),
                    description: description,
                    agent: agent,
                    priority: priority,
                    notify_on_complete: notifyOnComplete,
                    spectrum_ids: selectedSpectra
                },
                spectral_data: {
                    wavelengths: spectrum.wavelengths || generateSampleWavelengths(),
                    intensities: spectrum.intensities || generateSampleIntensities(),
                    sample_id: spectrum.sample_id || spectrum.id
                }
            };
            
            return axios.post('/api/crewai/analysis/start/', crewaiRequest);
        });
        
        Promise.all(jobPromises)
            .then(responses => {
                hideLoading();
                
                const successful = responses.filter(r => r && r.data && r.data.success).length;
                
                if (successful > 0) {
                    showSuccess(`${successful} job/jobs created successfully!`);
                    
                    // Close modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('createJobModal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Refresh jobs list
                    loadJobs();
                }
            })
            .catch(error => {
                console.error('Error creating jobs:', error);
                hideLoading();
                showError('Failed to create jobs. Please try again.');
            });
    } else {
        // For non-Crew AI agents, use the regular API
        const jobData = {
            name: jobName,
            analysis_type: analysisType,
            agent: agent,
            priority: priority,
            description: description,
            notify_on_complete: notifyOnComplete,
            spectrum_ids: selectedSpectra
        };
        
        axios.post('/api/jobs/', jobData)
            .then(response => {
                hideLoading();
                
                if (response.data && response.data.id) {
                    showSuccess('Job created successfully!');
                    
                    // Close modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('createJobModal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Refresh jobs list
                    loadJobs();
                } else {
                    showError('Failed to create job: ' + (response.data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error creating job:', error);
                hideLoading();
                showError('Failed to create job. Please try again.');
            });
    }
}

function retryJob(jobId) {
    if (!jobId && currentJob) {
        jobId = currentJob.id;
    }
    
    const job = allJobs.find(j => j.id === jobId);
    
    if (!job) {
        showError('Job not found');
        return;
    }
    
    showLoading();
    
    // For Crew AI jobs, retry using Crew AI API
    if (job.is_crewai) {
        const crewaiRequest = {
            sample_id: job.sample_id || job.id,
            analysis_mode: 'standard',
            privacy_level: 'local_only',
            report_type: job.analysis_type || 'spectral_analysis',
            report_format: 'html',
            include_calibration: true,
            include_federated_learning: false,
            metadata: {
                job_name: job.name || job.id,
                job_id: job.id,
                retry: true,
                original_job_id: job.id
            },
            spectral_data: {
                // This would be populated with actual spectral data
                wavelengths: generateSampleWavelengths(),
                intensities: generateSampleIntensities(),
                sample_id: job.sample_id || job.id
            }
        };
        
        axios.post('/api/crewai/analysis/start/', crewaiRequest)
            .then(response => {
                hideLoading();
                
                if (response.data && response.data.success) {
                    showSuccess('Job retry started successfully!');
                    
                    // Close modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('jobDetailsModal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Refresh jobs list
                    loadJobs();
                } else {
                    showError('Failed to retry job: ' + (response.data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error retrying job:', error);
                hideLoading();
                showError('Failed to retry job. Please try again.');
            });
    } else {
        // For regular jobs
        axios.post('/api/jobs/' + jobId + '/retry/')
            .then(response => {
                hideLoading();
                
                if (response.data && response.data.success) {
                    showSuccess('Job retry started successfully!');
                    
                    // Close modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('jobDetailsModal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Refresh jobs list
                    loadJobs();
                } else {
                    showError('Failed to retry job: ' + (response.data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error retrying job:', error);
                hideLoading();
                showError('Failed to retry job. Please try again.');
            });
    }
}

function cancelJob(jobId) {
    if (!jobId && currentJob) {
        jobId = currentJob.id;
    }
    
    const job = allJobs.find(j => j.id === jobId);
    
    if (!job) {
        showError('Job not found');
        return;
    }
    
    if (job.status !== 'running' && job.status !== 'pending') {
        showError('Only running or pending jobs can be cancelled');
        return;
    }
    
    showLoading();
    
    // For Crew AI jobs
    if (job.is_crewai) {
        // Note: Crew AI doesn't have a direct cancel endpoint, 
        // but we can mark it as cancelled in our system
        axios.post('/api/crewai/cleanup/', {
            max_age_days: 0,
            job_id: jobId
        })
            .then(response => {
                hideLoading();
                
                if (response.data && response.data.success) {
                    showSuccess('Job cancellation requested!');
                    
                    // Update job status locally
                    job.status = 'cancelled';
                    
                    // Close modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('jobDetailsModal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Refresh jobs list
                    loadJobs();
                } else {
                    showError('Failed to cancel job: ' + (response.data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error cancelling job:', error);
                hideLoading();
                showError('Failed to cancel job. Please try again.');
            });
    } else {
        // For regular jobs
        axios.post('/api/jobs/' + jobId + '/cancel/')
            .then(response => {
                hideLoading();
                
                if (response.data && response.data.success) {
                    showSuccess('Job cancellation requested!');
                    
                    // Update job status locally
                    job.status = 'cancelled';
                    
                    // Close modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('jobDetailsModal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Refresh jobs list
                    loadJobs();
                } else {
                    showError('Failed to cancel job: ' + (response.data.error || 'Unknown error'));
                }
            })
            .catch(error => {
                console.error('Error cancelling job:', error);
                hideLoading();
                showError('Failed to cancel job. Please try again.');
            });
    }
}

function viewJobReport(jobId) {
    if (!jobId && currentJob) {
        jobId = currentJob.id;
    }
    
    const job = allJobs.find(j => j.id === jobId);
    
    if (!job) {
        showError('Job not found');
        return;
    }
    
    if (job.is_crewai && job.crewai_data) {
        // For Crew AI jobs, use the report preview endpoint
        window.open('/api/crewai/reports/preview/?report_id=' + job.id, '_blank');
    } else {
        // For regular jobs
        window.open('/api/jobs/' + jobId + '/report/', '_blank');
    }
}

function refreshJobs() {
    loadJobs();
}

function refreshActiveJobs() {
    // Refresh only active jobs
    axios.get('/api/jobs/?status=running,pending')
        .then(response => {
            const activeJobs = response.data.results || [];
            
            // Update active jobs in the allJobs array
            activeJobs.forEach(activeJob => {
                const existingIndex = allJobs.findIndex(j => j.id === activeJob.id);
                if (existingIndex !== -1) {
                    allJobs[existingIndex] = activeJob;
                }
            });
            
            // Re-filter and re-render
            filterByStatus(currentStatusFilter);
        })
        .catch(error => {
            console.error('Error refreshing active jobs:', error);
        });
}

function toggleJobSelection(jobId) {
    const index = selectedJobs.indexOf(jobId);
    
    if (index === -1) {
        selectedJobs.push(jobId);
    } else {
        selectedJobs.splice(index, 1);
    }
}

function deleteSelectedJobs() {
    if (selectedJobs.length === 0) {
        showError('Please select at least one job to delete');
        return;
    }
    
    const count = selectedJobs.length;
    document.getElementById('jobsDeleteMessage').textContent = 
        `Are you sure you want to delete ${count} selected job/jobs? This action cannot be undone.`;
    
    const modal = new bootstrap.Modal(document.getElementById('jobsDeleteConfirmationModal'));
    modal.show();
}

function deleteSpectrum(spectrumId) {
    currentSpectrum = allSpectra.find(s => s.id === spectrumId);
    
    if (!currentSpectrum) {
        showError('Spectrum not found');
        return;
    }
    
    document.getElementById('jobsDeleteMessage').textContent = 
        `Are you sure you want to delete the spectrum "${currentSpectrum.name || currentSpectrum.sample_id}"? This action cannot be undone.`;
    
    const modal = new bootstrap.Modal(document.getElementById('jobsDeleteConfirmationModal'));
    modal.show();
}

function confirmDelete() {
    if (selectedJobs.length > 0) {
        // Delete selected jobs
        showLoading();
        
        const deletePromises = selectedJobs.map(jobId => {
            const job = allJobs.find(j => j.id === jobId);
            
            if (job && job.is_crewai) {
                // For Crew AI jobs, use cleanup endpoint
                return axios.post('/api/crewai/cleanup/', {
                    max_age_days: 0,
                    job_id: jobId
                });
            } else {
                // For regular jobs
                return axios.delete('/api/jobs/' + jobId + '/');
            }
        });
        
        Promise.all(deletePromises)
            .then(responses => {
                hideLoading();
                
                const successful = responses.filter(r => r.status === 200 || r.status === 204).length;
                
                if (successful > 0) {
                    showSuccess(`${successful} job/jobs deleted successfully!`);
                    
                    // Close modal
                    const deleteModal = bootstrap.Modal.getInstance(document.getElementById('jobsDeleteConfirmationModal'));
                    if (deleteModal) {
                        deleteModal.hide();
                    }
                    
                    // Clear selection
                    selectedJobs = [];
                    
                    // Refresh jobs list
                    loadJobs();
                }
            })
            .catch(error => {
                console.error('Error deleting jobs:', error);
                hideLoading();
                showError('Failed to delete jobs. Please try again.');
            });
    } else {
        showError('No jobs selected for deletion');
    }
}

function exportJobsList() {
    const data = filteredJobs.map(job => ({
        id: job.id,
        name: job.name || '',
        analysis_type: job.analysis_type || '',
        agent: job.agent || '',
        status: job.status || '',
        progress: job.progress || 0,
        duration: job.duration || 0,
        created: formatDate(job.created_at),
        completed: formatDate(job.completed_at),
        sample_id: job.sample_id || '',
        description: job.description || ''
    }));
    
    const csv = convertToCSV(data);
    downloadCSV(csv, 'jobs_' + new Date().toISOString().split('T')[0] + '.csv');
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

function formatDateTime(date) {
    if (!date || isNaN(date.getTime())) return 'N/A';
    
    return date.toLocaleDateString() + ' ' + date.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

function formatDuration(seconds) {
    if (!seconds && seconds !== 0) return 'N/A';
    
    if (seconds < 60) {
        return seconds.toFixed(1) + 's';
    } else if (seconds < 3600) {
        const minutes = Math.floor(seconds / 60);
        const secs = (seconds % 60).toFixed(1);
        return minutes + 'm ' + secs + 's';
    } else {
        const hours = Math.floor(seconds / 3600);
        const minutes = Math.floor((seconds % 3600) / 60);
        return hours + 'h ' + minutes + 'm';
    }
}