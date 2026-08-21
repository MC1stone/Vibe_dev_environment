# NIR Intelligence Platform - Workflow Integration

This document describes the comprehensive workflow integration for the NIR Intelligence Platform, which enables automated spectral analysis, Quarto report generation, and Django web interface integration.

## Overview

The NIR Intelligence Platform provides a complete solution for Near-Infrared (NIR) spectroscopy data analysis, including:

- **Automated Data Processing**: Handle multiple file types (CSV, JSON, HDF5, ZIP, images, audio)
- **Comprehensive Analysis**: Spectral quality assessment, metadata validation, calibration
- **Quarto Report Generation**: Automatic generation of comprehensive reports with analysis results and Python source code
- **Django Web Interface**: User-friendly interface for uploading files, managing workflows, and viewing results
- **Open Science Compliance**: Adherence to established NIR spectroscopy standards (ASTM E1655, ISO 12099, EURACHEM)

## Architecture

### Core Components

```
┌─────────────────────────────────────────────────────────────┐
│                    NIR Intelligence Platform                    │
├─────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐    ┌───────────┐ │
│  │  Data Upload     │    │  Workflow        │    │  Django   │ │
│  │  & Processing    │───▶│  Orchestrator    │───▶│  Web UI   │ │
│  └─────────────────┘    └─────────────────┘    └───────────┘ │
│           │                      │                      │        │
│           ▼                      ▼                      ▼        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌───────────┐ │
│  │  Data           │    │  Analysis        │    │  Report   │ │
│  │  Preparation    │───▶│  Crew           │───▶│  Display  │ │
│  │  Agent          │    │                 │    │           │ │
│  └─────────────────┘    └─────────────────┘    └───────────┘ │
│           │                      │                      │        │
│           ▼                      ▼                      ▼        │
│  ┌─────────────────┐    ┌─────────────────┐    ┌───────────┐ │
│  │  File           │    │  Spectral       │    │  HTML     │ │
│  │  Extraction     │    │  Analysis       │    │  Reports  │ │
│  │  & Validation   │    │  Agent          │    │           │ │
│  └─────────────────┘    └─────────────────┘    └───────────┘ │
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │  Metadata        │    │  Metadata       │                 │
│  │  Extraction      │───▶│  Quality        │                 │
│  └─────────────────┘    │  Assessment     │                 │
│                        │  Agent          │                 │
│                        └─────────────────┘                 │
│                                                                  │
│  ┌─────────────────┐    ┌─────────────────┐                 │
│  │  Quarto         │◀───│  Reporting      │                 │
│  │  Report         │    │  Agent          │                 │
│  │  Generation     │    └─────────────────┘                 │
│  └─────────────────┘                                          │
│                                                                  │
└─────────────────────────────────────────────────────────────┘
```

### Workflow Orchestrator

The `WorkflowOrchestrator` class is the central component that coordinates the complete analysis pipeline:

```python
from agents.workflow_orchestrator import WorkflowOrchestrator, WorkflowType

# Initialize orchestrator
orchestrator = WorkflowOrchestrator(
    input_directory="data/uploads",
    output_directory="data/output",
    temp_directory="data/temp",
    report_directory="reports",
    quarto_output_dir="output/quarto",
    html_output_dir="output/html"
)

# Execute workflow
workflow_result = orchestrator.execute_workflow(
    file_paths=["data/sample.csv", "data/metadata.json"],
    workflow_type=WorkflowType.COMPREHENSIVE_ANALYSIS
)
```

## Workflow Types

### 1. Standard Analysis
- Basic spectral analysis
- Metadata quality assessment
- Quality score calculation
- Parameter recommendations

### 2. Comprehensive Analysis
- All standard analysis features
- Advanced spectral processing
- Detailed metadata validation
- Calibration analysis
- Extensive recommendations

### 3. Quick Analysis
- Fast spectral quality check
- Basic metadata validation
- Minimal processing time

### 4. Metadata Only
- Focused metadata quality assessment
- Standards compliance checking
- Enhancement suggestions

### 5. Batch Processing
- Process multiple samples simultaneously
- Aggregated results and reports
- Batch statistics and summaries

## File Support

### Supported File Types

| Category | Extensions | Description |
|----------|------------|-------------|
| Spectral Data | `.csv`, `.json`, `.h5`, `.jdx`, `.spc`, `.txt` | Spectral intensity data |
| Metadata | `.json`, `.xml`, `.yaml`, `.yml` | Sample and instrument metadata |
| Images | `.png`, `.jpg`, `.jpeg` | Spectral images and visualizations |
| Audio | `.wav`, `.mp3` | Audio data (for specialized analysis) |
| Archives | `.zip` | Complete NIR project packages |

### File Processing

1. **Single Files**: Individual spectral data or metadata files
2. **Multiple Files**: Batch processing of multiple samples
3. **ZIP Archives**: Automatic extraction and processing of all contained files
4. **Mixed Types**: Simultaneous processing of different file types

## Quarto Report Generation

### Report Templates

The system includes comprehensive Quarto templates for different report types:

#### 1. Comprehensive Analysis Report (`comprehensive_analysis.qmd`)
- Executive summary with overall quality scores
- Detailed spectral analysis results
- Metadata quality assessment
- Visualizations (spectral plots, quality metrics)
- Python source code for analysis and preprocessing
- Recommendations and next steps
- Technical details and standards compliance

#### 2. Summary Report (`summary_report.qmd`)
- Workflow overview and statistics
- Sample results summary
- Quality distribution visualizations
- Generated outputs listing
- Issues and warnings summary

### Report Features

- **Automatic Generation**: Reports are automatically created from analysis results
- **Python Code Inclusion**: Complete analysis source code included in reports
- **Visualizations**: Automatic generation of spectral plots and quality charts
- **Standards Compliance**: Reports follow open science principles and established standards
- **Multiple Formats**: HTML, PDF, Word, and Markdown output support

### Example Report Structure

```
# Comprehensive NIR Spectral Analysis Report

## Executive Summary
- Overall Quality Score: 85.5 / 100
- Processing Time: 2.45 seconds
- Sample ID: sample_001

## Sample Information
- Sample ID, Request ID, Analysis Timestamp

## Spectral Analysis Results
- Quality Assessment (Grade, Score, Data Points)
- Signal Quality Metrics (Noise Level, SNR, Baseline Quality)
- Detected Issues
- Parameter Recommendations

## Metadata Quality Assessment
- Overall Metadata Quality
- Standards Compliance
- Missing Fields and Enhancements

## Visualizations
- Spectral Data Plot
- Quality Metrics Comparison

## Analysis Source Code
- Complete Python code for spectral analysis
- Data preprocessing code

## Recommendations and Next Steps
- Summary of recommendations
- Warnings and issues

## Technical Details
- Analysis configuration
- System information
- Data standards compliance
```

## Django Integration

### API Endpoints

#### Workflow Execution
- `POST /api/workflows/start/` - Start a new workflow
- `POST /api/workflows/upload-and-analyze/` - Upload files and start analysis
- `POST /api/workflows/standard/` - Start standard workflow
- `POST /api/workflows/comprehensive/` - Start comprehensive workflow
- `POST /api/workflows/quick/` - Start quick workflow

#### Workflow Management
- `GET /api/workflows/status/<workflow_id>/` - Get workflow status
- `GET /api/workflows/summary/<workflow_id>/` - Get workflow summary
- `GET /api/workflows/all/` - List all workflows
- `POST /api/workflows/cleanup/<workflow_id>/` - Clean up workflow files

#### Report Management
- `GET /api/reports/list/` - List all available reports
- `GET /api/reports/<report_filename>/` - Get a specific report

### Web Interface Views

#### Dashboard (`/` or `/dashboard/`)
- System status overview
- Quick actions (Upload Files, View Workflows, Documentation, Settings)
- Recent workflows list
- System information and getting started guide

#### Upload Form (`/upload/`)
- File selection (single or multiple)
- Workflow type selection
- Analysis options (calibration, report generation, source code inclusion)
- Upload progress tracking
- Results display

#### Workflow Results (`/workflows/<workflow_id>/`)
- Workflow status summary
- Workflow information
- Sample analysis results table
- Generated reports display
- Warnings and errors
- Action buttons (Refresh, Export, Cleanup, New Workflow)

#### Workflow List (`/workflows/`)
- All workflows overview
- Summary statistics
- Workflow history table
- Quick access to individual workflows

#### Workflow Details (`/workflows/<workflow_id>/details/`)
- Detailed workflow information
- Individual sample results
- Complete analysis data
- Technical details

### Template Structure

```
django_project/templates/
├── base.html                    # Base template with common layout
├── dashboard.html               # Main dashboard
├── upload_files.html            # File upload form
├── workflow_results.html        # Workflow results display
├── workflow_list.html           # Workflow list display
├── workflow_detail.html         # Workflow details display
└── reports/                      # Quarto report templates
    ├── comprehensive_analysis.qmd
    ├── summary_report.qmd
    ├── spectral_analysis.qmd
    ├── metadata_quality.qmd
    └── calibration.qmd
```

## Usage Examples

### Python API Usage

```python
# Test the complete workflow
from agents.workflow_orchestrator import WorkflowOrchestrator, WorkflowType

# Initialize orchestrator
orchestrator = WorkflowOrchestrator()

# Execute comprehensive workflow
workflow_result = orchestrator.execute_comprehensive_workflow([
    "data/sample1.csv",
    "data/sample2.json"
])

# Access results
print(f"Workflow ID: {workflow_result.workflow_id}")
print(f"Status: {workflow_result.status.value}")
print(f"Generated Reports: {len(workflow_result.generated_reports)}")
print(f"HTML Files: {workflow_result.html_files}")

# Get workflow status
workflow = orchestrator.get_workflow_status(workflow_result.workflow_id)

# List all workflows
all_workflows = orchestrator.get_all_workflows()
```

### Command Line Usage

```bash
# Run workflow integration test with sample data
python test_workflow_integration.py

# Test with specific files
python test_workflow_integration.py data/sample.csv data/metadata.json

# Run Django development server
python manage.py runserver

# Access the web interface
# Open http://localhost:8000 in your browser
```

### Web Interface Usage

1. **Start Analysis**:
   - Navigate to `/upload/`
   - Select files to upload
   - Choose workflow type
   - Configure options
   - Click "Start Analysis"

2. **View Results**:
   - After analysis completion, you'll be redirected to the results page
   - Or navigate to `/workflows/<workflow_id>/`

3. **Manage Workflows**:
   - View all workflows at `/workflows/`
   - Click on any workflow to view detailed results
   - Use action buttons to refresh, export, or cleanup

4. **View Reports**:
   - Generated HTML reports are accessible through the results page
   - Reports can be opened in the browser or downloaded

## Configuration

### Workflow Configuration

```python
# Configure workflow orchestrator
orchestrator = WorkflowOrchestrator(
    input_directory="path/to/input",
    output_directory="path/to/output",
    temp_directory="path/to/temp",
    report_directory="path/to/reports",
    quarto_output_dir="path/to/quarto",
    html_output_dir="path/to/html"
)
```

### Django Settings

```python
# settings.py

# Quarto configuration
QUARTO_ENABLED = True
QUARTO_PATH = "quarto"  # Path to Quarto executable
QUARTO_REPORTS_DIR = os.path.join(BASE_DIR, 'templates', 'reports')
QUARTO_OUTPUT_DIR = os.path.join(BASE_DIR, 'output', 'quarto')

# Workflow configuration
WORKFLOW_INPUT_DIR = os.path.join(BASE_DIR, 'data', 'uploads')
WORKFLOW_OUTPUT_DIR = os.path.join(BASE_DIR, 'data', 'output')
WORKFLOW_TEMP_DIR = os.path.join(BASE_DIR, 'data', 'temp')
```

## Testing

### Run Integration Tests

```bash
# Run the complete workflow integration test
python test_workflow_integration.py

# Test with specific files
python test_workflow_integration.py path/to/file1.csv path/to/file2.json

# Run individual component tests
python -m pytest tests/integration/test_workflow_integration.py
```

### Test Data

Sample test data can be created using the test script:

```python
from test_workflow_integration import create_sample_csv, create_sample_json

# Create sample CSV file
create_sample_csv("test_spectral_data.csv")

# Create sample JSON file
create_sample_json("test_metadata.json")
```

## Deployment

### Requirements

- Python 3.8+
- Django 4.0+
- CrewAI
- Quarto (for report generation)
- Required Python packages (see `requirements.txt`)

### Installation

```bash
# Clone the repository
git clone https://github.com/your-repo/nir-intelligence.git
cd nir-intelligence

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Install Quarto (if not already installed)
# Download from https://quarto.org/

# Run Django migrations
python manage.py migrate

# Start development server
python manage.py runserver
```

### Docker Deployment

```dockerfile
# Dockerfile
FROM python:3.9-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Quarto
RUN wget https://github.com/quarto-dev/quarto-cli/releases/download/v1.3.450/quarto-1.3.450-linux-amd64.deb \
    && dpkg -i quarto-1.3.450-linux-amd64.deb \
    && rm quarto-1.3.450-linux-amd64.deb

# Copy application code
COPY . .

# Expose port
EXPOSE 8000

# Start Django server
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## Standards Compliance

The NIR Intelligence Platform adheres to the following standards and guidelines:

### NIR Spectroscopy Standards
- **ASTM E1655**: Standard Practices for Infrared Multivariate Quantitative Analysis
- **ISO 12099**: Near Infrared Spectrometry
- **EURACHEM**: Guidelines for analytical chemistry

### Metadata Standards
- **NIR Public Database Standards**: Community-established metadata requirements
- **Dublin Core**: General metadata standards
- **ISO 19115**: Geographic information metadata

### Open Science Principles
- **Reproducibility**: Complete Python source code included in reports
- **Transparency**: Detailed analysis methodology and parameters
- **Data Quality**: Comprehensive quality assessment and validation
- **Standards Compliance**: Adherence to established scientific standards

## Privacy and Security

### Data Handling
- **Local Processing**: All data is processed locally by default
- **Privacy Levels**: Configurable privacy settings (Local Only, Private Federated, Public Federated)
- **Data Retention**: Temporary files are automatically cleaned up
- **Secure Storage**: Generated reports are stored securely

### User Control
- **Explicit Consent**: Users must explicitly enable federated learning
- **Data Ownership**: Users retain full ownership of their data
- **Access Control**: Reports are only accessible to the user who created them
- **Cleanup Options**: Users can cleanup workflow files while keeping reports

## Future Enhancements

### Planned Features
1. **Federated Learning Integration**: FlowerAI integration for collaborative model training
2. **Advanced Visualization**: Interactive charts and 3D visualizations
3. **Machine Learning**: Automated calibration and prediction models
4. **Database Integration**: Weaviate, FAISS, and PostgreSQL for data management
5. **ILIAS Integration**: Deep integration with the ILIAS learning platform
6. **Mobile Interface**: Responsive design for mobile devices
7. **API Documentation**: Comprehensive API documentation with Swagger/OpenAPI
8. **User Management**: Advanced user authentication and authorization

### Performance Optimizations
1. **Batch Processing**: Optimized processing of large datasets
2. **Parallel Analysis**: Multi-threaded analysis for improved performance
3. **Caching**: Intelligent caching of analysis results
4. **Incremental Processing**: Process data as it's uploaded for real-time feedback

## Support

### Troubleshooting

**Issue: Quarto not found**
- Solution: Install Quarto from https://quarto.org/
- Ensure Quarto is in your system PATH

**Issue: Missing Python dependencies**
- Solution: Run `pip install -r requirements.txt`

**Issue: File upload failed**
- Solution: Check file permissions and available disk space
- Ensure files are within the maximum size limit (100MB by default)

**Issue: Analysis taking too long**
- Solution: Try using Quick Analysis workflow type
- Reduce the number of files in batch processing
- Check system resources (CPU, memory)

### Getting Help

1. **Documentation**: Refer to this document and the platform documentation
2. **Community**: Join the NIR Intelligence community forum
3. **Bug Reports**: Submit issues on the GitHub repository
4. **Feature Requests**: Submit feature requests on the GitHub repository

## Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Follow the existing code style** and conventions
3. **Add tests** for new functionality
4. **Update documentation** for any changes
5. **Submit a pull request** with a clear description of your changes

### Development Setup

```bash
# Clone the repository
git clone https://github.com/your-repo/nir-intelligence.git
cd nir-intelligence

# Create feature branch
git checkout -b feature/your-feature-name

# Make your changes

# Run tests
python -m pytest tests/

# Run linting
flake8 agents/ django_project/

# Commit your changes
git commit -m "Add your feature description"

# Push to the branch
git push origin feature/your-feature-name

# Submit a pull request
```

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- **CrewAI**: For the powerful orchestration framework
- **Quarto**: For the excellent documentation and report generation
- **Django**: For the robust web framework
- **Open Science Community**: For the standards and best practices
- **All Contributors**: For their valuable contributions to the project

---

*This documentation was generated as part of the NIR Intelligence Platform workflow integration.*