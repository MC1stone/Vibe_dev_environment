# NIR_Mistral DeveloperAgent Framework - First Time Usage Guide

## 🎯 Welcome to the DeveloperAgent Framework!

This guide will walk you through your **first time using the NIR_Mistral DeveloperAgent Framework**. By the end of this guide, you'll have:

✅ Created your first agent  
✅ Understood the framework structure  
✅ Run validation and quality checks  
✅ Generated comprehensive tests  
✅ Deployed a working agent  

---

## 📋 Table of Contents

1. [Getting Started](#-getting-started)
2. [Framework Overview](#-framework-overview)
3. [Your First Agent](#-your-first-agent)
4. [Agent Templates](#-agent-templates)
5. [Framework Commands](#-framework-commands)
6. [Agent Development Workflow](#-agent-development-workflow)
7. [Testing Your Agent](#-testing-your-agent)
8. [Quality Enforcement](#-quality-enforcement)
9. [Debugging and Troubleshooting](#-debugging-and-troubleshooting)
10. [Next Steps](#-next-steps)

---

## 🚀 Getting Started

### **Prerequisites**

Before you begin, ensure you have:

1. ✅ **Installed the framework** (see [Installation Guide](./INSTALLATION_GUIDE.md))
2. ✅ **Activated the virtual environment** (if using manual installation)
3. ✅ **Verified the installation** with `python -m dev_framework info`

### **Quick Verification**

```bash
# Check framework is working
python -m dev_framework info

# You should see output like:
# ==========================================================
# NIR Intelligence Platform - Developer Framework
# ==========================================================
# Framework: Version: 1.0.0
# Agents: 21 implemented
# Tests: 3 test files
# Available Commands: generate, validate, test, quality, serve, info, clean
```

If you see this output, **you're ready to start!** 🎉

---

## 🏗️ Framework Overview

### **What is the DeveloperAgent Framework?**

The **DeveloperAgent Framework** is a **comprehensive development acceleration platform** for building **NIR (Near-Infrared) spectroscopy intelligence agents**. It provides:

- 🏗️ **Agent Generation**: Automatically create agent boilerplate code
- 🔍 **Validation**: Ensure agents follow best practices
- 🧪 **Testing**: Generate and run comprehensive tests
- 📊 **Quality**: Enforce code quality standards
- 📚 **Documentation**: Auto-generate agent documentation
- 🚀 **Deployment**: Easy deployment to Venty sticks and servers

### **Framework Architecture**

```
NIR_Mistral/
├── dev_framework/          # Framework code (10 modules, 5,771+ lines)
│   ├── __main__.py         # Entry point
│   ├── cli.py              # Command line interface
│   ├── generator.py        # Agent generation
│   ├── validator.py        # Agent validation
│   ├── quality.py          # Quality enforcement
│   ├── tester.py           # Test runner
│   ├── server.py           # Development server
│   └── docs.py             # Documentation generator
│
├── agents/                # Agent implementations (21 agents)
│   ├── base_agent.py       # Base class for all agents
│   ├── docker_agent.py     # Docker management agent
│   ├── postgresql_agent.py # Database agent
│   └── ...                 # Other agents
│
├── tests/                 # Test files
│   ├── unit/               # Unit tests
│   ├── integration/        # Integration tests
│   └── e2e/                # End-to-end tests
│
├── config/                # Configuration files
│   ├── agent_config.yaml   # Agent configurations
│   └── framework_config.yaml # Framework settings
│
├── ansible/               # Ansible deployment (for Venty stick)
│   ├── playbooks/          # Ansible playbooks
│   ├── inventory/          # Host configurations
│   └── templates/          # Jinja2 templates
│
└── docs/                  # Documentation
```

### **Key Concepts**

1. **Agents**: Individual components that perform specific NIR spectroscopy tasks
2. **Templates**: Pre-defined agent structures for different use cases
3. **Validation**: Automatic checking of agent code and structure
4. **Quality**: Code formatting, linting, and type checking
5. **Commands**: CLI interface for framework operations

---

## 🎯 Your First Agent

### **Step 1: Generate a New Agent**

Let's create your first agent! We'll use the **analysis template** which is perfect for NIR spectroscopy data analysis.

```bash
# Generate a new agent named "MyFirstAgent" with analysis template
python -m dev_framework generate agent MyFirstAgent --template analysis
```

**What this command does:**
- ✅ Creates `agents/my_first_agent.py` - Main agent file
- ✅ Creates `agents/my_first_agent.json` - Agent configuration
- ✅ Creates `tests/unit/test_my_first_agent.py` - Unit tests
- ✅ Creates `tests/integration/test_my_first_agent_integration.py` - Integration tests
- ✅ Creates `tests/e2e/test_my_first_agent_e2e.py` - End-to-end tests
- ✅ Creates `docs/agents/my_first_agent.md` - Documentation
- ✅ Updates `agents/__init__.py` to include your agent

### **Step 2: Verify Agent Creation**

```bash
# Check that the files were created
ls -la agents/my_first_agent.*
ls -la tests/*/test_my_first_agent* 
ls -la docs/agents/my_first_agent.md

# Check that the agent can be imported
python -c "from agents.my_first_agent import MyFirstAgent; print('✅ Agent import successful')"
```

### **Step 3: Examine Your Agent**

Let's look at the generated agent code:

```bash
# View the agent file
cat agents/my_first_agent.py
```

You should see something like this:

```python
#!/usr/bin/env python3
"""
NIR Intelligence Platform - MyFirstAgent
Agent for NIR spectroscopy data processing
"""

import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity, AgentError


class MyFirstAgent(BaseAgent):
    """Agent for MyFirst functionality"""
    
    def __init__(self, **kwargs):
        super().__init__(name="MyFirstAgent", version="1.0.0", **kwargs)
        self.dependencies = ["pandas", "numpy", "scipy", "scikit-learn"]
        self.logger = logging.getLogger(f"Agent.MyFirstAgent")
        
        # Initialize agent-specific attributes
        self._initialize_attributes()
    
    def _initialize_attributes(self):
        """Initialize agent-specific attributes"""
        # Add agent-specific initialization here
        pass
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the agent's primary function"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting MyFirstAgent execution")
            
            # TODO: Implement MyFirstAgent logic
            # Example workflow:
            # 1. Load and validate input data
            # 2. Perform agent-specific processing
            # 3. Generate output
            
            result = {
                "status": "completed",
                "message": "MyFirstAgent execution completed successfully"
            }
            
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(result)
            
        except Exception as e:
            return self._handle_error(e)
    
    def validate(self) -> List[AgentError]:
        """Validate agent configuration and state"""
        errors = super().validate()
        return errors
```

### **Step 4: Customize Your Agent**

Let's customize the agent to perform a simple NIR data analysis task:

```bash
# Edit the agent file
nano agents/my_first_agent.py
```

Replace the `execute` method with this custom implementation:

```python
def execute(self, context: Dict[str, Any]) -> AgentOutput:
    """Execute the agent's primary function - Custom NIR Analysis"""
    try:
        self.status = AgentStatus.PROCESSING
        self.logger.info("Starting MyFirstAgent NIR analysis execution")
        
        # Extract data from context
        input_data = context.get('data', [])
        
        if not input_data:
            self.logger.warning("No input data provided")
            return self._create_success_output({
                "status": "warning", 
                "message": "No input data for analysis"
            })
        
        # Perform simple NIR analysis (example)
        analysis_results = self._analyze_nir_data(input_data)
        
        # Create output
        result = {
            "status": "completed",
            "message": "NIR analysis completed successfully",
            "analysis": analysis_results,
            "timestamp": context.get('timestamp', 'Unknown')
        }
        
        self.status = AgentStatus.COMPLETED
        return self._create_success_output(result)
        
    except Exception as e:
        return self._handle_error(e)


def _analyze_nir_data(self, data: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Perform simple NIR data analysis"""
    try:
        # Example: Calculate basic statistics
        wavelengths = []
        intensities = []
        
        for item in data:
            if 'wavelength' in item and 'intensity' in item:
                wavelengths.append(item['wavelength'])
                intensities.append(item['intensity'])
        
        if wavelengths and intensities:
            return {
                "sample_count": len(wavelengths),
                "wavelength_range": {
                    "min": min(wavelengths),
                    "max": max(wavelengths),
                    "mean": sum(wavelengths) / len(wavelengths)
                },
                "intensity_stats": {
                    "min": min(intensities),
                    "max": max(intensities),
                    "mean": sum(intensities) / len(intensities),
                    "std": self._calculate_std(intensities)
                }
            }
        else:
            return {"error": "No valid NIR data found"}
            
    except Exception as e:
        self.logger.error(f"Error analyzing NIR data: {e}")
        return {"error": str(e)}


def _calculate_std(self, values: List[float]) -> float:
    """Calculate standard deviation"""
    import math
    if len(values) < 2:
        return 0.0
    mean = sum(values) / len(values)
    variance = sum((x - mean) ** 2 for x in values) / len(values)
    return math.sqrt(variance)
```

Save the file and test it:

```bash
# Test the agent can be imported
python -c "from agents.my_first_agent import MyFirstAgent; print('✅ Custom agent import successful')"
```

---

## 📚 Agent Templates

The framework provides **6 different templates** for agent generation:

| Template | Description | Use Case | Dependencies |
|----------|-------------|----------|--------------|
| `default` | Generic agent template | General purpose | - |
| `data` | Data processing agent | Data loading, validation, preprocessing | pandas, numpy |
| `ml` | Machine learning agent | Model training, evaluation, prediction | tensorflow, keras, scikit-learn, numpy |
| `db` | Database agent | Database connections, queries | sqlalchemy, psycopg2 |
| `api` | API/Web service agent | HTTP endpoints, web services | fastapi, uvicorn, requests |
| `analysis` | Statistical analysis agent | NIR spectroscopy analysis | pandas, numpy, scipy, scikit-learn |

### **Template Examples**

#### **1. Data Processing Agent**
```bash
# Generate a data processing agent
python -m dev_framework generate agent DataProcessor --template data
```

This creates an agent with:
- Data loading methods
- Data validation methods  
- Data preprocessing methods
- Pandas and NumPy dependencies

#### **2. Machine Learning Agent**
```bash
# Generate a machine learning agent
python -m dev_framework generate agent MLAgent --template ml
```

This creates an agent with:
- Model training methods
- Model evaluation methods
- Model saving/loading methods
- TensorFlow/Keras/Scikit-learn dependencies

#### **3. Database Agent**
```bash
# Generate a database agent
python -m dev_framework generate agent DBAgent --template db
```

This creates an agent with:
- Database connection methods
- Query execution methods
- SQLAlchemy integration
- PostgreSQL support

---

## 🎯 Framework Commands

The framework provides **7 main commands**:

### **1. `info` - Project Information**
```bash
# Show project and framework information
python -m dev_framework info
```

**Output**: Framework version, agents, tests, Docker services

### **2. `generate` - Agent Generation**
```bash
# Generate a new agent
python -m dev_framework generate agent AgentName --template analysis

# Force overwrite existing agent
python -m dev_framework generate agent AgentName --template analysis --force

# Generate tests for an agent
python -m dev_framework generate tests --agent AgentName

# Generate documentation for an agent
python -m dev_framework generate docs --agent AgentName
```

### **3. `validate` - Agent Validation**
```bash
# Validate all agents
python -m dev_framework validate

# Validate specific agent
python -m dev_framework validate --agent AgentName
```

**What it checks**:
- ✅ Agent class exists and inherits from BaseAgent
- ✅ Required `__init__` method with `super().__init__()` call
- ✅ Required attributes (name, version, status, errors)
- ✅ Syntax validation
- ✅ Import validation
- ✅ Configuration file validation

### **4. `test` - Run Tests**
```bash
# Run tests for all agents
python -m dev_framework test --all

# Run tests for specific agent
python -m dev_framework test --agent AgentName

# Run with coverage
python -m dev_framework test --agent AgentName --coverage
```

### **5. `quality` - Quality Checks**
```bash
# Check quality for all files
python -m dev_framework quality --check --all

# Check quality for specific agent
python -m dev_framework quality --check --agent AgentName

# Auto-fix quality issues
python -m dev_framework quality --fix --all
```

**Tools used**:
- ✅ **Black**: Code formatting
- ✅ **Flake8**: Linting
- ✅ **Isort**: Import sorting
- ✅ **Mypy**: Type checking

### **6. `serve` - Development Server**
```bash
# Start development server
python -m dev_framework serve

# Start on specific port
python -m dev_framework serve --port 8080

# Start with debug mode
python -m dev_framework serve --debug
```

**Features**:
- HTTP API endpoints
- Hot-reload for development
- Agent execution interface
- REST API for agent management

### **7. `clean` - Clean Build Artifacts**
```bash
# Clean __pycache__ files
python -m dev_framework clean

# Clean specific directories
python -m dev_framework clean --dir build/ --dir dist/
```

---

## 🔄 Agent Development Workflow

### **Step 1: Generate Agent**
```bash
python -m dev_framework generate agent MyAgent --template analysis
```

### **Step 2: Customize Agent**
```bash
# Edit the agent file
nano agents/my_agent.py

# Add your custom logic to the execute() method
# Add any required dependencies to the dependencies list
```

### **Step 3: Validate Agent**
```bash
# Validate your agent
python -m dev_framework validate --agent MyAgent

# Fix any validation errors
```

### **Step 4: Test Agent**
```bash
# Run unit tests
python -m dev_framework test --agent MyAgent

# Fix any test failures
```

### **Step 5: Check Quality**
```bash
# Check code quality
python -m dev_framework quality --check --agent MyAgent

# Auto-fix quality issues
python -m dev_framework quality --fix --agent MyAgent
```

### **Step 6: Generate Documentation**
```bash
# Generate documentation
python -m dev_framework generate docs --agent MyAgent
```

### **Step 7: Deploy Agent**
```bash
# For Venty stick (using Ansible)
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/deploy_framework.yml

# For local development
python -m dev_framework serve
```

---

## 🧪 Testing Your Agent

### **1. Unit Tests**

The framework automatically generates **unit tests** for your agent. These test:

- ✅ Agent initialization
- ✅ Agent attributes
- ✅ Agent dependencies
- ✅ Agent execution
- ✅ Agent validation
- ✅ Error handling

**Run unit tests**:
```bash
# Run unit tests for your agent
python -m pytest tests/unit/test_my_first_agent.py -v

# Run all unit tests
python -m pytest tests/unit/ -v
```

### **2. Integration Tests**

Integration tests verify that your agent works with other components:

```bash
# Run integration tests for your agent
python -m pytest tests/integration/test_my_first_agent_integration.py -v

# Run all integration tests
python -m pytest tests/integration/ -v
```

### **3. End-to-End Tests**

E2E tests verify complete workflows:

```bash
# Run E2E tests for your agent
python -m pytest tests/e2e/test_my_first_agent_e2e.py -v

# Run all E2E tests
python -m pytest tests/e2e/ -v
```

### **4. Using the Framework Test Command**

```bash
# Test specific agent
python -m dev_framework test --agent MyFirstAgent

# Test all agents
python -m dev_framework test --all

# Test with coverage
python -m dev_framework test --agent MyFirstAgent --coverage
```

### **5. Test Customization**

You can customize the generated tests by editing the test files:

```bash
# Edit unit tests
nano tests/unit/test_my_first_agent.py

# Edit integration tests
nano tests/integration/test_my_first_agent_integration.py

# Edit E2E tests
nano tests/e2e/test_my_first_agent_e2e.py
```

---

## 📊 Quality Enforcement

### **1. Check Quality**

```bash
# Check quality for all files
python -m dev_framework quality --check --all

# Check quality for specific agent
python -m dev_framework quality --check --agent MyFirstAgent
```

### **2. Auto-Fix Quality Issues**

```bash
# Auto-fix all quality issues
python -m dev_framework quality --fix --all

# Auto-fix for specific agent
python -m dev_framework quality --fix --agent MyFirstAgent
```

### **3. Individual Quality Tools**

You can also run the quality tools individually:

```bash
# Black - Code formatting
black dev_framework/
black agents/

# Flake8 - Linting
flake8 dev_framework/
flake8 agents/

# Isort - Import sorting
isort dev_framework/
isort agents/

# Mypy - Type checking
mypy dev_framework/
mypy agents/
```

### **4. Quality Configuration**

The framework uses configuration files for quality tools:

- `.flake8` - Flake8 configuration
- `.isort.cfg` - Isort configuration
- `mypy.ini` - Mypy configuration
- `pytest.ini` - Pytest configuration

You can customize these files to match your project's standards.

---

## 🐛 Debugging and Troubleshooting

### **1. Common Issues**

#### **Import Error: ModuleNotFoundError**

**Error**: `ModuleNotFoundError: No module named 'agents.my_agent'`

**Solution**:
```bash
# Check if the agent file exists
ls -la agents/my_agent.py

# Check if __init__.py includes the agent
grep "my_agent" agents/__init__.py

# If not, regenerate the agent
python -m dev_framework generate agent MyAgent --force
```

#### **Validation Error: Missing super().__init__()**

**Error**: `Missing super().__init__() call in __init__`

**Solution**:
```bash
# Edit your agent file
nano agents/my_agent.py

# Ensure your __init__ method calls super().__init__()
def __init__(self, **kwargs):
    super().__init__(name="MyAgent", version="1.0.0", **kwargs)
    # Your initialization code
```

#### **Test Failure: ImportError in Tests**

**Error**: `ImportError: cannot import name 'MyAgent'`

**Solution**:
```bash
# Check the test file imports
head -20 tests/unit/test_my_agent.py

# Ensure the import matches the agent class name
# If your agent is MyAgent, the import should be:
from agents.my_agent import MyAgent
```

### **2. Debugging Tools**

#### **Logging**

The framework uses Python's `logging` module. You can configure the log level:

```bash
# Set debug log level
python -m dev_framework serve --log-level DEBUG

# View logs
 tail -f /var/log/NIR_Mistral/framework.log
```

#### **Python Debugger**

Add breakpoints in your agent code:

```python
def execute(self, context: Dict[str, Any]) -> AgentOutput:
    import pdb; pdb.set_trace()  # Breakpoint here
    # Rest of your code
```

Then run your agent:
```bash
python -c "from agents.my_agent import MyAgent; agent = MyAgent(); agent.execute({})"
```

#### **Print Debugging**

Add print statements to your agent:

```python
def execute(self, context: Dict[str, Any]) -> AgentOutput:
    print(f"DEBUG: Context: {context}")
    print(f"DEBUG: Status: {self.status}")
    # Rest of your code
```

### **3. Framework Debug Mode**

```bash
# Run framework in debug mode
python -m dev_framework serve --debug

# This enables:
# - Detailed logging
# - Stack traces for errors
# - Development mode features
```

---

## 🎯 Next Steps

### **1. Explore More Templates**

Try generating agents with different templates:

```bash
# Data processing agent
python -m dev_framework generate agent DataProcessor --template data

# Machine learning agent
python -m dev_framework generate agent MLAgent --template ml

# Database agent
python -m dev_framework generate agent DBAgent --template db
```

### **2. Create a Complete Agent**

Now that you understand the basics, try creating a **complete, functional agent** that:

1. ✅ Accepts input data
2. ✅ Performs meaningful NIR analysis
3. ✅ Returns structured results
4. ✅ Handles errors gracefully
5. ✅ Has comprehensive tests
6. ✅ Passes all quality checks

### **3. Integrate with Existing Agents**

The framework includes **21 pre-built agents**. Learn how to use them:

```bash
# List all available agents
python -m dev_framework info | grep -A 25 "Agents:"

# Import and use existing agents
from agents.docker_agent import DockerAgent
from agents.postgresql_agent import PostgreSQLAgent

# Create instances
docker_agent = DockerAgent()
postgres_agent = PostgreSQLAgent()

# Use agents in your code
docker_agent.execute({})
postgres_agent.execute({})
```

### **4. Advanced Features**

#### **Agent Orchestration**

Create agents that use other agents:

```python
from agents.base_agent import BaseAgent
from agents.data_preparation_agent import DataPreparationAgent

class AnalysisPipelineAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(name="AnalysisPipelineAgent", version="1.0.0", **kwargs)
        self.data_agent = DataPreparationAgent()
        
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        # Use data agent to prepare data
        prepared_data = self.data_agent.execute(context)
        
        # Perform analysis on prepared data
        analysis_result = self._analyze(prepared_data)
        
        return self._create_success_output(analysis_result)
```

#### **Custom Templates**

Create your own agent templates:

```bash
# Copy an existing template
cp dev_framework/templates/agent/analysis.py.tpl dev_framework/templates/agent/my_template.py.tpl

# Edit the template
nano dev_framework/templates/agent/my_template.py.tpl

# Use your template
python -m dev_framework generate agent MyAgent --template my_template
```

#### **Custom Validation Rules**

Add custom validation to your agents:

```python
def validate(self) -> List[AgentError]:
    errors = super().validate()
    
    # Add custom validation
    if not hasattr(self, 'required_attribute'):
        errors.append(AgentError(
            message="Missing required_attribute",
            severity=ErrorSeverity.HIGH,
            code="CUSTOM_001"
        ))
    
    return errors
```

### **5. Deployment Options**

#### **Local Development**
```bash
# Start development server
python -m dev_framework serve

# Access at: http://localhost:8080
```

#### **Venty Stick Deployment**
```bash
# Using Ansible
ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/deploy_framework.yml

# Access at: http://<venty-stick-ip>:8080
```

#### **Docker Deployment**
```bash
# Build and run with Docker
docker-compose up -d

# Access at: http://localhost:8080
```

---

## 📚 Additional Resources

- [Installation Guide](./INSTALLATION_GUIDE.md) - Complete installation instructions
- [DeveloperAgent Framework Documentation](../dev_framework/README.md) - Framework details
- [Ansible Setup Documentation](../ansible/README.md) - Ansible deployment guide
- [Project Finalization Report](../PROJECT_FINALIZATION_REPORT.md) - Project status
- [System Test Report](../SYSTEM_TEST_REPORT.md) - System testing results

---

## 🤝 Support and Community

### **Getting Help**

1. **Check the documentation** - Most questions are answered in the docs
2. **Review the examples** - Look at existing agents for patterns
3. **Run validation** - `python -m dev_framework validate` often reveals issues
4. **Check logs** - Framework logs contain detailed error information

### **Common Questions**

#### **Q: How do I create an agent that processes NIR spectra?**
**A**: Use the `analysis` template and customize the `execute()` method to process your NIR data.

#### **Q: How do I connect to a database?**
**A**: Use the `db` template or import the `PostgreSQLAgent` from existing agents.

#### **Q: How do I test my agent?**
**A**: Run `python -m dev_framework test --agent YourAgent` or use pytest directly.

#### **Q: How do I fix quality issues?**
**A**: Run `python -m dev_framework quality --fix --all` for auto-fixing, or manually fix issues.

#### **Q: How do I deploy to a Venty stick?**
**A**: Use the Ansible playbooks: `ansible-playbook -i ansible/inventory/hosts.yml ansible/playbooks/setup_venty_stick.yml`

---

## 🏁 Conclusion

You have successfully completed the **First Time Usage Guide**! 🎉

### **What You've Accomplished**

✅ **Installed the framework** (if not already done)  
✅ **Generated your first agent** using the analysis template  
✅ **Customized the agent** with NIR data analysis logic  
✅ **Validated your agent** using the framework validation system  
✅ **Tested your agent** with the built-in test framework  
✅ **Checked code quality** with the quality enforcement tools  
✅ **Understood the workflow** for agent development  

### **What You Can Do Next**

🚀 **Create more agents** with different templates  
🔧 **Customize existing agents** for your specific needs  
🧪 **Write comprehensive tests** for your agents  
📊 **Improve code quality** with the quality tools  
🎯 **Deploy to production** using Ansible or Docker  
🔄 **Integrate with other agents** for complex workflows  

### **You're Now Ready to Build Amazing NIR Intelligence Agents!**

The **DeveloperAgent Framework** provides everything you need to **rapidly develop, test, and deploy** NIR spectroscopy intelligence agents. Whether you're working on **data preprocessing, statistical analysis, machine learning, or database integration**, the framework has you covered.

**Happy Agent Development!** 🎊

---

## 📄 License

This guide is part of the **NIR_Mistral DeveloperAgent Framework** and is licensed under the same terms as the main project.