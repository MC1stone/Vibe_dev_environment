# NIR Intelligence Platform

## Open Science Spectral Analysis System

A comprehensive platform for analyzing NIR (Near-Infrared) spectral data from any spectrometer, including DIY devices. Built with Django, CrewAI, Qdrant, Faiss, PostgreSQL, Quarto, n8n, and MCP.

## 🎯 Platform Overview

The NIR Intelligence Platform enables Open Science participants to:
- Upload and analyze spectral data from any spectrometer
- Evaluate metadata quality against international standards
- Generate comprehensive Quarto reports with analysis and source code
- Manage trial data using vector databases (Qdrant, Faiss) and PostgreSQL
- Interact with AI agents via CrewAI orchestration
- Visualize results through Django web interface with HSWT.de styling

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        NIR Intelligence Platform                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  Django UI   │    │  MCP Server  │    │   CrewAI Orchestrator│  │
│  │  (Frontend)  │◄──►│  (Orchestration) │◄──►│   (Analysis Engine)  │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│           ▲                  ▲                  ▲                │
│           │                  │                  │                │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────┐  │
│  │  Quarto     │    │  n8n        │    │   Spectral Agents    │  │
│  │  Reports    │    │  Workflows   │    │   (Specialized)      │  │
│  └─────────────┘    └─────────────┘    └─────────────────────┘  │
│           ▲                  ▲                  ▲                │
│           │                  │                  │                │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Data Management Layer                      │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │  │
│  │  │ PostgreSQL  │  │  Qdrant      │  │  Faiss               │  │  │
│  │  │ (Relational)│  │  (Vector DB) │  │  (Vector Index)      │  │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘  │  │
│  └─────────────────────────────────────────────────────────────┘  │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────────┐  │
│  │                    Docker Network                              │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │  │
│  │  │  Django     │  │  Ollama      │  │  n8n                │    │  │
│  │  │  Container  │  │  (Mistral)   │  │  Container          │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘    │  │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐    │  │
│  │  │ PostgreSQL  │  │  Qdrant      │  │  Faiss              │    │  │
│  │  └─────────────┘  └─────────────┘  └─────────────────────┘    │  │
│  └─────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────┘
```

## 📦 Components

### 1. **Django Web Application**
- User interface with HSWT.de styling
- File upload and management
- Analysis dashboard
- Report generation interface
- Chat interface for CrewAI agents

### 2. **MCP Server**
- Orchestrates communication between all agents and resources
- Manages tool access and permissions
- Handles federated learning data sharing

### 3. **CrewAI Orchestration**
- Spectral Data Analysis Agent
- Metadata Quality Agent
- Calibration Agent
- Reporting Agent
- Quality Assurance Agent

### 4. **Data Management**
- **PostgreSQL**: Trial data and documentation
- **Qdrant**: Vector search for spectral patterns
- **Faiss**: Local vector indexing for fast similarity search

### 5. **n8n Workflows**
- Interactive data processing pipelines
- User prompt-based analysis
- Automated report generation

### 6. **Quarto Reporting**
- HTML reports with embedded Python source
- Spectral analysis visualizations
- Metadata quality assessments
- Calibration formulas and recommendations

### 7. **Docker Infrastructure**
- Local network for all services
- Ollama with Mistral model
- Easy deployment and scaling

## 🚀 Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.8+
- Node.js (for n8n)

### Installation

1. **Clone the repository:**
```bash
git clone https://github.com/MC1stone/Vibe_dev_environment
cd Vibe_dev_environment/nir_platform
```

2. **Set up Docker network:**
```bash
docker-compose -f docker/docker-compose.yml up -d
```

3. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

4. **Run Django application:**
```bash
cd django_app
python manage.py migrate
python manage.py runserver
```

5. **Access the platform:**
- Django UI: http://localhost:8000
- n8n: http://localhost:5678
- Ollama: http://localhost:11434

## 📁 Project Structure

```
nir_platform/
├── django_app/                 # Django frontend application
│   ├── nir_platform/          # Django project
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── wsgi.py
│   ├── analysis/              # Analysis app
│   │   ├── models.py
│   │   ├── views.py
│   │   ├── templates/
│   │   └── static/
│   ├── uploads/               # File uploads
│   └── manage.py
│
├── agents/                    # Specialized agents
│   ├── spectral_analysis_agent.py
│   ├── metadata_quality_agent.py
│   ├── calibration_agent.py
│   ├── reporting_agent.py
│   └── mcp_server.py
│
├── workflows/                 # n8n workflows
│   ├── spectral_analysis.json
│   ├── metadata_evaluation.json
│   └── report_generation.json
│
├── reports/                   # Quarto report templates
│   ├── spectral_analysis.qmd
│   ├── metadata_quality.qmd
│   └── calibration_report.qmd
│
├── docker/                    # Docker configurations
│   ├── docker-compose.yml
│   ├── Dockerfile.django
│   ├── Dockerfile.n8n
│   └── ollama-config/
│
├── configs/                   # Configuration files
│   ├── crewai_config.yaml
│   ├── database_config.yaml
│   └── vector_db_config.yaml
│
├── scripts/                   # Utility scripts
│   ├── data_processor.py
│   ├── calibration_tools.py
│   └── quality_metrics.py
│
├── docs/                      # Documentation
│   ├── diy_spectrometer.md
│   ├── api_reference.md
│   └── user_guide.md
│
└── tests/                     # Test suite
    ├── test_spectral_analysis.py
    ├── test_metadata_quality.py
    └── test_integration.py
```

## 🎯 Key Features

### Spectral Data Analysis
- Support for any spectrometer file format
- Automatic detection of spectrometer type
- Wavelength calibration and correction
- Baseline correction and noise reduction
- Peak detection and analysis
- Spectrometer issue detection (shift, drift, etc.)

### Metadata Quality Assessment
- Standard compliance checking (ISO, ASTM, etc.)
- Completeness scoring
- Quality grading system
- Enhancement proposals
- Federated learning compatibility check

### Calibration System
- Multi-point calibration formulas
- Spectrometer-specific parameter recommendations
- Drift compensation
- Cross-spectrometer normalization

### Reporting
- Quarto-based HTML reports
- Embedded Python source code
- Interactive visualizations
- Downloadable analysis packages
- Federated learning opt-in system

### User Interface
- HSWT.de styled design
- Drag-and-drop file upload
- Real-time analysis progress
- Interactive chat with AI agents
- Clear, intuitive navigation

## 🔧 Technical Stack

- **Frontend**: Django, HTML5, CSS3, JavaScript
- **Backend**: Python, FastAPI (for MCP)
- **AI/ML**: CrewAI, Mistral (via Ollama)
- **Databases**: PostgreSQL, Qdrant, Faiss
- **Workflow**: n8n
- **Reporting**: Quarto
- **Containerization**: Docker
- **Styling**: HSWT.de design system

## 📊 Data Flow

1. **Upload**: User uploads spectral data (files, zip, or individual components)
2. **Parse**: System extracts spectral data and metadata
3. **Analyze**: CrewAI agents process data through specialized workflows
4. **Evaluate**: Metadata quality and spectral integrity are assessed
5. **Calibrate**: Spectrometer-specific calibration is applied
6. **Report**: Quarto generates comprehensive HTML report
7. **Store**: Results saved to PostgreSQL, vectors to Qdrant/Faiss
8. **Present**: Django displays results with interactive visualizations

## 🎓 DIY Spectrometer Support

The platform includes:
- Step-by-step DIY spectrometer building guide
- Calibration procedures for DIY devices
- Quality assessment for non-professional equipment
- Recommendations for improvement
- Community sharing of DIY configurations

## 🔒 Privacy & Security

- All data processed locally by default
- Federated learning requires explicit user consent
- No data shared without permission
- Local Ollama installation ensures data privacy
- Docker network isolates all services

## 🤝 Open Source

This platform is open source and encourages:
- Community contributions
- Extension of supported file formats
- Addition of new analysis methods
- Improvement of calibration algorithms
- Expansion of metadata standards

## 📞 Support

- Documentation: See `/docs` directory
- Issues: GitHub Issues
- Community: Open Science forums

## 📄 License

MIT License - Open for academic and commercial use

---

**Built with the Agent Framework** - Multi-agent system for complex software development
