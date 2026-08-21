#!/usr/bin/env python3
"""
DeveloperAgent Framework - Code Quality Enforcer

Enforces code quality standards: formatting, linting, type checking.
"""

import os
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger('QualityEnforcer')


@dataclass
class QualityIssue:
    """Represents a code quality issue"""
    severity: str  # 'error', 'warning', 'info'
    code: str
    message: str
    file: str
    line: Optional[int] = None
    column: Optional[int] = None
    fix: Optional[str] = None


@dataclass
class QualityResult:
    """Result of quality check"""
    success: bool
    issues: List[QualityIssue] = field(default_factory=list)
    files_checked: int = 0
    metrics: Dict[str, Any] = field(default_factory=dict)


class QualityEnforcer:
    """Enforces code quality standards"""
    
    def __init__(self):
        self.project_root = Path(__file__).parent.parent
        self.agents_dir = self.project_root / 'agents'
        self.scripts_dir = self.project_root / 'scripts'
        self.tests_dir = self.project_root / 'tests'
        
        # Tool configurations
        self.tools = {
            'black': {
                'enabled': True,
                'config': self.project_root / 'pyproject.toml',
                'line_length': 120
            },
            'flake8': {
                'enabled': True,
                'config': self.project_root / '.flake8',
                'max_line_length': 120,
                'ignore': ['E203', 'W503']  # Common conflicts with black
            },
            'isort': {
                'enabled': True,
                'config': self.project_root / '.isort.cfg',
                'profile': 'black'
            },
            'mypy': {
                'enabled': True,
                'config': self.project_root / 'mypy.ini',
                'python_version': '3.12'
            },
            'pylint': {
                'enabled': False,  # Disabled by default (slower)
                'config': self.project_root / '.pylintrc'
            }
        }
    
    def check_all(self) -> QualityResult:
        """Check quality for all Python files"""
        result = QualityResult(success=True)
        
        # Check agents
        agents_result = self._check_directory(self.agents_dir)
        result.issues.extend(agents_result.issues)
        result.files_checked += agents_result.files_checked
        result.success = result.success and agents_result.success
        
        # Check scripts
        scripts_result = self._check_directory(self.scripts_dir)
        result.issues.extend(scripts_result.issues)
        result.files_checked += scripts_result.files_checked
        result.success = result.success and scripts_result.success
        
        # Check tests
        if self.tests_dir.exists():
            tests_result = self._check_directory(self.tests_dir)
            result.issues.extend(tests_result.issues)
            result.files_checked += tests_result.files_checked
            result.success = result.success and tests_result.success
        
        # Check framework itself
        framework_dir = self.project_root / 'dev_framework'
        if framework_dir.exists():
            framework_result = self._check_directory(framework_dir)
            result.issues.extend(framework_result.issues)
            result.files_checked += framework_result.files_checked
            result.success = result.success and framework_result.success
        
        return result
    
    def check_agent(self, agent_name: str) -> QualityResult:
        """Check quality for a specific agent"""
        result = QualityResult(success=True)
        
        snake_name = self._to_snake_case(agent_name)
        agent_file = self.agents_dir / f"{snake_name}.py"
        
        if not agent_file.exists():
            result.success = False
            result.issues.append(QualityIssue(
                severity='error',
                code='QUALITY_001',
                message=f"Agent file not found: {agent_file}",
                file=str(agent_file)
            ))
            return result
        
        # Run all quality checks on the agent file
        file_result = self._check_file(agent_file)
        result.issues.extend(file_result.issues)
        result.files_checked += 1
        result.success = result.success and file_result.success
        
        return result
    
    def fix_all(self) -> QualityResult:
        """Auto-fix quality issues for all files"""
        result = QualityResult(success=True)
        
        # Fix agents
        agents_result = self._fix_directory(self.agents_dir)
        result.issues.extend(agents_result.issues)
        result.files_checked += agents_result.files_checked
        result.success = result.success and agents_result.success
        
        # Fix scripts
        scripts_result = self._fix_directory(self.scripts_dir)
        result.issues.extend(scripts_result.issues)
        result.files_checked += scripts_result.files_checked
        result.success = result.success and scripts_result.success
        
        # Fix tests
        if self.tests_dir.exists():
            tests_result = self._fix_directory(self.tests_dir)
            result.issues.extend(tests_result.issues)
            result.files_checked += tests_result.files_checked
            result.success = result.success and tests_result.success
        
        return result
    
    def fix_agent(self, agent_name: str) -> QualityResult:
        """Auto-fix quality issues for a specific agent"""
        result = QualityResult(success=True)
        
        snake_name = self._to_snake_case(agent_name)
        agent_file = self.agents_dir / f"{snake_name}.py"
        
        if not agent_file.exists():
            result.success = False
            result.issues.append(QualityIssue(
                severity='error',
                code='QUALITY_001',
                message=f"Agent file not found: {agent_file}",
                file=str(agent_file)
            ))
            return result
        
        # Fix the agent file
        file_result = self._fix_file(agent_file)
        result.issues.extend(file_result.issues)
        result.files_checked += 1
        result.success = result.success and file_result.success
        
        return result
    
    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case"""
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
        return name.lower()
    
    def _check_directory(self, directory: Path) -> QualityResult:
        """Check quality for all Python files in a directory"""
        result = QualityResult(success=True)
        
        if not directory.exists():
            return result
        
        for py_file in directory.rglob('*.py'):
            if py_file.name.startswith('_'):
                continue
            
            file_result = self._check_file(py_file)
            result.issues.extend(file_result.issues)
            result.files_checked += 1
            result.success = result.success and file_result.success
        
        return result
    
    def _check_file(self, file_path: Path) -> QualityResult:
        """Check quality for a single file"""
        result = QualityResult(success=True)
        
        logger.debug(f"Checking quality for: {file_path}")
        
        # Run each quality tool
        for tool_name, tool_config in self.tools.items():
            if not tool_config['enabled']:
                continue
            
            try:
                tool_result = self._run_tool(tool_name, file_path)
                if not tool_result['success']:
                    result.success = False
                    for issue in tool_result['issues']:
                        result.issues.append(QualityIssue(
                            severity=issue['severity'],
                            code=issue['code'],
                            message=issue['message'],
                            file=issue['file'],
                            line=issue.get('line'),
                            column=issue.get('column'),
                            fix=issue.get('fix')
                        ))
            except Exception as e:
                logger.error(f"Error running {tool_name} on {file_path}: {str(e)}")
                result.issues.append(QualityIssue(
                    severity='error',
                    code=f'{tool_name.upper()}_001',
                    message=f"Failed to run {tool_name}: {str(e)}",
                    file=str(file_path)
                ))
                result.success = False
        
        return result
    
    def _fix_directory(self, directory: Path) -> QualityResult:
        """Auto-fix quality issues for all Python files in a directory"""
        result = QualityResult(success=True)
        
        if not directory.exists():
            return result
        
        for py_file in directory.rglob('*.py'):
            if py_file.name.startswith('_'):
                continue
            
            file_result = self._fix_file(py_file)
            result.issues.extend(file_result.issues)
            result.files_checked += 1
            result.success = result.success and file_result.success
        
        return result
    
    def _fix_file(self, file_path: Path) -> QualityResult:
        """Auto-fix quality issues for a single file"""
        result = QualityResult(success=True)
        
        logger.debug(f"Fixing quality for: {file_path}")
        
        # Run fixable tools
        fixable_tools = ['black', 'isort']
        
        for tool_name in fixable_tools:
            if not self.tools[tool_name]['enabled']:
                continue
            
            try:
                tool_result = self._run_tool_fix(tool_name, file_path)
                if not tool_result['success']:
                    result.success = False
                    for issue in tool_result['issues']:
                        result.issues.append(QualityIssue(
                            severity=issue['severity'],
                            code=issue['code'],
                            message=issue['message'],
                            file=issue['file'],
                            line=issue.get('line'),
                            fix=issue.get('fix')
                        ))
            except Exception as e:
                logger.error(f"Error fixing with {tool_name} on {file_path}: {str(e)}")
                result.issues.append(QualityIssue(
                    severity='error',
                    code=f'{tool_name.upper()}_002',
                    message=f"Failed to fix with {tool_name}: {str(e)}",
                    file=str(file_path)
                ))
                result.success = False
        
        return result
    
    def _run_tool(self, tool_name: str, file_path: Path) -> Dict[str, Any]:
        """Run a quality tool on a file"""
        result = {
            'success': True,
            'issues': [],
            'output': ''
        }
        
        if tool_name == 'black':
            result = self._run_black(file_path, check=True)
        elif tool_name == 'flake8':
            result = self._run_flake8(file_path)
        elif tool_name == 'isort':
            result = self._run_isort(file_path, check=True)
        elif tool_name == 'mypy':
            result = self._run_mypy(file_path)
        elif tool_name == 'pylint':
            result = self._run_pylint(file_path)
        
        return result
    
    def _run_tool_fix(self, tool_name: str, file_path: Path) -> Dict[str, Any]:
        """Run a quality tool to fix issues"""
        result = {
            'success': True,
            'issues': [],
            'output': ''
        }
        
        if tool_name == 'black':
            result = self._run_black(file_path, check=False)
        elif tool_name == 'isort':
            result = self._run_isort(file_path, check=False)
        
        return result
    
    def _run_black(self, file_path: Path, check: bool = True) -> Dict[str, Any]:
        """Run black formatter"""
        result = {
            'success': True,
            'issues': [],
            'output': ''
        }
        
        cmd = ['black']
        if check:
            cmd.append('--check')
        cmd.extend([
            '--line-length', str(self.tools['black']['line_length']),
            '--quiet',
            str(file_path)
        ])
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_root)
            )
            stdout, stderr = process.communicate(timeout=30)
            result['output'] = stdout + stderr
            
            if process.returncode != 0:
                result['success'] = False
                # Parse black output for issues
                if 'would be left unchanged' in stderr:
                    # This is actually a success case for check mode
                    result['success'] = True
                else:
                    result['issues'].append({
                        'severity': 'error',
                        'code': 'BLACK_001',
                        'message': f"Black formatting failed: {stderr.strip()}",
                        'file': str(file_path)
                    })
        except subprocess.TimeoutExpired:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'BLACK_002',
                'message': 'Black timed out',
                'file': str(file_path)
            })
        except FileNotFoundError:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'BLACK_003',
                'message': 'Black not installed',
                'file': str(file_path),
                'fix': 'pip install black'
            })
        except Exception as e:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'BLACK_004',
                'message': f"Black error: {str(e)}",
                'file': str(file_path)
            })
        
        return result
    
    def _run_flake8(self, file_path: Path) -> Dict[str, Any]:
        """Run flake8 linter"""
        result = {
            'success': True,
            'issues': [],
            'output': ''
        }
        
        cmd = [
            'flake8',
            '--max-line-length', str(self.tools['flake8']['max_line_length']),
            '--ignore', ','.join(self.tools['flake8']['ignore']),
            '--format', 'json',
            str(file_path)
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_root)
            )
            stdout, stderr = process.communicate(timeout=30)
            result['output'] = stdout + stderr
            
            if process.returncode != 0 and stdout.strip():
                # Parse JSON output
                try:
                    import json
                    issues = json.loads(stdout)
                    for issue in issues:
                        result['issues'].append({
                            'severity': 'error' if issue['code'].startswith('E') else 'warning',
                            'code': f"FLAKE8_{issue['code']}",
                            'message': issue['text'],
                            'file': issue['filename'],
                            'line': issue['line_number'],
                            'column': issue['column_number']
                        })
                except json.JSONDecodeError:
                    result['issues'].append({
                        'severity': 'error',
                        'code': 'FLAKE8_001',
                        'message': f"Flake8 failed: {stdout.strip()}",
                        'file': str(file_path)
                    })
                
                result['success'] = len(result['issues']) == 0
        except subprocess.TimeoutExpired:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'FLAKE8_002',
                'message': 'Flake8 timed out',
                'file': str(file_path)
            })
        except FileNotFoundError:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'FLAKE8_003',
                'message': 'Flake8 not installed',
                'file': str(file_path),
                'fix': 'pip install flake8'
            })
        except Exception as e:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'FLAKE8_004',
                'message': f"Flake8 error: {str(e)}",
                'file': str(file_path)
            })
        
        return result
    
    def _run_isort(self, file_path: Path, check: bool = True) -> Dict[str, Any]:
        """Run isort import sorter"""
        result = {
            'success': True,
            'issues': [],
            'output': ''
        }
        
        cmd = ['isort']
        if check:
            cmd.append('--check-only')
        cmd.extend([
            '--profile', self.tools['isort']['profile'],
            '--quiet',
            str(file_path)
        ])
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_root)
            )
            stdout, stderr = process.communicate(timeout=30)
            result['output'] = stdout + stderr
            
            if process.returncode != 0:
                result['success'] = False
                result['issues'].append({
                    'severity': 'error',
                    'code': 'ISORT_001',
                    'message': f"Isort failed: {stderr.strip()}",
                    'file': str(file_path)
                })
        except subprocess.TimeoutExpired:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'ISORT_002',
                'message': 'Isort timed out',
                'file': str(file_path)
            })
        except FileNotFoundError:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'ISORT_003',
                'message': 'Isort not installed',
                'file': str(file_path),
                'fix': 'pip install isort'
            })
        except Exception as e:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'ISORT_004',
                'message': f"Isort error: {str(e)}",
                'file': str(file_path)
            })
        
        return result
    
    def _run_mypy(self, file_path: Path) -> Dict[str, Any]:
        """Run mypy type checker"""
        result = {
            'success': True,
            'issues': [],
            'output': ''
        }
        
        cmd = [
            'mypy',
            '--python-version', self.tools['mypy']['python_version'],
            '--ignore-missing-imports',
            '--show-error-codes',
            str(file_path)
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_root)
            )
            stdout, stderr = process.communicate(timeout=60)
            result['output'] = stdout + stderr
            
            if process.returncode != 0 and stdout.strip():
                # Parse mypy output
                for line in stdout.strip().split('\n'):
                    if ':' in line and 'error:' in line:
                        parts = line.split(':')
                        if len(parts) >= 4:
                            file_path = parts[0].strip()
                            line_num = parts[1].strip()
                            column = parts[2].strip().split()[0] if parts[2].strip() else '0'
                            message = ':'.join(parts[3:]).strip()
                            
                            result['issues'].append({
                                'severity': 'error',
                                'code': 'MYPY_001',
                                'message': message,
                                'file': file_path,
                                'line': int(line_num) if line_num.isdigit() else None,
                                'column': int(column) if column.isdigit() else None
                            })
                
                result['success'] = len(result['issues']) == 0
        except subprocess.TimeoutExpired:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'MYPY_002',
                'message': 'Mypy timed out',
                'file': str(file_path)
            })
        except FileNotFoundError:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'MYPY_003',
                'message': 'Mypy not installed',
                'file': str(file_path),
                'fix': 'pip install mypy'
            })
        except Exception as e:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'MYPY_004',
                'message': f"Mypy error: {str(e)}",
                'file': str(file_path)
            })
        
        return result
    
    def _run_pylint(self, file_path: Path) -> Dict[str, Any]:
        """Run pylint linter"""
        result = {
            'success': True,
            'issues': [],
            'output': ''
        }
        
        cmd = [
            'pylint',
            '--output-format', 'json',
            str(file_path)
        ]
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_root)
            )
            stdout, stderr = process.communicate(timeout=60)
            result['output'] = stdout + stderr
            
            if process.returncode != 0 and stdout.strip():
                # Parse pylint JSON output
                try:
                    import json
                    # Pylint outputs multiple JSON objects, we need to parse them
                    # This is a simplified approach
                    lines = stdout.strip().split('\n')
                    for line in lines:
                        if line.strip().startswith('{'):
                            try:
                                issue = json.loads(line)
                                result['issues'].append({
                                    'severity': issue.get('type', 'error').lower(),
                                    'code': f"PYLINT_{issue.get('symbol', '001')}",
                                    'message': issue.get('message', 'Unknown error'),
                                    'file': issue.get('path', str(file_path)),
                                    'line': issue.get('line'),
                                    'column': issue.get('column')
                                })
                            except json.JSONDecodeError:
                                continue
                except Exception:
                    result['issues'].append({
                        'severity': 'error',
                        'code': 'PYLINT_001',
                        'message': f"Pylint failed: {stdout.strip()}",
                        'file': str(file_path)
                    })
                
                result['success'] = len(result['issues']) == 0
        except subprocess.TimeoutExpired:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'PYLINT_002',
                'message': 'Pylint timed out',
                'file': str(file_path)
            })
        except FileNotFoundError:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'PYLINT_003',
                'message': 'Pylint not installed',
                'file': str(file_path),
                'fix': 'pip install pylint'
            })
        except Exception as e:
            result['success'] = False
            result['issues'].append({
                'severity': 'error',
                'code': 'PYLINT_004',
                'message': f"Pylint error: {str(e)}",
                'file': str(file_path)
            })
        
        return result
    
    def check_tools_available(self) -> Dict[str, bool]:
        """Check which quality tools are available"""
        available = {}
        
        for tool_name in self.tools.keys():
            try:
                # Try to get version
                cmd = [tool_name, '--version']
                subprocess.run(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=10
                )
                available[tool_name] = True
            except FileNotFoundError:
                available[tool_name] = False
            except Exception:
                available[tool_name] = False
        
        return available
    
    def install_missing_tools(self) -> Dict[str, Any]:
        """Install missing quality tools"""
        result = {
            'success': True,
            'installed': [],
            'failed': [],
            'already_installed': []
        }
        
        available = self.check_tools_available()
        
        tools_to_install = {
            'black': 'black',
            'flake8': 'flake8',
            'isort': 'isort',
            'mypy': 'mypy'
        }
        
        for tool_name, package_name in tools_to_install.items():
            if available.get(tool_name, False):
                result['already_installed'].append(tool_name)
            else:
                try:
                    subprocess.run(
                        ['pip', 'install', package_name],
                        check=True,
                        timeout=60
                    )
                    result['installed'].append(tool_name)
                except Exception as e:
                    result['success'] = False
                    result['failed'].append({
                        'tool': tool_name,
                        'error': str(e)
                    })
        
        return result
