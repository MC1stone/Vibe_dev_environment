#!/usr/bin/env python3
"""
DeveloperAgent Framework - Documentation Generator

Generates documentation for agents and the project.
"""

import os
import json
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

logger = logging.getLogger('DocsGenerator')


@dataclass
class DocsResult:
    """Result of documentation generation"""
    success: bool
    files_created: List[str] = field(default_factory=list)
    files_updated: List[str] = field(default_factory=list)
    error: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


class DocsGenerator:
    """Generates documentation for the project"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.docs_dir = self.project_root / 'docs'
        self.agents_dir = self.project_root / 'agents'
        
        # Ensure docs directory exists
        self.docs_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_all_docs(self) -> DocsResult:
        """Generate documentation for all agents and project"""
        result = DocsResult(success=True)
        
        # Generate main documentation
        main_result = self._generate_main_docs()
        if main_result.success:
            result.files_created.extend(main_result.files_created)
            result.files_updated.extend(main_result.files_updated)
        else:
            result.success = False
            result.error = main_result.error
        
        # Generate agent documentation
        agent_result = self._generate_agent_docs()
        if agent_result.success:
            result.files_created.extend(agent_result.files_created)
            result.files_updated.extend(agent_result.files_updated)
        else:
            result.success = False
            result.error = agent_result.error
        
        # Generate API documentation
        api_result = self._generate_api_docs()
        if api_result.success:
            result.files_created.extend(api_result.files_created)
            result.files_updated.extend(api_result.files_updated)
        else:
            result.warnings.append(api_result.error or "Failed to generate API docs")
        
        # Generate development guide
        dev_result = self._generate_development_guide()
        if dev_result.success:
            result.files_created.extend(dev_result.files_created)
            result.files_updated.extend(dev_result.files_updated)
        else:
            result.warnings.append(dev_result.error or "Failed to generate development guide")
        
        return result
    
    def generate_agent_docs(self, agent_name: str) -> DocsResult:
        """Generate documentation for a specific agent"""
        result = DocsResult(success=True)
        
        snake_name = self._to_snake_case(agent_name)
        
        # Create agent docs directory
        agent_docs_dir = self.docs_dir / 'agents'
        agent_docs_dir.mkdir(parents=True, exist_ok=True)
        
        # Generate agent documentation
        agent_file = self.agents_dir / f"{snake_name}.py"
        if not agent_file.exists():
            result.success = False
            result.error = f"Agent file not found: {agent_file}"
            return result
        
        # Parse agent file to extract information
        agent_info = self._parse_agent_file(agent_file, agent_name)
        
        # Generate markdown documentation
        docs_content = self._generate_agent_markdown(agent_info)
        
        # Write documentation file
        docs_file = agent_docs_dir / f"{snake_name}.md"
        try:
            with open(docs_file, 'w') as f:
                f.write(docs_content)
            
            result.files_created.append(str(docs_file.relative_to(self.project_root)))
            logger.info(f"Generated documentation for {agent_name}: {docs_file}")
        except Exception as e:
            result.success = False
            result.error = f"Failed to write documentation for {agent_name}: {str(e)}"
        
        return result
    
    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case"""
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
        return name.lower()
    
    def _parse_agent_file(self, file_path: Path, agent_name: str) -> Dict[str, Any]:
        """Parse agent file to extract information"""
        import ast
        
        info = {
            'name': agent_name,
            'file': str(file_path.relative_to(self.project_root)),
            'description': '',
            'version': '1.0.0',
            'dependencies': [],
            'methods': [],
            'attributes': [],
            'docstring': '',
            'source_code': ''
        }
        
        try:
            with open(file_path, 'r') as f:
                source = f.read()
            
            info['source_code'] = source
            
            # Parse AST
            tree = ast.parse(source, filename=str(file_path))
            
            # Find the agent class
            for node in ast.walk(tree):
                if isinstance(node, ast.ClassDef) and node.name == agent_name:
                    # Extract docstring
                    if ast.get_docstring(node):
                        info['docstring'] = ast.get_docstring(node).strip()
                    
                    # Extract methods
                    for item in node.body:
                        if isinstance(item, ast.FunctionDef):
                            method_info = {
                                'name': item.name,
                                'docstring': ast.get_docstring(item) or '',
                                'line': item.lineno,
                                'parameters': []
                            }
                            
                            # Extract parameters
                            if item.args.args:
                                for arg in item.args.args:
                                    method_info['parameters'].append(arg.arg)
                            
                            info['methods'].append(method_info)
                        
                        elif isinstance(item, ast.Assign):
                            # Extract class attributes
                            for target in item.targets:
                                if isinstance(target, ast.Attribute) and isinstance(target.value, ast.Name) and target.value.id == 'self':
                                    info['attributes'].append(target.attr)
                    
                    break
            
            # Extract imports for dependencies
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    for alias in node.names:
                        info['dependencies'].append(alias.name)
                elif isinstance(node, ast.ImportFrom):
                    if node.module:
                        info['dependencies'].append(node.module)
            
        except Exception as e:
            logger.error(f"Failed to parse agent file {file_path}: {str(e)}")
        
        return info
    
    def _generate_agent_markdown(self, agent_info: Dict[str, Any]) -> str:
        """Generate markdown documentation for an agent"""
        lines = []
        
        # Header
        lines.append(f"# {agent_info['name']}")
        lines.append("")
        lines.append(f"**File**: `{agent_info['file']}`")
        lines.append(f"**Version**: {agent_info['version']}")
        lines.append("")
        
        # Description
        if agent_info['docstring']:
            lines.append("## Description")
            lines.append("")
            lines.append(agent_info['docstring'])
            lines.append("")
        
        # Dependencies
        if agent_info['dependencies']:
            lines.append("## Dependencies")
            lines.append("")
            lines.append("This agent requires the following dependencies:")
            lines.append("")
            for dep in sorted(set(agent_info['dependencies'])):
                lines.append(f"- `{dep}`")
            lines.append("")
        
        # Installation
        if agent_info['dependencies']:
            lines.append("## Installation")
            lines.append("")
            lines.append("```bash")
            for dep in sorted(set(agent_info['dependencies'])):
                lines.append(f"pip install {dep}")
            lines.append("```")
            lines.append("")
        
        # Usage
        lines.append("## Usage")
        lines.append("")
        lines.append("### Basic Usage")
        lines.append("")
        lines.append("```python")
        lines.append(f"from agents.{self._to_snake_case(agent_info['name'])} import {agent_info['name']}")
        lines.append("")
        lines.append(f"# Create agent instance")
        lines.append(f"agent = {agent_info['name']}()")
        lines.append("")
        lines.append("# Initialize agent")
        lines.append("output = agent.initialize()")
        lines.append("")
        lines.append("# Execute agent")
        lines.append("context = {'iteration': 1, 'timestamp': time.time()}")
        lines.append("result = agent.execute(context)")
        lines.append("```")
        lines.append("")
        
        # Methods
        if agent_info['methods']:
            lines.append("## Methods")
            lines.append("")
            
            for method in agent_info['methods']:
                lines.append(f"### `{method['name']}`")
                lines.append("")
                
                if method['docstring']:
                    lines.append(method['docstring'])
                    lines.append("")
                
                if method['parameters']:
                    lines.append("**Parameters**:")
                    lines.append("")
                    for param in method['parameters']:
                        lines.append(f"- `{param}`: TODO")
                    lines.append("")
                
                lines.append("**Returns**: TODO")
                lines.append("")
        
        # Attributes
        if agent_info['attributes']:
            lines.append("## Attributes")
            lines.append("")
            for attr in agent_info['attributes']:
                lines.append(f"- `self.{attr}`: TODO")
            lines.append("")
        
        # Source Code
        lines.append("## Source Code")
        lines.append("")
        lines.append("```python")
        lines.append(agent_info['source_code'])
        lines.append("```")
        lines.append("")
        
        # Footer
        lines.append("---")
        lines.append("")
        lines.append("Generated by DeveloperAgent Framework")
        lines.append("")
        
        return "\n".join(lines)
    
    def _generate_main_docs(self) -> DocsResult:
        """Generate main documentation index"""
        result = DocsResult(success=True)
        
        # Get all agents
        agent_files = list(self.agents_dir.glob('*_agent.py'))
        agents = []
        for f in agent_files:
            agent_name = f.stem.replace('_agent', '')
            agents.append(''.join(word.capitalize() for word in agent_name.split('_')) + 'Agent')
        
        # Generate main index
        index_content = self._generate_main_index(agents)
        
        # Write index file
        index_file = self.docs_dir / 'index.md'
        try:
            with open(index_file, 'w') as f:
                f.write(index_content)
            
            result.files_created.append(str(index_file.relative_to(self.project_root)))
        except Exception as e:
            result.success = False
            result.error = f"Failed to write main index: {str(e)}"
        
        return result
    
    def _generate_main_index(self, agents: List[str]) -> str:
        """Generate main index page"""
        lines = []
        
        lines.append("# NIR Intelligence Platform")
        lines.append("")
        lines.append("Welcome to the NIR Intelligence Platform documentation!")
        lines.append("")
        lines.append("The NIR Intelligence Platform is a self-optimizing multi-agent system for Near-Infrared (NIR) spectroscopy data analysis.")
        lines.append("")
        
        lines.append("## Table of Contents")
        lines.append("")
        lines.append("- [Overview](#overview)")
        lines.append("- [Architecture](#architecture)")
        lines.append("- [Agents](#agents)")
        lines.append("- [Getting Started](#getting-started)")
        lines.append("- [Development](#development)")
        lines.append("- [API Reference](#api-reference)")
        lines.append("")
        
        lines.append("## Overview")
        lines.append("")
        lines.append("The NIR Intelligence Platform provides comprehensive NIR spectroscopy data analysis through a multi-agent architecture.")
        lines.append("")
        
        lines.append("## Architecture")
        lines.append("")
        lines.append("The platform consists of the following components:")
        lines.append("")
        lines.append("- **Master Orchestrator**: Central coordination and quality control")
        lines.append("- **Data Agents**: Data preparation, metadata management, sensor quality")
        lines.append("- **Analysis Agents**: Statistical analysis, neural networks, calibration")
        lines.append("- **Storage Agents**: Weaviate, FAISS, PostgreSQL for data storage")
        lines.append("- **Integration Agents**: Django, MCP, ILIAS, Quarto, Flower")
        lines.append("")
        
        lines.append("## Agents")
        lines.append("")
        lines.append(f"The platform includes {len(agents)} agents:")
        lines.append("")
        
        for agent in sorted(agents):
            snake_name = self._to_snake_case(agent)
            lines.append(f"- [{agent}](./agents/{snake_name}.md) - {agent.replace('Agent', '')}")
        lines.append("")
        
        lines.append("## Getting Started")
        lines.append("")
        lines.append("See [Installation Guide](./installation.md) for setup instructions.")
        lines.append("")
        
        lines.append("## Development")
        lines.append("")
        lines.append("See [Developer Guide](./development_guide.md) for development information.")
        lines.append("")
        
        lines.append("## API Reference")
        lines.append("")
        lines.append("See [API Documentation](./api_reference.md) for API details.")
        lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("Generated by DeveloperAgent Framework")
        
        return "\n".join(lines)
    
    def _generate_agent_docs(self) -> DocsResult:
        """Generate documentation for all agents"""
        result = DocsResult(success=True)
        
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
                result.files_updated.extend(agent_result.files_updated)
            else:
                result.warnings.append(agent_result.error or f"Failed to generate docs for {agent_name}")
        
        return result
    
    def _generate_api_docs(self) -> DocsResult:
        """Generate API documentation"""
        result = DocsResult(success=True)
        
        # Generate API reference
        api_content = self._generate_api_reference()
        
        # Write API file
        api_file = self.docs_dir / 'api_reference.md'
        try:
            with open(api_file, 'w') as f:
                f.write(api_content)
            
            result.files_created.append(str(api_file.relative_to(self.project_root)))
        except Exception as e:
            result.success = False
            result.error = f"Failed to write API reference: {str(e)}"
        
        return result
    
    def _generate_api_reference(self) -> str:
        """Generate API reference documentation"""
        lines = []
        
        lines.append("# API Reference")
        lines.append("")
        lines.append("This document describes the APIs provided by the NIR Intelligence Platform.")
        lines.append("")
        
        lines.append("## REST API")
        lines.append("")
        lines.append("The development server provides a REST API for testing agents.")
        lines.append("")
        
        lines.append("### Endpoints")
        lines.append("")
        lines.append("#### GET /agents")
        lines.append("")
        lines.append("List all available agents.")
        lines.append("")
        lines.append("**Response**:")
        lines.append("```json")
        lines.append("[")
        lines.append("  {")
        lines.append("    \"name\": \"DataPreparationAgent\",")
        lines.append("    \"file\": \"agents/data_preparation_agent.py\",")
        lines.append("    \"loaded\": true")
        lines.append("  }")
        lines.append("]")
        lines.append("```")
        lines.append("")
        
        lines.append("#### GET /agents/{agent_name}")
        lines.append("")
        lines.append("Get information about a specific agent.")
        lines.append("")
        lines.append("**Response**:")
        lines.append("```json")
        lines.append("{")
        lines.append("  \"name\": \"DataPreparationAgent\",")
        lines.append("  \"version\": \"1.0.0\",")
        lines.append("  \"status\": \"READY\",")
        lines.append("  \"dependencies\": [\"pandas\", \"numpy\"],")
        lines.append("  \"errors\": 0")
        lines.append("}")
        lines.append("```")
        lines.append("")
        
        lines.append("#### POST /agents/{agent_name}")
        lines.append("")
        lines.append("Execute a specific agent.")
        lines.append("")
        lines.append("**Request Body**:")
        lines.append("```json")
        lines.append("{")
        lines.append("  \"iteration\": 1,")
        lines.append("  \"timestamp\": 1234567890,")
        lines.append("  \"data\": {}")
        lines.append("}")
        lines.append("```")
        lines.append("")
        lines.append("**Response**:")
        lines.append("```json")
        lines.append("{")
        lines.append("  \"success\": true,")
        lines.append("  \"agent_name\": \"DataPreparationAgent\",")
        lines.append("  \"status\": \"COMPLETED\",")
        lines.append("  \"data\": {},")
        lines.append("  \"errors\": []")
        lines.append("}")
        lines.append("```")
        lines.append("")
        
        lines.append("#### GET /health")
        lines.append("")
        lines.append("Health check endpoint.")
        lines.append("")
        lines.append("**Response**:")
        lines.append("```json")
        lines.append("{")
        lines.append("  \"status\": \"healthy\",")
        lines.append("  \"agents_loaded\": 14,")
        lines.append("  \"timestamp\": 1234567890.123")
        lines.append("}")
        lines.append("```")
        lines.append("")
        
        lines.append("## Python API")
        lines.append("")
        lines.append("### Agent Base Class")
        lines.append("")
        lines.append("All agents inherit from `BaseAgent` and provide the following interface:")
        lines.append("")
        lines.append("```python")
        lines.append("class BaseAgent:")
        lines.append("    def __init__(self, name: str, version: str = \"1.0.0\", **kwargs):")
        lines.append("        \"\"\"Initialize agent\"\"\"")
        lines.append("    ")
        lines.append("    def initialize(self) -> AgentOutput:")
        lines.append("        \"\"\"Initialize agent and its environment\"\"\"")
        lines.append("    ")
        lines.append("    def execute(self, context: Dict[str, Any]) -> AgentOutput:")
        lines.append("        \"\"\"Execute agent's primary function\"\"\"")
        lines.append("    ")
        lines.append("    def validate(self) -> List[AgentError]:")
        lines.append("        \"\"\"Validate agent's current state and configuration\"\"\"")
        lines.append("```")
        lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("Generated by DeveloperAgent Framework")
        
        return "\n".join(lines)
    
    def _generate_development_guide(self) -> DocsResult:
        """Generate development guide"""
        result = DocsResult(success=True)
        
        # Generate development guide
        guide_content = self._generate_development_guide_content()
        
        # Write guide file
        guide_file = self.docs_dir / 'development_guide.md'
        try:
            with open(guide_file, 'w') as f:
                f.write(guide_content)
            
            result.files_created.append(str(guide_file.relative_to(self.project_root)))
        except Exception as e:
            result.success = False
            result.error = f"Failed to write development guide: {str(e)}"
        
        return result
    
    def _generate_development_guide_content(self) -> str:
        """Generate development guide content"""
        lines = []
        
        lines.append("# Development Guide")
        lines.append("")
        lines.append("This guide covers how to develop new agents for the NIR Intelligence Platform.")
        lines.append("")
        
        lines.append("## Prerequisites")
        lines.append("")
        lines.append("- Python 3.12+")
        lines.append("- Poetry or pip for dependency management")
        lines.append("- Git")
        lines.append("- Docker and Docker Compose")
        lines.append("")
        
        lines.append("## Project Structure")
        lines.append("")
        lines.append("```")
        lines.append("nir-intelligence-platform/")
        lines.append("├── agents/                  # Agent implementations")
        lines.append("│   ├── __init__.py")
        lines.append("│   ├── base_agent.py       # Base class for all agents")
        lines.append("│   ├── data_preparation_agent.py")
        lines.append("│   └── ...")
        lines.append("├── config/                  # Configuration files")
        lines.append("├── data/                    # Data directories")
        lines.append("├── docs/                    # Documentation")
        lines.append("├── scripts/                 # Utility scripts")
        lines.append("├── tests/                   # Test files")
        lines.append("└── dev_framework/           # Development framework")
        lines.append("```")
        lines.append("")
        
        lines.append("## Creating a New Agent")
        lines.append("")
        lines.append("### Using the Developer Framework")
        lines.append("")
        lines.append("The easiest way to create a new agent is using the DeveloperAgent Framework:")
        lines.append("")
        lines.append("```bash")
        lines.append("# Generate a new agent")
        lines.append("python -m dev_framework generate agent NewAgentName")
        lines.append("")
        lines.append("# Generate with specific template")
        lines.append("python -m dev_framework generate agent NewAgentName --template ml")
        lines.append("```")
        lines.append("")
        
        lines.append("### Manual Creation")
        lines.append("")
        lines.append("1. Create a new file in `agents/` named `{agent_name}_agent.py`")
        lines.append("2. Import `BaseAgent` from `base_agent`")
        lines.append("3. Create a class that inherits from `BaseAgent`")
        lines.append("4. Implement the required methods")
        lines.append("")
        
        lines.append("### Agent Template")
        lines.append("")
        lines.append("```python")
        lines.append("from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity")
        lines.append("")
        lines.append("class NewAgent(BaseAgent):")
        lines.append('    def __init__(self, **kwargs):')
        lines.append('        super().__init__(name="NewAgent", version="1.0.0", **kwargs)')
        lines.append('        self.dependencies = ["dep1", "dep2"]')
        lines.append('')
        lines.append('    def execute(self, context: Dict[str, Any]) -> AgentOutput:')
        lines.append('        try:')
        lines.append('            self.status = AgentStatus.PROCESSING')
        lines.append('            # Your implementation here')
        lines.append('            result = {"status": "completed"}')
        lines.append('            self.status = AgentStatus.COMPLETED')
        lines.append('            return self._create_success_output(result)')
        lines.append('        except Exception as e:')
        lines.append('            return self._handle_error(e)')
        lines.append("```")
        lines.append("")
        
        lines.append("## Agent Types and Templates")
        lines.append("")
        lines.append("The framework provides several templates for different agent types:")
        lines.append("")
        lines.append("| Template | Description | Dependencies |")
        lines.append("|----------|-------------|--------------|")
        lines.append("| `default` | Generic agent | None |")
        lines.append("| `data` | Data processing | pandas, numpy |")
        lines.append("| `ml` | Machine learning | tensorflow, keras, scikit-learn |")
        lines.append("| `db` | Database | sqlalchemy, psycopg2 |")
        lines.append("| `api` | API/Web service | fastapi, uvicorn |")
        lines.append("| `analysis` | Statistical analysis | pandas, numpy, scipy, scikit-learn |")
        lines.append("")
        
        lines.append("## Testing Agents")
        lines.append("")
        lines.append("### Running Tests")
        lines.append("")
        lines.append("```bash")
        lines.append("# Run all tests")
        lines.append("python -m dev_framework test")
        lines.append("")
        lines.append("# Run tests for specific agent")
        lines.append("python -m dev_framework test --agent DataPreparationAgent")
        lines.append("")
        lines.append("# Run with coverage")
        lines.append("python -m dev_framework test --coverage")
        lines.append("```")
        lines.append("")
        
        lines.append("### Test Structure")
        lines.append("")
        lines.append("Tests are organized in the `tests/` directory:")
        lines.append("")
        lines.append("```")
        lines.append("tests/")
        lines.append("├── unit/           # Unit tests")
        lines.append("│   └── test_*.py")
        lines.append("├── integration/    # Integration tests")
        lines.append("│   └── test_*_integration.py")
        lines.append("└── e2e/           # End-to-end tests")
        lines.append("    └── test_*_e2e.py")
        lines.append("```")
        lines.append("")
        
        lines.append("## Development Server")
        lines.append("")
        lines.append("The development server provides a way to test agents with hot-reload:")
        lines.append("")
        lines.append("```bash")
        lines.append("# Start development server")
        lines.append("python -m dev_framework serve")
        lines.append("")
        lines.append("# Start on specific port")
        lines.append("python -m dev_framework serve --port 8080")
        lines.append("")
        lines.append("# Serve specific agent")
        lines.append("python -m dev_framework serve --agent DataPreparationAgent")
        lines.append("```")
        lines.append("")
        
        lines.append("## Code Quality")
        lines.append("")
        lines.append("The framework enforces code quality standards:")
        lines.append("")
        lines.append("```bash")
        lines.append("# Check code quality")
        lines.append("python -m dev_framework quality")
        lines.append("")
        lines.append("# Auto-fix quality issues")
        lines.append("python -m dev_framework quality --fix")
        lines.append("```")
        lines.append("")
        
        lines.append("## Validation")
        lines.append("")
        lines.append("Validate agents against requirements:")
        lines.append("")
        lines.append("```bash")
        lines.append("# Validate all agents")
        lines.append("python -m dev_framework validate")
        lines.append("")
        lines.append("# Validate specific agent")
        lines.append("python -m dev_framework validate --agent DataPreparationAgent")
        lines.append("```")
        lines.append("")
        
        lines.append("## Best Practices")
        lines.append("")
        lines.append("- Always inherit from `BaseAgent`")
        lines.append("- Implement proper error handling")
        lines.append("- Use logging instead of print statements")
        lines.append("- Follow PEP 8 style guidelines")
        lines.append("- Write comprehensive tests")
        lines.append("- Document all methods and classes")
        lines.append("- Handle edge cases gracefully")
        lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("Generated by DeveloperAgent Framework")
        
        return "\n".join(lines)
    
    def generate_installation_guide(self) -> DocsResult:
        """Generate installation guide"""
        result = DocsResult(success=True)
        
        # Generate installation guide
        guide_content = self._generate_installation_guide_content()
        
        # Write guide file
        guide_file = self.docs_dir / 'installation.md'
        try:
            with open(guide_file, 'w') as f:
                f.write(guide_content)
            
            result.files_created.append(str(guide_file.relative_to(self.project_root)))
        except Exception as e:
            result.success = False
            result.error = f"Failed to write installation guide: {str(e)}"
        
        return result
    
    def _generate_installation_guide_content(self) -> str:
        """Generate installation guide content"""
        lines = []
        
        lines.append("# Installation Guide")
        lines.append("")
        lines.append("This guide covers how to install and set up the NIR Intelligence Platform.")
        lines.append("")
        
        lines.append("## Prerequisites")
        lines.append("")
        lines.append("### System Requirements")
        lines.append("")
        lines.append("- **Operating System**: Linux, macOS, or Windows 10/11")
        lines.append("- **Python**: 3.12 or higher")
        lines.append("- **Memory**: 8GB RAM minimum (16GB recommended)")
        lines.append("- **Storage**: 10GB free disk space")
        lines.append("- **Docker**: Docker and Docker Compose")
        lines.append("")
        
        lines.append("### Python Dependencies")
        lines.append("")
        lines.append("The project requires Python 3.12+. Check your version:")
        lines.append("")
        lines.append("```bash")
        lines.append("python --version")
        lines.append("```")
        lines.append("")
        
        lines.append("## Installation")
        lines.append("")
        
        lines.append("### 1. Clone the Repository")
        lines.append("")
        lines.append("```bash")
        lines.append("git clone https://github.com/your-org/nir-intelligence-platform.git")
        lines.append("cd nir-intelligence-platform")
        lines.append("```")
        lines.append("")
        
        lines.append("### 2. Create Virtual Environment")
        lines.append("")
        lines.append("Using venv:")
        lines.append("")
        lines.append("```bash")
        lines.append("python -m venv venv")
        lines.append("source venv/bin/activate  # On Windows: venv\Scripts\activate")
        lines.append("```")
        lines.append("")
        
        lines.append("Or using poetry:")
        lines.append("")
        lines.append("```bash")
        lines.append("poetry install")
        lines.append("poetry shell")
        lines.append("```")
        lines.append("")
        
        lines.append("### 3. Install Dependencies")
        lines.append("")
        lines.append("```bash")
        lines.append("pip install -r requirements.txt")
        lines.append("```")
        lines.append("")
        
        lines.append("### 4. Set Up Docker Containers")
        lines.append("")
        lines.append("```bash")
        lines.append("docker-compose up -d")
        lines.append("```")
        lines.append("")
        
        lines.append("### 5. Verify Installation")
        lines.append("")
        lines.append("```bash")
        lines.append("# Check framework")
        lines.append("python -m dev_framework info")
        lines.append("")
        lines.append("# Run validation")
        lines.append("python -m dev_framework validate")
        lines.append("")
        lines.append("# Run tests")
        lines.append("python -m dev_framework test")
        lines.append("```")
        lines.append("")
        
        lines.append("## Configuration")
        lines.append("")
        lines.append("### Environment Variables")
        lines.append("")
        lines.append("Create a `.env` file in the project root:")
        lines.append("")
        lines.append("```bash")
        lines.append("# Database configuration")
        lines.append("POSTGRES_USER=nir_user")
        lines.append("POSTGRES_PASSWORD=secure_password")
        lines.append("POSTGRES_DB=nir_metadata")
        lines.append("")
        lines.append("# Weaviate configuration")
        lines.append("WEAVIATE_HOST=localhost")
        lines.append("WEAVIATE_PORT=8080")
        lines.append("```")
        lines.append("")
        
        lines.append("### Agent Configuration")
        lines.append("")
        lines.append("Edit `config/agent_config.yaml` to configure agents:")
        lines.append("")
        lines.append("```yaml")
        lines.append("agents:")
        lines.append("  data_preparation_agent:")
        lines.append("    enabled: true")
        lines.append("    params:")
        lines.append("      input_directory: data/raw")
        lines.append("      output_directory: data/processed")
        lines.append("  neural_network_agent:")
        lines.append("    enabled: true")
        lines.append("    params:")
        lines.append("      models: [CNN, MLP, Autoencoder]")
        lines.append("```")
        lines.append("")
        
        lines.append("## Running the Platform")
        lines.append("")
        lines.append("### Development Mode")
        lines.append("")
        lines.append("```bash")
        lines.append("# Run orchestrator")
        lines.append("python scripts/main_orchestrator.py")
        lines.append("")
        lines.append("# With debug mode")
        lines.append("python scripts/main_orchestrator.py --debug")
        lines.append("```")
        lines.append("")
        
        lines.append("### Production Mode")
        lines.append("")
        lines.append("```bash")
        lines.append("# Build Docker image")
        lines.append("docker build -t nir-platform .")
        lines.append("")
        lines.append("# Run container")
        lines.append("docker run -p 8000:8000 nir-platform")
        lines.append("```")
        lines.append("")
        
        lines.append("## Troubleshooting")
        lines.append("")
        lines.append("### Common Issues")
        lines.append("")
        lines.append("#### Docker Permission Denied")
        lines.append("")
        lines.append("```bash")
        lines.append("sudo usermod -aG docker $USER")
        lines.append("newgrp docker")
        lines.append("```")
        lines.append("")
        
        lines.append("#### Missing Dependencies")
        lines.append("")
        lines.append("```bash")
        lines.append("pip install -r requirements.txt")
        lines.append("```")
        lines.append("")
        
        lines.append("#### Port Already in Use")
        lines.append("")
        lines.append("```bash")
        lines.append("# Find and kill process using port")
        lines.append("lsof -i :8001")
        lines.append("kill -9 <PID>")
        lines.append("```")
        lines.append("")
        
        lines.append("---")
        lines.append("")
        lines.append("Generated by DeveloperAgent Framework")
        
        return "\n".join(lines)
