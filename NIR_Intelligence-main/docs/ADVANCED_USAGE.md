# NIR_MISTRAL - Advanced Usage Guide

**Version**: 2.0.0  
**Last Updated**: 2026-08-06  
**Target Audience**: Developers, System Administrators, Advanced Users  

---

## 📚 TABLE OF CONTENTS

1. [🎛️ Command Line Interface](#-command-line-interface)
2. [🔧 Configuration Management](#-configuration-management)
3. [🧪 Testing & Quality Assurance](#-testing--quality-assurance)
4. [📈 Monitoring & Logging](#-monitoring--logging)
5. [🔄 Backup & Recovery](#-backup--recovery)
6. [🛠️ Development Guide](#-development-guide)

---

## 🎛️ Command Line Interface

### Framework Commands

| Command | Description | Example |
|---------|-------------|---------|
| `info` | Show system information | `python -m dev_framework info` |
| `generate` | Generate new agents | `python -m dev_framework generate agent MyAgent` |
| `validate` | Validate agents | `python -m dev_framework validate` |
| `test` | Run tests | `python -m dev_framework test --all` |
| `quality` | Check code quality | `python -m dev_framework quality --check --all` |
| `serve` | Start development server | `python -m dev_framework serve` |
| `clean` | Clean build artifacts | `python -m dev_framework clean` |

### Agent Commands

| Command | Description | Example |
|---------|-------------|---------|
| `analyze` | Run analysis on data | `python -m dev_framework analyze --file data.json` |
| `report` | Generate reports | `python -m dev_framework report --analysis 123` |
| `federated` | Manage federated learning | `python -m dev_framework federated --status` |
| `ilias` | Manage ILIAS integration | `python -m dev_framework ilias --sync` |

### Complete CLI Reference

```bash
# Framework information
python -m dev_framework info
python -m dev_framework info --verbose
python -m dev_framework info --json

# Agent generation
python -m dev_framework generate agent MyAgent --template analysis
python -m dev_framework generate agent MyAgent --template analysis --force
python -m dev_framework generate tests MyAgent
python -m dev_framework generate docs MyAgent

# Validation
python -m dev_framework validate
python -m dev_framework validate --agent MyAgent
python -m dev_framework validate --strict

# Testing
python -m dev_framework test --agent MyAgent
python -m dev_framework test --all
python -m dev_framework test --agent MyAgent --coverage
python -m dev_framework test --agent MyAgent --verbose

# Quality checks
python -m dev_framework quality --check --all
python -m dev_framework quality --check --agent MyAgent
python -m dev_framework quality --fix --all
python -m dev_framework quality --fix --agent MyAgent

# Development server
python -m dev_framework serve
python -m dev_framework serve --port 8000
python -m dev_framework serve --debug
python -m dev_framework serve --log-level DEBUG

# Analysis
python -m dev_framework analyze --file data/sample.json
python -m dev_framework analyze --directory data/samples/
python -m dev_framework analyze --file data.json --agents shift_detector,parameter_recommender
python -m dev_framework analyze --file data.json --output results.json

# Reporting
python -m dev_framework report --analysis analysis_123 --format html
python -m dev_framework report --analysis analysis_123 --format pdf --output report.pdf
python -m dev_framework report --analysis analysis_123 --template detailed

# Federated learning
python -m dev_framework federated --enable
python -m dev_framework federated --disable
python -m dev_framework federated --privacy-level metadata_only
python -m dev_framework federated --sync
python -m dev_framework federated --status

# ILIAS integration
python -m dev_framework ilias --test-connection
python -m dev_framework ilias --sync-courses
python -m dev_framework ilias --sync-users
python -m dev_framework ilias --enable-sso
```

---

## 🔧 Configuration Management

### Configuration Files

**Main Configuration** (`config/local_config.yaml`):
```yaml
# System settings
system:
  name: "NIR_MISTRAL"
  environment: "production"
  debug: false
  log_level: "INFO"

# Database
database:
  enabled: true
  type: "postgresql"  # postgresql, sqlite, mysql
  host: "localhost"
  port: 5432
  name: "nir_db"

# Web interface
web:
  enabled: true
  host: "0.0.0.0"
  port: 8000

# Agents
agents:
  max_concurrent: 4
  timeout: 300

# Reporting
reporting:
  quarto_enabled: true
  output_formats: ["html", "pdf"]

# Federated learning
federated:
  enabled: false
  mode: "standalone"
  privacy_level: "local_only"

# ILIAS
ilias:
  enabled: false
```

**Agent Configuration** (`config/agent_config.yaml`):
```yaml
agents:
  shift_detector:
    enabled: true
    wavelength_range: [700, 2500]
    min_data_points: 50
    sensitivity: "high"
    
  parameter_recommender:
    enabled: true
    snr_threshold: 100.0
    quality_threshold: 75.0
    optimization_method: "L-BFGS-B"
    
  metadata_quality:
    enabled: true
    standards: ["ISO_12825", "ASTM_E1655"]
    required_fields: ["sample_id", "date", "instrument"]
    
  spectral_analysis:
    enabled: true
    methods: ["PCA", "PLS", "SVM"]
    max_components: 10
```

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `DJANGO_SECRET_KEY` | Django secret key | Random | Yes |
| `DATABASE_URL` | Database connection URL | None | No |
| `REDIS_URL` | Redis connection URL | None | No |
| `FLOWER_ENABLED` | Enable federated learning | false | No |
| `FLOWER_MODE` | Federated mode | standalone | No |
| `WEB_PORT` | Web server port | 8000 | No |
| `LOG_LEVEL` | Logging level | INFO | No |

---

## 🧪 Testing & Quality Assurance

### Running Tests

```bash
# Run all tests
python -m pytest tests/ -v

# Run unit tests only
python -m pytest tests/unit/ -v

# Run integration tests only
python -m pytest tests/integration/ -v

# Run end-to-end tests only
python -m pytest tests/e2e/ -v

# Run tests for specific agent
python -m pytest tests/ -k "shift_detector" -v

# Run with coverage
python -m pytest tests/ --cov=agents --cov-report=html

# Run specific test file
python -m pytest tests/unit/test_shift_detector_agent.py -v
```

### Quality Checks

```bash
# Check all files
python -m dev_framework quality --check --all

# Check specific agent
python -m dev_framework quality --check --agent shift_detector

# Auto-fix issues
python -m dev_framework quality --fix --all

# Run individual tools
black agents/
flake8 agents/
isort agents/
mypy agents/
```

### Performance Testing

```bash
# Run performance tests
python -m pytest tests/performance/ -v

# Benchmark specific agent
python -c "
import time
from agents.shift_detector_agent import ShiftDetectorAgent
import numpy as np

# Create test data
wavelengths = list(range(700, 2500, 5))
intensities = [0.5 + 0.3 * np.sin(wl * 0.01) for wl in wavelengths]
test_data = {'wavelengths': wavelengths, 'intensities': intensities, 'sample_id': 'test'}

# Benchmark
agent = ShiftDetectorAgent()
start = time.time()
for _ in range(100):
    result = agent.execute({'spectral_data': test_data})
end = time.time()

print(f'100 executions: {end-start:.2f} seconds')
print(f'Average: {(end-start)/100*1000:.2f} ms per execution')
"
```

---

## 📈 Monitoring & Logging

### Logging Configuration

**Log Levels**:
- `DEBUG` - Detailed debugging information
- `INFO` - General operational information
- `WARNING` - Potential issues
- `ERROR` - Errors that need attention
- `CRITICAL` - Critical failures

**Log Files**:
```
logs/
├── framework.log              # Main framework log
├── agents/                    # Agent-specific logs
│   ├── shift_detector.log     # ShiftDetectorAgent log
│   ├── parameter_recommender.log # ParameterRecommenderAgent log
│   └── ...
└── web/                       # Web application logs
    ├── django.log             # Django application log
    └── access.log             # Web access log
```

### Monitoring Commands

```bash
# View framework logs
 tail -f logs/framework.log

# View agent logs
tail -f logs/agents/shift_detector.log

# View web logs
tail -f logs/web/django.log

# Check system status
python -m dev_framework info

# Check agent status
python -m dev_framework info --agents

# Check database status
python -m dev_framework info --database

# Check federated learning status
python -m dev_framework federated --status
```

---

## 🔄 Backup & Recovery

### Backup Procedures

```bash
# Backup database
python manage.py dumpdata --output=backup/database.json

# Backup configuration
cp -r config/ backup/config/

# Backup user data
cp -r data/spectral_data/ backup/spectral_data/
cp -r data/reports/ backup/reports/

# Backup logs
cp -r logs/ backup/logs/

# Create compressed backup
 tar -czvf backup/nir_mistral_$(date +%Y%m%d_%H%M%S).tar.gz backup/
```

### Recovery Procedures

```bash
# Restore database
python manage.py loaddata backup/database.json

# Restore configuration
cp -r backup/config/* config/

# Restore user data
cp -r backup/spectral_data/* data/spectral_data/
cp -r backup/reports/* data/reports/

# Restore from compressed backup
 tar -xzvf backup/nir_mistral_20260806_120000.tar.gz -C /
```

### Automated Backup Script

```bash
#!/bin/bash
# backup.sh - Automated backup script

BACKUP_DIR="/path/to/backup"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p "$BACKUP_DIR/$DATE"

# Backup database
python manage.py dumpdata --output="$BACKUP_DIR/$DATE/database.json"

# Backup configuration
cp -r config/ "$BACKUP_DIR/$DATE/config/"

# Backup user data
cp -r data/spectral_data/ "$BACKUP_DIR/$DATE/spectral_data/"
cp -r data/reports/ "$BACKUP_DIR/$DATE/reports/"

# Backup logs
cp -r logs/ "$BACKUP_DIR/$DATE/logs/"

# Create compressed archive
cd "$BACKUP_DIR"
tar -czvf "nir_mistral_$DATE.tar.gz" "$DATE"

# Clean up old backups (keep last 30 days)
find "$BACKUP_DIR" -name "nir_mistral_*.tar.gz" -mtime +30 -delete

# Remove temporary directory
rm -rf "$BACKUP_DIR/$DATE"

echo "Backup completed: $BACKUP_DIR/nir_mistral_$DATE.tar.gz"
```

---

## 🛠️ Development Guide

### 🏗️ Creating New Agents

#### Agent Development Workflow

1. **Concept** - Define agent purpose and functionality
2. **Design** - Plan methods and data structures
3. **Generate** - Use framework to create boilerplate
4. **Implement** - Add custom logic
5. **Test** - Create and run tests
6. **Validate** - Ensure compliance with standards
7. **Document** - Write documentation
8. **Integrate** - Add to agent ecosystem

#### Step 1: Generate Agent Boilerplate

```bash
# Generate a new agent
python -m dev_framework generate agent MyNewAgent --template analysis

# This creates:
# - agents/my_new_agent.py
# - agents/my_new_agent.json
# - tests/unit/test_my_new_agent.py
# - tests/integration/test_my_new_agent_integration.py
# - tests/e2e/test_my_new_agent_e2e.py
# - docs/agents/my_new_agent.md
```

#### Step 2: Implement Agent Logic

**Basic Agent Structure**:
```python
#!/usr/bin/env python3
"""
NIR Intelligence Platform - MyNewAgent
Agent for [specific functionality]
"""

import logging
from typing import Dict, Any, List
from dataclasses import dataclass
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity, AgentError

# Define data classes for structured output
@dataclass
class MyResult:
    """Result data structure"""
    metric1: float
    metric2: str
    quality_score: float

class MyNewAgent(BaseAgent):
    """
    Agent for [specific functionality]
    
    Features:
    - Feature 1
    - Feature 2
    - Feature 3
    """
    
    def __init__(self, **kwargs):
        super().__init__(name="MyNewAgent", version="1.0.0", **kwargs)
        self.dependencies = ["numpy", "pandas", "scipy"]
        self.logger = logging.getLogger(f"Agent.MyNewAgent")
        
        # Configuration
        self.config_param = kwargs.get('config_param', 'default_value')
        
        # Initialize agent-specific attributes
        self._initialize_attributes()
    
    def _initialize_attributes(self):
        """Initialize agent-specific attributes"""
        self.stats = {
            'analyses_performed': 0,
            'processing_time': 0.0,
            'errors': 0
        }
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the agent's primary function"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting MyNewAgent execution")
            
            # Extract data from context
            spectral_data = context.get('spectral_data', {})
            
            # Validate input
            validation_errors = self.validate_input(spectral_data)
            if validation_errors:
                return self._create_error_output(validation_errors)
            
            # Perform analysis
            result = self._analyze_data(spectral_data)
            
            # Update stats
            self.stats['analyses_performed'] += 1
            
            self.status = AgentStatus.COMPLETED
            self.logger.info(f"MyNewAgent execution completed for {spectral_data.get('sample_id', 'unknown')}")
            
            return self._create_success_output({
                "status": "completed",
                "message": "MyNewAgent analysis completed successfully",
                "sample_id": spectral_data.get('sample_id', 'unknown'),
                "result": result.__dict__,
                "stats": self.stats
            })
            
        except Exception as e:
            self.stats['errors'] += 1
            return self._handle_error(e)
    
    def validate_input(self, spectral_data: Dict[str, Any]) -> List[str]:
        """Validate input data"""
        errors = []
        
        # Check required fields
        required_fields = ["wavelengths", "intensities", "sample_id"]
        for field in required_fields:
            if field not in spectral_data:
                errors.append(f"Missing required field: {field}")
        
        # Check data types and shapes
        if "wavelengths" in spectral_data and "intensities" in spectral_data:
            if len(spectral_data["wavelengths"]) != len(spectral_data["intensities"]):
                errors.append("Wavelengths and intensities arrays must have the same length")
            
            if len(spectral_data["wavelengths"]) < 50:
                errors.append(f"Insufficient data points: {len(spectral_data['wavelengths'])} < 50")
        
        return errors
    
    def _analyze_data(self, spectral_data: Dict[str, Any]) -> MyResult:
        """Perform the core analysis"""
        import numpy as np
        
        wavelengths = np.array(spectral_data["wavelengths"])
        intensities = np.array(spectral_data["intensities"])
        
        # Example analysis - replace with your logic
        metric1 = np.mean(intensities)
        metric2 = "good"
        quality_score = 85.5
        
        return MyResult(
            metric1=metric1,
            metric2=metric2,
            quality_score=quality_score
        )
    
    def validate(self) -> List[AgentError]:
        """Validate agent configuration and state"""
        errors = super().validate()
        
        # Add custom validation
        if not isinstance(self.config_param, str):
            errors.append(AgentError(
                message="config_param must be a string",
                severity=ErrorSeverity.HIGH,
                code="CONFIG_001"
            ))
        
        return errors
```

#### Step 3: Create Tests

**Unit Test Example**:
```python
#!/usr/bin/env python3
"""
Unit tests for MyNewAgent
"""

import pytest
import numpy as np
from agents.my_new_agent import MyNewAgent


@pytest.fixture
def agent():
    """Create agent instance for testing"""
    return MyNewAgent()


@pytest.fixture
def sample_data():
    """Create sample spectral data for testing"""
    wavelengths = list(range(700, 2500, 10))
    intensities = [0.5 + 0.3 * np.sin(wl * 0.01) for wl in wavelengths]
    return {
        'sample_id': 'test_sample',
        'wavelengths': wavelengths,
        'intensities': intensities,
        'metadata': {'instrument': 'Test'}
    }


class TestMyNewAgent:
    """Test class for MyNewAgent"""
    
    def test_initialization(self, agent):
        """Test agent initialization"""
        assert agent.name == "MyNewAgent"
        assert agent.version == "1.0.0"
        assert agent.status.name == "IDLE"
        assert "numpy" in agent.dependencies
    
    def test_execute_success(self, agent, sample_data):
        """Test successful execution"""
        result = agent.execute({'spectral_data': sample_data})
        
        assert result.status.name == "COMPLETED"
        assert result.data["status"] == "completed"
        assert result.data["sample_id"] == "test_sample"
        assert "result" in result.data
    
    def test_execute_invalid_data(self, agent):
        """Test execution with invalid data"""
        invalid_data = {'sample_id': 'test'}  # Missing required fields
        result = agent.execute({'spectral_data': invalid_data})
        
        assert result.status.name == "ERROR"
        assert "errors" in result.data
    
    def test_validate(self, agent):
        """Test agent validation"""
        errors = agent.validate()
        assert len(errors) == 0  # No validation errors
    
    def test_analyze_data(self, agent, sample_data):
        """Test data analysis method"""
        result = agent._analyze_data(sample_data)
        
        assert hasattr(result, 'metric1')
        assert hasattr(result, 'metric2')
        assert hasattr(result, 'quality_score')
```

#### Step 4: Add to Agent Ecosystem

**Update `agents/__init__.py`**:
```python
# Add import for new agent
from .my_new_agent import MyNewAgent

# Add to __all__ list
__all__ = [
    # ... existing agents ...
    'MyNewAgent',
]
```

**Update Configuration**:
```yaml
# In config/agent_config.yaml
agents:
  my_new_agent:
    enabled: true
    config_param: "default_value"
    # Add other configuration parameters
```

### 🧩 Agent Integration

#### Using Multiple Agents Together

```python
from agents.shift_detector_agent import ShiftDetectorAgent
from agents.parameter_recommender_agent import ParameterRecommenderAgent
from agents.metadata_quality_agent import MetadataQualityAgent

def comprehensive_analysis(spectral_data):
    """Run comprehensive analysis using multiple agents"""
    
    # Initialize agents
    shift_agent = ShiftDetectorAgent()
    param_agent = ParameterRecommenderAgent()
    meta_agent = MetadataQualityAgent()
    
    # Run analyses
    shift_result = shift_agent.execute({'spectral_data': spectral_data})
    param_result = param_agent.execute({
        'spectral_data': spectral_data,
        'current_config': {}
    })
    meta_result = meta_agent.execute({'spectral_data': spectral_data})
    
    # Aggregate results
    comprehensive_report = {
        'sample_id': spectral_data.get('sample_id', 'unknown'),
        'shift_analysis': shift_result.data.get('report', {}),
        'parameter_recommendations': param_result.data.get('report', {}),
        'metadata_quality': meta_result.data.get('report', {}),
        'overall_quality': calculate_overall_quality([
            shift_result.data.get('report', {}).get('quality_score', 0),
            param_result.data.get('report', {}).get('overall_quality_score', 0),
            meta_result.data.get('report', {}).get('quality_score', 0)
        ])
    }
    
    return comprehensive_report

def calculate_overall_quality(scores):
    """Calculate overall quality from multiple scores"""
    if not scores:
        return 0
    return sum(scores) / len(scores)
```

#### Creating Agent Pipelines

```python
from crewai import Agent, Task, Crew, Process
from agents.base_agent import BaseAgent

class AnalysisPipeline(BaseAgent):
    """Pipeline that coordinates multiple agents"""
    
    def __init__(self, **kwargs):
        super().__init__(name="AnalysisPipeline", version="1.0.0", **kwargs)
        
        # Initialize component agents
        self.shift_agent = ShiftDetectorAgent()
        self.param_agent = ParameterRecommenderAgent()
        self.meta_agent = MetadataQualityAgent()
        self.report_agent = ReportingAgent()
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the analysis pipeline"""
        try:
            spectral_data = context.get('spectral_data', {})
            
            # Step 1: Metadata quality check
            meta_result = self.meta_agent.execute({'spectral_data': spectral_data})
            if meta_result.data.get('report', {}).get('quality_score', 0) < 50:
                return self._create_error_output(["Metadata quality too low"])
            
            # Step 2: Shift detection
            shift_result = self.shift_agent.execute({'spectral_data': spectral_data})
            
            # Step 3: Parameter recommendations
            param_result = self.param_agent.execute({
                'spectral_data': spectral_data,
                'current_config': context.get('current_config', {})
            })
            
            # Step 4: Generate comprehensive report
            report_result = self.report_agent.execute({
                'analysis_results': {
                    'shift': shift_result.data,
                    'parameter': param_result.data,
                    'metadata': meta_result.data
                },
                'format': context.get('format', 'html'),
                'template': context.get('template', 'detailed')
            })
            
            return self._create_success_output({
                'status': 'completed',
                'pipeline_results': {
                    'metadata_quality': meta_result.data,
                    'shift_detection': shift_result.data,
                    'parameter_recommendations': param_result.data,
                    'report': report_result.data
                }
            })
            
        except Exception as e:
            return self._handle_error(e)
```

### 📚 Documentation Standards

#### Agent Documentation Template

```markdown
# AgentName

**Version**: X.Y.Z  
**Author**: Your Name  
**Created**: YYYY-MM-DD  
**Type**: [analysis, data, ml, db, api, default]

## Overview

Brief description of the agent's purpose and functionality.

## Responsibilities

- [ ] Primary responsibility 1
- [ ] Primary responsibility 2
- [ ] Secondary responsibility 1
- [ ] Secondary responsibility 2

## Configuration

### Required Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| param1 | str | "default" | Description of parameter 1 |
| param2 | int | 100 | Description of parameter 2 |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| opt_param1 | bool | True | Description of optional parameter 1 |

## Dependencies

### System Dependencies
```bash
# List any system-level dependencies
apt install package1 package2
```

### Python Dependencies
```bash
# List Python package dependencies
pip install numpy pandas scipy
```

## Usage

### Basic Usage

```python
from agents.agent_name import AgentName

# Create agent instance
agent = AgentName()

# Initialize agent
output = agent.initialize()

# Execute agent
context = {
    "spectral_data": your_data,
    "param1": "value1"
}
result = agent.execute(context)
```

### With Configuration

```python
# Create agent with custom configuration
agent = AgentName(
    param1="custom_value",
    param2=200
)
```

## Methods

### `execute(context: Dict[str, Any]) -> AgentOutput`

Executes the agent's primary function.

**Parameters:**
- `context`: Dictionary containing execution context

**Returns:**
- `AgentOutput`: Output containing status, data, and errors

### `validate() -> List[AgentError]`

Validates the agent's current state and configuration.

**Returns:**
- `List[AgentError]`: List of validation errors

### `initialize() -> AgentOutput`

Initializes the agent and its environment.

**Returns:**
- `AgentOutput`: Initialization status

## Error Handling

AgentName handles the following error scenarios:

- **Error Scenario 1**: Description and recovery strategy
- **Error Scenario 2**: Description and recovery strategy

## Performance

- **Expected Execution Time**: X ms - Y ms
- **Memory Usage**: A MB - B MB
- **CPU Usage**: Low/Medium/High

## Testing

Run tests for AgentName:

```bash
# Unit tests
pytest tests/unit/test_agent_name.py

# Integration tests
pytest tests/integration/test_agent_name_integration.py

# End-to-end tests
pytest tests/e2e/test_agent_name_e2e.py
```

## Examples

### Example 1: Basic Execution

```python
# Code example showing basic usage
```

### Example 2: Advanced Usage

```python
# Code example showing advanced usage
```

## Notes

- Implementation notes
- Known limitations
- Future enhancements

## References

- [NIR Intelligence Platform Documentation](../README.md)
- [Base Agent Documentation](../base_agent.md)
- [Agent Development Guide](../development_guide.md)
```

---

*See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues and support information.*

*Check [LICENSE.md](./LICENSE.md) for legal and compliance details.*

---

## 📞 CONTACT & SUPPORT

- **Website**: https://nir-mistral.org
- **GitHub**: https://github.com/your-repo/NIR_Mistral
- **Email**: support@nir-mistral.org
- **Discord**: https://discord.gg/nir-mistral

---

*Documentation generated on 2026-08-06*  
*Last updated: 2026-08-06*  
*Version: 2.0.0*