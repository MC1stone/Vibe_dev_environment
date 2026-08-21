# DeveloperAgent Framework (DAF)

**DeveloperAgent Framework** is a comprehensive development toolkit for the **NIR Intelligence Platform**. It accelerates agent development, testing, validation, and deployment through automation and best practices.

## Features

### 🚀 Agent Generation
- **Code Generation**: Create new agents from templates (data, ML, DB, API, analysis)
- **Configuration**: Auto-generate JSON configuration files
- **Tests**: Generate unit, integration, and end-to-end tests
- **Documentation**: Auto-generate agent documentation

### ✅ Validation
- **Agent Validation**: Check agent implementations against requirements
- **Code Quality**: Enforce PEP 8, type hints, and best practices
- **Mandatory Files**: Verify all required files are present
- **Dependency Checking**: Validate agent dependencies

### 🧪 Testing
- **Test Runner**: Execute unit, integration, and E2E tests
- **Coverage Reporting**: Generate test coverage reports
- **Test Discovery**: Find and organize all tests
- **Test Generation**: Auto-create test stubs for new agents

### 🎨 Code Quality
- **Formatting**: Auto-format code with Black
- **Linting**: Check code with Flake8
- **Import Sorting**: Organize imports with isort
- **Type Checking**: Validate types with mypy
- **Auto-Fix**: Automatically fix formatting and import issues

### 🌐 Development Server
- **Hot-Reload**: Automatic reloading on code changes
- **REST API**: Test agents via HTTP endpoints
- **Agent Management**: Load, execute, and manage agents dynamically
- **Health Monitoring**: Check system status

### 📚 Documentation
- **Agent Docs**: Generate comprehensive agent documentation
- **API Docs**: Create API reference documentation
- **Development Guide**: Generate development guidelines
- **Installation Guide**: Create setup instructions

## Installation

The DeveloperAgent Framework is included with the NIR Intelligence Platform. No additional installation is required.

### Optional Dependencies

For full functionality, install these packages:

```bash
pip install black flake8 isort mypy pytest pytest-cov
```

## Usage

### Quick Start

```bash
# Show framework information
python -m dev_framework info

# Generate a new agent
python -m dev_framework generate agent NewAgentName

# Generate with specific template
python -m dev_framework generate agent CalibrationAgent --template ml

# Validate all agents
python -m dev_framework validate

# Run tests
python -m dev_framework test

# Check code quality
python -m dev_framework quality

# Start development server
python -m dev_framework serve
```

### Command Reference

#### `generate` - Generate new components

```bash
# Generate a new agent
python -m dev_framework generate agent AgentName [--template TEMPLATE] [--no-python] [--no-json] [--no-tests] [--no-docs] [--force]

# Generate tests for all agents
python -m dev_framework generate tests --all [--type TYPE]

# Generate tests for specific agent
python -m dev_framework generate tests --agent AgentName [--type TYPE]

# Generate documentation
python -m dev_framework generate docs [--all | --agent AgentName]
```

**Templates**: `default`, `data`, `ml`, `db`, `api`, `analysis`

**Test Types**: `unit`, `integration`, `e2e`, `all`

#### `validate` - Validate agents and configuration

```bash
# Validate all agents
python -m dev_framework validate [--strict] [--fix]

# Validate specific agent
python -m dev_framework validate --agent AgentName [--strict] [--fix]
```

**Options**:
- `--strict`: Fail on warnings
- `--fix`: Attempt to auto-fix issues

#### `test` - Run agent tests

```bash
# Run all tests
python -m dev_framework test [--type TYPE] [--coverage] [--verbose] [--watch]

# Run tests for specific agent
python -m dev_framework test --agent AgentName [--type TYPE] [--coverage] [--verbose]
```

**Options**:
- `--type`: `unit`, `integration`, `e2e`, `all`
- `--coverage`: Enable coverage reporting
- `--verbose`: Show detailed output
- `--watch`: Watch for changes and re-run tests

#### `quality` - Check and enforce code quality

```bash
# Check quality for all files
python -m dev_framework quality [--check | --fix] [--agent AgentName]

# Check specific agent
python -m dev_framework quality --agent AgentName [--check | --fix]
```

**Options**:
- `--check`: Check quality without fixing (default)
- `--fix`: Auto-fix quality issues

#### `serve` - Start development server

```bash
# Start server with all agents
python -m dev_framework serve [--port PORT] [--host HOST] [--no-reload]

# Serve specific agent
python -m dev_framework serve --agent AgentName [--port PORT] [--host HOST] [--no-reload]
```

**Options**:
- `--port`: Server port (default: 8001)
- `--host`: Server host (default: localhost)
- `--no-reload`: Disable hot-reload

#### `info` - Show framework and project information

```bash
python -m dev_framework info
```

#### `clean` - Clean build artifacts

```bash
# Clean everything
python -m dev_framework clean --all

# Clean specific artifacts
python -m dev_framework clean [--tests] [--docs]
```

## Agent Templates

The framework provides several templates for different agent types:

| Template | Description | Dependencies |
|----------|-------------|--------------|
| `default` | Generic agent | None |
| `data` | Data processing | pandas, numpy |
| `ml` | Machine learning | tensorflow, keras, scikit-learn |
| `db` | Database | sqlalchemy, psycopg2 |
| `api` | API/Web service | fastapi, uvicorn, requests |
| `analysis` | Statistical analysis | pandas, numpy, scipy, scikit-learn |

## Project Structure

```
nir-intelligence-platform/
├── agents/                          # Agent implementations
│   ├── __init__.py
│   ├── base_agent.py               # Base class for all agents
│   ├── data_preparation_agent.py
│   └── ...
├── tests/                          # Test files
│   ├── __init__.py
│   ├── conftest.py
│   ├── unit/
│   │   └── test_*.py
│   ├── integration/
│   │   └── test_*_integration.py
│   └── e2e/
│       └── test_*_e2e.py
├── docs/                           # Documentation
│   ├── index.md
│   ├── agents/
│   │   └── *.md
│   └── api_reference.md
├── dev_framework/                  # Development framework
│   ├── __init__.py
│   ├── cli.py
│   ├── generator.py
│   ├── validator.py
│   ├── quality.py
│   ├── tester.py
│   ├── server.py
│   ├── docs.py
│   ├── setup_framework.py
│   ├── config/
│   │   └── framework_config.yaml
│   └── templates/
│       └── agent/
│           └── *.tpl
├── config/                         # Configuration files
│   └── agent_config.yaml
└── scripts/                        # Utility scripts
    └── main_orchestrator.py
```

## Development Workflow

### 1. Create a New Agent

```bash
# Generate agent with template
python -m dev_framework generate agent SensorQualityAgent --template data

# Or create manually
touch agents/sensor_quality_agent.py
```

### 2. Implement the Agent

```python
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity

class SensorQualityAgent(BaseAgent):
    def __init__(self, **kwargs):
        super().__init__(name="SensorQualityAgent", version="1.0.0", **kwargs)
        self.dependencies = ["pandas", "numpy"]
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        try:
            self.status = AgentStatus.PROCESSING
            # Your implementation here
            result = {"status": "completed"}
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(result)
        except Exception as e:
            return self._handle_error(e)
```

### 3. Validate the Agent

```bash
python -m dev_framework validate --agent SensorQualityAgent
```

### 4. Generate Tests

```bash
python -m dev_framework generate tests --agent SensorQualityAgent
```

### 5. Implement Tests

Edit the generated test files in `tests/` directory.

### 6. Run Tests

```bash
python -m dev_framework test --agent SensorQualityAgent
```

### 7. Check Code Quality

```bash
python -m dev_framework quality --agent SensorQualityAgent --fix
```

### 8. Generate Documentation

```bash
python -m dev_framework generate docs --agent SensorQualityAgent
```

## REST API (Development Server)

### Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/agents` | List all available agents |
| GET | `/agents/{agent_name}` | Get info about a specific agent |
| POST | `/agents/{agent_name}` | Execute a specific agent |
| GET | `/health` | Health check |

### Example Requests

```bash
# List all agents
curl http://localhost:8001/agents

# Get agent info
curl http://localhost:8001/agents/DataPreparationAgent

# Execute agent
curl -X POST http://localhost:8001/agents/DataPreparationAgent \
  -H "Content-Type: application/json" \
  -d '{"iteration": 1, "data": {}}'

# Health check
curl http://localhost:8001/health
```

## Best Practices

### Agent Development

1. **Inherit from BaseAgent**: All agents must extend `BaseAgent`
2. **Implement Required Methods**: At minimum, implement `execute()`
3. **Use Proper Error Handling**: Use `try/except` and `_handle_error()`
4. **Logging**: Use `self.logger` instead of `print()`
5. **Type Hints**: Add type hints to all methods
6. **Documentation**: Add docstrings to all classes and methods

### Testing

1. **Unit Tests**: Test individual methods in isolation
2. **Integration Tests**: Test agent interactions
3. **E2E Tests**: Test complete workflows
4. **Edge Cases**: Test error conditions and edge cases
5. **Mocking**: Use mocking for external dependencies

### Code Quality

1. **PEP 8**: Follow Python style guidelines
2. **Line Length**: Keep lines under 120 characters
3. **Type Safety**: Use type hints and mypy
4. **Imports**: Use isort for consistent import ordering
5. **Formatting**: Use Black for consistent formatting

## Configuration

The framework uses configuration files in `dev_framework/config/`:

- `framework_config.yaml`: Main framework configuration
- `.flake8`: Flake8 linter configuration
- `.isort.cfg`: isort import sorting configuration
- `mypy.ini`: mypy type checker configuration
- `pytest.ini`: pytest test runner configuration

## Troubleshooting

### Common Issues

#### Framework commands not found
```bash
# Make sure you're in the project root
cd /path/to/nir-intelligence-platform

# Run from project root
python -m dev_framework info
```

#### Missing dependencies
```bash
pip install black flake8 isort mypy pytest pytest-cov
```

#### Port already in use
```bash
# Find and kill the process
lsof -i :8001
kill -9 <PID>

# Or use a different port
python -m dev_framework serve --port 8002
```

#### Agent not found
```bash
# Check the agent name (case-sensitive)
python -m dev_framework info

# Make sure the agent file exists in agents/
ls agents/*_agent.py
```

## Contributing

Contributions to the DeveloperAgent Framework are welcome! Please follow these guidelines:

1. **Fork the repository**
2. **Create a feature branch** (`git checkout -b feature/amazing-feature`)
3. **Commit your changes** (`git commit -m 'Add amazing feature'`)
4. **Push to the branch** (`git push origin feature/amazing-feature`)
5. **Open a Pull Request**

## License

This framework is part of the NIR Intelligence Platform and is licensed under the MIT License.

## Support

For questions or support, please contact the development team or open an issue in the repository.

---

**Version**: 1.0.0  
**Author**: NIR Development Team  
**License**: MIT
