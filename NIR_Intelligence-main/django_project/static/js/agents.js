// NIR_Mistral Framework - Agents Page JavaScript
// Crew AI Agent Management

// Global variables
let allAgents = [];
let filteredAgents = [];
let currentAgent = null;
let availableSpectra = [];

// Utility function for safe element access
function getElementSafely(id, parent = document) {
    const element = parent.getElementById(id);
    if (!element) {
        console.warn(`Element with ID "${id}" not found`);
        return null;
    }
    return element;
}

// Agent type definitions and their properties
const agentTypes = {
    'spectral': {
        name: 'Spectral Analysis',
        icon: 'bi-graph-up',
        color: 'var(--color-primary)',
        background: 'rgba(122, 185, 41, 0.1)',
        description: 'Analyzes NIR spectral data for quality and characteristics'
    },
    'metadata': {
        name: 'Metadata Quality',
        icon: 'bi-check-circle',
        color: 'var(--color-primary-dark)',
        background: 'rgba(34, 89, 51, 0.1)',
        description: 'Validates and assesses metadata completeness and accuracy'
    },
    'calibration': {
        name: 'Calibration',
        icon: 'bi-tools',
        color: 'var(--color-primary-light)',
        background: 'rgba(168, 208, 101, 0.1)',
        description: 'Performs spectrometer calibration and validation'
    },
    'reporting': {
        name: 'Reporting',
        icon: 'bi-file-earmark-text',
        color: '#5a8a3f',
        background: 'rgba(90, 138, 63, 0.1)',
        description: 'Generates comprehensive analysis reports'
    },
    'federated': {
        name: 'Federated Learning',
        icon: 'bi-cloud',
        color: '#007bff',
        background: 'rgba(0, 123, 255, 0.1)',
        description: 'Enables collaborative learning across multiple devices'
    }
};

// Crew AI specific agents
const crewaiAgents = [
    {
        name: 'SpectralAnalysisAgent',
        display_name: 'Spectral Analysis Agent',
        type: 'spectral',
        version: '1.0.0',
        description: 'Comprehensive NIR spectral data processing and quality assessment agent',
        capabilities: ['spectral_analysis', 'quality_assessment', 'noise_detection', 'peak_identification'],
        status: 'available',
        success_rate: 95.5,
        total_executions: 1247,
        successful_executions: 1191,
        average_execution_time: 2.3,
        author: 'NIR_Mistral Team',
        license: 'MIT',
        documentation: '/documentation/agents/spectral-analysis/',
        is_crewai: true
    },
    {
        name: 'MetadataQualityAgent',
        display_name: 'Metadata Quality Agent',
        type: 'metadata',
        version: '1.0.0',
        description: 'Assesses and validates metadata completeness, accuracy, and consistency',
        capabilities: ['metadata_validation', 'completeness_check', 'accuracy_assessment', 'consistency_analysis'],
        status: 'available',
        success_rate: 98.2,
        total_executions: 892,
        successful_executions: 876,
        average_execution_time: 1.8,
        author: 'NIR_Mistral Team',
        license: 'MIT',
        documentation: '/documentation/agents/metadata-quality/',
        is_crewai: true
    },
    {
        name: 'CalibrationAgent',
        display_name: 'Calibration Agent',
        type: 'calibration',
        version: '1.0.0',
        description: 'Performs spectrometer calibration and performance validation',
        capabilities: ['wavelength_calibration', 'intensity_calibration', 'performance_validation', 'reference_standards'],
        status: 'available',
        success_rate: 99.1,
        total_executions: 456,
        successful_executions: 452,
        average_execution_time: 3.5,
        author: 'NIR_Mistral Team',
        license: 'MIT',
        documentation: '/documentation/agents/calibration/',
        is_crewai: true
    },
    {
        name: 'ReportingAgent',
        display_name: 'Reporting Agent',
        type: 'reporting',
        version: '1.0.0',
        description: 'Generates comprehensive HTML, PDF, and Quarto reports from analysis results',
        capabilities: ['html_reports', 'pdf_generation', 'quarto_templates', 'data_visualization'],
        status: 'available',
        success_rate: 97.8,
        total_executions: 2034,
        successful_executions: 1989,
        average_execution_time: 4.2,
        author: 'NIR_Mistral Team',
        license: 'MIT',
        documentation: '/documentation/agents/reporting/',
        is_crewai: true
    },
    {
        name: 'FlowerAgent',
        display_name: 'Flower Federated Learning Agent',
        type: 'federated',
        version: '1.0.0',
        description: 'Enables federated learning for collaborative model training across devices',
        capabilities: ['federated_learning', 'model_aggregation', 'privacy_preservation', 'distributed_training'],
        status: 'available',
        success_rate: 94.3,
        total_executions: 312,
        successful_executions: 294,
        average_execution_time: 8.7,
        author: 'NIR_Mistral Team',
        license: 'Apache 2.0',
        documentation: '/documentation/agents/federated-learning/',
        is_crewai: true
    }
];

// Initialize the page
document.addEventListener('DOMContentLoaded', function() {
    loadAgents();
    loadCapabilities();
    loadSpectra();
    
    // Set up real-time updates
    setInterval(loadCrewAIStatus, 30000);
});

function loadCrewAIStatus() {
    axios.get('/api/crewai/status/')
        .then(function(response) {
            const status = response.data;
            if (status.available) {
                // Update Crew AI agent statuses
                updateCrewAIAgentStatuses();
            }
        })
        .catch(function(error) {
            // Log error but don't show to user - service might be temporarily unavailable
            console.debug('Crew AI status check failed:', error.message);
        });
}

function updateCrewAIAgentStatuses() {
    // This would update the status of Crew AI agents based on real-time data
    // For now, we'll just ensure the Crew AI agents are displayed properly
    renderCrewAIAgents();
}

function loadAgents() {
    showLoading();
    
    // First, try to load agents from the API
    axios.get('/api/agents/')
        .then(function(response) {
            allAgents = response.data.results || [];
            
            // Add Crew AI agents if they're not already in the list
            crewaiAgents.forEach(crewaiAgent => {
                if (!allAgents.some(agent => agent.name === crewaiAgent.name)) {
                    allAgents.push(crewaiAgent);
                }
            });
            
            filteredAgents = [...allAgents];
            filterAgents();
            updateAgentStatistics(allAgents);
            hideLoading();
        })
        .catch(function(error) {
            console.error('Error loading agents from API:', error);
            
            // Fallback to Crew AI agents only
            allAgents = [...crewaiAgents];
            filteredAgents = [...allAgents];
            filterAgents();
            updateAgentStatistics(allAgents);
            hideLoading();
        });
}

function loadSpectra() {
    axios.get('/api/spectra/')
        .then(function(response) {
            availableSpectra = response.data.results || [];
        })
        .catch(function(error) {
            console.error('Error loading spectra:', error);
            availableSpectra = [];
        });
}

function loadCapabilities() {
    // Extract unique capabilities from all agents
    const capabilities = new Set();
    
    allAgents.forEach(agent => {
        if (agent.capabilities) {
            agent.capabilities.forEach(cap => capabilities.add(cap));
        }
    });
    
    // Also add Crew AI agent capabilities
    crewaiAgents.forEach(agent => {
        if (agent.capabilities) {
            agent.capabilities.forEach(cap => capabilities.add(cap));
        }
    });
    
    const capabilityFilter = document.getElementById('capabilityFilter');
    const currentValue = capabilityFilter.value;
    
    capabilityFilter.innerHTML = '<option value="">All Capabilities</option>';
    
    Array.from(capabilities).sort().forEach(cap => {
        const option = document.createElement('option');
        option.value = cap;
        option.textContent = formatCapabilityName(cap);
        if (cap === currentValue) {
            option.selected = true;
        }
        capabilityFilter.appendChild(option);
    });
}

function formatCapabilityName(cap) {
    return cap.replace(/_/g, ' ').replace(/\b\w/g, l => l.toUpperCase());
}

function filterAgents() {
    const search = document.getElementById('agentSearch').value.toLowerCase();
    const status = document.getElementById('statusFilter').value;
    const type = document.getElementById('typeFilter').value;
    const capability = document.getElementById('capabilityFilter').value;
    
    filteredAgents = allAgents.filter(agent => {
        // Search filter
        if (search) {
            const searchMatch = agent.name.toLowerCase().includes(search) ||
                              (agent.display_name && agent.display_name.toLowerCase().includes(search)) ||
                              (agent.description && agent.description.toLowerCase().includes(search));
            if (!searchMatch) return false;
        }
        
        // Status filter
        if (status && agent.status !== status) return false;
        
        // Type filter
        if (type && agent.type !== type) return false;
        
        // Capability filter
        if (capability && agent.capabilities && !agent.capabilities.includes(capability)) return false;
        
        return true;
    });
    
    updateAgentsTable(filteredAgents);
    renderCrewAIAgents();
    updateAgentStatistics(filteredAgents);
}

function updateAgentStatistics(agents) {
    const total = agents.length;
    const available = agents.filter(a => a.status === 'available').length;
    const running = agents.filter(a => a.status === 'running').length;
    const error = agents.filter(a => a.status === 'error').length;
    const crewai = agents.filter(a => a.is_crewai === true).length;
    
    document.getElementById('totalAgents').textContent = total;
    document.getElementById('availableAgents').textContent = available;
    document.getElementById('runningAgents').textContent = running;
    document.getElementById('errorAgents').textContent = error;
    document.getElementById('crewaiAgentsCount').textContent = crewai;
    document.getElementById('allAgentsCount').textContent = total + ' agents';
    document.getElementById('agentsCount').textContent = total + ' agents';
}

function renderCrewAIAgents() {
    const grid = document.getElementById('crewaiAgentsGrid');
    const crewaiAgentsList = filteredAgents.filter(agent => agent.is_crewai === true);
    
    if (crewaiAgentsList.length === 0) {
        grid.innerHTML = `
            <div class="col-12">
                <div class="c-card text-center py-lg">
                    <i class="bi bi-robot text-muted" style="font-size: 3rem;"></i>
                    <p class="mt-sm text-muted">No Crew AI agents found</p>
                </div>
            </div>
        `;
        return;
    }
    
    grid.innerHTML = crewaiAgentsList.map(agent => {
        const typeInfo = agentTypes[agent.type] || agentTypes.spectral;
        const statusColor = getStatusColor(agent.status);
        
        return `
            <div class="col-md-4 col-12">
                <div class="c-card agent-card h-100" onclick="showAgentDetails('${agent.name}')">
                    ${agent.is_crewai ? '<div class="crewai-agent-badge">CREW AI</div>' : ''}
                    <div class="c-card__body">
                        <div class="d-flex align-items-center mb-3">
                            <div class="agent-icon" style="background: ${typeInfo.background}; color: ${typeInfo.color};">
                                <i class="bi ${typeInfo.icon}"></i>
                            </div>
                            <div class="flex-grow-1 ms-3">
                                <h5 class="mb-0">${agent.display_name || agent.name}</h5>
                                <p class="text-muted small mb-0">v${agent.version}</p>
                            </div>
                        </div>
                        
                        <p class="text-muted small mb-3">${agent.description || 'No description available'}</p>
                        
                        <div class="d-flex align-items-center mb-3">
                            <span class="agent-status-dot" style="background: ${statusColor};"></span>
                            <span class="small">${agent.status}</span>
                        </div>
                        
                        <div class="agent-stats">
                            <div class="agent-stat">
                                <div class="agent-stat-value">${agent.success_rate.toFixed(1)}%</div>
                                <div class="agent-stat-label">Success Rate</div>
                            </div>
                            <div class="agent-stat">
                                <div class="agent-stat-value">${agent.total_executions}</div>
                                <div class="agent-stat-label">Executions</div>
                            </div>
                            <div class="agent-stat">
                                <div class="agent-stat-value">${agent.average_execution_time.toFixed(1)}s</div>
                                <div class="agent-stat-label">Avg Time</div>
                            </div>
                        </div>
                        
                        <div class="mt-3">
                            ${agent.capabilities && agent.capabilities.length > 0 ? 
                                agent.capabilities.slice(0, 3).map(cap => 
                                    `<span class="agent-capability-tag">${formatCapabilityName(cap)}</span>`
                                ).join('') + 
                                (agent.capabilities.length > 3 ? `<span class="agent-capability-tag">+${agent.capabilities.length - 3} more</span>` : '') : 
                                '<span class="text-muted small">No capabilities defined</span>'
                            }
                        </div>
                    </div>
                </div>
            </div>
        `;
    }).join('');
}

function updateAgentsTable(agents) {
    const tableBody = document.getElementById('agentsTable');
    
    if (agents.length === 0) {
        tableBody.innerHTML = `
            <tr>
                <td colspan="7" class="text-center py-lg">
                    <i class="bi bi-inbox text-muted" style="font-size: 2rem;"></i>
                    <p class="mt-sm text-muted">No agents found</p>
                </td>
            </tr>
        `;
        return;
    }
    
    tableBody.innerHTML = agents.map(agent => {
        const typeInfo = agentTypes[agent.type] || agentTypes.spectral;
        const statusBadge = getStatusBadge(agent.status);
        const successRate = agent.success_rate || 0;
        const capabilities = agent.capabilities ? agent.capabilities.join(', ') : 'None';
        
        return `
            <tr>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="agent-type-icon" style="background: ${typeInfo.background}; color: ${typeInfo.color};">
                            <i class="bi ${typeInfo.icon}"></i>
                        </div>
                        <div>
                            <strong>${agent.display_name || agent.name}</strong>
                            <div class="text-muted small">${agent.name}</div>
                        </div>
                    </div>
                </td>
                <td>
                    <span class="c-badge c-badge--outline-primary">${typeInfo.name}</span>
                </td>
                <td>v${agent.version}</td>
                <td>${statusBadge}</td>
                <td>
                    <div class="d-flex align-items-center">
                        <div class="progress" style="height: 8px; width: 60px; margin-right: 8px;">
                            <div class="progress-bar bg-success" 
                                 style="width: ${successRate}%" 
                                 role="progressbar" 
                                 aria-valuenow="${successRate}" aria-valuemin="0" aria-valuemax="100">
                            </div>
                        </div>
                        <span class="small">${successRate.toFixed(1)}%</span>
                    </div>
                </td>
                <td><small>${capabilities}</small></td>
                <td>
                    <button class="c-button c-button--outline-primary c-button--sm" 
                            onclick="showAgentDetails('${agent.name}')" 
                            data-bs-toggle="tooltip" title="View Details">
                        <i class="bi bi-eye c-button__icon"></i>
                    </button>
                    <button class="c-button c-button--outline-success c-button--sm" 
                            onclick="executeAgent('${agent.name}')" 
                            data-bs-toggle="tooltip" title="Execute">
                        <i class="bi bi-play c-button__icon"></i>
                    </button>
                    ${agent.is_crewai ? `
                    <button class="c-button c-button--outline-info c-button--sm" 
                            onclick="configureAgent('${agent.name}')" 
                            data-bs-toggle="tooltip" title="Configure">
                        <i class="bi bi-gear c-button__icon"></i>
                    </button>
                    ` : ''}
                </td>
            </tr>
        `;
    }).join('');
    
    // Initialize tooltips
    initTooltips();
}

function getStatusBadge(status) {
    const statusClasses = {
        'available': 'c-badge--success',
        'running': 'c-badge--info',
        'disabled': 'c-badge--secondary',
        'error': 'c-badge--danger'
    };
    
    const className = statusClasses[status] || 'c-badge--primary';
    return `<span class="c-badge ${className}">${status}</span>`;
}

function getStatusColor(status) {
    const statusColors = {
        'available': 'var(--color-success)',
        'running': 'var(--color-info)',
        'disabled': 'var(--color-secondary)',
        'error': 'var(--color-danger)'
    };
    
    return statusColors[status] || 'var(--color-primary)';
}

function initTooltips() {
    // Initialize Bootstrap tooltips
    const tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
    tooltipTriggerList.map(function (tooltipTriggerEl) {
        return new bootstrap.Tooltip(tooltipTriggerEl);
    });
}

function showAgentDetails(agentName) {
    const agent = allAgents.find(a => a.name === agentName);
    
    if (!agent) {
        showError('Agent not found');
        return;
    }
    
    currentAgent = agent;
    const modal = new bootstrap.Modal(document.getElementById('agentDetailsModal'));
    const content = document.getElementById('agentDetailsContent');
    
    const typeInfo = agentTypes[agent.type] || agentTypes.spectral;
    const capabilities = agent.capabilities ? agent.capabilities.join(', ') : 'None';
    const supportedFormats = agent.supported_formats ? agent.supported_formats.join(', ') : 'None';
    const dependencies = agent.dependencies ? agent.dependencies.join(', ') : 'None';
    
    content.innerHTML = `
        <div class="row g-4">
            <div class="col-md-4">
                <div class="text-center">
                    <div class="agent-icon" style="background: ${typeInfo.background}; color: ${typeInfo.color}; width: 80px; height: 80px; font-size: 2.5rem; margin: 0 auto 16px;">
                        <i class="bi ${typeInfo.icon}"></i>
                    </div>
                    <h3>${agent.display_name || agent.name}</h3>
                    <p class="text-muted">v${agent.version}</p>
                    <span class="c-badge ${getStatusBadgeClass(agent.status)}">${agent.status}</span>
                    ${agent.is_crewai ? '<span class="c-badge c-badge--primary ms-2">CREW AI</span>' : ''}
                </div>
                
                <div class="mt-4">
                    <h5 class="c-heading c-heading--5"><i class="bi bi-star"></i> Quick Stats</h5>
                    <div class="d-grid gap-3 mt-3">
                        <div class="c-stat-card c-stat-card--small">
                            <div class="c-stat-card__number">${agent.success_rate.toFixed(1)}%</div>
                            <div class="c-stat-card__label small">Success Rate</div>
                        </div>
                        <div class="c-stat-card c-stat-card--small">
                            <div class="c-stat-card__number">${agent.total_executions}</div>
                            <div class="c-stat-card__label small">Total Executions</div>
                        </div>
                        <div class="c-stat-card c-stat-card--small">
                            <div class="c-stat-card__number">${agent.average_execution_time.toFixed(1)}s</div>
                            <div class="c-stat-card__label small">Avg Time</div>
                        </div>
                    </div>
                </div>
            </div>
            
            <div class="col-md-8">
                <h4 class="c-heading c-heading--4"><i class="bi bi-info-circle"></i> Basic Information</h4>
                <dl class="row mb-4">
                    <dt class="col-sm-3">Name</dt>
                    <dd class="col-sm-9">${agent.name}</dd>
                    
                    <dt class="col-sm-3">Display Name</dt>
                    <dd class="col-sm-9">${agent.display_name || agent.name}</dd>
                    
                    <dt class="col-sm-3">Version</dt>
                    <dd class="col-sm-9">v${agent.version}</dd>
                    
                    <dt class="col-sm-3">Type</dt>
                    <dd class="col-sm-9"><span class="c-badge c-badge--outline-primary">${typeInfo.name}</span></dd>
                    
                    <dt class="col-sm-3">Author</dt>
                    <dd class="col-sm-9">${agent.author || 'Unknown'}</dd>
                    
                    <dt class="col-sm-3">License</dt>
                    <dd class="col-sm-9">${agent.license || 'MIT'}</dd>
                </dl>
                
                <h4 class="c-heading c-heading--4"><i class="bi bi-gear"></i> Capabilities</h4>
                <p class="mb-4">${capabilities}</p>
                
                <h4 class="c-heading c-heading--4"><i class="bi bi-graph-up"></i> Performance Metrics</h4>
                <dl class="row mb-4">
                    <dt class="col-sm-4">Total Executions</dt>
                    <dd class="col-sm-8">${agent.total_executions || 0}</dd>
                    
                    <dt class="col-sm-4">Successful Executions</dt>
                    <dd class="col-sm-8">${agent.successful_executions || 0}</dd>
                    
                    <dt class="col-sm-4">Success Rate</dt>
                    <dd class="col-sm-8">${(agent.success_rate || 0).toFixed(1)}%</dd>
                    
                    <dt class="col-sm-4">Average Execution Time</dt>
                    <dd class="col-sm-8">${(agent.average_execution_time || 0).toFixed(2)}s</dd>
                </dl>
                
                <h4 class="c-heading c-heading--4"><i class="bi bi-journal-text"></i> Description</h4>
                <p class="mb-4">${agent.description || 'No description available.'}</p>
                
                ${agent.documentation ? `
                <h4 class="c-heading c-heading--4"><i class="bi bi-link"></i> Documentation</h4>
                <p class="mb-4">
                    <a href="${agent.documentation}" target="_blank" class="c-button c-button--outline-primary c-button--sm">
                        <i class="bi bi-box-arrow-up-right c-button__icon"></i>
                        <span class="c-button__text">View Documentation</span>
                    </a>
                </p>
                ` : ''}
                
                ${agent.is_crewai ? `
                <div class="c-alert c-alert--info">
                    <i class="bi bi-info-circle c-alert__icon"></i>
                    <div class="c-alert__content">
                        <strong>Crew AI Agent</strong> - This agent is part of the Crew AI framework and can be used in automated workflows.
                    </div>
                </div>
                ` : ''}
            </div>
        </div>
    `;
    
    // Update execute button
    document.getElementById('executeAgentBtn').onclick = function() {
        executeAgent(agent.name);
    };
    
    modal.show();
}

function getStatusBadgeClass(status) {
    const statusClasses = {
        'available': 'c-badge--success',
        'running': 'c-badge--info',
        'disabled': 'c-badge--secondary',
        'error': 'c-badge--danger'
    };
    return 'c-badge ' + (statusClasses[status] || 'c-badge--primary');
}

function executeAgent(agentName) {
    const agent = allAgents.find(a => a.name === agentName);
    
    if (!agent) {
        showError('Agent not found');
        return;
    }
    
    currentAgent = agent;
    
    // Set agent name
    document.getElementById('executeAgentName').value = agentName;
    document.getElementById('jobName').value = `Analysis with ${agent.display_name || agent.name}`;
    document.getElementById('jobDescription').value = `Automated analysis using ${agent.display_name || agent.name}`;
    
    // Load spectra selection
    const spectraContainer = document.getElementById('spectraSelection');
    spectraContainer.innerHTML = '';
    
    if (availableSpectra.length > 0) {
        availableSpectra.forEach(spectrum => {
            const div = document.createElement('div');
            div.className = 'col-md-6';
            div.innerHTML = `
                <div class="c-form-check">
                    <input class="c-checkbox" type="checkbox" 
                           name="spectrum_ids" value="${spectrum.id}" id="spectrum_${spectrum.id}">
                    <label class="c-checkbox__label" for="spectrum_${spectrum.id}">
                        ${spectrum.name || spectrum.sample_id || spectrum.id}
                    </label>
                </div>
            `;
            spectraContainer.appendChild(div);
        });
    } else {
        spectraContainer.innerHTML = '<div class="col-12"><p class="text-muted small">No spectra available. Upload spectra first.</p></div>';
    }
    
    // Load agent parameters
    const parametersContainer = document.getElementById('agentParameters');
    parametersContainer.innerHTML = '';
    
    // For Crew AI agents, we'll add some default parameters
    if (agent.is_crewai) {
        const params = getAgentParameters(agent.name);
        params.forEach(param => {
            const div = document.createElement('div');
            div.className = 'col-md-6';
            
            let inputHtml = '';
            switch (param.type) {
                case 'boolean':
                    inputHtml = `
                        <select class="c-form-control" name="parameters[${param.name}]">
                            <option value="true">Yes</option>
                            <option value="false">No</option>
                        </select>
                    `;
                    break;
                case 'number':
                    inputHtml = `
                        <input type="number" class="c-form-control" name="parameters[${param.name}]" 
                               value="${param.default || ''}" step="${param.step || 1}">
                    `;
                    break;
                case 'select':
                    inputHtml = `
                        <select class="c-form-control" name="parameters[${param.name}]">
                            ${param.options.map(opt => `<option value="${opt.value}">${opt.label}</option>`).join('')}
                        </select>
                    `;
                    break;
                default:
                    inputHtml = `
                        <input type="text" class="c-form-control" name="parameters[${param.name}]" 
                               value="${param.default || ''}">
                    `;
                    break;
            }
            
            div.innerHTML = `
                <label class="c-form-label">${param.label}</label>
                ${inputHtml}
                ${param.description ? `<small class="form-text text-muted">${param.description}</small>` : ''}
            `;
            parametersContainer.appendChild(div);
        });
    } else {
        parametersContainer.innerHTML = '<div class="col-12"><p class="text-muted small">No parameters required</p></div>';
    }
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('executeAgentModal'));
    modal.show();
}

function getAgentParameters(agentName) {
    // Define parameters for each Crew AI agent
    const agentParams = {
        'SpectralAnalysisAgent': [
            {
                name: 'wavelength_min',
                label: 'Minimum Wavelength (nm)',
                type: 'number',
                default: 700,
                description: 'Minimum wavelength for analysis'
            },
            {
                name: 'wavelength_max',
                label: 'Maximum Wavelength (nm)',
                type: 'number',
                default: 2500,
                description: 'Maximum wavelength for analysis'
            },
            {
                name: 'noise_threshold',
                label: 'Noise Threshold',
                type: 'number',
                default: 0.1,
                step: 0.01,
                description: 'Threshold for noise detection'
            },
            {
                name: 'include_calibration',
                label: 'Include Calibration',
                type: 'boolean',
                default: true,
                description: 'Whether to include calibration in analysis'
            }
        ],
        'MetadataQualityAgent': [
            {
                name: 'completeness_threshold',
                label: 'Completeness Threshold (%)',
                type: 'number',
                default: 80,
                min: 0,
                max: 100,
                description: 'Minimum completeness percentage required'
            },
            {
                name: 'accuracy_threshold',
                label: 'Accuracy Threshold (%)',
                type: 'number',
                default: 90,
                min: 0,
                max: 100,
                description: 'Minimum accuracy percentage required'
            },
            {
                name: 'required_fields',
                label: 'Required Fields',
                type: 'text',
                default: 'sample_id,measurement_date,instrument_type',
                description: 'Comma-separated list of required metadata fields'
            }
        ],
        'CalibrationAgent': [
            {
                name: 'calibration_type',
                label: 'Calibration Type',
                type: 'select',
                options: [
                    { value: 'wavelength', label: 'Wavelength Calibration' },
                    { value: 'intensity', label: 'Intensity Calibration' },
                    { value: 'full', label: 'Full System Calibration' }
                ],
                default: 'wavelength',
                description: 'Type of calibration to perform'
            },
            {
                name: 'reference_standard',
                label: 'Reference Standard',
                type: 'select',
                options: [
                    { value: 'polystyrene', label: 'Polystyrene' },
                    { value: 'cerium_oxide', label: 'Cerium Oxide' },
                    { value: 'custom', label: 'Custom Reference' }
                ],
                default: 'polystyrene',
                description: 'Reference standard to use for calibration'
            }
        ],
        'ReportingAgent': [
            {
                name: 'report_format',
                label: 'Report Format',
                type: 'select',
                options: [
                    { value: 'html', label: 'HTML' },
                    { value: 'pdf', label: 'PDF' },
                    { value: 'md', label: 'Markdown' },
                    { value: 'qmd', label: 'Quarto' }
                ],
                default: 'html',
                description: 'Format for the generated report'
            },
            {
                name: 'include_visualizations',
                label: 'Include Visualizations',
                type: 'boolean',
                default: true,
                description: 'Whether to include charts and graphs in the report'
            },
            {
                name: 'detailed_analysis',
                label: 'Detailed Analysis',
                type: 'boolean',
                default: true,
                description: 'Whether to include detailed analysis in the report'
            }
        ],
        'FlowerAgent': [
            {
                name: 'privacy_level',
                label: 'Privacy Level',
                type: 'select',
                options: [
                    { value: 'local_only', label: 'Local Only' },
                    { value: 'public_federated', label: 'Public Federated' },
                    { value: 'private_federated', label: 'Private Federated' }
                ],
                default: 'local_only',
                description: 'Privacy level for federated learning'
            },
            {
                name: 'contribution_size',
                label: 'Contribution Size',
                type: 'select',
                options: [
                    { value: 'small', label: 'Small' },
                    { value: 'medium', label: 'Medium' },
                    { value: 'large', label: 'Large' }
                ],
                default: 'medium',
                description: 'Size of data contribution to federated learning'
            }
        ]
    };
    
    return agentParams[agentName] || [];
}

function submitAgentExecution() {
    const agentName = document.getElementById('executeAgentName').value;
    const jobName = document.getElementById('jobName').value;
    const jobDescription = document.getElementById('jobDescription').value;
    const analysisType = document.getElementById('jobAnalysisType').value;
    
    if (!jobName) {
        showError('Please enter a job name');
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
    
    // Get parameters
    const parameters = {};
    const paramInputs = document.querySelectorAll('input[name^="parameters["], select[name^="parameters["]');
    paramInputs.forEach(input => {
        const name = input.name.replace('parameters[', '').replace(']', '');
        parameters[name] = input.value;
    });
    
    showLoading();
    
    // Prepare the execution request
    const executionRequest = {
        agent_name: agentName,
        name: jobName,
        description: jobDescription,
        analysis_type: analysisType,
        spectrum_ids: selectedSpectra,
        parameters: parameters
    };
    
    // For Crew AI agents, use the Crew AI API
    const agent = allAgents.find(a => a.name === agentName);
    if (agent && agent.is_crewai) {
        // Map to Crew AI analysis request
        const crewaiRequest = {
            sample_id: 'job_' + Date.now(),
            analysis_mode: 'standard',
            privacy_level: 'local_only',
            report_type: analysisType,
            report_format: 'html',
            include_calibration: true,
            include_federated_learning: false,
            metadata: {
                job_name: jobName,
                description: jobDescription,
                agent: agentName,
                spectrum_ids: selectedSpectra
            },
            spectral_data: {
                // This would be populated with actual spectral data
                wavelengths: [700, 710, 720, 730, 740, 750], // Sample data
                intensities: [0.5, 0.6, 0.4, 0.7, 0.8, 0.6], // Sample data
                sample_id: 'sample_' + Date.now()
            }
        };
        
        // Add agent-specific parameters
        if (parameters.wavelength_min) {
            crewaiRequest.metadata.wavelength_min = parseFloat(parameters.wavelength_min);
        }
        if (parameters.wavelength_max) {
            crewaiRequest.metadata.wavelength_max = parseFloat(parameters.wavelength_max);
        }
        if (parameters.noise_threshold) {
            crewaiRequest.metadata.noise_threshold = parseFloat(parameters.noise_threshold);
        }
        
        axios.post('/api/crewai/analysis/start/', crewaiRequest)
            .then(function(response) {
                hideLoading();
                const result = response.data;
                
                if (result.success) {
                    showSuccess('Agent execution started successfully!');
                    
                    // Close the modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('executeAgentModal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Refresh the page or redirect to jobs
                    setTimeout(() => {
                        window.location.href = '/jobs/';
                    }, 1000);
                } else {
                    showError('Failed to start agent execution: ' + (result.error || 'Unknown error'));
                }
            })
            .catch(function(error) {
                console.error('Error executing agent:', error);
                hideLoading();
                showError('Failed to execute agent. Please try again.');
            });
    } else {
        // For non-Crew AI agents, use the regular API
        axios.post('/api/agents/' + agentName + '/execute/', executionRequest)
            .then(function(response) {
                hideLoading();
                const result = response.data;
                
                if (result.success) {
                    showSuccess('Agent execution started successfully!');
                    
                    // Close the modal
                    const modal = bootstrap.Modal.getInstance(document.getElementById('executeAgentModal'));
                    if (modal) {
                        modal.hide();
                    }
                    
                    // Refresh the page
                    loadAgents();
                } else {
                    showError('Failed to start agent execution: ' + (result.error || 'Unknown error'));
                }
            })
            .catch(function(error) {
                console.error('Error executing agent:', error);
                hideLoading();
                showError('Failed to execute agent. Please try again.');
            });
    }
}

function configureAgent(agentName) {
    const agent = allAgents.find(a => a.name === agentName);
    
    if (!agent || !agent.is_crewai) {
        showError('Only Crew AI agents can be configured');
        return;
    }
    
    currentAgent = agent;
    document.getElementById('configAgentName').value = agentName;
    
    const settingsContainer = document.getElementById('agentConfigSettings');
    settingsContainer.innerHTML = '';
    
    // Add configuration options for Crew AI agents
    const configOptions = getAgentConfigurationOptions(agent.name);
    configOptions.forEach(option => {
        const div = document.createElement('div');
        div.className = 'c-form-group';
        
        let inputHtml = '';
        switch (option.type) {
            case 'boolean':
                inputHtml = `
                    <select class="c-form-control" name="config[${option.name}]">
                        <option value="true">Enabled</option>
                        <option value="false">Disabled</option>
                    </select>
                `;
                break;
            case 'number':
                inputHtml = `
                    <input type="number" class="c-form-control" name="config[${option.name}]" 
                           value="${option.default || ''}" step="${option.step || 1}">
                `;
                break;
            case 'select':
                inputHtml = `
                    <select class="c-form-control" name="config[${option.name}]">
                        ${option.options.map(opt => `<option value="${opt.value}">${opt.label}</option>`).join('')}
                    </select>
                `;
                break;
            default:
                inputHtml = `
                    <input type="text" class="c-form-control" name="config[${option.name}]" 
                           value="${option.default || ''}">
                `;
                break;
        }
        
        div.innerHTML = `
            <label class="c-form-label">${option.label}</label>
            ${inputHtml}
            ${option.description ? `<small class="form-text text-muted">${option.description}</small>` : ''}
        `;
        settingsContainer.appendChild(div);
    });
    
    // Show modal
    const modal = new bootstrap.Modal(document.getElementById('agentConfigModal'));
    modal.show();
}

function getAgentConfigurationOptions(agentName) {
    // Define configuration options for each Crew AI agent
    const configOptions = {
        'SpectralAnalysisAgent': [
            {
                name: 'default_analysis_mode',
                label: 'Default Analysis Mode',
                type: 'select',
                options: [
                    { value: 'standard', label: 'Standard' },
                    { value: 'comprehensive', label: 'Comprehensive' },
                    { value: 'quick', label: 'Quick' },
                    { value: 'batch', label: 'Batch' }
                ],
                default: 'standard',
                description: 'Default analysis mode for this agent'
            },
            {
                name: 'max_data_points',
                label: 'Maximum Data Points',
                type: 'number',
                default: 10000,
                description: 'Maximum number of data points to process'
            },
            {
                name: 'enable_auto_calibration',
                label: 'Enable Auto Calibration',
                type: 'boolean',
                default: true,
                description: 'Automatically calibrate before analysis'
            }
        ],
        'MetadataQualityAgent': [
            {
                name: 'strict_mode',
                label: 'Strict Mode',
                type: 'boolean',
                default: false,
                description: 'Enable strict validation rules'
            },
            {
                name: 'min_completeness',
                label: 'Minimum Completeness (%)',
                type: 'number',
                default: 80,
                min: 0,
                max: 100,
                description: 'Minimum completeness percentage required'
            }
        ],
        'CalibrationAgent': [
            {
                name: 'auto_reference_detection',
                label: 'Auto Reference Detection',
                type: 'boolean',
                default: true,
                description: 'Automatically detect reference standards'
            },
            {
                name: 'calibration_frequency',
                label: 'Calibration Frequency',
                type: 'select',
                options: [
                    { value: 'daily', label: 'Daily' },
                    { value: 'weekly', label: 'Weekly' },
                    { value: 'monthly', label: 'Monthly' },
                    { value: 'manual', label: 'Manual Only' }
                ],
                default: 'daily',
                description: 'How often to perform calibration'
            }
        ],
        'ReportingAgent': [
            {
                name: 'default_format',
                label: 'Default Report Format',
                type: 'select',
                options: [
                    { value: 'html', label: 'HTML' },
                    { value: 'pdf', label: 'PDF' },
                    { value: 'md', label: 'Markdown' },
                    { value: 'qmd', label: 'Quarto' }
                ],
                default: 'html',
                description: 'Default format for generated reports'
            },
            {
                name: 'include_raw_data',
                label: 'Include Raw Data',
                type: 'boolean',
                default: false,
                description: 'Include raw spectral data in reports'
            }
        ],
        'FlowerAgent': [
            {
                name: 'enable_federated_learning',
                label: 'Enable Federated Learning',
                type: 'boolean',
                default: true,
                description: 'Enable federated learning functionality'
            },
            {
                name: 'default_privacy_level',
                label: 'Default Privacy Level',
                type: 'select',
                options: [
                    { value: 'local_only', label: 'Local Only' },
                    { value: 'public_federated', label: 'Public Federated' },
                    { value: 'private_federated', label: 'Private Federated' }
                ],
                default: 'local_only',
                description: 'Default privacy level for federated learning'
            }
        ]
    };
    
    return configOptions[agentName] || [];
}

function saveAgentConfig() {
    const agentName = document.getElementById('configAgentName').value;
    
    // Get configuration values
    const config = {};
    const configInputs = document.querySelectorAll('input[name^="config["], select[name^="config["]');
    configInputs.forEach(input => {
        const name = input.name.replace('config[', '').replace(']', '');
        config[name] = input.value;
    });
    
    showLoading();
    
    // Save configuration via API
    axios.post('/api/agents/' + agentName + '/configure/', {
        configuration: config
    })
        .then(function(response) {
            hideLoading();
            const result = response.data;
            
            if (result.success) {
                showSuccess('Agent configuration saved successfully!');
                
                // Close the modal
                const modal = bootstrap.Modal.getInstance(document.getElementById('agentConfigModal'));
                if (modal) {
                    modal.hide();
                }
                
                // Refresh the page
                loadAgents();
            } else {
                showError('Failed to save configuration: ' + (result.error || 'Unknown error'));
            }
        })
        .catch(function(error) {
            console.error('Error saving agent configuration:', error);
            hideLoading();
            showError('Failed to save agent configuration. Please try again.');
        });
}

function exportAgentsList() {
    const data = filteredAgents.map(agent => ({
        name: agent.name,
        display_name: agent.display_name || agent.name,
        type: agent.type || 'unknown',
        version: agent.version || '1.0.0',
        status: agent.status || 'unknown',
        capabilities: agent.capabilities ? agent.capabilities.join(', ') : '',
        success_rate: agent.success_rate || 0,
        is_crewai: agent.is_crewai || false
    }));
    
    const csv = convertToCSV(data);
    downloadCSV(csv, 'nir_agents_' + new Date().toISOString().split('T')[0] + '.csv');
}

function convertToCSV(data) {
    if (data.length === 0) return '';
    
    const headers = Object.keys(data[0]);
    const rows = data.map(row => headers.map(header => {
        const value = row[header];
        // Escape quotes and wrap in quotes if contains commas
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