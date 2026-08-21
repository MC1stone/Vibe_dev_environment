#!/usr/bin/env python3
"""
DeveloperAgent Framework - Setup Script
Sets up the framework and creates necessary files and directories.
"""

import os
import sys
import logging
from pathlib import Path
from typing import Dict, List, Any

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('FrameworkSetup')


class FrameworkSetup:
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.framework_dir = self.project_root / 'dev_framework'
        
    def setup(self) -> Dict[str, Any]:
        result = {
            'success': True,
            'actions': [],
            'errors': [],
            'warnings': []
        }
        
        logger.info("Starting DeveloperAgent Framework setup...")
        self._create_directories(result)
        self._create_config_files(result)
        self._create_templates(result)
        self._create_test_structure(result)
        self._create_sample_files(result)
        self._check_dependencies(result)
        logger.info("Framework setup completed!")
        return result
    
    def _create_directories(self, result: Dict[str, Any]):
        directories = [
            self.project_root / 'agents',
            self.project_root / 'tests' / 'unit',
            self.project_root / 'tests' / 'integration',
            self.project_root / 'tests' / 'e2e',
            self.project_root / 'docs' / 'agents',
            self.project_root / 'config',
            self.project_root / 'data' / 'raw',
            self.project_root / 'data' / 'processed',
            self.project_root / 'output',
            self.project_root / 'logs',
            self.framework_dir / 'templates' / 'agent',
            self.framework_dir / 'templates' / 'test',
            self.framework_dir / 'config'
        ]
        
        for directory in directories:
            try:
                directory.mkdir(parents=True, exist_ok=True)
                result['actions'].append(f"Created directory: {directory.relative_to(self.project_root)}")
            except Exception as e:
                result['errors'].append(f"Failed to create directory {directory}: {str(e)}")
                result['success'] = False
    
    def _create_config_files(self, result: Dict[str, Any]):
        configs = {
            '.flake8': """[flake8]
max-line-length = 120
ignore = E203, W503
exclude = .venv, venv, __pycache__, .git, *.egg-info
per-file-ignores = 
    */tests/*: S101
""",
            '.isort.cfg': """[settings]
profile = black
line_length = 120
known_first_party = agents, scripts, dev_framework
known_third_party = crewai, tensorflow, keras, torch, pandas, numpy, scipy, scikit-learn, weaviate, faiss, postgres, django, fastapi, pytest
""",
            'mypy.ini': """[mypy]
python_version = 3.12
warn_return_any = True
warn_unused_configs = True
disallow_untyped_defs = True
disallow_incomplete_defs = True
check_untyped_defs = True
warn_redundant_casts = True
warn_unused_ignores = True
ignore_missing_imports = True

[mypy-*.py]
ignore_errors = True
""",
            'pytest.ini': """[pytest]
testpaths = tests
python_files = test_*.py
python_functions = test_*
addopts = -v --tb=short
markers = 
    slow: marks tests as slow (deselect with '-m "not slow"')
    integration: marks integration tests
    e2e: marks end-to-end tests
"""
        }
        
        for filename, content in configs.items():
            config_file = self.project_root / filename
            if not config_file.exists():
                try:
                    with open(config_file, 'w') as f:
                        f.write(content)
                    result['actions'].append(f"Created config: {filename}")
                except Exception as e:
                    result['errors'].append(f"Failed to create {filename}: {str(e)}")
                    result['success'] = False
    
    def _create_templates(self, result: Dict[str, Any]):
        agent_template = self.framework_dir / 'templates' / 'agent' / 'default_agent.py.tpl'
        if not agent_template.exists():
            try:
                with open(agent_template, 'w') as f:
                    f.write('''#!/usr/bin/env python3
"""
NIR Intelligence Platform - NewAgent
Agent for NIR spectroscopy data processing
"""

import logging
from typing import Dict, Any, List
from .base_agent import BaseAgent, AgentOutput, AgentStatus, ErrorSeverity


class NewAgent(BaseAgent):
    """Agent for NewAgent functionality"""
    
    def __init__(self, **kwargs):
        super().__init__(name="NewAgent", version="1.0.0", **kwargs)
        self.dependencies = []
        self.logger = logging.getLogger(f"Agent.{self.name}")
    
    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute the agents primary function"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting NewAgent execution")
            
            # TODO: Implement NewAgent logic
            result = {
                "status": "completed",
                "message": "NewAgent execution completed successfully"
            }
            
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(result)
            
        except Exception as e:
            return self._handle_error(e)
''')
                result['actions'].append(f"Created template: {agent_template.relative_to(self.project_root)}")
            except Exception as e:
                result['errors'].append(f"Failed to create template: {str(e)}")
                result['success'] = False
    
    def _create_test_structure(self, result: Dict[str, Any]):
        init_files = [
            self.project_root / 'tests' / '__init__.py',
            self.project_root / 'tests' / 'unit' / '__init__.py',
            self.project_root / 'tests' / 'integration' / '__init__.py',
            self.project_root / 'tests' / 'e2e' / '__init__.py'
        ]
        
        for init_file in init_files:
            if not init_file.exists():
                try:
                    with open(init_file, 'w') as f:
                        f.write("# Test package\n")
                    result['actions'].append(f"Created: {init_file.relative_to(self.project_root)}")
                except Exception as e:
                    result['errors'].append(f"Failed to create {init_file}: {str(e)}")
                    result['success'] = False
        
        conftest_file = self.project_root / 'tests' / 'conftest.py'
        if not conftest_file.exists():
            try:
                with open(conftest_file, 'w') as f:
                    f.write('''#!/usr/bin/env python3
import pytest
import os
from pathlib import Path

# Fixtures available to all tests

@pytest.fixture
def project_root():
    return Path(__file__).parent.parent

@pytest.fixture
def agents_dir(project_root):
    return project_root / 'agents'

@pytest.fixture
def test_data_dir(tmp_path):
    """Create temporary test data directory"""
    data_dir = tmp_path / 'data'
    data_dir.mkdir()
    return data_dir
''')
                result['actions'].append(f"Created: {conftest_file.relative_to(self.project_root)}")
            except Exception as e:
                result['errors'].append(f"Failed to create {conftest_file}: {str(e)}")
                result['success'] = False
    
    def _create_sample_files(self, result: Dict[str, Any]):
        sample_data_dir = self.project_root / 'data' / 'raw'
        sample_data_file = sample_data_dir / 'sample_nir_data.csv'
        if not sample_data_file.exists():
            try:
                with open(sample_data_file, 'w') as f:
                    f.write("""wavelength,intensity,sample_id
700,0.123,sample_1
750,0.145,sample_1
800,0.167,sample_1
850,0.189,sample_1
900,0.211,sample_1
950,0.233,sample_1
1000,0.255,sample_1
1050,0.277,sample_1
1100,0.299,sample_1
1150,0.321,sample_1
700,0.135,sample_2
750,0.157,sample_2
800,0.179,sample_2
850,0.201,sample_2
900,0.223,sample_2
950,0.245,sample_2
1000,0.267,sample_2
1050,0.289,sample_2
1100,0.311,sample_2
1150,0.333,sample_2
""")
                result['actions'].append(f"Created sample data: {sample_data_file.relative_to(self.project_root)}")
            except Exception as e:
                result['errors'].append(f"Failed to create sample data: {str(e)}")
                result['success'] = False
    
    def _check_dependencies(self, result: Dict[str, Any]):
        required_packages = ['black', 'flake8', 'isort', 'mypy', 'pytest', 'pytest-cov']
        missing_packages = []
        
        for package in required_packages:
            try:
                __import__(package)
            except ImportError:
                missing_packages.append(package)
        
        if missing_packages:
            result['warnings'].append(
                f"Missing optional packages: {', '.join(missing_packages)}. "
                f"Install with: pip install {' '.join(missing_packages)}"
            )
        else:
            result['actions'].append("All optional dependencies are installed")
    
    def verify_setup(self) -> Dict[str, Any]:
        result = {
            'success': True,
            'checks': [],
            'errors': [],
            'warnings': []
        }
        
        required_dirs = ['agents', 'tests', 'docs', 'config', 'data', 'output', 'logs']
        for dir_name in required_dirs:
            dir_path = self.project_root / dir_name
            if dir_path.exists() and dir_path.is_dir():
                result['checks'].append(f"Directory exists: {dir_name}")
            else:
                result['errors'].append(f"Directory missing: {dir_name}")
                result['success'] = False
        
        config_files = ['.flake8', '.isort.cfg', 'mypy.ini', 'pytest.ini']
        for config_file in config_files:
            file_path = self.project_root / config_file
            if file_path.exists():
                result['checks'].append(f"Config file exists: {config_file}")
            else:
                result['warnings'].append(f"Config file missing: {config_file}")
        
        framework_files = [
            'dev_framework/__init__.py', 'dev_framework/cli.py', 
            'dev_framework/generator.py', 'dev_framework/validator.py',
            'dev_framework/quality.py', 'dev_framework/tester.py',
            'dev_framework/server.py', 'dev_framework/docs.py'
        ]
        
        for framework_file in framework_files:
            file_path = self.project_root / framework_file
            if file_path.exists():
                result['checks'].append(f"Framework file exists: {framework_file}")
            else:
                result['errors'].append(f"Framework file missing: {framework_file}")
                result['success'] = False
        
        return result


def main():
    setup = FrameworkSetup()
    result = setup.setup()
    
    print("=" * 60)
    print("DeveloperAgent Framework Setup")
    print("=" * 60)
    print()
    
    if result['success']:
        print("Setup completed successfully!")
        print()
        print("Actions performed:")
        for action in result['actions']:
            print(f"  ✓ {action}")
        
        if result['warnings']:
            print()
            print("Warnings:")
            for warning in result['warnings']:
                print(f"  ⚠ {warning}")
        
        print()
        print("Next steps:")
        print("  1. Run: python -m dev_framework info")
        print("  2. Generate agents: python -m dev_framework generate agent NewAgent")
        print("  3. Validate: python -m dev_framework validate")
        print("  4. Test: python -m dev_framework test")
        print("  5. Start server: python -m dev_framework serve")
        return 0
    else:
        print("Setup completed with errors!")
        print()
        print("Errors:")
        for error in result['errors']:
            print(f"  ✗ {error}")
        
        if result['warnings']:
            print()
            print("Warnings:")
            for warning in result['warnings']:
                print(f"  ⚠ {warning}")
        return 1


if __name__ == '__main__':
    sys.exit(main())
