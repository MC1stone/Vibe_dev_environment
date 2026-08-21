// NIR_Mistral Framework - Analysis Page JavaScript
// Crew AI Integration for Spectral Analysis

// Global variables
let analysisJobs = [];
let analysisHistory = [];
let availableSpectra = [];
let availableAgents = [];
let analysisChart = null;
let currentAnalysisRequest = null;
let fileUploadData = null;

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    loadCrewAIStatus();
    loadAnalysisData();
    loadSpectraForAnalysis();
    loadAgentsForAnalysis();
    setupEventListeners();
    
    // Set up real-time updates
    setInterval(refreshActiveJobs, 10000);
    setInterval(loadCrewAIStatus, 30000);
});

function setupEventListeners() {
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
                handleFileUpload({ target: { files: e.dataTransfer.files } });
            }
        });
    }
}

function loadCrewAIStatus() {
    // Check if required elements exist
    const crewaiStatusEl = getElementSafely('crewaiStatus');
    const agentsAvailableEl = getElementSafely('agentsAvailable');
    const totalAnalysesEl = getElementSafely('totalAnalyses');
    const avgProcessingTimeEl = getElementSafely('avgProcessingTime');
    
    if (!crewaiStatusEl) return;
    
    axios.get('/api/crewai/status/')
        .then(function(response) {
            const status = response.data;
            
            // Update status indicators
            const statusText = status.available ? 'Ready' : 'Not Available';
            const statusColor = status.available ? 'var(--color-success)' : 'var(--color-danger)';
            crewaiStatusEl.textContent = statusText;
            crewaiStatusEl.style.color = statusColor;
            
            // Update agents available
            if (agentsAvailableEl) {
                const agents = status.agents || {};
                const agentCount = Object.values(agents).filter(a => a === true).length;
                agentsAvailableEl.textContent = agentCount + ' available';
            }
            
            // Update total analyses
            if (totalAnalysesEl) {
                totalAnalysesEl.textContent = (status.analysis_history_count || 0) + ' total';
            }
            
            // Update average processing time (placeholder)
            if (avgProcessingTimeEl) {
                avgProcessingTimeEl.textContent = '~2.5s';
            }
        })
        .catch(function(error) {
            // If service is unavailable, show as not available
            if (crewaiStatusEl) {
                crewaiStatusEl.textContent = 'Not Available';
                crewaiStatusEl.style.color = 'var(--color-warning)';
            }
            console.debug('Crew AI status check failed:', error.message);
        });
}

function loadAnalysisData() {
    showLoading();
    
    // Load active jobs
    axios.get('/api/crewai/analysis/history/?limit=10')
        .then(function(response) {
            const history = response.data.history || [];
            analysisJobs = history.filter(h => h.status === 'running' || h.status === 'pending' || h.status === 'processing');
            analysisHistory = history.filter(h => h.status === 'completed' || h.status === 'failed' || h.status === 'cancelled');
            
            updateActiveJobs();
            updateActiveJobsCount();
            renderRecentResults();
            hideLoading();
        })
        .catch(function(error) {
            console.error('Error loading analysis data:', error);
            hideLoading();
        });
}

function loadSpectraForAnalysis() {
    axios.get('/api/spectra/')
        .then(function(response) {
            availableSpectra = response.data.results || [];
        })
        .catch(function(error) {
            console.error('Error loading spectra:', error);
        });
}

function loadAgentsForAnalysis() {
    axios.get('/api/agents/')
        .then(function(response) {
            availableAgents = response.data.results || [];
        })
        .catch(function(error) {
            console.error('Error loading agents:', error);
        });
}

function selectAnalysisMethod(method) {
    document.getElementById('analysisType').value = method;
    updateAnalysisOptions();
    const modal = new bootstrap.Modal(document.getElementById('newAnalysisModal'));
    modal.show();
}

function updateAnalysisOptions() {
    const analysisType = document.getElementById('analysisType').value;
    const container = document.getElementById('analysisOptionsContainer');
    container.innerHTML = '';
    
    if (analysisType === 'spectral_analysis') {
        container.innerHTML = `
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="c-form-label">Wavelength Range (nm)</label>
                    <div class="d-flex gap-2">
                        <input type="number" class="c-form-control" id="wavelengthMin" placeholder="Min" value="700">
                        <span style="align-self: center;">-</span>
                        <input type="number" class="c-form-control" id="wavelengthMax" placeholder="Max" value="2500">
                    </div>
                </div>
                <div class="col-md-6">
                    <label class="c-form-label">Noise Threshold</label>
                    <input type="number" class="c-form-control" id="noiseThreshold" value="0.1" step="0.01">
                </div>
            </div>
        `;
    } else if (analysisType === 'metadata_quality') {
        container.innerHTML = `
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="c-form-label">Completeness Threshold (%)</label>
                    <input type="number" class="c-form-control" id="completenessThreshold" value="80" min="0" max="100">
                </div>
                <div class="col-md-6">
                    <label class="c-form-label">Accuracy Threshold (%)</label>
                    <input type="number" class="c-form-control" id="accuracyThreshold" value="90" min="0" max="100">
                </div>
            </div>
        `;
    } else if (analysisType === 'calibration') {
        container.innerHTML = `
            <div class="row g-3">
                <div class="col-md-6">
                    <label class="c-form-label">Calibration Type</label>
                    <select class="c-form-control" id="calibrationType">
                        <option value="wavelength">Wavelength Calibration</option>
                        <option value="intensity">Intensity Calibration</option>
                        <option value="full">Full System Calibration</option>
                    </select>
                </div>
                <div class="col-md-6">
                    <label class="c-form-label">Reference Standard</label>
                    <select class="c-form-control" id="referenceStandard">
                        <option value="polystyrene">Polystyrene</option>
                        <option value="cerium_oxide">Cerium Oxide</option>
                        <option value="custom">Custom Reference</option>
                    </select>
                </div>
            </div>
        `;
    }
}

function startAnalysis() {
    const analysisName = document.getElementById('analysisName').value;
    const sampleId = document.getElementById('sampleId').value;
    const analysisType = document.getElementById('analysisType').value;
    const analysisMode = document.getElementById('analysisMode').value;
    const privacyLevel = document.getElementById('privacyLevel').value;
    const reportFormat = document.getElementById('reportFormat').value;
    const description = document.getElementById('analysisDescription').value;
    
    if (!analysisName || !sampleId || !analysisType) {
        showError('Please fill in all required fields.');
        return;
    }
    
    showLoading();
    
    // Prepare the analysis request for Crew AI
    const analysisRequest = {
        sample_id: sampleId,
        analysis_mode: analysisMode,
        privacy_level: privacyLevel,
        report_type: analysisType,
        report_format: reportFormat,
        include_calibration: true,
        include_federated_learning: false,
        metadata: {
            analysis_name: analysisName,
            description: description,
            user_id: 'current_user' // This would be replaced with actual user ID
        }
    };
    
    // If we have spectral data from file upload, include it
    if (fileUploadData) {
        analysisRequest.spectral_data = fileUploadData;
    } else {
        // For demo purposes, create some sample spectral data
        analysisRequest.spectral_data = generateSampleSpectralData();
    }
    
    currentAnalysisRequest = analysisRequest;
    
    // Send to Crew AI API
    axios.post('/api/crewai/analysis/start/', analysisRequest)
        .then(function(response) {
            hideLoading();
            const result = response.data;
            
            if (result.success) {
                showSuccess('Analysis started successfully!');
                document.getElementById('newAnalysisForm').reset();
                bootstrap.Modal.getInstance(document.getElementById('newAnalysisModal')).hide();
                
                // Store the request ID for tracking
                currentAnalysisRequest.request_id = result.request_id;
                
                // Refresh data and show results
                loadAnalysisData();
                
                // Show results after a short delay to allow processing
                setTimeout(() => {
                    viewAnalysisResults(result.request_id);
                }, 2000);
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

function startQuickAnalysis() {
    const analysisType = document.getElementById('quickAnalysisType').value;
    
    showLoading();
    
    // Prepare quick analysis request
    const quickRequest = {
        sample_id: 'quick_sample_' + Date.now(),
        analysis_mode: 'standard',
        privacy_level: 'local_only',
        report_type: analysisType,
        report_format: 'html',
        include_calibration: true,
        include_federated_learning: false,
        metadata: {
            analysis_name: 'Quick Analysis - ' + new Date().toLocaleTimeString(),
            description: 'Quick analysis performed via dashboard'
        },
        spectral_data: generateSampleSpectralData() // Generate sample data for demo
    };
    
    axios.post('/api/crewai/analysis/start/', quickRequest)
        .then(function(response) {
            hideLoading();
            const result = response.data;
            
            if (result.success) {
                showSuccess('Quick analysis started!');
                loadAnalysisData();
                
                // Show results after processing
                setTimeout(() => {
                    viewAnalysisResults(result.request_id);
                }, 2000);
            } else {
                showError('Failed to start quick analysis: ' + (result.error || 'Unknown error'));
            }
        })
        .catch(function(error) {
            console.error('Error starting quick analysis:', error);
            hideLoading();
            showError('Failed to start quick analysis. Please try again.');
        });
}

function generateSampleSpectralData() {
    // Generate sample spectral data for demonstration
    const wavelengths = [];
    const intensities = [];
    
    // Generate wavelengths from 700 to 2500 nm
    for (let i = 700; i <= 2500; i += 10) {
        wavelengths.push(i);
        // Generate some sample intensity values with peaks
        let intensity = Math.random() * 0.5 + 0.3;
        if (i >= 1200 && i <= 1400) intensity += 0.8; // Peak around 1300 nm
        if (i >= 1700 && i <= 1900) intensity += 0.6; // Peak around 1800 nm
        intensities.push(intensity);
    }
    
    return {
        wavelengths: wavelengths,
        intensities: intensities,
        sample_id: 'sample_' + Date.now()
    };
}

function handleFileUpload(event) {
    const files = event.target.files;
    if (files.length === 0) return;
    
    const file = files[0];
    
    // Read the file content
    const reader = new FileReader();
    reader.onload = function(e) {
        try {
            const content = e.target.result;
            fileUploadData = parseSpectrumFile(content, file.name);
            showSuccess('File uploaded: ' + file.name);
        } catch (error) {
            console.error('Error parsing spectrum file:', error);
            showError('Failed to parse spectrum file. Please check the format.');
        }
    };
    
    if (file.name.endsWith('.json')) {
        reader.readAsText(file);
    } else if (file.name.endsWith('.csv') || file.name.endsWith('.txt')) {
        reader.readAsText(file);
    } else {
        showError('Unsupported file format. Please upload .json, .csv, or .txt files.');
    }
}

function parseSpectrumFile(content, fileName) {
    // Simple parser for different spectrum file formats
    if (fileName.endsWith('.json')) {
        const data = JSON.parse(content);
        return {
            wavelengths: data.wavelengths || [],
            intensities: data.intensities || data.values || [],
            sample_id: data.sample_id || fileName.replace('.json', '')
        };
    } else {
        // CSV format: assuming first column is wavelength, second is intensity
        const lines = content.split('\n');
        const wavelengths = [];
        const intensities = [];
        
        for (let i = 0; i < lines.length; i++) {
            const line = lines[i].trim();
            if (line === '') continue;
            
            const parts = line.split(',').map(p => parseFloat(p.trim()));
            if (parts.length >= 2 && !isNaN(parts[0]) && !isNaN(parts[1])) {
                wavelengths.push(parts[0]);
                intensities.push(parts[1]);
            }
        }
        
        return {
            wavelengths: wavelengths,
            intensities: intensities,
            sample_id: fileName.replace('.csv', '').replace('.txt', '')
        };
    }
}

function viewAnalysisResults(requestId) {
    showLoading();
    
    axios.get('/api/crewai/analysis/status/?request_id=' + requestId)
        .then(function(response) {
            const result = response.data;
            
            if (result.found) {
                displayAnalysisResults(result);
            } else {
                // If not found in status, try to get it from history
                axios.get('/api/crewai/analysis/history/?limit=50')
                    .then(function(historyResponse) {
                        const history = historyResponse.data.history || [];
                        const foundResult = history.find(h => h.request_id === requestId);
                        
                        if (foundResult) {
                            displayAnalysisResults(foundResult);
                        } else {
                            hideLoading();
                            showError('Analysis results not found.');
                        }
                    })
                    .catch(function(error) {
                        hideLoading();
                        showError('Failed to load analysis results.');
                    });
            }
        })
        .catch(function(error) {
            console.error('Error loading analysis results:', error);
            hideLoading();
            showError('Failed to load analysis results.');
        });
}

function displayAnalysisResults(result) {
    hideLoading();
    
    // Update basic information
    document.getElementById('resultAnalysisName').textContent = result.sample_id || 'N/A';
    document.getElementById('resultAnalysisType').textContent = result.report_type || result.analysis_type || 'Unknown';
    document.getElementById('resultSampleId').textContent = result.sample_id || 'N/A';
    document.getElementById('resultStatus').innerHTML = '<span class="c-badge c-badge--success">Completed</span>';
    document.getElementById('resultCompleted').textContent = formatDate(result.timestamp);
    document.getElementById('resultProcessingTime').textContent = (result.processing_time || 0).toFixed(2) + 's';
    
    // Update summary
    const summary = result.summary || 'No summary available';
    document.getElementById('resultSummary').innerHTML = '<p>' + summary + '</p>';
    
    // Update quality scores
    const qualityScores = document.getElementById('qualityScores');
    qualityScores.innerHTML = '';
    
    if (result.overall_quality_score) {
        qualityScores.innerHTML = `
            <div class="col-12 col-md-6">
                <div class="c-stat-card h-100">
                    <div class="c-stat-card__icon c-stat-card__icon--primary">
                        <i class="bi bi-star"></i>
                    </div>
                    <div class="c-stat-card__number">${result.overall_quality_score.toFixed(2)}</div>
                    <div class="c-stat-card__label">Overall Quality</div>
                </div>
            </div>
        `;
    }
    
    if (result.spectral_analysis) {
        qualityScores.innerHTML += `
            <div class="col-12 col-md-6">
                <div class="c-stat-card h-100">
                    <div class="c-stat-card__icon c-stat-card__icon--success">
                        <i class="bi bi-graph-up"></i>
                    </div>
                    <div class="c-stat-card__number">${result.spectral_analysis.quality_score.toFixed(2)}</div>
                    <div class="c-stat-card__label">Spectral Quality</div>
                </div>
            </div>
        `;
    }
    
    if (result.metadata_quality) {
        qualityScores.innerHTML += `
            <div class="col-12 col-md-6">
                <div class="c-stat-card h-100">
                    <div class="c-stat-card__icon c-stat-card__icon--info">
                        <i class="bi bi-check-circle"></i>
                    </div>
                    <div class="c-stat-card__number">${result.metadata_quality.overall_quality_score.toFixed(2)}</div>
                    <div class="c-stat-card__label">Metadata Quality</div>
                </div>
            </div>
        `;
    }
    
    // Update detailed results
    const resultData = document.getElementById('resultData');
    resultData.innerHTML = formatResultsData(result);
    
    // Create chart with sample data
    createAnalysisChart(result);
    
    // Show the results modal
    const modal = new bootstrap.Modal(document.getElementById('analysisResultsModal'));
    modal.show();
}

function formatResultsData(result) {
    let html = '<div class="table-responsive"><table class="c-table c-table--bordered c-table--sm">';
    
    // Add spectral analysis data
    if (result.spectral_analysis) {
        const sa = result.spectral_analysis;
        html += '<tr><th colspan="2" class="bg-light">Spectral Analysis</th></tr>';
        html += `<tr><td>Quality Score</td><td>${sa.quality_score.toFixed(2)}</td></tr>`;
        html += `<tr><td>Quality Grade</td><td>${sa.quality_grade}</td></tr>`;
        html += `<tr><td>Wavelength Range</td><td>${sa.wavelength_range[0]} - ${sa.wavelength_range[1]} nm</td></tr>`;
        html += `<tr><td>Data Points</td><td>${sa.data_points}</td></tr>`;
        html += `<tr><td>Noise Level</td><td>${sa.noise_level.toFixed(4)}</td></tr>`;
        html += `<tr><td>Signal to Noise Ratio</td><td>${sa.signal_to_noise_ratio.toFixed(2)}</td></tr>`;
        html += `<tr><td>Shift Detected</td><td>${sa.shift_detected ? 'Yes' : 'No'}</td></tr>`;
        
        if (sa.issues_detected && sa.issues_detected.length > 0) {
            html += `<tr><td>Issues Detected</td><td>${sa.issues_detected.join(', ')}</td></tr>`;
        }
        
        if (sa.recommendations && sa.recommendations.length > 0) {
            html += `<tr><td>Recommendations</td><td><ul class="mb-0">${sa.recommendations.map(r => `<li>${r}</li>`).join('')}</ul></td></tr>`;
        }
    }
    
    // Add metadata quality data
    if (result.metadata_quality) {
        const mq = result.metadata_quality;
        html += '<tr><th colspan="2" class="bg-light">Metadata Quality</th></tr>';
        html += `<tr><td>Overall Score</td><td>${mq.overall_quality_score.toFixed(2)}</td></tr>`;
        html += `<tr><td>Quality Grade</td><td>${mq.overall_quality_grade}</td></tr>`;
        html += `<tr><td>Completeness Score</td><td>${mq.completeness_score.toFixed(2)}</td></tr>`;
        html += `<tr><td>Accuracy Score</td><td>${mq.accuracy_score.toFixed(2)}</td></tr>`;
        html += `<tr><td>Consistency Score</td><td>${mq.consistency_score.toFixed(2)}</td></tr>`;
        
        if (mq.missing_required_fields && mq.missing_required_fields.length > 0) {
            html += `<tr><td>Missing Fields</td><td>${mq.missing_required_fields.join(', ')}</td></tr>`;
        }
        
        if (mq.recommendations && mq.recommendations.length > 0) {
            html += `<tr><td>Recommendations</td><td><ul class="mb-0">${mq.recommendations.map(r => `<li>${r}</li>`).join('')}</ul></td></tr>`;
        }
    }
    
    // Add recommendations and warnings
    if (result.recommendations && result.recommendations.length > 0) {
        html += '<tr><th colspan="2" class="bg-light">Recommendations</th></tr>';
        html += `<tr><td colspan="2"><ul class="mb-0">${result.recommendations.map(r => `<li>${r}</li>`).join('')}</ul></td></tr>`;
    }
    
    if (result.warnings && result.warnings.length > 0) {
        html += '<tr><th colspan="2" class="bg-light">Warnings</th></tr>';
        html += `<tr><td colspan="2"><ul class="mb-0">${result.warnings.map(w => `<li class="text-warning">${w}</li>`).join('')}</ul></td></tr>`;
    }
    
    if (result.errors && result.errors.length > 0) {
        html += '<tr><th colspan="2" class="bg-light">Errors</th></tr>';
        html += `<tr><td colspan="2"><ul class="mb-0">${result.errors.map(e => `<li class="text-danger">${e}</li>`).join('')}</ul></td></tr>`;
    }
    
    html += '</table></div>';
    return html;
}

function createAnalysisChart(result) {
    const ctx = document.getElementById('analysisChart');
    
    // Destroy existing chart if it exists
    if (analysisChart) {
        analysisChart.destroy();
    }
    
    // Generate sample spectral data for visualization
    const wavelengths = [];
    const intensities = [];
    
    for (let i = 700; i <= 2500; i += 10) {
        wavelengths.push(i);
        let intensity = Math.random() * 0.5 + 0.3;
        if (i >= 1200 && i <= 1400) intensity += 0.8;
        if (i >= 1700 && i <= 1900) intensity += 0.6;
        intensities.push(intensity);
    }
    
    analysisChart = new Chart(ctx, {
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
}

function viewReport() {
    if (!currentAnalysisRequest || !currentAnalysisRequest.request_id) {
        showError('No analysis results available to view report.');
        return;
    }
    
    // Open the report in a new tab
    window.open('/api/crewai/reports/preview/?report_id=' + currentAnalysisRequest.request_id, '_blank');
}

function exportAnalysisResults() {
    if (!currentAnalysisRequest || !currentAnalysisRequest.request_id) {
        showError('No analysis results available to export.');
        return;
    }
    
    showLoading();
    
    // This would trigger a download of the analysis results
    axios.get('/api/crewai/reports/list/?limit=1&request_id=' + currentAnalysisRequest.request_id)
        .then(function(response) {
            hideLoading();
            const reports = response.data.reports;
            
            if (reports && reports.length > 0) {
                const report = reports[0];
                // In a real implementation, this would trigger a file download
                showSuccess('Export functionality would download: ' + report.report_id);
            } else {
                showError('No reports available for export.');
            }
        })
        .catch(function(error) {
            hideLoading();
            showError('Failed to export analysis results.');
        });
}

function updateActiveJobs() {
    const tableBody = document.getElementById('activeJobsTableBody');
    
    if (analysisJobs.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-lg">
                    <i class="bi bi-inbox text-muted" style="font-size: 2rem;"></i>
                    <p class="mt-sm text-muted">No active jobs</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = analysisJobs.map(job => `
        <tr>
            <td>${job.request_id || job.id || 'N/A'}</td>
            <td>${job.report_type || job.analysis_type || 'Unknown'}</td>
            <td>${job.sample_id || 'N/A'}</td>
            <td><span class="c-badge c-badge--${getStatusBadge(job.status)}">${job.status || 'unknown'}</span></td>
            <td>
                <div class="progress-container">
                    <div class="progress-bar progress-bar-striped progress-bar-animated" 
                         style="width: ${job.progress || 0}%; background: var(--color-primary);"></div>
                </div>
            </td>
            <td>${formatDate(job.timestamp || job.created_at)}</td>
            <td>
                <button class="c-button c-button--outline-primary c-button--sm" onclick="viewAnalysisResults('${job.request_id || job.id}')">
                    <i class="bi bi-eye c-button__icon"></i>
                </button>
            </td>
        </tr>
    `).join('');
}

function updateActiveJobsCount() {
    document.getElementById('activeJobsCount').textContent = analysisJobs.length;
}

function renderRecentResults() {
    const grid = document.getElementById('recentResultsGrid');
    
    if (analysisHistory.length === 0) {
        grid.innerHTML = `
            <div class="col-12">
                <div class="c-card text-center py-lg">
                    <i class="bi bi-inbox text-muted" style="font-size: 3rem;"></i>
                    <p class="mt-sm text-muted">No recent analysis results found</p>
                </div>
            </div>
        `;
        return;
    }
    
    // Show the 6 most recent results
    const recentResults = analysisHistory.slice(0, 6);
    
    grid.innerHTML = recentResults.map(result => `
        <div class="col-md-4 col-12">
            <div class="c-card h-100">
                <div class="c-card__header">
                    <h6 class="mb-0">${result.sample_id || 'Unknown'}</h6>
                </div>
                <div class="c-card__body">
                    <div class="d-flex justify-content-between align-items-center mb-3">
                        <span class="c-badge c-badge--${getStatusBadge(result.status || 'completed')}">
                            ${result.status || 'completed'}
                        </span>
                        <small class="text-muted">${formatDate(result.timestamp)}</small>
                    </div>
                    
                    <div class="mb-3">
                        <div class="d-flex justify-content-between mb-2">
                            <span>Analysis Type:</span>
                            <strong>${result.report_type || result.analysis_type || 'Unknown'}</strong>
                        </div>
                        <div class="d-flex justify-content-between mb-2">
                            <span>Quality Score:</span>
                            <strong>${result.overall_quality_score ? result.overall_quality_score.toFixed(2) : 'N/A'}</strong>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Processing Time:</span>
                            <strong>${(result.processing_time || 0).toFixed(2)}s</strong>
                        </div>
                    </div>
                    
                    <div class="d-flex gap-2">
                        <button class="c-button c-button--outline-primary c-button--sm flex-grow-1" 
                                onclick="viewAnalysisResults('${result.request_id}')">
                            <i class="bi bi-eye c-button__icon"></i>
                            <span class="c-button__text">View</span>
                        </button>
                        <button class="c-button c-button--outline-secondary c-button--sm" 
                                onclick="viewReport('${result.request_id}')">
                            <i class="bi bi-file-earmark-text c-button__icon"></i>
                        </button>
                    </div>
                </div>
            </div>
        </div>
    `).join('');
}

function refreshAnalysis() {
    loadAnalysisData();
    loadCrewAIStatus();
}

function refreshActiveJobs() {
    // Refresh active jobs from Crew AI API
    axios.get('/api/crewai/analysis/history/?limit=10')
        .then(function(response) {
            const history = response.data.history || [];
            analysisJobs = history.filter(h => h.status === 'running' || h.status === 'pending' || h.status === 'processing');
            updateActiveJobs();
            updateActiveJobsCount();
        })
        .catch(function(error) {
            console.error('Error refreshing active jobs:', error);
        });
}

function getStatusBadge(status) {
    const statuses = {
        'completed': 'success',
        'running': 'primary',
        'pending': 'warning',
        'processing': 'info',
        'failed': 'danger',
        'cancelled': 'secondary'
    };
    return statuses[status] || 'secondary';
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