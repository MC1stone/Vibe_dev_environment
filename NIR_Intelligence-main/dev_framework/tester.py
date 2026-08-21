#!/usr/bin/env python3
"""
DeveloperAgent Framework - Agent Tester

Runs unit, integration, and end-to-end tests for agents.
"""

import os
import sys
import json
import subprocess
import logging
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

logger = logging.getLogger('AgentTester')


@dataclass
class TestResult:
    """Result of a test run"""
    success: bool
    passed: int = 0
    failed: int = 0
    skipped: int = 0
    errors: int = 0
    coverage: Optional[float] = None
    duration: float = 0.0
    test_files: List[str] = field(default_factory=list)
    failed_tests: List[Dict[str, Any]] = field(default_factory=list)
    error_message: Optional[str] = None


@dataclass
class AgentTestResult:
    """Result of testing a specific agent"""
    agent_name: str
    unit: TestResult = field(default_factory=TestResult)
    integration: TestResult = field(default_factory=TestResult)
    e2e: TestResult = field(default_factory=TestResult)
    overall: TestResult = field(default_factory=TestResult)


class AgentTester:
    """Runs tests for agents"""
    
    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self.project_root = Path(__file__).parent.parent
        self.agents_dir = self.project_root / 'agents'
        self.tests_dir = self.project_root / 'tests'
        self.coverage_dir = self.project_root / 'htmlcov'
        self.coverage_file = self.project_root / '.coverage'
        
        # Ensure tests directory exists
        self.tests_dir.mkdir(parents=True, exist_ok=True)
    
    def run_all_tests(
        self,
        test_type: str = 'all',
        with_coverage: bool = False
    ) -> Dict[str, Any]:
        """Run tests for all agents"""
        result = {
            'success': True,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'coverage': None,
            'duration': 0.0,
            'agents': {},
            'test_files': []
        }
        
        # Get all agent files
        agent_files = list(self.agents_dir.glob('*_agent.py'))
        
        for agent_file in agent_files:
            # Extract agent name from filename
            agent_name = agent_file.stem.replace('_agent', '')
            # Convert snake_case to CamelCase
            agent_name = ''.join(word.capitalize() for word in agent_name.split('_')) + 'Agent'
            
            # Run tests for this agent
            agent_result = self.run_agent_tests(
                agent_name=agent_name,
                test_type=test_type,
                with_coverage=False  # Coverage is handled separately
            )
            
            if agent_result['success']:
                result['passed'] += agent_result['passed']
                result['failed'] += agent_result['failed']
                result['skipped'] += agent_result['skipped']
                result['errors'] += agent_result['errors']
                result['duration'] += agent_result['duration']
                result['test_files'].extend(agent_result['test_files'])
                result['agents'][agent_name] = agent_result
            else:
                result['success'] = False
                result['error_message'] = agent_result.get('error_message', 'Test failed')
        
        # Run coverage if requested
        if with_coverage:
            coverage_result = self.run_coverage()
            result['coverage'] = coverage_result.get('coverage')
        
        return result
    
    def run_agent_tests(
        self,
        agent_name: str,
        test_type: str = 'all',
        with_coverage: bool = False
    ) -> Dict[str, Any]:
        """Run tests for a specific agent"""
        snake_name = self._to_snake_case(agent_name)
        
        result = {
            'success': True,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'coverage': None,
            'duration': 0.0,
            'test_files': [],
            'agent_name': agent_name
        }
        
        # Determine which test types to run
        if test_type == 'all':
            test_types = ['unit', 'integration', 'e2e']
        else:
            test_types = [test_type]
        
        for ttype in test_types:
            type_result = self._run_test_type(agent_name, ttype)
            
            if type_result.success:
                result['passed'] += type_result.passed
                result['failed'] += type_result.failed
                result['skipped'] += type_result.skipped
                result['errors'] += type_result.errors
                result['duration'] += type_result.duration
                result['test_files'].extend(type_result.test_files)
            else:
                result['success'] = False
                result['error_message'] = type_result.error_message
        
        # Run coverage for this agent if requested
        if with_coverage:
            coverage_result = self.run_coverage([f'tests/{ttype}/test_{snake_name}*' for ttype in test_types])
            result['coverage'] = coverage_result.get('coverage')
        
        return result
    
    def _to_snake_case(self, name: str) -> str:
        """Convert CamelCase to snake_case"""
        import re
        name = re.sub('(.)([A-Z][a-z]+)', r'\1_\2', name)
        name = re.sub('([a-z0-9])([A-Z])', r'\1_\2', name)
        return name.lower()
    
    def _run_test_type(self, agent_name: str, test_type: str) -> TestResult:
        """Run a specific type of test for an agent"""
        snake_name = self._to_snake_case(agent_name)
        
        # Determine test file pattern
        if test_type == 'unit':
            pattern = f'tests/unit/test_{snake_name}.py'
        elif test_type == 'integration':
            pattern = f'tests/integration/test_{snake_name}_integration.py'
        else:  # e2e
            pattern = f'tests/e2e/test_{snake_name}_e2e.py'
        
        # Check if test file exists
        test_file = self.project_root / pattern
        if not test_file.exists():
            return TestResult(
                success=True,
                passed=0,
                failed=0,
                skipped=0,
                errors=0,
                duration=0.0,
                test_files=[str(test_file)],
                error_message=f"Test file not found: {test_file}"
            )
        
        # Run pytest on the test file
        return self._run_pytest(str(test_file))
    
    def _run_pytest(self, test_path: str) -> TestResult:
        """Run pytest on a specific test file or pattern"""
        result = TestResult(
            success=True,
            passed=0,
            failed=0,
            skipped=0,
            errors=0,
            duration=0.0,
            test_files=[test_path]
        )
        
        # Build pytest command
        cmd = [
            sys.executable, '-m', 'pytest',
            test_path,
            '-v' if self.verbose else '-q',
            '--tb=short',
            '-r', 'pfsE'  # Show passed, failed, skipped, errors
        ]
        
        try:
            start_time = time.time()
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_root)
            )
            stdout, stderr = process.communicate(timeout=300)  # 5 minute timeout
            result.duration = time.time() - start_time
            
            # Parse pytest output
            output = stdout + stderr
            
            # Count results from output
            if 'passed' in output:
                passed_match = re.search(r'(\d+) passed', output)
                if passed_match:
                    result.passed = int(passed_match.group(1))
            
            if 'failed' in output:
                failed_match = re.search(r'(\d+) failed', output)
                if failed_match:
                    result.failed = int(failed_match.group(1))
            
            if 'skipped' in output:
                skipped_match = re.search(r'(\d+) skipped', output)
                if skipped_match:
                    result.skipped = int(skipped_match.group(1))
            
            if 'error' in output:
                error_match = re.search(r'(\d+) error', output)
                if error_match:
                    result.errors = int(error_match.group(1))
            
            # Check overall success
            if process.returncode != 0:
                result.success = False
            
            # Parse failed tests
            if result.failed > 0:
                self._parse_failed_tests(output, result)
            
        except subprocess.TimeoutExpired:
            result.success = False
            result.error_message = f"Tests timed out after 300 seconds"
        except FileNotFoundError:
            result.success = False
            result.error_message = "pytest not installed"
        except Exception as e:
            result.success = False
            result.error_message = f"Error running tests: {str(e)}"
        
        return result
    
    def _parse_failed_tests(self, output: str, result: TestResult):
        """Parse failed test details from pytest output"""
        import re
        
        # Look for FAILED entries
        failed_pattern = r'FAILED\s+(.+?)\s+-\s+(.+)'
        matches = re.finditer(failed_pattern, output)
        
        for match in matches:
            test_file = match.group(1).strip()
            test_name = match.group(2).strip()
            
            result.failed_tests.append({
                'file': test_file,
                'name': test_name,
                'message': 'Test failed'
            })
        
        # Look for error details
        error_pattern = r'E\s+=\s+(.+)'
        error_matches = re.finditer(error_pattern, output)
        
        for i, match in enumerate(error_matches):
            if i < len(result.failed_tests):
                result.failed_tests[i]['message'] = match.group(1).strip()
    
    def run_coverage(self, test_patterns: Optional[List[str]] = None) -> Dict[str, Any]:
        """Run tests with coverage"""
        result = {
            'success': True,
            'coverage': None,
            'report': '',
            'error_message': None
        }
        
        # Build coverage command
        cmd = [
            sys.executable, '-m', 'pytest',
            '--cov=agents',
            '--cov=scripts',
            '--cov-report=term-missing',
            '--cov-report=html:htmlcov'
        ]
        
        # Add test patterns if specified
        if test_patterns:
            cmd.extend(test_patterns)
        else:
            # Test all agents
            cmd.append('tests/')
        
        try:
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                cwd=str(self.project_root)
            )
            stdout, stderr = process.communicate(timeout=600)  # 10 minute timeout
            
            output = stdout + stderr
            result['report'] = output
            
            # Parse coverage percentage
            coverage_match = re.search(r'TOTAL\s+\d+\s+\d+\s+(\d+)%', output)
            if coverage_match:
                result['coverage'] = float(coverage_match.group(1))
            
            # Check success
            if process.returncode != 0:
                result['success'] = False
                result['error_message'] = "Coverage test failed"
            
        except subprocess.TimeoutExpired:
            result['success'] = False
            result['error_message'] = "Coverage test timed out"
        except FileNotFoundError:
            result['success'] = False
            result['error_message'] = "pytest or pytest-cov not installed"
        except Exception as e:
            result['success'] = False
            result['error_message'] = f"Coverage error: {str(e)}"
        
        return result
    
    def run_specific_test(self, test_path: str) -> Dict[str, Any]:
        """Run a specific test file"""
        result = {
            'success': True,
            'passed': 0,
            'failed': 0,
            'skipped': 0,
            'errors': 0,
            'duration': 0.0,
            'output': '',
            'error_message': None
        }
        
        # Run pytest on specific file
        test_result = self._run_pytest(test_path)
        
        result['success'] = test_result.success
        result['passed'] = test_result.passed
        result['failed'] = test_result.failed
        result['skipped'] = test_result.skipped
        result['errors'] = test_result.errors
        result['duration'] = test_result.duration
        result['output'] = f"Passed: {test_result.passed}, Failed: {test_result.failed}, Skipped: {test_result.skipped}"
        
        if not test_result.success:
            result['error_message'] = test_result.error_message
        
        return result
    
    def discover_tests(self) -> Dict[str, Any]:
        """Discover all available tests"""
        result = {
            'unit': [],
            'integration': [],
            'e2e': [],
            'total': 0
        }
        
        # Check each test directory
        for test_type in ['unit', 'integration', 'e2e']:
            test_dir = self.tests_dir / test_type
            if test_dir.exists():
                test_files = list(test_dir.glob('test_*.py'))
                result[test_type] = [str(f.relative_to(self.project_root)) for f in test_files]
                result['total'] += len(test_files)
        
        return result
    
    def check_test_coverage(self) -> Dict[str, Any]:
        """Check which agents have tests"""
        result = {
            'agents_with_tests': [],
            'agents_without_tests': [],
            'coverage_percentage': 0.0
        }
        
        # Get all agents
        agent_files = list(self.agents_dir.glob('*_agent.py'))
        agents = []
        for f in agent_files:
            agent_name = f.stem.replace('_agent', '')
            agents.append(''.join(word.capitalize() for word in agent_name.split('_')) + 'Agent')
        
        # Check for tests
        for agent in agents:
            snake_name = self._to_snake_case(agent)
            has_unit = (self.tests_dir / 'unit' / f'test_{snake_name}.py').exists()
            has_integration = (self.tests_dir / 'integration' / f'test_{snake_name}_integration.py').exists()
            has_e2e = (self.tests_dir / 'e2e' / f'test_{snake_name}_e2e.py').exists()
            
            if has_unit or has_integration or has_e2e:
                result['agents_with_tests'].append({
                    'agent': agent,
                    'unit': has_unit,
                    'integration': has_integration,
                    'e2e': has_e2e
                })
            else:
                result['agents_without_tests'].append(agent)
        
        # Calculate coverage percentage
        total_agents = len(agents)
        if total_agents > 0:
            result['coverage_percentage'] = \
                (len(result['agents_with_tests']) / total_agents) * 100
        
        return result
    
    def generate_test_report(self, output_format: str = 'text') -> str:
        """Generate a test report"""
        # Run all tests first
        test_result = self.run_all_tests()
        
        if output_format == 'text':
            return self._generate_text_report(test_result)
        elif output_format == 'json':
            return json.dumps(test_result, indent=2)
        elif output_format == 'html':
            return self._generate_html_report(test_result)
        else:
            return self._generate_text_report(test_result)
    
    def _generate_text_report(self, test_result: Dict[str, Any]) -> str:
        """Generate text report"""
        lines = []
        lines.append("=" * 60)
        lines.append("NIR Intelligence Platform - Test Report")
        lines.append("=" * 60)
        lines.append("")
        
        # Summary
        lines.append("SUMMARY")
        lines.append("-" * 40)
        lines.append(f"Total Tests: {test_result['passed'] + test_result['failed'] + test_result['skipped'] + test_result['errors']}")
        lines.append(f"Passed: {test_result['passed']}")
        lines.append(f"Failed: {test_result['failed']}")
        lines.append(f"Skipped: {test_result['skipped']}")
        lines.append(f"Errors: {test_result['errors']}")
        lines.append(f"Duration: {test_result['duration']:.2f}s")
        if test_result['coverage'] is not None:
            lines.append(f"Coverage: {test_result['coverage']:.1f}%")
        lines.append("")
        
        # Agent details
        lines.append("AGENT DETAILS")
        lines.append("-" * 40)
        for agent_name, agent_result in test_result['agents'].items():
            lines.append(f"\n{agent_name}:")
            lines.append(f"  Passed: {agent_result['passed']}")
            lines.append(f"  Failed: {agent_result['failed']}")
            lines.append(f"  Skipped: {agent_result['skipped']}")
            lines.append(f"  Errors: {agent_result['errors']}")
        
        # Failed tests
        if test_result['failed'] > 0:
            lines.append("\nFAILED TESTS")
            lines.append("-" * 40)
            for agent_name, agent_result in test_result['agents'].items():
                if agent_result['failed'] > 0:
                    lines.append(f"\n{agent_name}:")
                    for failed_test in agent_result.get('failed_tests', []):
                        lines.append(f"  - {failed_test['name']}: {failed_test['message']}")
        
        lines.append("\n" + "=" * 60)
        
        return "\n".join(lines)
    
    def _generate_html_report(self, test_result: Dict[str, Any]) -> str:
        """Generate HTML report"""
        html = []
        html.append("""<!DOCTYPE html>
<html>
<head>
    <title>NIR Intelligence Platform - Test Report</title>
    <style>
        body { font-family: Arial, sans-serif; margin: 20px; }
        h1 { color: #333; }
        .summary { background: #f5f5f5; padding: 15px; border-radius: 5px; margin-bottom: 20px; }
        .passed { color: green; }
        .failed { color: red; }
        .skipped { color: orange; }
        .error { color: purple; }
        table { width: 100%; border-collapse: collapse; margin: 10px 0; }
        th, td { padding: 8px; text-align: left; border-bottom: 1px solid #ddd; }
        th { background: #f5f5f5; }
        .failed-test { background: #ffebee; padding: 10px; margin: 5px 0; border-radius: 5px; }
    </style>
</head>
<body>
    <h1>NIR Intelligence Platform - Test Report</h1>
""")
        
        # Summary
        total = test_result['passed'] + test_result['failed'] + test_result['skipped'] + test_result['errors']
        html.append(f"""
    <div class="summary">
        <h2>Summary</h2>
        <p>Total Tests: {total}</p>
        <p class="passed">Passed: {test_result['passed']}</p>
        <p class="failed">Failed: {test_result['failed']}</p>
        <p class="skipped">Skipped: {test_result['skipped']}</p>
        <p class="error">Errors: {test_result['errors']}</p>
        <p>Duration: {test_result['duration']:.2f}s</p>
        """)
        if test_result['coverage'] is not None:
            html.append(f"<p>Coverage: {test_result['coverage']:.1f}%</p>")
        html.append("</div>")
        
        # Agent table
        html.append("""
    <h2>Agent Details</h2>
    <table>
        <tr>
            <th>Agent</th>
            <th>Passed</th>
            <th>Failed</th>
            <th>Skipped</th>
            <th>Errors</th>
        </tr>
""")
        
        for agent_name, agent_result in test_result['agents'].items():
            html.append(f"""
        <tr>
            <td>{agent_name}</td>
            <td class="passed">{agent_result['passed']}</td>
            <td class="failed">{agent_result['failed']}</td>
            <td class="skipped">{agent_result['skipped']}</td>
            <td class="error">{agent_result['errors']}</td>
        </tr>
""")
        
        html.append("</table>")
        
        # Failed tests
        if test_result['failed'] > 0:
            html.append("<h2>Failed Tests</h2>")
            for agent_name, agent_result in test_result['agents'].items():
                if agent_result['failed'] > 0:
                    html.append(f"<h3>{agent_name}</h3>")
                    for failed_test in agent_result.get('failed_tests', []):
                        html.append(f"""
                    <div class="failed-test">
                        <p><strong>{failed_test['name']}</strong></p>
                        <p>{failed_test['message']}</p>
                    </div>
""")
        
        html.append("</body></html>")
        
        return "".join(html)


# Import time at the end to avoid circular imports
import time
import re
