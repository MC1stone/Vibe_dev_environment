# NIR Intelligence Platform - User Manual

**Version**: 1.0.0  
**Last Updated**: August 6, 2026  
**Target Audience**: Users with medium IT experience  

---

## 📖 Table of Contents

1. [Introduction](#-introduction)
2. [System Requirements](#-system-requirements)
3. [Installation Options](#-installation-options)
4. [Ventoy USB Stick Setup](#-ventoy-usb-stick-setup)
5. [Ansible Deployment](#-ansible-deployment)
6. [Running the System](#-running-the-system)
7. [Using the NIR Intelligence Platform](#-using-the-nir-intelligence-platform)
8. [Agent Overview](#-agent-overview)
9. [Troubleshooting](#-troubleshooting)
10. [Maintenance](#-maintenance)

---

## 🎯 Introduction

Welcome to the **NIR Intelligence Platform** - a comprehensive solution for analyzing Near-Infrared (NIR) spectral data. This platform enables Open Science participants to analyze spectra collected with any type of spectrometer, including DIY devices.

### What You Can Do

- **Analyze Spectral Data**: Process and analyze NIR spectra from various file formats
- **Detect Instrument Issues**: Identify wavelength shifts, intensity drifts, and baseline problems
- **Optimize Parameters**: Get recommendations for optimal spectrometer settings
- **Quality Assessment**: Evaluate data quality with comprehensive metrics
- **Federated Learning**: Contribute to and benefit from a collaborative knowledge base

### Platform Components

- **Django Web Interface**: User-friendly interface with HSWT.de styling
- **Agent Framework**: Specialized agents for different analysis tasks
- **CrewAI Orchestration**: Intelligent workflow management
- **Quarto Reporting**: Professional report generation
- **FlowerAI**: Federated learning capabilities

---

## 💻 System Requirements

### Hardware Requirements

| Component | Minimum | Recommended | Development |
|-----------|---------|-------------|-------------|
| **CPU** | 2 cores | 4+ cores | 8+ cores |
| **RAM** | 4 GB | 8 GB | 16+ GB |
| **Storage** | 20 GB | 50 GB SSD | 100+ GB SSD |
| **USB Port** | USB 2.0 | USB 3.0+ | USB 3.0+ |
| **Display** | 1280x720 | 1920x1080 | 1920x1080+ |

### Software Requirements

#### For Ventoy USB Stick Setup
- **Operating System**: Windows 7+, macOS 10.12+, or Linux
- **Ventoy**: Latest version (included in setup)
- **USB Drive**: 16GB+ USB stick (will be formatted!)

#### For Local Installation
- **Operating System**: Ubuntu 22.04 LTS or Windows 10/11
- **Python**: 3.10+ (3.11 recommended)
- **Docker**: 20.10+ (optional, for containerized deployment)
- **Git**: Latest version

#### For Development
- **IDE**: VS Code, PyCharm, or similar
- **Additional Tools**: Ansible 2.14+, Node.js 18+ (for frontend development)

---

## 🚀 Installation Options

You have **three main ways** to install and run the NIR Intelligence Platform:

### Option 1: Ventoy USB Stick (Recommended for First-Time Users)
**Best for**: Users who want a portable, self-contained system that runs from USB.

### Option 2: Local Installation with Ansible
**Best for**: Users who want a permanent installation on their computer.

### Option 3: Docker Container
**Best for**: Advanced users who prefer containerized environments.

---

## 🔧 Ventoy USB Stick Setup

This is the **recommended method** for first-time users. It creates a portable system that runs directly from a USB stick.

### What You Need
- A **16GB or larger USB drive** (all data will be erased!)
- A computer with **USB port** and **internet connection**
- **Administrator/root privileges** (for Ventoy installation)

### Step 1: Download Ventoy

1. Go to [https://www.ventoy.net](https://www.ventoy.net)
2. Download the latest version for your operating system
3. Extract the downloaded file

### Step 2: Install Ventoy on USB Drive

#### On Windows:
```cmd
# Navigate to Ventoy directory
cd path\to\ventoy

# Run Ventoy2Disk (replace X with your USB drive letter)
Ventoy2Disk.exe -i -g /WAIT /REPLACE
```

#### On macOS/Linux:
```bash
# Navigate to Ventoy directory
cd /path/to/ventoy

# Make script executable
chmod +x Ventoy2Disk.sh

# Run Ventoy2Disk (replace /dev/sdX with your USB device)
sudo ./Ventoy2Disk.sh -i /dev/sdX
```

⚠️ **WARNING**: This will **ERASE ALL DATA** on your USB drive! Make sure you select the correct device.

### Step 3: Copy NIR Intelligence Platform Files

1. **Download the NIR Intelligence Platform** from the repository
2. **Copy the entire project folder** to your Ventoy USB stick
3. **Create a `nir_config` folder** on the USB stick (if it doesn't exist)

Your USB stick should now have:
```
USB Drive/
├── ventoy/          # Ventoy system files
├── NIR_Mistral/     # NIR Intelligence Platform
│   ├── ansible/     # Ansible playbooks
│   ├── agents/      # Agent implementations
│   ├── django_app/  # Django application
│   ├── docs/        # Documentation
│   └── ...
└── nir_config/      # Configuration files
```

### Step 4: Boot from Ventoy USB Stick

1. **Insert the USB stick** into your computer
2. **Restart your computer**
3. **Enter BIOS/UEFI** (usually by pressing F2, F12, DEL, or ESC during boot)
4. **Select the USB drive** as boot device
5. **Choose Ventoy** from the boot menu
6. **Select "Local Disk"** to browse files
7. **Navigate to NIR_Mistral/ansible/ventoy_setup**

---

## 🎭 Ansible Deployment

The NIR Intelligence Platform uses **Ansible** for automated deployment. This allows you to set up the entire system with a single command.

### Ansible Setup Options

#### Option A: Quick Setup (Recommended)
For users who want the simplest installation:

```bash
# Navigate to the ansible directory
cd NIR_Mistral/ansible

# Run the quick setup playbook
ansible-playbook quick_setup.yml
```

This will:
- Install all required dependencies
- Set up Python virtual environment
- Install NIR platform packages
- Configure basic settings

#### Option B: Ventoy-Specific Setup
For users running from Ventoy USB stick:

```bash
# Navigate to Ventoy setup directory
cd NIR_Mistral/ansible/ventoy_setup

# Run Ventoy-specific playbook
ansible-playbook nir_mistral_ventoy.yml
```

This playbook is **optimized for Ventoy** and includes:
- Portable Python installation
- Configuration file setup
- USB-specific optimizations

#### Option C: Full Custom Setup
For advanced users who want full control:

```bash
# Navigate to ansible directory
cd NIR_Mistral/ansible

# Edit inventory file to customize your setup
nano inventory.ini

# Run the main deployment playbook
ansible-playbook main_deployment.yml -i inventory.ini
```

### Ansible Playbooks Overview

| Playbook | Purpose | Best For |
|----------|---------|----------|
| `quick_setup.yml` | Fast, simple installation | Beginners |
| `nir_mistral_ventoy.yml` | Ventoy USB optimization | USB users |
| `main_deployment.yml` | Full custom deployment | Advanced users |
| `django_setup.yml` | Django application setup | Web interface |
| `agent_deployment.yml` | Agent framework setup | Custom agent config |
| `federated_learning.yml` | FlowerAI setup | Federated learning |

### Ansible Configuration Files

The main configuration is in `ansible/group_vars/all.yml`:

```yaml
# Python version
python_version: "3.11"

# Project settings
project_name: "NIR_Mistral"
project_dir: "/opt/{{ project_name }}"

# Django settings
django_port: 8000
django_debug: false

# Database settings (SQLite by default)
database_engine: "django.db.backends.sqlite3"
database_name: "{{ project_dir }}/db.sqlite3"

# Federated learning
flower_server_enabled: true
flower_server_port: 50051
```

### Running Ansible Playbooks

#### Basic Command
```bash
ansible-playbook playbook_name.yml
```

#### With Inventory File
```bash
ansible-playbook -i inventory.ini playbook_name.yml
```

#### With Extra Variables
```bash
ansible-playbook playbook_name.yml -e "django_port=8080 flower_server_enabled=false"
```

#### Check Mode (Dry Run)
```bash
ansible-playbook playbook_name.yml --check
```

#### Verbose Mode
```bash
ansible-playbook playbook_name.yml -v
```

---

## ▶️ Running the System

### Starting the Django Web Interface

#### Method 1: Using Ansible (Recommended)
```bash
# Start the Django development server
ansible-playbook start_django.yml
```

#### Method 2: Manual Start
```bash
# Navigate to Django project directory
cd NIR_Mistral/django_app

# Activate virtual environment (if using one)
source venv/bin/activate  # Linux/macOS
# OR
venv\Scripts\activate  # Windows

# Install dependencies (if not already done)
pip install -r requirements.txt

# Run migrations
python manage.py migrate

# Create superuser (admin account)
python manage.py createsuperuser

# Start development server
python manage.py runserver 0.0.0.0:8000
```

#### Method 3: Production Server (Gunicorn)
```bash
# Install Gunicorn
pip install gunicorn

# Start Gunicorn server
gunicorn --bind 0.0.0.0:8000 --workers 4 nir_mistral.wsgi:application
```

### Accessing the Web Interface

After starting the server:

1. **Open your web browser**
2. **Navigate to**: `http://localhost:8000` (or your server's IP address)
3. **Log in** with your credentials (if you created a superuser)

### Using the Command Line Interface

#### Running Individual Agents

```bash
# Example: Run ShiftDetectorAgent
python -c "
from agents.shift_detector_agent import ShiftDetectorAgent
import numpy as np

# Create agent
agent = ShiftDetectorAgent()

# Sample data
wavelengths = list(range(700, 2500, 10))
intensities = [abs(np.sin(i * 0.01)) for i in range(700, 2500, 10)]

# Run analysis
context = {
    'sample_id': 'test_001',
    'spectral_data': {
        'wavelengths': wavelengths,
        'intensities': intensities,
        'sample_id': 'test_001'
    }
}

result = agent.execute(context)
print('Analysis complete:', result.status.name)
"
```

#### Running Parameter Recommender

```bash
# Example: Get parameter recommendations
python -c "
from agents.parameter_recommender_agent import ParameterRecommenderAgent
import numpy as np

# Create agent
agent = ParameterRecommenderAgent()

# Sample data and configuration
wavelengths = list(range(700, 2500, 10))
intensities = [abs(np.sin(i * 0.01)) * 1000 for i in range(700, 2500, 10)]

context = {
    'sample_id': 'test_002',
    'spectral_data': {
        'wavelengths': wavelengths,
        'intensities': intensities,
        'sample_id': 'test_002'
    },
    'current_config': {
        'integration_time': 100,
        'scans_to_average': 10,
        'gain': 20
    }
}

result = agent.execute(context)
print('Recommendations:', len(result.data['report']['parameter_recommendations']))
"
```

### Running the Full Analysis Pipeline

```bash
# Run the complete NIR analysis crew
python -c "
from agents.nir_analysis_crew import NIRAnalysisCrew

# Create crew
crew = NIRAnalysisCrew()

# Run analysis on your spectral data
result = crew.run_analysis('path/to/your/spectral_data.json')

print('Analysis complete!')
print('Report generated:', result.report_path)
"
```

---

## 🎯 Using the NIR Intelligence Platform

### Step 1: Upload Your Data

1. **Supported File Formats**:
   - **Spectral Data**: CSV, JSON, TXT, JDX, SPD
   - **Audio Files**: WAV, MP3, FLAC (for audio-based spectra)
   - **Image Files**: PNG, JPG, TIFF (for image-based spectra)
   - **Metadata**: JSON, XML, CSV

2. **Upload Methods**:
   - **Web Interface**: Drag and drop files or use file picker
   - **API**: POST to `/api/upload/` endpoint
   - **Command Line**: Use `python manage.py import_data /path/to/files`

### Step 2: Select Analysis Type

The platform offers several analysis options:

| Analysis Type | Description | Best For |
|---------------|-------------|----------|
| **Quick Analysis** | Basic spectral analysis | First-time users |
| **Comprehensive Analysis** | Full analysis with all agents | Detailed results |
| **Shift Detection** | Wavelength shift and drift analysis | Instrument calibration |
| **Parameter Optimization** | Spectrometer parameter recommendations | Performance tuning |
| **Quality Assessment** | Data quality evaluation | Quality control |
| **Federated Learning** | Contribute to collaborative model | Open science |

### Step 3: Run Analysis

1. **Click "Start Analysis"** button
2. **Wait for processing** (progress bar will show status)
3. **Review results** in the web interface

### Step 4: View Reports

- **HTML Reports**: Interactive reports in your browser
- **PDF Reports**: Downloadable PDF files
- **JSON Reports**: Machine-readable results
- **Quarto Reports**: Professional, publication-ready documents

### Step 5: Export and Share

- **Export Data**: Download processed data and results
- **Share Results**: Generate shareable links (for public data)
- **Federated Learning**: Contribute anonymized data to improve models

---

## 🤖 Agent Overview

The NIR Intelligence Platform uses specialized **agents** to perform different analysis tasks. Here are the main agents you'll work with:

### 🎨 UI/UX Agents

| Agent | Purpose | Key Features |
|-------|---------|--------------|
| **HSWTStylingAgent** | Applies HSWT.de styling | Professional design, responsive layout, accessibility |
| **OnboardingAgent** | User onboarding | Guided tours, help system, progress indicators |

### 📊 Data Processing Agents

| Agent | Purpose | Key Features |
|-------|---------|--------------|
| **AudioProcessorAgent** | Process audio spectral data | WAV, MP3, FLAC support, FFT analysis, noise filtering |
| **ImageProcessorAgent** | Process image spectral data | PNG, JPG, TIFF support, spectral extraction, quality assessment |
| **DataPreparationAgent** | Prepare data for analysis | Cleaning, normalization, format conversion |

### 🔬 Analysis Agents

| Agent | Purpose | Key Features |
|-------|---------|--------------|
| **SpectralAnalysisAgent** | Core spectral analysis | Quality assessment, preprocessing, issue detection |
| **ShiftDetectorAgent** | Detect instrument issues | Wavelength shift, intensity drift, baseline analysis |
| **ParameterRecommenderAgent** | Optimize parameters | Integration time, gain, scans to average, wavelength range |
| **MetadataQualityAgent** | Assess metadata quality | Completeness, standards compliance, grading |
| **StatisticalAnalysisAgent** | Statistical analysis | Correlation, regression, clustering |

### 🌐 Integration Agents

| Agent | Purpose | Key Features |
|-------|---------|--------------|
| **ILIASIntegrationAgent** | ILIAS LMS integration | Single sign-on, course integration, grade synchronization |
| **FlowerAgent** | Federated learning | Model aggregation, privacy preservation, collaborative learning |
| **DjangoAgent** | Django web interface | User management, authentication, API endpoints |

### 📈 Advanced Agents

| Agent | Purpose | Key Features |
|-------|---------|--------------|
| **NeuralNetworkAgent** | Machine learning | Model training, prediction, evaluation |
| **CalibrationAgent** | Instrument calibration | Reference standards, calibration curves, validation |
| **ReportingAgent** | Report generation | HTML, PDF, Quarto reports, visualization |

---

## 🚨 Troubleshooting

### Common Issues and Solutions

#### Issue: "ModuleNotFoundError: No module named 'numpy'"

**Solution**: Install required dependencies
```bash
pip install -r requirements.txt
```

#### Issue: "Port 8000 is already in use"

**Solution**: Use a different port
```bash
python manage.py runserver 0.0.0.0:8080
```

#### Issue: Ventoy USB not booting

**Solution**:
1. Check USB drive is properly formatted with Ventoy
2. Ensure BIOS is set to boot from USB
3. Try a different USB port
4. Recreate Ventoy USB with latest version

#### Issue: Ansible playbook fails

**Solution**:
1. Check Ansible version: `ansible --version`
2. Update Ansible: `pip install --upgrade ansible`
3. Run with verbose mode: `ansible-playbook playbook.yml -v`
4. Check inventory file paths

#### Issue: Django migrations fail

**Solution**:
1. Reset migrations: `python manage.py migrate --fake`
2. Delete database and recreate: `rm db.sqlite3 && python manage.py migrate`
3. Check database permissions

#### Issue: Agents not found in registry

**Solution**:
1. Check imports in `agents/__init__.py`
2. Verify agent files exist in `agents/` directory
3. Restart Python interpreter

### Debug Mode

Enable debug mode for more detailed error information:

```bash
# For Django
python manage.py runserver --debug

# For Ansible
ansible-playbook playbook.yml -v -vvv

# For Python scripts
python -m pdb your_script.py
```

### Log Files

Check these log files for troubleshooting:

- **Django logs**: `django_app/logs/django.log`
- **Ansible logs**: `ansible/logs/ansible.log`
- **Agent logs**: Each agent logs to its own file in `logs/`
- **System logs**: `/var/log/syslog` (Linux) or Event Viewer (Windows)

---

## 🔧 Maintenance

### Regular Maintenance Tasks

#### 1. Update the System

```bash
# Update NIR Intelligence Platform
git pull origin main

# Update dependencies
pip install --upgrade -r requirements.txt

# Run database migrations
python manage.py migrate
```

#### 2. Backup Your Data

```bash
# Backup database
python manage.py dumpdata > backup.json

# Backup configuration files
cp -r nir_config/ nir_config_backup_

# Backup uploaded files
cp -r media/ media_backup_
```

#### 3. Clean Up Temporary Files

```bash
# Remove temporary files
rm -rf __pycache__/ *.pyc *.pyo

# Clean up old logs
find logs/ -name "*.log" -size +10M -delete

# Clean up old backups
find . -name "backup_*" -mtime +30 -delete
```

#### 4. Monitor System Health

```bash
# Check disk space
df -h

# Check memory usage
free -h

# Check running processes
ps aux | grep python

# Check Django server status
curl -I http://localhost:8000
```

### Ventoy USB Maintenance

#### Update Ventoy

1. Download latest Ventoy version
2. Run Ventoy2Disk with update option:
   ```bash
   # Windows
   Ventoy2Disk.exe -u
   
   # Linux/macOS
   sudo ./Ventoy2Disk.sh -u /dev/sdX
   ```

#### Add More Space

If your USB stick is running out of space:

1. **Backup your data** from the USB stick
2. **Use a larger USB drive** (32GB+ recommended)
3. **Recreate Ventoy** on the new drive
4. **Copy your data** back to the new drive

#### Fix Corrupted USB

If your Ventoy USB becomes corrupted:

1. **Backup any important data** (if possible)
2. **Reformat the USB drive**
3. **Reinstall Ventoy** from scratch
4. **Copy NIR Intelligence Platform** files back

---

## 📚 Additional Resources

### Documentation

- **Main Documentation**: `docs/README.md`
- **API Documentation**: `docs/API.md`
- **Developer Guide**: `docs/DEVELOPMENT.md`
- **Agent Documentation**: `docs/agents/`

### Support

- **GitHub Issues**: [https://github.com/your-repo/issues](https://github.com/your-repo/issues)
- **Community Forum**: [Link to your forum]
- **Email Support**: support@nir-platform.org

### Learning Resources

- **Tutorials**: `tutorials/` directory
- **Examples**: `examples/` directory
- **Video Guides**: [Link to video tutorials]

---

## 🎉 Quick Start Checklist

- [ ] **Hardware**: ✅ USB stick (16GB+) or computer meeting requirements
- [ ] **Ventoy Setup**: ✅ Ventoy installed on USB (or local installation)
- [ ] **Files Copied**: ✅ NIR Intelligence Platform files on USB/computer
- [ ] **Dependencies**: ✅ All required software installed
- [ ] **First Run**: ✅ System starts without errors
- [ ] **Data Upload**: ✅ Successfully uploaded test spectral data
- [ ] **Analysis**: ✅ Ran first analysis successfully
- [ ] **Results**: ✅ Viewed and understood analysis results

---

## 📞 Contact Information

For questions, support, or feedback:

- **Project Lead**: [Name, Email]
- **Technical Support**: [Email, Phone]
- **Community Manager**: [Name, Email]
- **Website**: [https://nir-platform.org](https://nir-platform.org)

---

**Thank you for using the NIR Intelligence Platform!** 🚀

This manual provides a comprehensive guide for users with medium IT experience to set up, use, and maintain the NIR Intelligence Platform. The system is designed to be user-friendly while providing powerful analysis capabilities for NIR spectral data.

*Last updated: August 6, 2026*