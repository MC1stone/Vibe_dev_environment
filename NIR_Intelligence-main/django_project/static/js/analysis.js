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

function getCsrfToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

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
                const dataTransfer = new DataTransfer();
                dataTransfer.items.add(e.dataTransfer.files[0]);
                document.getElementById('fileInput').files = dataTransfer.files;
                handleFileUpload({ target: { files: dataTransfer.files } });
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
            
            // Average processing time is computed from the real history
            // (updateAvgProcessingTime, called by loadAnalysisData)
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
            
            analysisHistory = history.filter(h => (h.status === 'completed' || h.status === 'failed' || h.status === 'cancelled') || (h.status === undefined && h.request_id));
            updateActiveJobs();
            updateActiveJobsCount();
            updateAvgProcessingTime();
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
    // The single consolidated workflow: data quality + spectral analysis +
    // statistics + neural networks + one comprehensive report.
    if (!fileUploadData || !fileUploadData.fileId) {
        showError('Please upload a spectrum file first (.json, .csv or .txt).');
        return;
    }

    showLoading();
    setWorkflowStep(2);

    // Run the full CrewAI pipeline on the stored file. The backend loads the
    // file with the S3 format-agnostic loader, runs every agent and stores
    // the comprehensive report; the response carries the full summary.
    const runBtn = document.getElementById('runWorkflowBtn');
    if (runBtn) runBtn.disabled = true;

    fetch('/api/files/' + encodeURIComponent(fileUploadData.fileId) + '/crew-analysis/', {
        method: 'POST',
        body: JSON.stringify({ include_calibration: true }),
        credentials: 'same-origin',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(function(response) {
        if (response.status === 401 || response.status === 403) {
            throw new Error('Please log in to run the analysis.');
        }
        return response.json().catch(function() { return {}; });
    })
    .then(function(result) {
        hideLoading();
        if (runBtn) runBtn.disabled = false;
        if (!result.success) {
            showError('Analysis failed: ' + (result.error || result.message || 'Unknown error'));
            return;
        }
        showSuccess('Complete analysis finished - the report is ready.');
        const enriched = Object.assign({
            sample_id: fileUploadData.fileName,
            processing_time: result.processing_time,
            overall_quality_score: result.overall_quality_score,
            spectral_data: result.spectral_data || (result.summary && result.summary.spectral_data),
            report_url: result.report_url
        }, result.summary || {});
        currentAnalysisRequest = enriched;
        displayAnalysisResults(enriched);
        loadAnalysisData();
    })
    .catch(function(error) {
        console.error('Error running analysis:', error);
        hideLoading();
        if (runBtn) runBtn.disabled = false;
        showError('Failed to run analysis: ' + error.message);
    });
}

// The workflow entry point wired to the single Run button.
function runCompleteWorkflow() {
    startAnalysis();
}

function handleFileUpload(event) {
    const files = event.target.files;
    if (!files || files.length === 0) return;
    
    const file = files[0];
    
    // Upload the file to the server so the crew agents analyse the real
    // stored file (same endpoint and parser chain as the Files page).
    const formData = new FormData();
    formData.append('files', file);
    
    const info = document.getElementById('uploadedFileInfo');
    if (info) info.textContent = 'Uploading ' + file.name + '...';
    
    fetch('/api/files/upload/', {
        method: 'POST',
        body: formData,
        credentials: 'same-origin',
        headers: { 'X-CSRFToken': getCsrfToken() }
    })
    .then(function(response) {
        if (response.status === 401 || response.status === 403) {
            throw new Error('Please log in to upload files.');
        }
        return response.json().catch(function() { return {}; });
    })
    .then(function(data) {
        if (!data.success || !data.uploaded_files || data.uploaded_files.length === 0) {
            const msg = (data.errors && data.errors.length) ? data.errors.join('; ') : (data.message || data.error || 'Upload failed');
            throw new Error(msg);
        }
        const fileId = data.uploaded_files[0];
        fileUploadData = {
            fileName: file.name,
            fileId: fileId
        };
        showSuccess('File uploaded: ' + file.name);
        if (info) info.textContent = file.name + ' stored on the server. Ready to run the workflow.';
        const runBtn = document.getElementById('runWorkflowBtn');
        if (runBtn) runBtn.disabled = false;
        setWorkflowStep(1);
    })
    .catch(function(error) {
        console.error('Upload failed:', error);
        fileUploadData = null;
        const runBtn = document.getElementById('runWorkflowBtn');
        if (runBtn) runBtn.disabled = true;
        if (info) info.textContent = '';
        showError('Upload failed: ' + error.message);
    });
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

// Mark a workflow step in the stepper (1..5); steps before it are done.
function setWorkflowStep(step) {
    const steps = document.querySelectorAll('#workflowSteps .workflow-step');
    steps.forEach(function(el) {
        const n = parseInt(el.getAttribute('data-step'), 10);
        el.classList.toggle('is-done', n < step);
        el.classList.toggle('is-active', n === step);
    });
}

// Show the workflow results panels and link to the complete report.
function showWorkflowReport(result) {
    const row = document.getElementById('workflowResultsRow');
    if (row) row.classList.remove('d-none');
    const note = document.getElementById('workflowProgressNote');
    if (note) note.classList.add('d-none');
    setWorkflowStep(5);

    const reports = (result.reports || (result.summary && result.summary.reports) || []);
    const reportUrl = result.report_url || null;
    const linkArea = document.getElementById('reportLinkArea');
    const openBtn = document.getElementById('openReportBtn');
    if (reportUrl || reports.length > 0) {
        const label = reports.length > 0 ? reports[0].report_id : 'Complete report';
        if (linkArea) linkArea.innerHTML = 'Complete report generated: <strong>' + escapeHtml(label) + '</strong>';
        if (openBtn) openBtn.disabled = false;
    } else if (linkArea) {
        linkArea.textContent = 'No report was generated for this analysis.';
    }
}

function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text == null ? '' : String(text);
    return div.innerHTML;
}

function displayAnalysisResults(result) {
    hideLoading();
    
    // Update basic information
    const nameEl = document.getElementById('resultAnalysisName');
    if (nameEl) nameEl.textContent = result.sample_id || 'N/A';
    const typeEl = document.getElementById('resultAnalysisType');
    if (typeEl) typeEl.textContent = result.report_type || result.analysis_type || 'Unknown';
    const sampleEl = document.getElementById('resultSampleId');
    if (sampleEl) sampleEl.textContent = result.sample_id || 'N/A';
    const statusEl = document.getElementById('resultStatus');
    if (statusEl) statusEl.innerHTML = '<span class="c-badge c-badge--success">Completed</span>';
    const completedEl = document.getElementById('resultCompleted');
    if (completedEl) completedEl.textContent = formatDate(result.timestamp);
    const timeEl = document.getElementById('resultProcessingTime');
    if (timeEl) timeEl.textContent = (result.processing_time || 0).toFixed(2) + 's';
    
    // Update summary (object from the crew, rendered as key facts)
    const summary = result.summary || {};
    const summaryEl = document.getElementById('resultSummary');
    if (summaryEl) summaryEl.innerHTML = formatSummaryText(summary, result);
    
    // Update quality scores
    const qualityScores = document.getElementById('qualityScores');
    if (qualityScores) qualityScores.innerHTML = '';
    
    if (result.overall_quality_score !== undefined && result.overall_quality_score !== null) {
        qualityScores.innerHTML += `
            <div class="col-12 col-md-6">
                <div class="c-stat-card h-100">
                    <div class="c-stat-card__icon c-stat-card__icon--primary">
                        <i class="bi bi-star"></i>
                    </div>
                    <div class="c-stat-card__number">${Number(result.overall_quality_score).toFixed(2)}</div>
                    <div class="c-stat-card__label">Overall Quality</div>
                </div>
            </div>
        `;
    }
    
    if (result.spectral_analysis && result.spectral_analysis.quality_score !== undefined) {
        qualityScores.innerHTML += `
            <div class="col-12 col-md-6">
                <div class="c-stat-card h-100">
                    <div class="c-stat-card__icon c-stat-card__icon--success">
                        <i class="bi bi-graph-up"></i>
                    </div>
                    <div class="c-stat-card__number">${Number(result.spectral_analysis.quality_score).toFixed(2)}</div>
                    <div class="c-stat-card__label">Spectral Quality</div>
                </div>
            </div>
        `;
    }
    
    if (result.metadata_quality && result.metadata_quality.overall_score !== undefined) {
        qualityScores.innerHTML += `
            <div class="col-12 col-md-6">
                <div class="c-stat-card h-100">
                    <div class="c-stat-card__icon c-stat-card__icon--info">
                        <i class="bi bi-check-circle"></i>
                    </div>
                    <div class="c-stat-card__number">${Number(result.metadata_quality.overall_score).toFixed(2)}</div>
                    <div class="c-stat-card__label">Metadata Quality</div>
                </div>
            </div>
        `;
    }
    
    if (result.sensor_quality && result.sensor_quality.overall_quality_score !== undefined) {
        qualityScores.innerHTML += `
            <div class="col-12 col-md-6">
                <div class="c-stat-card h-100">
                    <div class="c-stat-card__icon c-stat-card__icon--warning">
                        <i class="bi bi-activity"></i>
                    </div>
                    <div class="c-stat-card__number">${(Number(result.sensor_quality.overall_quality_score) * 100).toFixed(1)}%</div>
                    <div class="c-stat-card__label">Sensor Quality</div>
                </div>
            </div>
        `;
    }
    
    // Render the agent result panels (crew agent results, OP6/OP8)
    renderSensorQualityResults(result.sensor_quality || (result.summary && result.summary.sensor_quality));
    renderStatisticalResults(result.statistical_analysis || (result.summary && result.summary.statistical_analysis));
    renderNeuralNetworkResults(result.neural_network || (result.summary && result.summary.neural_network));
    
    // Update detailed results
    const resultData = document.getElementById('resultData');
    if (resultData) resultData.innerHTML = formatResultsData(result);
    
    // Create chart from the real spectral data submitted to the crew
    createAnalysisChart(result);
    
    // The consolidated workflow page shows the results inline instead of a modal
    showWorkflowReport(result);
}

function formatSummaryText(summary, result) {
    const lines = [];
    const spectral = result.spectral_analysis || summary.spectral_analysis || {};
    if (spectral.quality_grade) {
        lines.push(`<p class="mb-1"><strong>Spectral grade:</strong> ${spectral.quality_grade}</p>`);
    }
    if (spectral.issues_detected && spectral.issues_detected.length > 0) {
        lines.push(`<p class="mb-1"><strong>Issues:</strong> ${spectral.issues_detected.join(', ')}</p>`);
    }
    const metadata = result.metadata_quality || summary.metadata_quality || {};
    if (metadata.grade) {
        lines.push(`<p class="mb-1"><strong>Metadata grade:</strong> ${metadata.grade}</p>`);
    }
    if (summary.recommendations && summary.recommendations.length > 0) {
        lines.push('<p class="mb-1"><strong>Recommendations:</strong></p><ul class="mb-0">' +
            summary.recommendations.map(r => `<li>${r}</li>`).join('') + '</ul>');
    }
    if (lines.length === 0) {
        lines.push('<p class="mb-0">No summary available.</p>');
    }
    return lines.join('');
}

function fmt(value) {
    if (value === undefined || value === null) return 'N/A';
    const num = Number(value);
    if (Number.isNaN(num)) return 'N/A';
    return String(num.toFixed(4));
}

function renderSensorQualityResults(sq) {
    const el = document.getElementById('sensorQualityResults');
    if (!el) return;
    if (!sq || Object.keys(sq).length === 0) {
        el.innerHTML = '<p class="text-muted mb-0">Sensor quality agent did not produce results for this analysis.</p>';
        return;
    }
    let html = '<div class="table-responsive"><table class="c-table c-table--sm c-table--bordered">';
    if (sq.status) html += `<tr><td>Status</td><td>${sq.status}</td></tr>`;
    if (sq.num_spectra !== undefined) html += `<tr><td>Spectra assessed</td><td>${sq.num_spectra}</td></tr>`;
    if (sq.data_points !== undefined) html += `<tr><td>Data points</td><td>${sq.data_points}</td></tr>`;
    if (sq.drift_level !== undefined) html += `<tr><td>Drift level</td><td>${fmt(sq.drift_level)} ${sq.drift_detected ? '<span class="c-badge c-badge--danger">detected</span>' : '<span class="c-badge c-badge--success">ok</span>'}</td></tr>`;
    if (sq.offset_level !== undefined) html += `<tr><td>Offset level</td><td>${fmt(sq.offset_level)} ${sq.offset_detected ? '<span class="c-badge c-badge--danger">detected</span>' : '<span class="c-badge c-badge--success">ok</span>'}</td></tr>`;
    if (sq.noise_level !== undefined) html += `<tr><td>Noise level</td><td>${fmt(sq.noise_level)} ${sq.noise_detected ? '<span class="c-badge c-badge--danger">detected</span>' : '<span class="c-badge c-badge--success">ok</span>'}</td></tr>`;
    if (sq.overall_quality_score !== undefined) html += `<tr><td>Overall quality</td><td><strong>${(Number(sq.overall_quality_score) * 100).toFixed(1)}%</strong></td></tr>`;
    if (sq.warnings && sq.warnings.length > 0) {
        html += `<tr><td>Warnings</td><td><ul class="mb-0">${sq.warnings.map(w => `<li class="text-warning">${w}</li>`).join('')}</ul></td></tr>`;
    }
    if (sq.checks_performed && sq.checks_performed.length > 0) {
        html += `<tr><td>Checks</td><td>${sq.checks_performed.join(', ')}</td></tr>`;
    }
    html += '</table></div>';
    el.innerHTML = html;
}

function renderStatisticalResults(stats) {
    const el = document.getElementById('statisticalResults');
    if (!el) return;
    if (!stats || Object.keys(stats).length === 0) {
        el.innerHTML = '<p class="text-muted mb-0">Statistical analysis agent did not produce results for this analysis.</p>';
        return;
    }
    let html = '<div class="table-responsive"><table class="c-table c-table--sm c-table--bordered">';
    if (stats.status) html += `<tr><td>Status</td><td>${stats.status}</td></tr>`;
    if (stats.num_samples !== undefined) html += `<tr><td>Samples</td><td>${stats.num_samples}</td></tr>`;
    if (stats.data_points !== undefined) html += `<tr><td>Data points</td><td>${stats.data_points}</td></tr>`;
    const applied = stats.methods_applied || [];
    if (applied.length > 0) {
        html += `<tr><td>Methods applied</td><td>${applied.map(m => `<span class="c-badge c-badge--success me-1">${m}</span>`).join('')}</td></tr>`;
    }
    const methodResults = stats.method_results || {};
    if (methodResults.PCA && methodResults.PCA.cumulative_variance_explained !== undefined && methodResults.PCA.cumulative_variance_explained !== null) {
        html += `<tr><td>PCA variance explained</td><td>${(Number(methodResults.PCA.cumulative_variance_explained) * 100).toFixed(1)}% (${methodResults.PCA.n_components} components)</td></tr>`;
    }
    if (methodResults.PLS && methodResults.PLS.mean_r2 !== undefined && methodResults.PLS.mean_r2 !== null) {
        html += `<tr><td>PLS CV R&sup2;</td><td>${Number(methodResults.PLS.mean_r2).toFixed(3)}</td></tr>`;
    }
    if (methodResults.PCR && methodResults.PCR.mean_r2 !== undefined && methodResults.PCR.mean_r2 !== null) {
        html += `<tr><td>PCR CV R&sup2;</td><td>${Number(methodResults.PCR.mean_r2).toFixed(3)}</td></tr>`;
    }
    if (methodResults.ClusterAnalysis && methodResults.ClusterAnalysis.silhouette_score !== undefined && methodResults.ClusterAnalysis.silhouette_score !== null) {
        html += `<tr><td>Cluster silhouette</td><td>${Number(methodResults.ClusterAnalysis.silhouette_score).toFixed(3)} (k=${methodResults.ClusterAnalysis.k})</td></tr>`;
    }
    const skipped = stats.methods_skipped || [];
    if (skipped.length > 0) {
        html += `<tr><td>Skipped</td><td><ul class="mb-0">${skipped.map(s => `<li>${s.method}: ${s.reason}</li>`).join('')}</ul></td></tr>`;
    }
    html += '</table></div>';
    el.innerHTML = html;
}

function renderNeuralNetworkResults(nn) {
    const el = document.getElementById('neuralNetworkResults');
    if (!el) return;
    if (!nn || Object.keys(nn).length === 0) {
        el.innerHTML = '<p class="text-muted mb-0">Neural network agent did not produce results for this analysis.</p>';
        return;
    }
    let html = '<div class="table-responsive"><table class="c-table c-table--sm c-table--bordered">';
    if (nn.status) html += `<tr><td>Status</td><td>${nn.status}</td></tr>`;
    if (nn.num_samples !== undefined) html += `<tr><td>Samples</td><td>${nn.num_samples}</td></tr>`;
    const trained = nn.models_trained || [];
    if (trained.length > 0) {
        html += `<tr><td>Models trained</td><td>${trained.map(m => `<span class="c-badge c-badge--success me-1">${m}</span>`).join('')}</td></tr>`;
    }
    const modelResults = nn.model_results || {};
    if (modelResults.MLP && modelResults.MLP.r2_score !== undefined && modelResults.MLP.r2_score !== null) {
        html += `<tr><td>MLP test R&sup2;</td><td>${Number(modelResults.MLP.r2_score).toFixed(3)}</td></tr>`;
    }
    if (modelResults.Autoencoder && modelResults.Autoencoder.reconstruction_mse !== undefined && modelResults.Autoencoder.reconstruction_mse !== null) {
        html += `<tr><td>Autoencoder MSE</td><td>${Number(modelResults.Autoencoder.reconstruction_mse).toFixed(4)}</td></tr>`;
        html += `<tr><td>Anomalies detected</td><td>${modelResults.Autoencoder.anomalies_detected}</td></tr>`;
    }
    if (nn.best_model && nn.best_model_r2_score !== undefined && nn.best_model_r2_score !== null) {
        html += `<tr><td>Best model</td><td><strong>${nn.best_model}</strong> (R&sup2; ${Number(nn.best_model_r2_score).toFixed(3)})</td></tr>`;
    }
    const deferred = nn.models_deferred || [];
    if (deferred.length > 0) {
        html += `<tr><td>Deferred</td><td><ul class="mb-0">${deferred.map(d => `<li>${d.model}: ${d.reason}</li>`).join('')}</ul></td></tr>`;
    }
    const skipped = nn.models_skipped || [];
    if (skipped.length > 0) {
        html += `<tr><td>Skipped</td><td><ul class="mb-0">${skipped.map(s => `<li>${s.model}: ${s.reason}</li>`).join('')}</ul></td></tr>`;
    }
    html += '</table></div>';
    el.innerHTML = html;
}

function formatResultsData(result) {
    let html = '<div class="table-responsive"><table class="c-table c-table--bordered c-table--sm">';
    
    // Add spectral analysis data
    if (result.spectral_analysis) {
        const sa = result.spectral_analysis;
        html += '<tr><th colspan="2" class="bg-light">Spectral Analysis</th></tr>';
        html += `<tr><td>Quality Score</td><td>${Number(sa.quality_score).toFixed(2)}</td></tr>`;
        html += `<tr><td>Quality Grade</td><td>${sa.quality_grade}</td></tr>`;
        html += `<tr><td>Wavelength Range</td><td>${sa.wavelength_range[0]} - ${sa.wavelength_range[1]} nm</td></tr>`;
        html += `<tr><td>Data Points</td><td>${sa.data_points}</td></tr>`;
        html += `<tr><td>Noise Level</td><td>${Number(sa.noise_level).toFixed(4)}</td></tr>`;
        html += `<tr><td>Signal to Noise Ratio</td><td>${Number(sa.signal_to_noise_ratio).toFixed(2)}</td></tr>`;
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
        html += `<tr><td>Overall Score</td><td>${Number(mq.overall_quality_score !== undefined ? mq.overall_quality_score : mq.overall_score).toFixed(2)}</td></tr>`;
        html += `<tr><td>Quality Grade</td><td>${mq.overall_quality_grade}</td></tr>`;
        html += `<tr><td>Completeness Score</td><td>${Number(mq.completeness_score).toFixed(2)}</td></tr>`;
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
    if (!ctx) return;
    
    // Destroy existing chart if it exists
    if (analysisChart) {
        analysisChart.destroy();
    }
    
    // Use the real spectral data submitted to / returned by the crew
    const spectral = (result && result.spectral_data) || fileUploadData || null;
    const wavelengths = spectral ? (spectral.wavelengths || []) : [];
    const intensities = spectral ? (spectral.intensities || []) : [];
    
    if (wavelengths.length === 0 || intensities.length === 0) {
        if (analysisChart) {
            analysisChart.destroy();
            analysisChart = null;
        }
        const parent = ctx.parentElement;
        let note = document.getElementById('analysisChartEmpty');
        if (!note && parent) {
            note = document.createElement('p');
            note.id = 'analysisChartEmpty';
            note.className = 'text-muted mb-0';
            note.textContent = 'No spectral data available for this analysis.';
            parent.appendChild(note);
        }
        return;
    }
    
    const existingNote = document.getElementById('analysisChartEmpty');
    if (existingNote) existingNote.remove();
    
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
    if (currentAnalysisRequest && currentAnalysisRequest.report_url) {
        window.open(currentAnalysisRequest.report_url, '_blank');
        return;
    }
    if (!currentAnalysisRequest || !currentAnalysisRequest.request_id) {
        showError('No analysis results available to view report.');
        return;
    }
    
    showLoading();
    
    // Look up the report generated for this analysis request, then preview it
    axios.get('/api/crewai/analysis/status/?request_id=' + currentAnalysisRequest.request_id)
        .then(function(response) {
            const result = response.data;
            const reports = (result.reports || (result.summary && result.summary.reports) || []);
            if (reports.length > 0) {
                hideLoading();
                window.open('/api/crewai/reports/preview/?report_id=' + reports[0].report_id, '_blank');
            } else {
                hideLoading();
                showError('No report was generated for this analysis.');
            }
        })
        .catch(function(error) {
            hideLoading();
            showError('Failed to load the report for this analysis.');
        });
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

function updateAvgProcessingTime() {
    const el = getElementSafely('avgProcessingTime');
    if (!el) return;
    const times = analysisHistory
        .map(h => Number(h.processing_time))
        .filter(t => !Number.isNaN(t));
    if (times.length === 0) {
        el.textContent = '0s';
        return;
    }
    const avg = times.reduce((sum, t) => sum + t, 0) / times.length;
    el.textContent = avg.toFixed(2) + 's';
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
                            <strong>${result.overall_quality_score !== undefined && result.overall_quality_score !== null ? Number(result.overall_quality_score).toFixed(2) : 'N/A'}</strong>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Processing Time:</span>
                            <strong>${Number(result.processing_time || 0).toFixed(2)}s</strong>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Statistics:</span>
                            <strong>${(result.statistical_methods_applied || []).length || 'N/A'} methods</strong>
                        </div>
                        <div class="d-flex justify-content-between">
                            <span>Neural Networks:</span>
                            <strong>${(result.neural_models_trained || []).length || 'N/A'} models</strong>
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