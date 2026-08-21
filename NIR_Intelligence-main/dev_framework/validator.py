#!/usr/bin/env python3
"""
DeveloperAgent Framework - Agent Validator

Validates agent implementations against requirements and best practices.
"""

import os
import re
import ast
import json
import yaml
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger('AgentValidator')


@dataclass
class ValidationIssue:
    """Represents a validation issue"""
    severity: str  # 'error', 'warning', 'info'
    code: str
    message: str
    file: str
    line: Optional[int] = None
    column: Optional[int] = None
    details: Optional[Dict[str, Any]] = None
    fix: Optional[str] = None


@dataclass
class ValidationResult:
    """Result of validation"""
    valid: bool
    errors: List[ValidationIssue] = field(default_factory=list)
    warnings: List[ValidationIssue] = field(default_factory=list)
    info: List[ValidationIssue] = field(default_factory=list)
    agent_name: Optional[str] = None
    
    def add_issue(self, issue: ValidationIssue):
        """Add issue to appropriate list based on severity"""
        if issue.severity == 'error':
            self.errors.append(issue)
            self.valid = False
        elif issue.severity == 'warning':
            self.warnings.append(issue)
        else:
            self.info.append(issue)


class AgentValidator:
    """Validates agent implementations"""
    
    # Validation rules
    REQUIRED_METHODS = ['execute']
    REQUIRED_ATTRIBUTES = ['name', 'version', 'dependencies', 'errors']
    REQUIRED_BASE_CLASS = 'BaseAgent'
    
    # Quality rules
    MAX_LINE_LENGTH = 120
    MAX_FUNCTION_LENGTH = 50
    MAX_CYCLOMATIC_COMPLEXITY = 10
    
    def __init__(self, strict: bool = False):
        self.strict = strict
        self.project_root = Path(__file__).parent.parent
        self.agents_dir = self.project_root / 'agents'
        self.config_dir = self.project_root / 'config'
        
    def validate_all(self) -> ValidationResult:
        """Validate all agents"""
        result = ValidationResult(valid=True)
        
        # Validate each agent - exclude test files
        agent_files = list(self.agents_dir.glob('*_agent.py'))
        
        for agent_file in agent_files:
            # Skip test files and base agent
            if 'test_' in agent_file.name or agent_file.name == 'base_agent.py':
                continue
                
            # Extract agent name from filename (e.g., data_preparation_agent.py -> DataPreparationAgent)
            stem = agent_file.stem
            if stem.endswith('_agent'):
                agent_name = stem[:-6]  # Remove _agent
            else:
                agent_name = stem
            
            # Convert snake_case to CamelCase
            agent_name = ''.join(word.capitalize() for word in agent_name.split('_')) + 'Agent'
            
            agent_result = self.validate_agent(agent_name)
            
            if not agent_result.valid:
                result.valid = False
            
            result.errors.extend(agent_result.errors)
            result.warnings.extend(agent_result.warnings)
            result.info.extend(agent_result.info)
        
        # Validate configuration
        config_result = self.validate_configuration()
        if not config_result.valid:
            result.valid = False
        result.errors.extend(config_result.errors)
        result.warnings.extend(config_result.warnings)
        
        # Validate mandatory files
        mandatory_result = self.validate_mandatory_files()
        if not mandatory_result.valid:
            result.valid = False
        result.errors.extend(mandatory_result.errors)
        result.warnings.extend(mandatory_result.warnings)
        
        return result
    
    def validate_agent(self, agent_name: str) -> ValidationResult:
        """Validate a specific agent"""
        result = ValidationResult(valid=True, agent_name=agent_name)
        
        snake_name = self._to_snake_case(agent_name)
        # Try both with and without _agent suffix
        python_files = [
            self.agents_dir / f"{snake_name}_agent.py",
            self.agents_dir / f"{snake_name}.py"
        ]
        python_file = next((f for f in python_files if f.exists()), None)
        
        json_files = [
            self.agents_dir / f"{snake_name}_agent.json",
            self.agents_dir / f"{snake_name}.json"
        ]
        json_file = next((f for f in json_files if f.exists()), None)
        
        logger.info(f"Validating agent: {agent_name}")
        
        # Check if Python file exists
        if not python_file or not python_file.exists():
            result.add_issue(ValidationIssue(
                severity='error',
                code='AGENT_001',
                message=f"Python file not found for agent {agent_name}",
                file=str(self.agents_dir)
            ))
            return result
        
        # Validate Python file
        py_result = self._validate_python_file(python_file, agent_name)
        result.errors.extend(py_result.errors)
        result.warnings.extend(py_result.warnings)
        result.info.extend(py_result.info)
        result.valid = result.valid and py_result.valid
        
        # Validate JSON configuration if exists
        if json_file and json_file.exists():
            json_result = self._validate_json_file(json_file, agent_name)
            result.errors.extend(json_result.errors)
            result.warnings.extend(json_result.warnings)
            result.info.extend(json_result.info)
            result.valid = result.valid and json_result.valid
        elif json_file:
            result.add_issue(ValidationIssue(
                severity='warning',
                code='AGENT_002',
                message=f"JSON configuration file not found: {json_file}",
                file=str(json_file),
                fix=f"Create {json_file} with agent configuration"
            ))
        
        # Validate agent against mandatory files
        mandatory_result = self._validate_agent_mandatory_files(agent_name)
        result.errors.extend(mandatory_result.errors)
        result.warnings.extend(mandatory_result.warnings)
        result.valid = result.valid and mandatory_result.valid
        
        return result
    
    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case"""
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
        return name.lower()
    
    def _validate_python_file(self, file_path: Path, agent_name: str) -> ValidationResult:
        """Validate a Python agent file"""
        result = ValidationResult(valid=True, agent_name=agent_name)
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            result.add_issue(ValidationIssue(
                severity='error',
                code='PY_001',
                message=f"Failed to read file: {str(e)}",
                file=str(file_path)
            ))
            return result
        
        # Parse AST
        try:
            tree = ast.parse(content, filename=str(file_path))
        except SyntaxError as e:
            result.add_issue(ValidationIssue(
                severity='error',
                code='PY_002',
                message=f"Syntax error: {str(e)}",
                file=str(file_path),
                line=e.lineno,
                column=e.offset
            ))
            return result
        
        # Find the agent class - look for any class that inherits from BaseAgent
        agent_class = None
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                # Check if this class inherits from BaseAgent
                for base in node.bases:
                    base_name = base.id if isinstance(base, ast.Name) else str(base)
                    if base_name == 'BaseAgent':
                        agent_class = node
                        break
                if agent_class:
                    break
        
        if not agent_class:
            result.add_issue(ValidationIssue(
                severity='error',
                code='PY_003',
                message=f"No agent class inheriting from BaseAgent found in {file_path}",
                file=str(file_path)
            ))
            return result
        
        # Check base class
        base_classes = [base.id if isinstance(base, ast.Name) else str(base) 
                       for base in agent_class.bases]
        
        if self.REQUIRED_BASE_CLASS not in base_classes:
            result.add_issue(ValidationIssue(
                severity='error',
                code='PY_004',
                message=f"Agent must inherit from {self.REQUIRED_BASE_CLASS}",
                file=str(file_path),
                line=agent_class.lineno,
                fix=f"class {agent_name}({self.REQUIRED_BASE_CLASS}):"
            ))
        
        # Check required methods
        class_methods = {method.name for method in agent_class.body 
                       if isinstance(method, ast.FunctionDef)}
        
        for method in self.REQUIRED_METHODS:
            if method not in class_methods:
                result.add_issue(ValidationIssue(
                    severity='error',
                    code='PY_005',
                    message=f"Required method '{method}' not implemented",
                    file=str(file_path),
                    line=agent_class.lineno,
                    fix=f"def {method}(self, context): # Implement {method}"
                ))
        
        # Check required attributes in __init__
        init_method = None
        for method in agent_class.body:
            if isinstance(method, ast.FunctionDef) and method.name == '__init__':
                init_method = method
                break
        
        if init_method:
            # Check for super().__init__() call
            has_super_init = False
            for node in ast.walk(init_method):
                if isinstance(node, ast.Call):
                    # Check for super().__init__() pattern
                    if (isinstance(node.func, ast.Attribute) and 
                        node.func.attr == '__init__' and
                        isinstance(node.func.value, ast.Call) and
                        isinstance(node.func.value.func, ast.Name) and
                        node.func.value.func.id == 'super'):
                        has_super_init = True
                        break
            
            if not has_super_init:
                result.add_issue(ValidationIssue(
                    severity='error',
                    code='PY_006',
                    message=f"Missing super().__init__() call in __init__ for {agent_class.name}",
                    file=str(file_path),
                    line=init_method.lineno,
                    fix="super().__init__(name=..., version=..., **kwargs)"
                ))
        
        # Check for required attributes
        for attr in self.REQUIRED_ATTRIBUTES:
            found = False
            for node in ast.walk(init_method) if init_method else []:
                if isinstance(node, ast.Assign):
                    for target in node.targets:
                        if isinstance(target, ast.Attribute):
                            if target.attr == attr:
                                found = True
                                break
            
            if not found:
                result.add_issue(ValidationIssue(
                    severity='warning',
                    code='PY_007',
                    message=f"Recommended attribute '{attr}' not set in __init__",
                    file=str(file_path),
                    fix=f"self.{attr} = ..."
                ))
        
        # Check for TODO comments
        for i, line in enumerate(lines, 1):
            if 'TODO' in line.upper() or 'FIXME' in line.upper():
                result.add_issue(ValidationIssue(
                    severity='warning',
                    code='PY_008',
                    message=f"TODO/FIXME comment found",
                    file=str(file_path),
                    line=i,
                    details={'line': line.strip()}
                ))
        
        # Check line length
        for i, line in enumerate(lines, 1):
            if len(line) > self.MAX_LINE_LENGTH:
                result.add_issue(ValidationIssue(
                    severity='warning',
                    code='PY_009',
                    message=f"Line too long ({len(line)} > {self.MAX_LINE_LENGTH})",
                    file=str(file_path),
                    line=i
                ))
        
        # Check for print statements (should use logging)
        for i, line in enumerate(lines, 1):
            if 'print(' in line and not line.strip().startswith('#'):
                result.add_issue(ValidationIssue(
                    severity='warning',
                    code='PY_010',
                    message="Use logging instead of print statements",
                    file=str(file_path),
                    line=i,
                    fix="self.logger.info(...) instead of print(...)"
                ))
        
        # Check for proper error handling
        has_error_handling = False
        for node in ast.walk(tree):
            if isinstance(node, ast.ExceptHandler):
                has_error_handling = True
                break
        
        if not has_error_handling:
            result.add_issue(ValidationIssue(
                severity='warning',
                code='PY_011',
                message="No try/except blocks found - consider adding error handling",
                file=str(file_path)
            ))
        
        return result
    
    def _validate_json_file(self, file_path: Path, agent_name: str) -> ValidationResult:
        """Validate a JSON configuration file"""
        result = ValidationResult(valid=True, agent_name=agent_name)
        
        try:
            with open(file_path, 'r') as f:
                config = json.load(f)
        except json.JSONDecodeError as e:
            result.add_issue(ValidationIssue(
                severity='error',
                code='JSON_001',
                message=f"Invalid JSON: {str(e)}",
                file=str(file_path)
            ))
            return result
        except Exception as e:
            result.add_issue(ValidationIssue(
                severity='error',
                code='JSON_002',
                message=f"Failed to read file: {str(e)}",
                file=str(file_path)
            ))
            return result
        
        # Check required fields
        required_fields = ['name', 'version', 'description']
        for field in required_fields:
            if field not in config:
                result.add_issue(ValidationIssue(
                    severity='error',
                    code='JSON_003',
                    message=f"Missing required field: {field}",
                    file=str(file_path)
                ))
        
        # Check name matches
        if 'name' in config and config['name'] != agent_name:
            result.add_issue(ValidationIssue(
                severity='warning',
                code='JSON_004',
                message=f"Name mismatch: expected '{agent_name}', got '{config['name']}'",
                file=str(file_path)
            ))
        
        # Check version format
        if 'version' in config:
            version = config['version']
            if not re.match(r'^\d+\.\d+\.\d+$', version):
                result.add_issue(ValidationIssue(
                    severity='warning',
                    code='JSON_005',
                    message=f"Version should follow semantic versioning: {version}",
                    file=str(file_path),
                    fix="Use format: MAJOR.MINOR.PATCH (e.g., 1.0.0)"
                ))
        
        return result
    
    def _validate_agent_mandatory_files(self, agent_name: str) -> ValidationResult:
        """Validate that agent reads mandatory files"""
        result = ValidationResult(valid=True, agent_name=agent_name)
        
        snake_name = self._to_snake_case(agent_name)
        python_file = self.agents_dir / f"{snake_name}.py"
        
        if not python_file.exists():
            return result
        
        try:
            with open(python_file, 'r') as f:
                content = f.read()
        except Exception as e:
            return result
        
        # Check for mandatory file reads
        mandatory_files = ['TASK.md', 'task_definition.yaml', 'system_manifest.json']
        
        for mandatory_file in mandatory_files:
            # Check for direct file reads
            if mandatory_file not in content:
                # Check for path joins
                if f"'{mandatory_file}'" not in content and f'"{mandatory_file}"' not in content:
                    result.add_issue(ValidationIssue(
                        severity='warning',
                        code='AGENT_003',
                        message=f"Agent should read mandatory file: {mandatory_file}",
                        file=str(python_file),
                        fix=f"Add: with open('{mandatory_file}', 'r') as f: ..."
                    ))
        
        return result
    
    def validate_configuration(self) -> ValidationResult:
        """Validate project configuration files"""
        result = ValidationResult(valid=True)
        
        # Validate agent_config.yaml
        config_file = self.config_dir / 'agent_config.yaml'
        if config_file.exists():
            config_result = self._validate_yaml_file(config_file)
            result.errors.extend(config_result.errors)
            result.warnings.extend(config_result.warnings)
            result.valid = result.valid and config_result.valid
        else:
            result.add_issue(ValidationIssue(
                severity='warning',
                code='CONFIG_001',
                message=f"Configuration file not found: {config_file}",
                file=str(config_file),
                fix="Create agent_config.yaml with agent configurations"
            ))
        
        return result
    
    def _validate_yaml_file(self, file_path: Path) -> ValidationResult:
        """Validate a YAML file"""
        result = ValidationResult(valid=True)
        
        try:
            with open(file_path, 'r') as f:
                config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            result.add_issue(ValidationIssue(
                severity='error',
                code='YAML_001',
                message=f"Invalid YAML: {str(e)}",
                file=str(file_path)
            ))
            return result
        except Exception as e:
            result.add_issue(ValidationIssue(
                severity='error',
                code='YAML_002',
                message=f"Failed to read file: {str(e)}",
                file=str(file_path)
            ))
            return result
        
        if not isinstance(config, dict):
            result.add_issue(ValidationIssue(
                severity='error',
                code='YAML_003',
                message="Configuration should be a dictionary",
                file=str(file_path)
            ))
            return result
        
        # Check for agents section
        if 'agents' not in config:
            result.add_issue(ValidationIssue(
                severity='warning',
                code='YAML_004',
                message="Missing 'agents' section in configuration",
                file=str(file_path)
            ))
        
        return result
    
    def validate_mandatory_files(self) -> ValidationResult:
        """Validate that mandatory files exist"""
        result = ValidationResult(valid=True)
        
        mandatory_files = [
            'TASK.md',
            'task_definition.yaml',
            'system_manifest.json'
        ]
        
        for mandatory_file in mandatory_files:
            file_path = self.project_root / mandatory_file
            if not file_path.exists():
                result.add_issue(ValidationIssue(
                    severity='error',
                    code='MANDATORY_001',
                    message=f"Mandatory file missing: {mandatory_file}",
                    file=str(file_path),
                    fix=f"Create {mandatory_file} in project root"
                ))
        
        return result
    
    def fix_issues(self, issues: List[ValidationIssue]) -> Dict[str, Any]:
        """Attempt to auto-fix validation issues"""
        fixed_count = 0
        failed_fixes = []
        
        for issue in issues:
            if issue.fix and issue.file and issue.line:
                try:
                    file_path = Path(issue.file)
                    if file_path.exists():
                        with open(file_path, 'r') as f:
                            lines = f.readlines()
                        
                        # Apply fix at specific line
                        if issue.line <= len(lines):
                            # For now, just log the fix suggestion
                            logger.info(f"Suggested fix for {issue.code} at {issue.file}:{issue.line}")
                            logger.info(f"  {issue.fix}")
                            fixed_count += 1
                        else:
                            failed_fixes.append(issue.code)
                    else:
                        failed_fixes.append(issue.code)
                except Exception as e:
                    logger.error(f"Failed to apply fix for {issue.code}: {str(e)}")
                    failed_fixes.append(issue.code)
        
        return {
            'success': len(failed_fixes) == 0,
            'fixed_count': fixed_count,
            'failed_fixes': failed_fixes,
            'error': f"Failed to fix {len(failed_fixes)} issues" if failed_fixes else None
        }


class CodeQualityChecker:
    """Checks code quality metrics"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        
    def check_file(self, file_path: Path) -> Dict[str, Any]:
        """Check code quality for a single file"""
        result = {
            'file': str(file_path),
            'issues': [],
            'metrics': {}
        }
        
        try:
            with open(file_path, 'r') as f:
                content = f.read()
                lines = content.split('\n')
        except Exception as e:
            result['issues'].append({
                'severity': 'error',
                'code': 'QUALITY_001',
                'message': f"Failed to read file: {str(e)}"
            })
            return result
        
        # Count lines
        result['metrics']['lines'] = len(lines)
        result['metrics']['non_empty_lines'] = len([l for l in lines if l.strip()])
        
        # Check for common issues
        for i, line in enumerate(lines, 1):
            # Check line length
            if len(line) > 120:
                result['issues'].append({
                    'severity': 'warning',
                    'code': 'QUALITY_002',
                    'message': f"Line too long ({len(line)} chars)",
                    'line': i
                })
            
            # Check for trailing whitespace
            if line.rstrip() != line:
                result['issues'].append({
                    'severity': 'info',
                    'code': 'QUALITY_003',
                    'message': "Trailing whitespace",
                    'line': i,
                    'fix': "Remove trailing whitespace"
                })
            
            # Check for mixed tabs and spaces
            if '\t' in line and '    ' in line:
                result['issues'].append({
                    'severity': 'warning',
                    'code': 'QUALITY_004',
                    'message': "Mixed tabs and spaces",
                    'line': i,
                    'fix': "Use spaces only (PEP 8)"
                })
        
        return result
    
    def check_all_files(self) -> Dict[str, Any]:
        """Check code quality for all Python files"""
        result = {
            'files_checked': 0,
            'total_issues': 0,
            'issues_by_severity': {'error': 0, 'warning': 0, 'info': 0},
            'files': {}
        }
        
        # Check agents directory
        agents_dir = self.project_root / 'agents'
        if agents_dir.exists():
            for py_file in agents_dir.glob('*.py'):
                if py_file.name.startswith('_'):
                    continue
                    
                file_result = self.check_file(py_file)
                result['files_checked'] += 1
                result['total_issues'] += len(file_result['issues'])
                result['files'][str(py_file)] = file_result
                
                for issue in file_result['issues']:
                    severity = issue['severity']
                    result['issues_by_severity'][severity] = \
                        result['issues_by_severity'].get(severity, 0) + 1
        
        return result
