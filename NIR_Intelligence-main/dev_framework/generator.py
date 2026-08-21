#!/usr/bin/env python3
"""
DeveloperAgent Framework - Agent Generator

Generates agent code, configuration, tests, and documentation from templates.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger('AgentGenerator')


@dataclass
class TemplateConfig:
    """Configuration for code templates"""
    name: str
    description: str
    dependencies: List[str] = field(default_factory=list)
    base_class: str = "BaseAgent"
    required_methods: List[str] = field(default_factory=list)
    template_dir: str = "templates"


@dataclass
class GenerationResult:
    """Result of code generation"""
    success: bool
    files_created: List[str] = field(default_factory=list)
    files_modified: List[str] = field(default_factory=list)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class TemplateManager:
    """Manages code templates for different agent types"""
    
    # Agent type templates
    AGENT_TEMPLATES = {
        'default': TemplateConfig(
            name="default",
            description="Generic agent template",
            dependencies=[],
            base_class="BaseAgent",
            required_methods=["execute"],
            template_dir="templates/agent"
        ),
        'data': TemplateConfig(
            name="data",
            description="Data processing agent template",
            dependencies=["pandas", "numpy"],
            base_class="BaseAgent",
            required_methods=["execute", "_load_data", "_validate_data", "_preprocess_data"],
            template_dir="templates/agent"
        ),
        'ml': TemplateConfig(
            name="ml",
            description="Machine learning agent template",
            dependencies=["tensorflow", "keras", "scikit-learn", "numpy"],
            base_class="BaseAgent",
            required_methods=["execute", "_train_model", "_evaluate_model", "_save_model"],
            template_dir="templates/agent"
        ),
        'db': TemplateConfig(
            name="db",
            description="Database agent template",
            dependencies=["sqlalchemy", "psycopg2"],
            base_class="BaseAgent",
            required_methods=["execute", "_connect", "_query", "_disconnect"],
            template_dir="templates/agent"
        ),
        'api': TemplateConfig(
            name="api",
            description="API/web service agent template",
            dependencies=["fastapi", "uvicorn", "requests"],
            base_class="BaseAgent",
            required_methods=["execute", "_start_server", "_handle_request"],
            template_dir="templates/agent"
        ),
        'analysis': TemplateConfig(
            name="analysis",
            description="Statistical analysis agent template",
            dependencies=["pandas", "numpy", "scipy", "scikit-learn"],
            base_class="BaseAgent",
            required_methods=["execute", "_perform_pca", "_perform_pls", "_perform_cluster"],
            template_dir="templates/agent"
        )
    }
    
    def __init__(self, templates_dir: Optional[str] = None):
        self.templates_dir = Path(templates_dir or 
            os.path.join(os.path.dirname(__file__), 'templates'))
        
    def get_template(self, template_name: str) -> Optional[TemplateConfig]:
        """Get template configuration by name"""
        return self.AGENT_TEMPLATES.get(template_name)
    
    def get_template_path(self, template_name: str, file_type: str) -> Optional[Path]:
        """Get path to template file"""
        template = self.get_template(template_name)
        if not template:
            return None
            
        template_path = self.templates_dir / template.template_dir / file_type
        
        # Try different extensions
        for ext in ['.py.tpl', '.tpl', '.py', '']:
            test_path = template_path.with_suffix(ext)
            if test_path.exists():
                return test_path
        
        return None
    
    def render_template(self, template_path: Path, context: Dict[str, Any]) -> str:
        """Render template with context variables"""
        if not template_path.exists():
            raise FileNotFoundError(f"Template not found: {template_path}")
        
        with open(template_path, 'r') as f:
            content = f.read()
        
        # Simple template rendering (can be replaced with Jinja2 if needed)
        for key, value in context.items():
            placeholder = f"{{{{key}}}}"
            content = content.replace(placeholder, str(value))
        
        return content


class AgentGenerator:
    """Generates agent code and configuration files"""
    
    def __init__(self):
        self.template_manager = TemplateManager()
        self.project_root = Path(__file__).parent.parent
        self.agents_dir = self.project_root / 'agents'
        self.tests_dir = self.project_root / 'tests'
        self.docs_dir = self.project_root / 'docs'
        
        # Ensure directories exist
        self.agents_dir.mkdir(parents=True, exist_ok=True)
        self.tests_dir.mkdir(parents=True, exist_ok=True)
        self.docs_dir.mkdir(parents=True, exist_ok=True)
    
    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case"""
        # Handle acronyms (e.g., NIRAgent -> nir_agent)
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
        return name.lower()
    
    def _to_file_name(self, name: str, prefix: str = '', suffix: str = '') -> str:
        """Convert agent name to file name"""
        snake_name = self._to_snake_case(name)
        if prefix:
            snake_name = f"{prefix}_{snake_name}"
        if suffix:
            snake_name = f"{snake_name}_{suffix}"
        return snake_name
    
    def _get_agent_context(self, name: str, template: str) -> Dict[str, Any]:
        """Get context for template rendering"""
        snake_name = self._to_snake_case(name)
        file_name = self._to_file_name(name)
        
        template_config = self.template_manager.get_template(template)
        if not template_config:
            template_config = self.template_manager.get_template('default')
        
        # Get existing agents for imports
        existing_agents = []
        if self.agents_dir.exists():
            for f in self.agents_dir.glob('*_agent.py'):
                existing_agents.append(f.stem.replace('_agent', ''))
        
        return {
            'agent_name': name,
            'snake_name': snake_name,
            'file_name': file_name,
            'class_name': name,
            'template': template,
            'base_class': template_config.base_class,
            'dependencies': template_config.dependencies,
            'required_methods': template_config.required_methods,
            'existing_agents': existing_agents,
            'project_root': str(self.project_root),
            'agents_dir': str(self.agents_dir),
            'year': '2026',
            'author': 'NIR Development Team'
        }
    
    def generate_python_file(self, name: str, template: str, force: bool = False) -> Dict[str, Any]:
        """Generate Python agent file"""
        context = self._get_agent_context(name, template)
        file_name = f"{self._to_file_name(name)}.py"
        file_path = self.agents_dir / file_name
        
        # Check if file exists
        if file_path.exists() and not force:
            return {
                'success': False,
                'error': f"File already exists: {file_path}",
                'path': str(file_path)
            }
        
        # Get template
        template_path = self.template_manager.get_template_path(template, 'agent.py.tpl')
        if not template_path:
            template_path = self.template_manager.get_template_path('default', 'agent.py.tpl')
        
        if not template_path:
            # Create default template if not found
            template_content = self._create_default_agent_template(context)
        else:
            template_content = self.template_manager.render_template(template_path, context)
        
        # Write file
        try:
            with open(file_path, 'w') as f:
                f.write(template_content)
            
            return {
                'success': True,
                'path': str(file_path),
                'file_name': file_name
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'path': str(file_path)
            }
    
    def _create_default_agent_template(self, context: Dict[str, Any]) -> str:
        """Create default agent template"""
        class_name = context['class_name']
        agent_name = context['agent_name']
        description = context.get('description', 'Agent for NIR spectroscopy data processing')
        dependencies = context['dependencies']
        
        return f'''#!/usr/bin/env python3
"""
NIR Intelligence Platform - {class_name}
{description}
"""

import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity, AgentError


class {class_name}(BaseAgent):
    """Agent for {class_name.replace("Agent", "")} functionality"""
    
    def __init__(self, **kwargs):
        super().__init__(name="{class_name}", version="1.0.0", **kwargs)
        self.dependencies = {dependencies}
        self.logger = logging.getLogger(f"Agent.{class_name}")
        
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
            self.logger.info("Starting {class_name} execution")
            
            # TODO: Implement {class_name} logic
            # Example workflow:
            # 1. Load and validate input data
            # 2. Perform agent-specific processing
            # 3. Generate output
            
            result = {{
                "status": "completed",
                "message": "{class_name} execution completed successfully"
            }}
            
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(result)
            
        except Exception as e:
            return self._handle_error(e)
    
    def validate(self) -> List[AgentError]:
        """Validate agent configuration and state"""
        errors = super().validate()
        
        # Add agent-specific validation
        # Example: Check required dependencies
        # for dep in self.dependencies:
        #     try:
        #         __import__(dep)
        #     except ImportError:
        #         self.log_error(
        #             f"Missing dependency: {{dep}}",
        #             ErrorSeverity.HIGH,
        #             {{"dependency": dep}},
        #             f"Install with: pip install {{dep}}"
        #         )
        
        return errors


if __name__ == "__main__":
    # Allow direct execution for testing
    agent = {class_name}()
    output = agent.initialize()
    print(f"{class_name} initialized: {{output.status.name}}")
'''
    
    def generate_json_file(self, name: str, template: str, force: bool = False) -> Dict[str, Any]:
        """Generate JSON configuration file"""
        context = self._get_agent_context(name, template)
        file_name = f"{self._to_file_name(name)}.json"
        file_path = self.agents_dir / file_name
        
        # Check if file exists
        if file_path.exists() and not force:
            return {
                'success': False,
                'error': f"File already exists: {file_path}",
                'path': str(file_path)
            }
        
        # Create JSON configuration
        config = {
            "name": context['class_name'],
            "version": "1.0.0",
            "description": f"{context['class_name'].replace('Agent', '')} for NIR Intelligence Platform",
            "type": template,
            "dependencies": context['dependencies'],
            "required_methods": context['required_methods'],
            "configuration": {
                "enabled": True,
                "params": {}
            },
            "quality_control": {
                "min_performance": 0.80,
                "max_errors": 0,
                "timeout_seconds": 300
            },
            "documentation": {
                "author": context['author'],
                "created": context['year'],
                "updated": context['year']
            }
        }
        
        # Add template-specific configuration
        if template == 'ml':
            config['configuration']['params'] = {
                "model_type": "CNN",
                "epochs": 50,
                "batch_size": 32,
                "learning_rate": 0.001
            }
        elif template == 'db':
            config['configuration']['params'] = {
                "host": "localhost",
                "port": 5432,
                "database": "nir_metadata",
                "user": "nir_user"
            }
        elif template == 'data':
            config['configuration']['params'] = {
                "input_directory": "data/raw",
                "output_directory": "data/processed",
                "default_format": "HDF5",
                "batch_size": 1000
            }
        
        try:
            with open(file_path, 'w') as f:
                json.dump(config, f, indent=2)
            
            return {
                'success': True,
                'path': str(file_path),
                'file_name': file_name
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'path': str(file_path)
            }
    
    def generate_test_file(self, name: str, template: str, test_type: str = 'unit', force: bool = False) -> Dict[str, Any]:
        """Generate test file for agent"""
        context = self._get_agent_context(name, template)
        snake_name = self._to_snake_case(name)
        
        # Determine test file path
        if test_type == 'unit':
            test_dir = self.tests_dir / 'unit'
            file_name = f"test_{snake_name}.py"
        elif test_type == 'integration':
            test_dir = self.tests_dir / 'integration'
            file_name = f"test_{snake_name}_integration.py"
        else:  # e2e
            test_dir = self.tests_dir / 'e2e'
            file_name = f"test_{snake_name}_e2e.py"
        
        test_dir.mkdir(parents=True, exist_ok=True)
        file_path = test_dir / file_name
        
        # Check if file exists
        if file_path.exists() and not force:
            return {
                'success': False,
                'error': f"File already exists: {file_path}",
                'path': str(file_path)
            }
        
        # Create test content
        test_content = self._create_test_template(context, test_type)
        
        try:
            with open(file_path, 'w') as f:
                f.write(test_content)
            
            return {
                'success': True,
                'path': str(file_path),
                'file_name': file_name,
                'test_type': test_type
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'path': str(file_path)
            }
    
    def _create_test_template(self, context: Dict[str, Any], test_type: str) -> str:
        """Create test template based on type"""
        snake_name = context['snake_name']
        class_name = context['class_name']
        
        if test_type == 'unit':
            return f'''#!/usr/bin/env python3
"""
Unit tests for {class_name}
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from agents.{snake_name} import {class_name}
from agents.base_agent import AgentStatus, ErrorSeverity


@pytest.fixture
def {snake_name}():
    """Create {class_name} instance for testing"""
    return {class_name}()


class Test{class_name}Initialization:
    """Test {class_name} initialization"""
    
    def test_agent_initialization(self, {snake_name}):
        """Test that agent initializes correctly"""
        assert {snake_name}.name == "{class_name}"
        assert {snake_name}.version == "1.0.0"
        assert {snake_name}.status == AgentStatus.INITIALIZING
        assert isinstance({snake_name}.errors, list)
        assert len({snake_name}.errors) == 0
    
    def test_agent_dependencies(self, {snake_name}):
        """Test that agent has correct dependencies"""
        expected_deps = {context['dependencies']}
        assert {snake_name}.dependencies == expected_deps


class Test{class_name}Execution:
    """Test {class_name} execution"""
    
    def test_execute_success(self, {snake_name}):
        """Test successful execution"""
        # Initialize agent
        {snake_name}.initialize()
        
        # Mock context
        context = {{
            "iteration": 1,
            "timestamp": 1234567890,
            "orchestrator_version": "1.0.0"
        }}
        
        # Execute should not raise exceptions
        try:
            output = {snake_name}.execute(context)
            assert output.agent_name == "{class_name}"
            assert output.status in [AgentStatus.COMPLETED, AgentStatus.ERROR]
        except NotImplementedError:
            # Expected if execute method is not implemented yet
            pytest.skip("Execute method not implemented")
    
    def test_execute_with_empty_context(self, {snake_name}):
        """Test execution with empty context"""
        {snake_name}.initialize()
        
        try:
            output = {snake_name}.execute({{}})
            assert output.agent_name == "{class_name}"
        except NotImplementedError:
            pytest.skip("Execute method not implemented")


class Test{class_name}Validation:
    """Test {class_name} validation"""
    
    def test_validate_no_errors(self, {snake_name}):
        """Test validation with no errors"""
        errors = {snake_name}.validate()
        assert isinstance(errors, list)
        # Should have no errors initially
        assert len(errors) == 0
    
    def test_validate_with_errors(self, {snake_name}):
        """Test validation with errors"""
        # Add a test error
        {snake_name}.log_error(
            "Test error",
            ErrorSeverity.MEDIUM,
            {{"test": "value"}},
            "Fix the test error"
        )
        
        errors = {snake_name}.validate()
        assert len(errors) == 1
        assert errors[0].message == "Test error"
        assert errors[0].severity == ErrorSeverity.MEDIUM


class Test{class_name}ErrorHandling:
    """Test {class_name} error handling"""
    
    def test_handle_error(self, {snake_name}):
        """Test error handling"""
        try:
            raise ValueError("Test error")
        except ValueError as e:
            output = {snake_name}._handle_error(e)
            assert output.status == AgentStatus.ERROR
            assert len(output.errors) == 1
            assert "Test error" in output.errors[0].message
    
    def test_clear_errors(self, {snake_name}):
        """Test clearing errors"""
        {snake_name}.log_error("Test error", ErrorSeverity.LOW)
        assert len({snake_name}.errors) == 1
        
        {snake_name}.clear_errors()
        assert len({snake_name}.errors) == 0
    
    def test_has_errors(self, {snake_name}):
        """Test has_errors method"""
        assert not {snake_name}.has_errors()
        
        {snake_name}.log_error("Test error", ErrorSeverity.LOW)
        assert {snake_name}.has_errors()
'''
        
        elif test_type == 'integration':
            return f'''#!/usr/bin/env python3
"""
Integration tests for {class_name}
Tests interaction with other agents and systems
"""

import pytest
import os
from agents.{snake_name} import {class_name}
from agents.base_agent import BaseAgent, AgentStatus


@pytest.fixture
def {snake_name}():
    """Create {class_name} instance"""
    return {class_name}()


class Test{class_name}Integration:
    """Test {class_name} integration with other components"""
    
    def test_integration_with_base_agent(self, {snake_name}):
        """Test that {class_name} properly extends BaseAgent"""
        assert isinstance({snake_name}, BaseAgent)
        assert hasattr({snake_name}, 'execute')
        assert hasattr({snake_name}, 'validate')
        assert hasattr({snake_name}, 'initialize')
    
    def test_agent_communication(self, {snake_name}):
        """Test agent communication patterns"""
        # Test that agent can receive and process context
        context = {{
            "from_agent": "DataPreparationAgent",
            "data": {{"test": "data"}},
            "iteration": 1
        }}
        
        {snake_name}.initialize()
        try:
            output = {snake_name}.execute(context)
            # Should be able to process context without errors
            assert output.agent_name == "{class_name}"
        except NotImplementedError:
            pytest.skip("Execute method not implemented")


class Test{class_name}Dependencies:
    """Test {class_name} dependency management"""
    
    def test_dependency_availability(self, {snake_name}):
        """Test that dependencies are available"""
        missing_deps = []
        for dep in {snake_name}.dependencies:
            try:
                __import__(dep)
            except ImportError:
                missing_deps.append(dep)
        
        if missing_deps:
            pytest.skip(f"Missing dependencies: {{missing_deps}}")
        else:
            assert True  # All dependencies available
'''
        
        else:  # e2e
            return f'''#!/usr/bin/env python3
"""
End-to-end tests for {class_name}
Tests complete workflows involving {class_name}
"""

import pytest
import os
import tempfile
from pathlib import Path
from agents.{snake_name} import {class_name}
from scripts.main_orchestrator import MainOrchestrator


@pytest.fixture
def temp_data_dir():
    """Create temporary data directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


class Test{class_name}E2E:
    """End-to-end tests for {class_name}"""
    
    def test_full_workflow_with_{snake_name}(self, temp_data_dir):
        """Test complete workflow with {class_name}"""
        # Setup test environment
        raw_dir = temp_data_dir / "raw"
        processed_dir = temp_data_dir / "processed"
        raw_dir.mkdir()
        processed_dir.mkdir()
        
        # Create sample data
        sample_file = raw_dir / "test_data.csv"
        sample_file.write_text("wavelength,intensity\\n700,0.5\\n800,0.6\\n900,0.7\\n")
        
        # Create agent with test configuration
        agent = {class_name}(
            input_directory=str(raw_dir),
            output_directory=str(processed_dir)
        )
        
        # Initialize and execute
        agent.initialize()
        
        try:
            context = {{
                "iteration": 1,
                "data_directory": str(raw_dir)
            }}
            output = agent.execute(context)
            
            # Verify output
            assert output.agent_name == "{class_name}"
            assert output.status in [AgentStatus.COMPLETED, AgentStatus.ERROR]
            
        except NotImplementedError:
            pytest.skip("Execute method not implemented")
    
    def test_orchestrator_integration(self, temp_data_dir):
        """Test {class_name} integration with orchestrator"""
        # This test verifies that {class_name} works within the full orchestrator
        # Note: This may require mocking or specific setup
        
        orchestrator = MainOrchestrator()
        
        # Check that {class_name} is in the execution order
        flat_order = []
        for item in orchestrator.execution_order:
            if isinstance(item, list):
                flat_order.extend(item)
            else:
                flat_order.append(item)
        
        snake_name_lower = "{snake_name}".replace("_", "")
        assert any(snake_name_lower in agent for agent in flat_order), \
            f"{class_name} not found in execution order"
'''
    
    def generate_docs_file(self, name: str, template: str, force: bool = False) -> Dict[str, Any]:
        """Generate documentation file for agent"""
        context = self._get_agent_context(name, template)
        snake_name = self._to_snake_case(name)
        
        # Create docs directory structure
        agent_docs_dir = self.docs_dir / 'agents'
        agent_docs_dir.mkdir(parents=True, exist_ok=True)
        
        file_name = f"{snake_name}.md"
        file_path = agent_docs_dir / file_name
        
        # Check if file exists
        if file_path.exists() and not force:
            return {
                'success': False,
                'error': f"File already exists: {file_path}",
                'path': str(file_path)
            }
        
        # Create documentation content
        docs_content = self._create_docs_template(context)
        
        try:
            with open(file_path, 'w') as f:
                f.write(docs_content)
            
            return {
                'success': True,
                'path': str(file_path),
                'file_name': file_name
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e),
                'path': str(file_path)
            }
    
    def _create_docs_template(self, context: Dict[str, Any]) -> str:
        """Create documentation template"""
        return f'''# {context['class_name']}

**Version**: 1.0.0  
**Author**: {context['author']}  
**Created**: {context['year']}  
**Type**: {context['template']} Agent

## Overview

{context['class_name']} is a specialized agent in the NIR Intelligence Platform responsible for {context['class_name'].replace('Agent', '')} functionality.

## Responsibilities

- [ ] TODO: Define primary responsibilities
- [ ] TODO: Define secondary responsibilities
- [ ] TODO: Define success criteria

## Configuration

### Required Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| N/A | - | - | TODO: Add configuration parameters |

### Optional Parameters

| Parameter | Type | Default | Description |
|-----------|------|---------|-------------|
| N/A | - | - | TODO: Add optional parameters |

## Dependencies

{context['class_name']} requires the following dependencies:

```bash
{chr(10).join(f"pip install {dep}" for dep in context['dependencies'])}
```

### Python Dependencies
- {chr(10).join(f"- `{dep}`" for dep in context['dependencies'])}

## Usage

### Basic Usage

```python
from agents.{context['snake_name']} import {context['class_name']}

# Create agent instance
agent = {context['class_name']}()

# Initialize agent
output = agent.initialize()

# Execute agent
context = {{
    "iteration": 1,
    "timestamp": time.time()
}}
result = agent.execute(context)
```

### With Configuration

```python
# Create agent with custom configuration
agent = {context['class_name']}(
    param1="value1",
    param2="value2"
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

{context['class_name']} handles the following error scenarios:

- [ ] TODO: Document error scenarios
- [ ] TODO: Document recovery strategies

## Performance

- **Expected Execution Time**: TODO
- **Memory Usage**: TODO
- **CPU Usage**: TODO

## Testing

Run tests for {context['class_name']}:

```bash
# Unit tests
pytest tests/unit/test_{context['snake_name']}.py

# Integration tests
pytest tests/integration/test_{context['snake_name']}_integration.py

# End-to-end tests
pytest tests/e2e/test_{context['snake_name']}_e2e.py
```

## Examples

### Example 1: Basic Execution

```python
# TODO: Add example
```

### Example 2: Advanced Usage

```python
# TODO: Add example
```

## Notes

- TODO: Add implementation notes
- TODO: Add known limitations
- TODO: Add future enhancements

## References

- [NIR Intelligence Platform Documentation](../README.md)
- [Base Agent Documentation](../base_agent.md)
- [Agent Development Guide](../development_guide.md)
'''
    
    def generate_agent(
        self,
        name: str,
        template: str = 'default',
        generate_python: bool = True,
        generate_json: bool = True,
        generate_tests: bool = True,
        generate_docs: bool = True,
        force: bool = False
    ) -> GenerationResult:
        """Generate a complete agent with all files"""
        result = GenerationResult(success=True)
        
        logger.info(f"Generating agent: {name} (template: {template})")
        
        # Generate Python file
        if generate_python:
            py_result = self.generate_python_file(name, template, force)
            if py_result['success']:
                result.files_created.append(py_result['path'])
            else:
                result.success = False
                result.error = py_result['error']
                return result
        
        # Generate JSON configuration
        if generate_json:
            json_result = self.generate_json_file(name, template, force)
            if json_result['success']:
                result.files_created.append(json_result['path'])
            else:
                result.success = False
                result.error = json_result['error']
                return result
        
        # Generate test files
        if generate_tests:
            for test_type in ['unit', 'integration', 'e2e']:
                test_result = self.generate_test_file(name, template, test_type, force)
                if test_result['success']:
                    result.files_created.append(test_result['path'])
                else:
                    result.warnings.append(test_result['error'])
        
        # Generate documentation
        if generate_docs:
            docs_result = self.generate_docs_file(name, template, force)
            if docs_result['success']:
                result.files_created.append(docs_result['path'])
            else:
                result.warnings.append(docs_result['error'])
        
        # Update __init__.py to include new agent
        self._update_init_file(name)
        
        logger.info(f"Successfully generated agent: {name}")
        return result
    
    def _update_init_file(self, name: str):
        """Update agents/__init__.py to include new agent"""
        init_file = self.agents_dir / '__init__.py'
        snake_name = self._to_snake_case(name)
        
        if init_file.exists():
            with open(init_file, 'r') as f:
                content = f.read()
            
            # Check if agent is already imported
            if f"from .{snake_name} import {name}" not in content:
                # Add import
                content = content.rstrip()
                if not content.endswith('\n'):
                    content += '\n'
                if content.endswith('"""'):
                    content += '\n'
                content += f"from .{snake_name} import {name}\n"
                
                with open(init_file, 'w') as f:
                    f.write(content)
                
                logger.info(f"Updated {init_file} to include {name}")
        else:
            # Create new __init__.py
            content = f'''# NIR Intelligence Platform - Agents Package
# Auto-generated by DeveloperAgent Framework

from .base_agent import BaseAgent
from .{snake_name} import {name}
'''
            with open(init_file, 'w') as f:
                f.write(content)
            
            logger.info(f"Created {init_file}")


class TestGenerator:
    """Generates test files for agents"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.agents_dir = self.project_root / 'agents'
        self.tests_dir = self.project_root / 'tests'
        self.generator = AgentGenerator()
    
    def generate_agent_tests(self, agent_name: str, test_type: str = 'all') -> GenerationResult:
        """Generate tests for a specific agent"""
        result = GenerationResult(success=True)
        
        snake_name = self.generator._to_snake_case(agent_name)
        
        if test_type == 'all':
            test_types = ['unit', 'integration', 'e2e']
        else:
            test_types = [test_type]
        
        for ttype in test_types:
            test_result = self.generator.generate_test_file(
                agent_name, 'default', ttype
            )
            if test_result['success']:
                result.files_created.append(test_result['path'])
            else:
                result.success = False
                result.error = test_result['error']
                break
        
        return result
    
    def generate_all_tests(self, test_type: str = 'all') -> GenerationResult:
        """Generate tests for all agents"""
        result = GenerationResult(success=True)
        
        # Get all agent files
        agent_files = list(self.agents_dir.glob('*_agent.py'))
        
        for agent_file in agent_files:
            # Extract agent name from filename
            agent_name = agent_file.stem.replace('_agent', '')
            # Convert snake_case to CamelCase
            agent_name = ''.join(word.capitalize() for word in agent_name.split('_')) + 'Agent'
            
            # Generate tests for this agent
            agent_result = self.generate_agent_tests(agent_name, test_type)
            if agent_result.success:
                result.files_created.extend(agent_result.files_created)
            else:
                result.success = False
                result.error = agent_result.error
                break
        
        return result


class DocsGenerator:
    """Generates documentation for agents"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.agents_dir = self.project_root / 'agents'
        self.docs_dir = self.project_root / 'docs'
        self.generator = AgentGenerator()
    
    def generate_agent_docs(self, agent_name: str) -> GenerationResult:
        """Generate documentation for a specific agent"""
        result = GenerationResult(success=True)
        
        # Generate agent docs
        docs_result = self.generator.generate_docs_file(agent_name, 'default')
        if docs_result['success']:
            result.files_created.append(docs_result['path'])
        else:
            result.success = False
            result.error = docs_result['error']
        
        return result
    
    def generate_all_docs(self) -> GenerationResult:
        """Generate documentation for all agents"""
        result = GenerationResult(success=True)
        
        # Get all agent files
        agent_files = list(self.agents_dir.glob('*_agent.py'))
        
        for agent_file in agent_files:
            # Extract agent name from filename
            agent_name = agent_file.stem.replace('_agent', '')
            # Convert snake_case to CamelCase
            agent_name = ''.join(word.capitalize() for word in agent_name.split('_')) + 'Agent'
            
            # Generate docs for this agent
            agent_result = self.generate_agent_docs(agent_name)
            if agent_result.success:
                result.files_created.extend(agent_result.files_created)
            else:
                result.success = False
                result.error = agent_result.error
                break
        
        # Also generate main documentation
        main_docs_result = self._generate_main_docs()
        if main_docs_result.success:
            result.files_created.extend(main_docs_result.files_created)
        
        return result
    
    def _generate_main_docs(self) -> GenerationResult:
        """Generate main documentation index"""
        result = GenerationResult(success=True)
        
        # Get all agent docs
        agent_docs_dir = self.docs_dir / 'agents'
        if not agent_docs_dir.exists():
            return result
        
        agent_docs = list(agent_docs_dir.glob('*.md'))
        
        # Create main index
        index_path = self.docs_dir / 'index.md'
        if not index_path.exists():
            content = """# NIR Intelligence Platform - Documentation

Welcome to the NIR Intelligence Platform documentation!

## Agents

"""
            
            for doc in sorted(agent_docs):
                agent_name = doc.stem.replace('_', ' ').title()
                content += f"\n- [{agent_name}](./agents/{doc.name}) - {doc.stem.replace('_', ' ').title()}"
            
            content += """

## Getting Started

- [Installation Guide](./installation.md)
- [User Guide](./user_guide.md)
- [Developer Guide](./developer_guide.md)
- [API Reference](./api_reference.md)

## Additional Resources

- [GitHub Repository](https://github.com/your-org/nir-intelligence-platform)
- [Issue Tracker](https://github.com/your-org/nir-intelligence-platform/issues)
- [Contributing Guide](./CONTRIBUTING.md)
"""
            
            with open(index_path, 'w') as f:
                f.write(content)
            
            result.files_created.append(str(index_path))
        
        return result
