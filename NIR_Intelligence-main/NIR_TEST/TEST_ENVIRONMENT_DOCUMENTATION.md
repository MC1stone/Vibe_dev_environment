# NIR_Mistral DeveloperAgent Framework - Test Environment Documentation

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Test Environment Setup](#-test-environment-setup)
3. [NIR_TEST Environment Structure](#-nir_test-environment-structure)
4. [Running Tests](#-running-tests)
5. [Django Frontend Integration](#-django-frontend-integration)
6. [API Endpoints](#-api-endpoints)
7. [Test Data Format](#-test-data-format)
8. [Expected Results](#-expected-results)
9. [Troubleshooting](#-troubleshooting)
10. [Automation](#-automation)

---

## 🎯 Overview

The **NIR_TEST Environment** is a comprehensive test suite for the **NIR_Mistral DeveloperAgent Framework** that demonstrates the functionality using realistic NIR spectroscopy test data. This environment provides:

- ✅ **Realistic Test Data**: NIR spectroscopy data in TXT format
- ✅ **Complete Framework Testing**: All major components and agents
- ✅ **Quality Control**: Data validation and quality checks
- ✅ **Django Integration**: Full web-based interface
- ✅ **API Access**: RESTful API endpoints for programmatic access
- ✅ **HSWT Design System**: Professional UI matching HSWT.de website

### **Key Features**

| Feature | Description |
|---------|-------------|
| **Test Data** | Real NIR spectroscopy data (Wheat Flour, Corn Meal) |
| **Analysis Agents** | Multiple NIR analysis agents with different capabilities |
| **Quality Control** | Comprehensive data quality validation |
| **Reporting** | Detailed test reports and analysis results |
| **Web Interface** | Django frontend with HSWT.de-inspired design |
| **API Integration** | RESTful API for programmatic access |

---

## 🚀 Test Environment Setup

### **Prerequisites**

Before setting up the test environment, ensure you have the following installed:

```bash
# Python 3.8+ 
python3 --version

# pip (Python package manager)
pip3 --version

# Git (for version control)
git --version
```

### **Quick Setup**

The NIR_TEST environment is automatically included with the NIR_Mistral framework. To set it up:

```bash
# Navigate to the NIR_TEST directory
cd /path/to/NIR_Mistral/NIR_TEST

# Setup the environment (creates directories, validates data)
python run_test_environment.py setup

# Install dependencies
python run_test_environment.py install

# Verify the setup
python run_test_environment.py info
```

### **Environment Configuration**

The test environment uses a YAML configuration file located at `NIR_TEST/config/test_config.yaml`:

```yaml
# Environment Settings
environment:
  name: "NIR_TEST"
  type: "test"
  description: "Test environment for NIR_Mistral framework"
  version: "1.0.0"

# Path Configuration
paths:
  root: "/home/martin/Development/vsCode_Environment/NIR_Mistral/NIR_TEST"
  data: "/home/martin/Development/vsCode_Environment/NIR_Mistral/NIR_TEST/data"
  raw_data: "/home/martin/Development/vsCode_Environment/NIR_Mistral/NIR_TEST/data/raw"
  # ... other paths

# NIR Spectroscopy Settings
nir_settings:
  wavelength_range: [700, 2500]
  resolution: 2
  units: "nm"
  spectral_type: "absorbance"

# Test Data Configuration
test_data:
  samples:
    - id: "001"
      name: "Wheat Flour"
      file: "nir_spectrum_001.txt"
      type: "absorbance"
      expected_properties:
        protein: 12.0
        moisture: 14.0
        fat: 1.5
    - id: "002"
      name: "Corn Meal"
      file: "nir_spectrum_002.txt"
      type: "reflectance"
      expected_properties:
        starch: 72.0
        moisture: 10.0
        protein: 8.0
```

---

## 📁 NIR_TEST Environment Structure

```
NIR_TEST/
├── agents/                          # Test agents
│   └── nir_test_agent.py           # Main test agent
├── config/                         # Configuration files
│   └── test_config.yaml            # Test environment configuration
├── data/                           # Test data
│   ├── raw/                        # Raw test data files
│   │   ├── nir_spectrum_001.txt     # Wheat Flour spectrum
│   │   ├── nir_spectrum_002.txt     # Corn Meal spectrum
│   │   └── metadata.txt             # Metadata file
│   ├── processed/                  # Processed data (generated)
│   └── results/                    # Analysis results (generated)
├── logs/                           # Log files (generated)
├── models/                        # Model files (generated)
├── output/                        # Output files (generated)
│   └── test_report.txt             # Generated test report
├── scripts/                       # Utility scripts
└── run_test_environment.py        # Main test runner
```

---

## 🧪 Running Tests

### **Available Commands**

The `run_test_environment.py` script provides several commands:

| Command | Description | Usage |
|---------|-------------|-------|
| `info` | Show environment information | `python run_test_environment.py info` |
| `setup` | Setup the test environment | `python run_test_environment.py setup` |
| `run` | Run complete demonstration | `python run_test_environment.py run` |
| `test` | Run specific test | `python run_test_environment.py test <test_name>` |
| `install` | Install dependencies | `python run_test_environment.py install` |
| `clean` | Clean up test files | `python run_test_environment.py clean` |

### **Running the Complete Demonstration**

```bash
# Run the full demonstration
python run_test_environment.py run
```

This will:
1. Load test data from files
2. Analyze all spectra
3. Validate data quality
4. Generate a comprehensive report
5. Display a summary of results

### **Running Specific Tests**

```bash
# Load test data
python run_test_environment.py test load_data

# Analyze spectra
python run_test_environment.py test analyze

# Validate data quality
python run_test_environment.py test validate

# Generate report
python run_test_environment.py test report
```

### **Expected Output**

A successful demonstration will produce output similar to:

```
============================================================
NIR TEST ENVIRONMENT - DEMONSTRATION SUMMARY
============================================================
Agent: NIR_Test_Agent v1.0.0
Test Date: 2026-08-03 11:40:21
Configuration: NIR_TEST

Loaded Spectra: 2
  - Wheat Flour (001): 902 data points
  - Corn Meal (002): 901 data points

Analysis Results:
  - Wheat Flour:
    Wavelength Range: 700-2500 nm
    Mean Absorbance: 1.072
    Peaks Found: 5
  - Corn Meal:
    Wavelength Range: 700-2500 nm
    Mean Absorbance: 1.219
    Peaks Found: 4

Quality Control:
  - Wheat Flour: PASS
  - Corn Meal: PASS

Demonstration completed successfully!
Detailed report saved to: output/test_report.txt
============================================================
```

---

## 🌐 Django Frontend Integration

### **HSWT Design System**

The Django frontend uses a custom **HSWT Design System** inspired by the HSWT.de website, featuring:

- **Color Scheme**: Primary green (#7ab929), dark green (#225933)
- **Component Library**: Cards, buttons, tables, modals, forms
- **Responsive Design**: Mobile-first approach
- **Accessibility**: ARIA labels, keyboard navigation
- **Modern UI**: Clean, professional interface

### **Key CSS Classes**

The HSWT design system includes the following component classes:

#### **Layout**
- `o-container` - Container with max-width
- `o-container--full-width` - Full-width container
- `o-grid` - Grid layout
- `o-grid--2-col`, `o-grid--3-col`, `o-grid--4-col` - Grid variants

#### **Components**
- `c-card` - Card component
- `c-card__header`, `c-card__body`, `c-card__footer` - Card sections
- `c-button` - Button component
- `c-button--primary`, `c-button--secondary`, `c-button--success`, etc. - Button variants
- `c-table` - Table component
- `c-form-group` - Form group
- `c-input`, `c-select`, `c-textarea` - Form controls
- `c-modal` - Modal dialog
- `c-stat` - Statistics display
- `c-badge` - Badge component
- `c-progress` - Progress bar

#### **Utilities**
- `c-text--primary`, `c-text--secondary`, `c-text--muted` - Text colors
- `c-text--small`, `c-text--large` - Text sizes
- `c-flex` - Flex container
- `c-flex--justify-between`, `c-flex--align-center` - Flex utilities
- `c-mt-1`, `c-mt-2`, `c-mt-3`, `c-mt-4` - Margin top utilities
- `c-mb-1`. `c-mb-2`, `c-mb-3`, `c-mb-4` - Margin bottom utilities

### **Page Templates**

The following templates have been updated to use the HSWT design system:

| Template | Description | Status |
|----------|-------------|--------|
| `base.html` | Base template with header, navigation, footer | ✅ Complete |
| `dashboard.html` | Main dashboard with statistics and charts | ✅ Complete |
| `agents.html` | Agent management interface | ✅ Complete |
| `spectra.html` | Spectrum management interface | ✅ Complete |
| `analysis.html` | Analysis interface | ✅ Complete |
| `jobs.html` | Job management interface | ✅ Complete |
| `settings.html` | Settings page | ✅ Complete |
| `documentation.html` | Documentation page | ✅ Complete |

### **Using the Frontend**

1. **Start the Django development server**:
   ```bash
   cd django_project
   python manage.py runserver
   ```

2. **Access the web interface**:
   - Open your browser to `http://localhost:8000/`
   - Navigate to the **Agents** page to see the NIR_TEST integration

3. **Test the NIR_TEST functionality**:
   - The frontend provides a user-friendly interface to run tests
   - Real-time results and visualizations
   - Access to test reports and analysis data

---

## 🔌 API Endpoints

### **NIR_TEST Environment API**

The following API endpoints are available for programmatic access to the NIR_TEST environment:

| Endpoint | Method | Description | Authentication |
|----------|--------|-------------|----------------|
| `/api/nir-test/info/` | GET | Get environment information | Required |
| `/api/nir-test/demo/` | GET | Run complete demonstration | Required |
| `/api/nir-test/run/<test_name>/` | GET | Run specific test | Required |
| `/api/nir-test/files/` | GET | Get test data files | Required |
| `/api/nir-test/report/` | GET | Get latest test report | Required |
| `/api/nir-test/setup/` | POST | Setup test environment | Required |
| `/api/nir-test/clean/` | POST | Clean test environment | Required |

### **API Usage Examples**

#### **Get Environment Information**

```bash
curl -X GET http://localhost:8000/api/nir-test/info/ \
  -H "Authorization: Bearer <your_token>"
```

Response:
```json
{
  "status": "success",
  "data": {
    "directory_structure": {
      "data/raw": true,
      "data/processed": true,
      "config": true,
      "scripts": true,
      "output": true,
      "logs": true,
      "agents": true,
      "models": true
    },
    "test_data_files": [
      {"name": "nir_spectrum_001.txt", "full_line": "- nir_spectrum_001.txt (9159 bytes)"},
      {"name": "nir_spectrum_002.txt", "full_line": "- nir_spectrum_002.txt (9134 bytes)"},
      {"name": "metadata.txt", "full_line": "- metadata.txt (1340 bytes)"}
    ],
    "configuration": "found",
    "agents": ["nir_test_agent.py"]
  },
  "message": "Environment information retrieved successfully"
}
```

#### **Run Demonstration**

```bash
curl -X GET http://localhost:8000/api/nir-test/demo/ \
  -H "Authorization: Bearer <your_token>"
```

#### **Run Specific Test**

```bash
curl -X GET http://localhost:8000/api/nir-test/run/load_data/ \
  -H "Authorization: Bearer <your_token>"
```

#### **Get Test Report**

```bash
curl -X GET http://localhost:8000/api/nir-test/report/ \
  -H "Authorization: Bearer <your_token>"
```

---

## 📊 Test Data Format

### **NIR Spectrum Data Files**

The test data files (`nir_spectrum_001.txt`, `nir_spectrum_002.txt`) contain NIR spectroscopy data in the following format:

```
# NIR Spectrum Data
# Sample: Wheat Flour
# Instrument: NIR Spectrometer
# Date: 2026-08-03
# Wavelength Range: 700-2500 nm
# Data Points: 902
700,0.250
702,0.265
704,0.280
706,0.295
...
2500,2.160
```

**Format Specifications**:
- **Delimiter**: Comma (`,`) 
- **Columns**: Wavelength (nm), Absorbance/Reflectance value
- **Header**: 6 lines of metadata (prefixed with `#`)
- **Data**: Wavelength-value pairs, one per line
- **Wavelength Range**: 700-2500 nm
- **Resolution**: 2 nm step
- **Data Points**: ~900-902 per spectrum

### **Metadata File**

The `metadata.txt` file contains additional information about the test samples:

```
# NIR Test Data Metadata
# Generated: 2026-08-03
# Samples: 2

# Sample 001 - Wheat Flour
id,001
name,Wheat Flour
type,absorbance
protein,12.0
moisture,14.0
fat,1.5

# Sample 002 - Corn Meal
id,002
name,Corn Meal
type,reflectance
starch,72.0
moisture,10.0
protein,8.0
```

---

## ✅ Expected Results

### **Test Environment Validation**

When you run `python run_test_environment.py info`, you should see:

```
NIR_TEST Environment Information
==================================================
Directory Structure:
  ✓ data/raw
  ✓ data/processed
  ✓ data/results
  ✓ config
  ✓ scripts
  ✓ output
  ✓ logs
  ✓ agents
  ✓ models

Test Data Files (3):
  - nir_spectrum_001.txt (9159 bytes)
  - nir_spectrum_002.txt (9134 bytes)
  - metadata.txt (1340 bytes)

Configuration: ✓ test_config.yaml found
Agents: 1 available
  - nir_test_agent.py
```

### **Data Loading Results**

When you run `python run_test_environment.py test load_data`, you should see:

```
✓ Successfully loaded 2 spectra
  - Wheat Flour: 902 data points
  - Corn Meal: 901 data points
```

### **Analysis Results**

When you run `python run_test_environment.py test analyze`, you should see:

```
✓ Analyzed 2 spectra
  - Wheat Flour: Mean=1.072, Peaks=5
  - Corn Meal: Mean=1.219, Peaks=4
```

### **Quality Control Results**

When you run `python run_test_environment.py test validate`, you should see:

```
✓ Validated 2 spectra
  - Wheat Flour: PASS
  - Corn Meal: PASS
```

### **Test Report**

The generated test report (`output/test_report.txt`) should contain:

```
============================================================
NIR_MISTRAL TEST ENVIRONMENT REPORT
============================================================
Generated: 2026-08-03 11:40:21
Agent: NIR_Test_Agent v1.0.0

SPECTRAL ANALYSIS RESULTS
----------------------------------------

Sample: Wheat Flour (ID: 001)
Type: absorbance
Wavelength Range: 700-2500 nm
Data Points: 902
Wavelength Step: 2.0 nm
Mean Absorbance: 1.072
Max Absorbance: 2.160
Min Absorbance: 0.250
Peaks Found: 5
Peak Positions (nm, value):
  840: 0.950
  1040: 1.050
  1200: 1.250
  1420: 1.250
  1900: 2.160

Sample: Corn Meal (ID: 002)
Type: reflectance
Wavelength Range: 700-2500 nm
Data Points: 901
Wavelength Step: 2.0 nm
Mean Absorbance: 1.219
Max Absorbance: 2.550
Min Absorbance: 0.350
Peaks Found: 4
Peak Positions (nm, value):
  840: 1.050
  1040: 1.150
  1440: 2.050
  1900: 1.650


QUALITY CONTROL REPORT
----------------------------------------

Sample: Wheat Flour (ID: 001)
Overall Quality: PASS
  wavelength_range: PASS
  resolution: PASS
  data_integrity: PASS
  signal_range: PASS

Sample: Corn Meal (ID: 002)
Overall Quality: PASS
  wavelength_range: PASS
  resolution: PASS
  data_integrity: PASS
  signal_range: PASS

============================================================
END OF REPORT
============================================================
```

---

## 🔧 Troubleshooting

### **Common Issues and Solutions**

#### **1. Module Not Found Errors**

**Error**: `ModuleNotFoundError: No module named 'agents.nir_test_agent'`

**Solution**:
```bash
# Ensure PYTHONPATH includes NIR_TEST directory
export PYTHONPATH=/path/to/NIR_Mistral/NIR_TEST:$PYTHONPATH

# Or run from the NIR_TEST directory
cd /path/to/NIR_Mistral/NIR_TEST
python agents/nir_test_agent.py
```

#### **2. Missing Dependencies**

**Error**: `ModuleNotFoundError: No module named 'numpy'` or similar

**Solution**:
```bash
# Install required dependencies
python run_test_environment.py install

# Or manually install
pip install numpy pandas pyyaml
```

#### **3. File Not Found Errors**

**Error**: `FileNotFoundError: [Errno 2] No such file or directory: 'data/raw/nir_spectrum_001.txt'`

**Solution**:
```bash
# Ensure you're in the correct directory
cd /path/to/NIR_Mistral/NIR_TEST

# Verify files exist
ls data/raw/

# If files are missing, check the repository
git status
```

#### **4. Permission Denied Errors**

**Error**: `Permission denied` when creating directories or files

**Solution**:
```bash
# Check current permissions
ls -la

# Fix permissions
chmod -R 755 NIR_TEST/
chown -R $USER:$USER NIR_TEST/
```

#### **5. Configuration File Missing**

**Error**: `Configuration file not found: .../config/test_config.yaml`

**Solution**:
```bash
# Create the config directory
mkdir -p NIR_TEST/config

# Copy the default configuration
cp /path/to/default/test_config.yaml NIR_TEST/config/
```

#### **6. Django API Not Working**

**Error**: API endpoints return 404 or 500 errors

**Solution**:
```bash
# Ensure Django server is running
cd django_project
python manage.py runserver

# Check URL configuration
# Ensure the NIR_TEST API endpoints are included in urls.py

# Test the API manually
curl http://localhost:8000/api/nir-test/info/
```

#### **7. Timeout Errors**

**Error**: Demonstration or test times out

**Solution**:
```bash
# Increase timeout in the API views
# Edit django_project/api/views/nir_test_views.py
# Change timeout values from 30/60/120 to higher values

# Or run tests directly from command line
python run_test_environment.py run
```

---

## 🤖 Automation

### **Automated Testing Script**

Create a script to run all tests automatically:

```python
#!/usr/bin/env python3
"""
Automated NIR_TEST Environment Testing
"""

import subprocess
import sys
import time

def run_command(cmd, cwd=None):
    """Run a command and return the result"""
    try:
        result = subprocess.run(
            cmd,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=120
        )
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.TimeoutExpired:
        return False, "", "Command timed out"
    except Exception as e:
        return False, "", str(e)

def main():
    """Run automated tests"""
    nir_test_path = "/path/to/NIR_Mistral/NIR_TEST"
    
    tests = [
        ("Environment Info", [sys.executable, "run_test_environment.py", "info"]),
        ("Setup Environment", [sys.executable, "run_test_environment.py", "setup"]),
        ("Load Data", [sys.executable, "run_test_environment.py", "test", "load_data"]),
        ("Analyze Spectra", [sys.executable, "run_test_environment.py", "test", "analyze"]),
        ("Validate Data", [sys.executable, "run_test_environment.py", "test", "validate"]),
        ("Generate Report", [sys.executable, "run_test_environment.py", "test", "report"]),
        ("Complete Demo", [sys.executable, "run_test_environment.py", "run"]),
    ]
    
    print("Starting Automated NIR_TEST Environment Testing...")
    print("=" * 60)
    
    passed = 0
    failed = 0
    
    for test_name, cmd in tests:
        print(f"\nRunning: {test_name}...")
        success, stdout, stderr = run_command(cmd, cwd=nir_test_path)
        
        if success:
            print(f"✓ {test_name}: PASSED")
            passed += 1
        else:
            print(f"✗ {test_name}: FAILED")
            print(f"  Error: {stderr}")
            failed += 1
    
    print("\n" + "=" * 60)
    print(f"Automated Testing Summary:")
    print(f"  Total Tests: {len(tests)}")
    print(f"  Passed: {passed}")
    print(f"  Failed: {failed}")
    print(f"  Success Rate: {(passed/len(tests)*100):.1f}%")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print(f"\n❌ {failed} test(s) failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main())
```

### **Continuous Integration**

For CI/CD pipelines, add the following to your workflow:

```yaml
# .github/workflows/test-environment.yml
name: NIR_TEST Environment

on:
  push:
    branches: [ main, develop ]
  pull_request:
    branches: [ main ]

jobs:
  test:
    runs-on: ubuntu-latest
    
    steps:
    - uses: actions/checkout@v3
    
    - name: Set up Python
      uses: actions/setup-python@v4
      with:
        python-version: '3.11'
    
    - name: Install dependencies
      run: |
        cd NIR_TEST
        pip install -r requirements.txt
    
    - name: Run NIR_TEST environment
      run: |
        cd NIR_TEST
        python run_test_environment.py run
    
    - name: Verify test report
      run: |
        cd NIR_TEST
        test -f output/test_report.txt
        grep -q "PASS" output/test_report.txt
```

---

## 📚 Additional Resources

- [NIR_Mistral Framework Documentation](../docs/INSTALLATION_GUIDE.md)
- [DeveloperAgent Framework Documentation](../dev_framework/README.md)
- [Django Project Documentation](../django_project/README.md)
- [HSWT Design System](../django_project/static/css/hswt-style.css)

---

## 🤝 Support

For issues or questions related to the NIR_TEST environment:

1. **Check this documentation** for setup and usage instructions
2. **Review the troubleshooting section** for common problems
3. **Consult the test report** for detailed analysis results
4. **Check the logs** in `NIR_TEST/logs/` for error details
5. **Open an issue** in the project repository

---

## 📄 License

This documentation is part of the **NIR_Mistral DeveloperAgent Framework** and is licensed under the same terms as the main project.

---

## 🏁 Conclusion

The **NIR_TEST Environment** provides a complete, automated testing framework for the **NIR_Mistral DeveloperAgent Framework**. With this environment, you can:

- ✅ **Test Framework Functionality**: Verify all components work correctly
- ✅ **Analyze Real Data**: Process realistic NIR spectroscopy data
- ✅ **Validate Quality**: Ensure data integrity and analysis accuracy
- ✅ **Generate Reports**: Create comprehensive test reports
- ✅ **Integrate with Django**: Use the web interface for easy access
- ✅ **Automate Testing**: Run tests programmatically via API

**Next Steps**:
1. Run the complete demonstration: `python run_test_environment.py run`
2. Explore the Django frontend: `http://localhost:8000/`
3. Integrate with your workflow using the API endpoints
4. Extend with your own test data and agents

---

*Documentation generated for NIR_Mistral DeveloperAgent Framework v1.0.0*
*Last updated: 2026-08-03*