// NIR Intelligence Platform - Files Management JavaScript
// Handles file upload, processing, and display for generic file types

// Global variables
let currentFiles = [];
let selectedFiles = [];
let currentPage = 1;
let filesPerPage = 20;
let currentFilter = 'all';
let currentCategoryFilter = 'all';

// File type icons mapping
const fileTypeIcons = {
    'spectral': 'bi-graph-up',
    'tabular': 'bi-table',
    'text': 'bi-file-text',
    'image': 'bi-image',
    'audio': 'bi-volume-up',
    'video': 'bi-film',
    'archive': 'bi-file-earmark-zip',
    'document': 'bi-file-earmark-pdf',
    'binary': 'bi-file-binary',
    'unknown': 'bi-file-earmark'
};

// File type colors mapping
const fileTypeColors = {
    'spectral': '#7ab929',
    'tabular': '#20c997',
    'text': '#6c757d',
    'image': '#fd7e14',
    'audio': '#e83e8c',
    'video': '#6f42c1',
    'archive': '#ffc107',
    'document': '#dc3545',
    'binary': '#6c757d',
    'unknown': '#6c757d'
};

// Supported file extensions by category
const supportedExtensions = {
    'spectral': ['.csv', '.json', '.h5', '.jdx', '.spc'],
    'tabular': ['.csv', '.xlsx', '.xls', '.parquet', '.feather'],
    'text': ['.txt', '.json', '.xml', '.yaml', '.yml', '.md'],
    'image': ['.png', '.jpg', '.jpeg', '.gif', '.tiff', '.webp', '.svg'],
    'audio': ['.wav', '.mp3', '.ogg', '.flac'],
    'video': ['.mp4', '.avi', '.mov', '.wmv'],
    'archive': ['.zip', '.tar', '.gz', '.rar', '.7z'],
    'document': ['.pdf', '.docx', '.doc', '.pptx']
};

// Quality badge classes
const qualityBadgeClasses = {
    'excellent': 'quality-excellent',
    'good': 'quality-good',
    'fair': 'quality-fair',
    'poor': 'quality-poor',
    'unknown': 'quality-unknown'
};

// Initialize the files page
function initializeFilesPage() {
    setupEventListeners();
    loadFiles();
    setupDragAndDrop();
    setupFileInput();
}

// Setup event listeners
function setupEventListeners() {
    // Filter change events
    document.getElementById('fileFilter').addEventListener('change', filterFiles);
    document.getElementById('categoryFilter').addEventListener('change', filterFiles);
    
    // Select all checkbox
    document.getElementById('selectAllFiles').addEventListener('change', toggleSelectAll);
}

// Setup drag and drop functionality
function setupDragAndDrop() {
    const dropZone = document.getElementById('dropZone');
    
    if (dropZone) {
        dropZone.addEventListener('dragover', function(e) {
            e.preventDefault();
            this.classList.add('drag-over');
        });
        
        dropZone.addEventListener('dragleave', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
        });
        
        dropZone.addEventListener('drop', function(e) {
            e.preventDefault();
            this.classList.remove('drag-over');
            
            if (e.dataTransfer.files.length > 0) {
                handleFileSelection(e.dataTransfer.files);
            }
        });
        
        dropZone.addEventListener('click', function() {
            document.getElementById('fileInput').click();
        });
    }
}

// Setup file input
function setupFileInput() {
    const fileInput = document.getElementById('fileInput');
    
    if (fileInput) {
        fileInput.addEventListener('change', function() {
            if (this.files.length > 0) {
                handleFileSelection(this.files);
            }
        });
    }
}

// Handle file selection
function handleFileSelection(files) {
    const filePreview = document.getElementById('filePreview');
    if (filePreview) {
        filePreview.innerHTML = '';
        
        for (let i = 0; i < Math.min(files.length, 5); i++) {
            const file = files[i];
            const fileInfo = document.createElement('div');
            fileInfo.className = 'd-flex align-items-center gap-2 p-2 bg-light rounded mb-2';
            
            // Get file category and icon
            const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
            let category = 'unknown';
            
            for (const [cat, exts] of Object.entries(supportedExtensions)) {
                if (exts.includes(extension)) {
                    category = cat;
                    break;
                }
            }
            
            const icon = fileTypeIcons[category] || 'bi-file-earmark';
            const color = fileTypeColors[category] || '#6c757d';
            
            fileInfo.innerHTML = `
                <i class="bi ${icon}" style="color: ${color}; font-size: 1.5rem;"></i>
                <div class="flex-fill">
                    <div class="fw-bold">${escapeHtml(file.name)}</div>
                    <div class="small text-muted">${formatFileSize(file.size)}</div>
                </div>
                <span class="badge bg-secondary">${category}</span>
            `;
            
            filePreview.appendChild(fileInfo);
        }
        
        if (files.length > 5) {
            const moreFiles = document.createElement('div');
            moreFiles.className = 'text-muted small';
            moreFiles.textContent = `+ ${files.length - 5} more files`;
            filePreview.appendChild(moreFiles);
        }
    }
}

// Format file size
function formatFileSize(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB', 'GB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i];
}

// Escape HTML to prevent XSS
function escapeHtml(text) {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
}

// Scroll to files section
function scrollToFiles() {
    const filesGallery = document.getElementById('filesGallery');
    if (filesGallery) {
        filesGallery.scrollIntoView({ behavior: 'smooth' });
    }
}

// Load files from server
function loadFiles() {
    const filesGallery = document.getElementById('filesGallery');
    const filesTable = document.getElementById('filesTable');
    
    if (filesGallery) {
        filesGallery.innerHTML = '<div class="col-12 text-center py-lg"><div class="c-loading-overlay__spinner" style="width: 2rem; height: 2rem; border-width: 0.2rem;"></div><p class="mt-sm text-muted">Loading files...</p></div>';
    }
    
    if (filesTable) {
        filesTable.innerHTML = '<tr><td colspan="8" class="text-center py-lg"><div class="c-loading-overlay__spinner" style="width: 2rem; height: 2rem; border-width: 0.2rem;"></div><p class="mt-sm text-muted">Loading files...</p></td></tr>';
    }
    
    // Use axios to fetch files from the API
    axios.get('/api/files/')
        .then(response => {
            if (response.data && response.data.files) {
                currentFiles = response.data.files;
                displayFiles();
                updateStatistics(response.data.statistics);
                updateCategoryCounts();
            }
        })
        .catch(error => {
            console.error('Error loading files:', error);
            if (filesGallery) {
                filesGallery.innerHTML = '<div class="col-12 text-center py-lg"><div class="text-danger">Error loading files. Please try again.</div></div>';
            }
            if (filesTable) {
                filesTable.innerHTML = '<tr><td colspan="8" class="text-center py-lg text-danger">Error loading files. Please try again.</td></tr>';
            }
        });
}

// Display files in gallery and table
function displayFiles() {
    const filesGallery = document.getElementById('filesGallery');
    const filesTable = document.getElementById('filesTable');
    const filesCount = document.getElementById('filesCount');
    
    // Filter files based on current filters
    let filteredFiles = filterFilesByCriteria(currentFiles);
    
    // Pagination
    const startIndex = (currentPage - 1) * filesPerPage;
    const paginatedFiles = filteredFiles.slice(startIndex, startIndex + filesPerPage);
    
    // Display gallery
    if (filesGallery) {
        if (paginatedFiles.length === 0) {
            filesGallery.innerHTML = '<div class="col-12 text-center py-lg"><div class="text-muted">No files found.</div></div>';
        } else {
            filesGallery.innerHTML = '';
            
            paginatedFiles.forEach(file => {
                const fileCard = createFileCard(file);
                filesGallery.appendChild(fileCard);
            });
        }
    }
    
    // Display table
    if (filesTable) {
        if (paginatedFiles.length === 0) {
            filesTable.innerHTML = '<tr><td colspan="8" class="text-center py-lg text-muted">No files found.</td></tr>';
        } else {
            filesTable.innerHTML = '';
            
            paginatedFiles.forEach(file => {
                const fileRow = createFileTableRow(file);
                filesTable.appendChild(fileRow);
            });
        }
    }
    
    // Update count
    if (filesCount) {
        filesCount.textContent = `${filteredFiles.length} files`;
    }
}

// Filter files by current criteria
function filterFilesByCriteria(files) {
    return files.filter(file => {
        // Filter by validity
        if (currentFilter === 'valid' && !file.is_valid) return false;
        if (currentFilter === 'invalid' && file.is_valid) return false;
        
        // Filter by category
        if (currentCategoryFilter !== 'all' && file.category !== currentCategoryFilter) return false;
        
        return true;
    });
}

// Create file card for gallery
function createFileCard(file) {
    const col = document.createElement('div');
    col.className = 'col-md-4 col-sm-6';
    
    const card = document.createElement('div');
    card.className = 'c-card file-card h-100';
    card.onclick = () => showFileDetails(file);
    
    // Get file type icon and color
    const icon = fileTypeIcons[file.category] || 'bi-file-earmark';
    const color = fileTypeColors[file.category] || '#6c757d';
    const qualityClass = qualityBadgeClasses[file.quality || 'unknown'] || 'quality-unknown';
    
    // File extension
    const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    
    card.innerHTML = `
        <div class="c-card__body">
            <div class="file-preview" style="height: 120px;">
                <i class="bi ${icon} file-icon" style="color: ${color};"></i>
                ${qualityClass !== 'quality-unknown' ? `<span class="quality-badge ${qualityClass}">${file.quality || 'unknown'}</span>` : ''}
            </div>
            <h6 class="mb-1">${escapeHtml(file.name)}</h6>
            <div class="file-meta mb-2">
                <span class="file-type-tag">${extension}</span>
                <span class="file-type-tag">${file.category}</span>
            </div>
            <div class="d-flex justify-content-between align-items-center">
                <small class="text-muted">${formatFileSize(file.size)}</small>
                <small class="text-muted">${formatDate(file.uploaded_at)}</small>
            </div>
            <div class="progress-container mt-2">
                <div class="progress-bar" style="width: ${file.quality_score ? file.quality_score * 100 : 0}%;"></div>
            </div>
        </div>
        <div class="c-card__footer bg-transparent">
            <div class="file-actions d-flex gap-2 justify-content-end">
                <button class="btn btn-sm btn-outline-primary" onclick="event.stopPropagation(); analyzeFile('${file.id}')" title="Analyze">
                    <i class="bi bi-play-circle"></i>
                </button>
                <button class="btn btn-sm btn-outline-success" onclick="event.stopPropagation(); downloadFile('${file.id}')" title="Download">
                    <i class="bi bi-download"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="event.stopPropagation(); deleteFile('${file.id}')" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </div>
    `;
    
    col.appendChild(card);
    return col;
}

// Create file table row
function createFileTableRow(file) {
    const tr = document.createElement('tr');
    
    // Get file type icon and color
    const icon = fileTypeIcons[file.category] || 'bi-file-earmark';
    const color = fileTypeColors[file.category] || '#6c757d';
    const qualityClass = qualityBadgeClasses[file.quality || 'unknown'] || 'quality-unknown';
    
    // File extension
    const extension = file.name.slice(file.name.lastIndexOf('.')).toLowerCase();
    
    tr.innerHTML = `
        <td>
            <input type="checkbox" value="${file.id}" onchange="updateSelectedFiles()">
        </td>
        <td>
            <i class="bi ${icon}" style="color: ${color}; margin-right: 8px;"></i>
            ${escapeHtml(file.name)}
        </td>
        <td><span class="badge bg-secondary">${extension}</span></td>
        <td><span class="badge bg-primary">${file.category}</span></td>
        <td>${formatFileSize(file.size)}</td>
        <td><span class="badge ${qualityClass}">${file.quality || 'unknown'}</span></td>
        <td>${formatDate(file.uploaded_at)}</td>
        <td>
            <div class="d-flex gap-1">
                <button class="btn btn-sm btn-outline-primary" onclick="analyzeFile('${file.id}')" title="Analyze">
                    <i class="bi bi-play-circle"></i>
                </button>
                <button class="btn btn-sm btn-outline-success" onclick="downloadFile('${file.id}')" title="Download">
                    <i class="bi bi-download"></i>
                </button>
                <button class="btn btn-sm btn-outline-danger" onclick="deleteFile('${file.id}')" title="Delete">
                    <i class="bi bi-trash"></i>
                </button>
            </div>
        </td>
    `;
    
    return tr;
}

// Update selected files
function updateSelectedFiles() {
    const checkboxes = document.querySelectorAll('#filesTable input[type="checkbox"]:checked');
    selectedFiles = Array.from(checkboxes).map(cb => cb.value);
}

// Toggle select all
function toggleSelectAll() {
    const checkbox = document.getElementById('selectAllFiles');
    const checkboxes = document.querySelectorAll('#filesTable input[type="checkbox"]');
    checkboxes.forEach(cb => cb.checked = checkbox.checked);
    updateSelectedFiles();
}

// Filter files
function filterFiles() {
    currentFilter = document.getElementById('fileFilter').value;
    currentCategoryFilter = document.getElementById('categoryFilter').value;
    currentPage = 1;
    displayFiles();
}

// Load more files
function loadMoreFiles() {
    currentPage++;
    displayFiles();
}

// Refresh files
function refreshFiles() {
    currentPage = 1;
    loadFiles();
}

// Update statistics
function updateStatistics(statistics) {
    if (statistics) {
        document.getElementById('totalFiles').textContent = statistics.total || 0;
        document.getElementById('validFiles').textContent = statistics.valid || 0;
        document.getElementById('invalidFiles').textContent = statistics.invalid || 0;
        document.getElementById('totalStorage').textContent = formatFileSize(statistics.total_size || 0);
    }
}

// Update category counts
function updateCategoryCounts() {
    // Reset all counts to 0
    const categories = ['spectral', 'tabular', 'text', 'image', 'audio', 'video', 'archive', 'document', 'unknown'];
    categories.forEach(cat => {
        const element = document.getElementById(`${cat}Count`);
        if (element) element.textContent = '0';
    });
    
    // Count files by category
    const counts = {};
    currentFiles.forEach(file => {
        counts[file.category] = (counts[file.category] || 0) + 1;
    });
    
    // Update counts
    categories.forEach(cat => {
        const element = document.getElementById(`${cat}Count`);
        if (element) element.textContent = counts[cat] || '0';
    });
}

// Show file details
function showFileDetails(file) {
    const modal = new bootstrap.Modal(document.getElementById('fileDetailsModal'));
    
    // Set basic info
    document.getElementById('detailName').textContent = file.name || 'N/A';
    document.getElementById('detailFileId').textContent = file.id || 'N/A';
    document.getElementById('detailType').textContent = file.type || 'N/A';
    document.getElementById('detailCategory').textContent = file.category || 'N/A';
    document.getElementById('detailSize').textContent = formatFileSize(file.size) || 'N/A';
    document.getElementById('detailQuality').textContent = file.quality || 'N/A';
    document.getElementById('detailUploaded').textContent = formatDate(file.uploaded_at) || 'N/A';
    document.getElementById('detailModified').textContent = formatDate(file.modified_at) || 'N/A';
    document.getElementById('detailDescription').textContent = file.description || 'No description available';
    
    // Set preview based on file type
    const preview = document.getElementById('filePreviewDetails');
    if (preview) {
        const icon = fileTypeIcons[file.category] || 'bi-file-earmark';
        const color = fileTypeColors[file.category] || '#6c757d';
        
        if (file.category === 'image' && file.preview_url) {
            preview.innerHTML = `<img src="${file.preview_url}" alt="Preview" style="max-width: 100%; max-height: 100%; object-fit: contain;">`;
        } else if (file.category === 'spectral' && file.preview_data) {
            // Could render a simple chart preview here
            preview.innerHTML = `<canvas id="spectrumPreviewChart"></canvas>`;
        } else {
            preview.innerHTML = `<i class="bi ${icon}" style="font-size: 4rem; color: ${color};"></i>`;
        }
    }
    
    // Set metadata
    const metadataContainer = document.getElementById('detailMetadata');
    if (metadataContainer && file.metadata) {
        metadataContainer.innerHTML = '';
        
        for (const [key, value] of Object.entries(file.metadata)) {
            const dt = document.createElement('dt');
            dt.className = 'col-sm-4';
            dt.textContent = key + ':';
            
            const dd = document.createElement('dd');
            dd.className = 'col-sm-8';
            dd.textContent = typeof value === 'object' ? JSON.stringify(value) : value;
            
            metadataContainer.appendChild(dt);
            metadataContainer.appendChild(dd);
        }
    }
    
    // Set analysis results
    const analysisContainer = document.getElementById('detailAnalysis');
    if (analysisContainer && file.analysis_results) {
        analysisContainer.innerHTML = '';
        
        if (typeof file.analysis_results === 'string') {
            analysisContainer.textContent = file.analysis_results;
        } else if (typeof file.analysis_results === 'object') {
            const pre = document.createElement('pre');
            pre.textContent = JSON.stringify(file.analysis_results, null, 2);
            analysisContainer.appendChild(pre);
        }
    }
    
    modal.show();
}

// Format date
function formatDate(dateString) {
    if (!dateString) return 'N/A';
    
    const date = new Date(dateString);
    return date.toLocaleDateString('en-US', {
        year: 'numeric',
        month: 'short',
        day: 'numeric',
        hour: '2-digit',
        minute: '2-digit'
    });
}

// Upload files
function uploadFiles() {
    const fileInput = document.getElementById('fileInput');
    const fileName = document.getElementById('fileName').value;
    const fileCategory = document.getElementById('fileCategory').value;
    const fileDescription = document.getElementById('fileDescription').value;
    const fileTags = document.getElementById('fileTags').value;
    const metadataAuthor = document.getElementById('metadataAuthor').value;
    const metadataDate = document.getElementById('metadataDate').value;
    const metadataSource = document.getElementById('metadataSource').value;
    const autoAnalyze = document.getElementById('autoAnalyze').checked;
    
    if (!fileInput || fileInput.files.length === 0) {
        alert('Please select at least one file to upload.');
        return;
    }
    
    const formData = new FormData();
    
    // Append files
    for (let i = 0; i < fileInput.files.length; i++) {
        formData.append('files', fileInput.files[i]);
    }
    
    // Append metadata
    formData.append('file_name', fileName);
    formData.append('file_category', fileCategory);
    formData.append('description', fileDescription);
    formData.append('tags', fileTags);
    formData.append('metadata_author', metadataAuthor);
    formData.append('metadata_date', metadataDate);
    formData.append('metadata_source', metadataSource);
    formData.append('auto_analyze', autoAnalyze);
    
    // Show loading state
    const uploadButton = document.querySelector('#uploadFileModal .btn-primary');
    const originalText = uploadButton.innerHTML;
    uploadButton.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span> Uploading...';
    uploadButton.disabled = true;
    
    // Send request
    axios.post('/api/files/upload/', formData, {
        headers: {
            'Content-Type': 'multipart/form-data',
            'X-CSRFToken': getCsrfToken()
        },
        onUploadProgress: function(progressEvent) {
            const percentCompleted = Math.round((progressEvent.loaded * 100) / progressEvent.total);
            console.log(`Upload progress: ${percentCompleted}%`);
        }
    })
    .then(response => {
        if (response.data && response.data.success) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('uploadFileModal'));
            modal.hide();
            
            // Reset form
            document.getElementById('uploadFileForm').reset();
            document.getElementById('filePreview').innerHTML = '';
            
            // Show success message
            alert('Files uploaded successfully!');
            
            // Refresh files
            refreshFiles();
        } else {
            alert('Error uploading files: ' + (response.data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Upload error:', error);
        alert('Error uploading files. Please try again.');
    })
    .finally(() => {
        uploadButton.innerHTML = originalText;
        uploadButton.disabled = false;
    });
}

// Get CSRF token
function getCsrfToken() {
    const token = document.querySelector('meta[name="csrf-token"]');
    return token ? token.getAttribute('content') : '';
}

// Analyze file
function analyzeFile(fileId) {
    axios.post(`/api/files/${fileId}/analyze/`, {
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => {
        if (response.data && response.data.success) {
            alert('Analysis started successfully!');
            refreshFiles();
        } else {
            alert('Error starting analysis: ' + (response.data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Analysis error:', error);
        alert('Error starting analysis. Please try again.');
    });
}

// Analyze current file (from details modal)
function analyzeCurrentFile() {
    const modal = document.getElementById('fileDetailsModal');
    const fileId = document.getElementById('detailFileId').textContent;
    if (fileId && fileId !== 'N/A') {
        analyzeFile(fileId);
    }
}

// Download file
function downloadFile(fileId) {
    window.location.href = `/api/files/${fileId}/download/`;
}

// Delete file
function deleteFile(fileId) {
    if (confirm('Are you sure you want to delete this file?')) {
        axios.post(`/api/files/${fileId}/delete/`, {
            headers: {
                'X-CSRFToken': getCsrfToken()
            }
        })
        .then(response => {
            if (response.data && response.data.success) {
                alert('File deleted successfully!');
                refreshFiles();
            } else {
                alert('Error deleting file: ' + (response.data.error || 'Unknown error'));
            }
        })
        .catch(error => {
            console.error('Delete error:', error);
            alert('Error deleting file. Please try again.');
        });
    }
}

// Delete selected files
function deleteSelectedFiles() {
    if (selectedFiles.length === 0) {
        alert('Please select at least one file to delete.');
        return;
    }
    
    const message = document.getElementById('filesDeleteMessage');
    if (message) {
        message.textContent = `Are you sure you want to delete ${selectedFiles.length} selected file(s)?`;
    }
    
    const modal = new bootstrap.Modal(document.getElementById('filesDeleteConfirmationModal'));
    modal.show();
}

// Confirm delete
function confirmDelete() {
    if (selectedFiles.length === 0) return;
    
    axios.post('/api/files/delete-multiple/', {
        file_ids: selectedFiles,
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => {
        if (response.data && response.data.success) {
            // Close modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('filesDeleteConfirmationModal'));
            modal.hide();
            
            // Clear selection
            selectedFiles = [];
            document.getElementById('selectAllFiles').checked = false;
            
            // Show success message
            alert(`${response.data.deleted_count || selectedFiles.length} files deleted successfully!`);
            
            // Refresh files
            refreshFiles();
        } else {
            alert('Error deleting files: ' + (response.data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Delete error:', error);
        alert('Error deleting files. Please try again.');
    });
}

// Export files list
function exportFilesList() {
    const filteredFiles = filterFilesByCriteria(currentFiles);
    
    if (filteredFiles.length === 0) {
        alert('No files to export.');
        return;
    }
    
    // Create CSV content
    const headers = ['ID', 'Name', 'Type', 'Category', 'Size', 'Quality', 'Uploaded', 'Description'];
    const rows = filteredFiles.map(file => [
        file.id || '',
        file.name || '',
        file.type || '',
        file.category || '',
        file.size || '',
        file.quality || '',
        formatDate(file.uploaded_at) || '',
        file.description || ''
    ]);
    
    const csvContent = [
        headers.join(','),
        ...rows.map(row => row.map(cell => `"${cell.toString().replace(/"/g, '""')}"`).join(','))
    ].join('\n');
    
    // Create download link
    const blob = new Blob([csvContent], { type: 'text/csv;charset=utf-8;' });
    const url = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = url;
    link.download = `files_export_${new Date().toISOString().slice(0, 10)}.csv`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
}

// Quick analyze selected
function quickAnalyzeSelected() {
    if (selectedFiles.length === 0) {
        alert('Please select at least one file to analyze.');
        return;
    }
    
    axios.post('/api/files/analyze-multiple/', {
        file_ids: selectedFiles,
        headers: {
            'X-CSRFToken': getCsrfToken()
        }
    })
    .then(response => {
        if (response.data && response.data.success) {
            alert(`${response.data.analyzed_count || selectedFiles.length} files analysis started successfully!`);
            refreshFiles();
        } else {
            alert('Error starting analysis: ' + (response.data.error || 'Unknown error'));
        }
    })
    .catch(error => {
        console.error('Analysis error:', error);
        alert('Error starting analysis. Please try again.');
    });
}

// Initialize when DOM is loaded
document.addEventListener('DOMContentLoaded', initializeFilesPage);