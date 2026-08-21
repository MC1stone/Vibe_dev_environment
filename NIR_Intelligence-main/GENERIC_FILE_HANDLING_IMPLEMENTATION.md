# Generic File Handling Implementation

## Overview

This implementation extends the NIR Intelligence Platform to handle **any uploaded file type** for metadata extraction, analysis, and processing. The system generalizes the existing spectral-specific workflow while maintaining backward compatibility with existing spectral data processing.

## Key Components

### 1. GenericFileHandlerAgent (`agents/generic_file_handler_agent.py`)

The core agent that processes any file type with the following capabilities:

#### Features:
- **Automatic File Categorization**: Detects file types based on extension, MIME type, and content
- **Comprehensive Metadata Extraction**: Extracts basic and type-specific metadata from all supported file types
- **Content Analysis**: Provides specialized analysis based on file category
- **Quality Assessment**: Evaluates file quality and integrity
- **Batch Processing**: Handles multiple files efficiently
- **Custom Handler Support**: Allows registration of custom handlers for specific file types
- **Report Generation**: Creates comprehensive processing reports

#### Supported File Categories:
- **Spectral**: `.csv`, `.json`, `.h5`, `.jdx`, `.spc`
- **Tabular**: `.csv`, `.xlsx`, `.xls`, `.parquet`, `.feather`
- **Text**: `.txt`, `.json`, `.xml`, `.yaml`, `.yml`, `.md`
- **Image**: `.png`, `.jpg`, `.jpeg`, `.gif`, `.tiff`, `.webp`, `.svg`
- **Audio**: `.wav`, `.mp3`, `.ogg`, `.flac`
- **Video**: `.mp4`, `.avi`, `.mov`, `.wmv`
- **Archive**: `.zip`, `.tar`, `.gz`, `.rar`, `.7z`
- **Document**: `.pdf`, `.docx`, `.doc`, `.pptx`
- **Binary**: `.bin`, `.dat`
- **Unknown**: Any other file type

#### Type-Specific Metadata Extracted:
- **Spectral/Tabular**: Number of rows, columns, column names, data types
- **Text**: Number of lines, words, characters, content type
- **Image**: Dimensions, channels, format, EXIF data
- **Audio**: Duration, sample rate, channels, bit rate
- **Video**: Duration, resolution, frame rate, codec
- **Archive**: Contents list, number of files

#### Handler Registry System:
- Pluggable architecture for file type handlers
- Priority-based handler selection
- Support for custom handler registration
- Default handlers for all supported categories

### 2. Django Models (`django_project/core/models.py`)

#### GenericFile Model:
- Stores any file type with comprehensive metadata
- Supports file relationships (e.g., linking to spectral data)
- Tracks processing status and quality metrics
- Includes integrity hashes (MD5, SHA1, SHA256)
- Stores processing results and analysis outputs

#### Key Fields:
- `file_category`: Automatic categorization of file type
- `content_metadata`: Extracted metadata from file content
- `quality_score` and `quality_grade`: Quality assessment results
- `processing_status`: Current processing state
- `analysis_results`: Results from content analysis
- `recommendations`: Suggestions for file processing
- Type-specific fields for each category (image dimensions, audio duration, etc.)

### 3. Django API Views (`django_project/api/file_views.py`)

#### Endpoints:
- `GET /api/files/` - List all files for current user
- `GET /api/files/<file_id>/` - Get file details
- `POST /api/files/upload/` - Upload files with metadata
- `POST /api/files/<file_id>/delete/` - Delete a file
- `POST /api/files/delete-multiple/` - Delete multiple files
- `GET /api/files/<file_id>/download/` - Download a file
- `POST /api/files/<file_id>/analyze/` - Analyze a file
- `POST /api/files/analyze-multiple/` - Analyze multiple files
- `GET /api/files/categories/` - Get supported categories and extensions
- `GET /api/files/statistics/` - Get file statistics

#### Features:
- Automatic file processing on upload (optional)
- File metadata extraction and storage
- File type detection and categorization
- Batch operations for multiple files
- Comprehensive error handling
- Progress tracking

### 4. Django Serializers (`django_project/api/serializers.py`)

#### Serializers Added:
- `GenericFileSerializer`: Full file serialization
- `GenericFileUploadSerializer`: File upload request validation
- `GenericFileListSerializer`: Lightweight file listing

### 5. Django URLs (`django_project/api/file_urls.py` and `django_project/nir_web/urls.py`)

- Added file management API endpoints
- Added files page template URL
- Integrated with existing URL structure

### 6. Frontend Template (`django_project/templates/files.html`)

#### Features:
- Responsive file management interface
- File gallery with thumbnails and previews
- File table with sorting and filtering
- Drag-and-drop file upload
- File category visualization
- File details modal with comprehensive information
- Batch operations (delete, analyze, export)
- Real-time progress indicators

#### File Type Icons and Colors:
- Each file category has unique icon and color scheme
- Visual distinction between different file types
- Quality badges for file status

### 7. JavaScript (`django_project/static/js/files.js`)

#### Features:
- File upload with drag-and-drop support
- File type detection and categorization
- File filtering by category and validity
- Batch operations
- File preview generation
- Real-time updates
- Error handling
- Export functionality

## Implementation Details

### File Processing Pipeline

1. **Upload**: Files are uploaded via API with optional metadata
2. **Categorization**: Files are automatically categorized by type
3. **Metadata Extraction**: Basic and type-specific metadata is extracted
4. **Content Analysis**: Files are analyzed based on their category
5. **Quality Assessment**: Files are evaluated for quality and integrity
6. **Storage**: Files and metadata are stored in the database
7. **Reporting**: Comprehensive reports are generated

### Integration with Existing System

- **Backward Compatibility**: Existing spectral data processing continues to work
- **Agent Integration**: Uses existing agent infrastructure
- **Database Integration**: Extends existing models without breaking changes
- **API Integration**: Adds new endpoints without affecting existing ones

### File Type Detection Algorithm

1. **Extension-Based**: Primary detection method using file extensions
2. **MIME Type**: Uses python-magic library for content-based detection (optional)
3. **Fallback**: Uses mimetypes module for basic MIME type guessing
4. **Default**: Falls back to "unknown" category

### Handler Selection

1. **Category-Based**: Handlers are selected based on file category
2. **Priority-Based**: Higher priority handlers are tried first
3. **Fallback**: Generic handler for unknown file types
4. **Custom**: Support for custom handler registration

## Usage Examples

### Python API Usage

```python
from agents.generic_file_handler_agent import GenericFileHandlerAgent

# Initialize agent
agent = GenericFileHandlerAgent(
    input_directory='path/to/files',
    output_directory='path/to/output',
    max_file_size=500*1024*1024  # 500MB
)

# Process single file
result = agent._process_single_file('path/to/file.csv')

# Process batch of files
results = agent._process_batch(['file1.csv', 'file2.json', 'file3.png'])

# Execute full pipeline
output = agent.execute({
    'input_directory': 'path/to/files',
    'generate_report': True
})

# Get supported file types
categories = agent.get_supported_categories()
extensions = agent.get_supported_extensions()

# Register custom handler
def my_custom_handler(file_path, metadata):
    # Custom processing logic
    return FileProcessingResult(
        file_path=file_path,
        success=True,
        file_metadata=metadata,
        analysis_results={'custom': True}
    )

agent.register_custom_handler(FileCategory.TEXT, my_custom_handler)
```

### REST API Usage

```bash
# Upload a file
curl -X POST -F "files=@test.csv" -F "description=Test file" \
  -F "auto_analyze=true" http://localhost:8000/api/files/upload/

# List all files
curl -X GET http://localhost:8000/api/files/

# Get file details
curl -X GET http://localhost:8000/api/files/<file_id>/

# Analyze a file
curl -X POST http://localhost:8000/api/files/<file_id>/analyze/

# Download a file
curl -X GET http://localhost:8000/api/files/<file_id>/download/ > file.csv

# Delete a file
curl -X POST http://localhost:8000/api/files/<file_id>/delete/
```

### Frontend Usage

```javascript
// Upload files
uploadFiles();

// Load files
loadFiles();

// Filter files
filterFiles();

// Analyze selected files
quickAnalyzeSelected();

// Delete selected files
deleteSelectedFiles();

// Export files list
exportFilesList();
```

## Testing

A comprehensive test suite is provided in `test_generic_file_handler.py`:

```bash
# Run all tests
python test_generic_file_handler.py

# Test specific components
python -c "from agents.generic_file_handler_agent import GenericFileHandlerAgent; print('Import successful')"
```

### Test Coverage:
- File type detection
- Handler registry functionality
- Individual file processing
- Batch processing
- Execute method
- Error handling

## Files Modified/Created

### New Files Created:
- `agents/generic_file_handler_agent.py` - Main agent implementation
- `agents/generic_file_handler_agent.json` - Agent configuration
- `django_project/api/file_views.py` - API views for file management
- `django_project/api/file_urls.py` - URL routing for file endpoints
- `django_project/templates/files.html` - Frontend template
- `django_project/static/js/files.js` - Frontend JavaScript
- `test_generic_file_handler.py` - Test suite

### Files Modified:
- `agents/__init__.py` - Added GenericFileHandlerAgent to registry
- `django_project/core/models.py` - Added GenericFile model
- `django_project/api/serializers.py` - Added file serializers
- `django_project/nir_web/urls.py` - Added file URLs

## Dependencies

### Required:
- pandas
- numpy

### Optional (for enhanced functionality):
- python-magic (for MIME type detection)
- Pillow (for image metadata extraction)
- librosa (for audio metadata extraction)
- openpyxl/xlrd (for Excel file support)
- pyarrow/fastparquet (for Parquet/Feather support)

## Configuration

### Agent Configuration:
```python
agent = GenericFileHandlerAgent(
    input_directory='data/uploads',
    output_directory='data/processed',
    temp_directory='data/temp',
    max_file_size=500*1024*1024,  # 500MB
    batch_size=100
)
```

### Django Settings:
```python
# File upload settings
MAX_FILE_UPLOAD_SIZE = 500 * 1024 * 1024  # 500MB
FILE_UPLOAD_HANDLERS = ['django.core.files.uploadhandler.TemporaryFileUploadHandler']

# Media settings
MEDIA_ROOT = os.path.join(BASE_DIR, 'media')
MEDIA_URL = '/media/'
```

## Benefits

1. **Generalization**: Extends spectral-specific system to handle any file type
2. **Flexibility**: Pluggable architecture for custom file handlers
3. **Comprehensive**: Extracts rich metadata from all supported file types
4. **Integration**: Seamlessly integrates with existing NIR platform
5. **User Experience**: Provides consistent interface for all file types
6. **Scalability**: Batch processing and efficient resource usage
7. **Maintainability**: Clean separation of concerns and modular design

## Future Enhancements

1. **Additional File Types**: Support for more specialized formats
2. **Advanced Analysis**: More sophisticated content analysis for each file type
3. **Machine Learning**: AI-based file classification and analysis
4. **Cloud Integration**: Support for cloud storage providers
5. **Real-time Processing**: Streaming processing for large files
6. **Collaboration**: Multi-user file sharing and collaboration
7. **Versioning**: File version control and history tracking

## Migration Guide

### For Existing Users:
1. The existing spectral data processing continues to work unchanged
2. New file types can be uploaded and processed using the same interface
3. Existing spectra can be accessed through both the old and new interfaces

### For Developers:
1. Use the GenericFileHandlerAgent for new file processing needs
2. Register custom handlers for specialized file types
3. Extend the GenericFile model for additional metadata as needed
4. Use the provided API endpoints for file management

## Support

This implementation provides comprehensive error handling, logging, and debugging information. Issues can be reported through the standard NIR platform support channels.

## License

This implementation is provided under the same license as the NIR Intelligence Platform (MIT License).