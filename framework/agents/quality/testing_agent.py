"""
Testing Agent - Software Testing and Quality Assurance

Responsibilities:
- Test planning and design
- Test case development
- Test execution
- Defect tracking
- Test automation
- Performance testing
- Security testing
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from enum import Enum
import json
import asyncio
from datetime import datetime


class TestType(Enum):
    """Test types"""
    UNIT = "unit"
    INTEGRATION = "integration"
    SYSTEM = "system"
    ACCEPTANCE = "acceptance"
    PERFORMANCE = "performance"
    SECURITY = "security"
    USABILITY = "usability"
    REGRESSION = "regression"
    SMOKE = "smoke"


class TestLevel(Enum):
    """Test levels"""
    COMPONENT = "component"
    API = "api"
    UI = "ui"
    END_TO_END = "end_to_end"


class TestStatus(Enum):
    """Test status types"""
    PASSED = "passed"
    FAILED = "failed"
    SKIPPED = "skipped"
    PENDING = "pending"
    BLOCKED = "blocked"


class TestPriority(Enum):
    """Test priority levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DefectSeverity(Enum):
    """Defect severity levels"""
    CRITICAL = "critical"
    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class DefectStatus(Enum):
    """Defect status types"""
    NEW = "new"
    OPEN = "open"
    IN_PROGRESS = "in_progress"
    FIXED = "fixed"
    VERIFIED = "verified"
    CLOSED = "closed"
    REOPENED = "reopened"
    DUPLICATE = "duplicate"
    WONT_FIX = "wont_fix"


@dataclass
class TestCase:
    """Represents a test case"""
    test_case_id: str
    name: str
    description: str = ""
    test_type: TestType = TestType.UNIT
    test_level: TestLevel = TestLevel.COMPONENT
    priority: TestPriority = TestPriority.MEDIUM
    steps: List[str] = field(default_factory=list)
    expected_result: str = ""
    actual_result: str = ""
    status: TestStatus = TestStatus.PENDING
    preconditions: List[str] = field(default_factory=list)
    postconditions: List[str] = field(default_factory=list)
    data: Dict[str, Any] = field(default_factory=dict)
    tags: List[str] = field(default_factory=list)
    created_at: str = ""
    updated_at: str = ""
    executed_at: Optional[str] = None
    execution_time: float = 0.0


@dataclass
class TestSuite:
    """Represents a test suite"""
    suite_id: str
    name: str
    description: str = ""
    test_cases: List[str] = field(default_factory=list)
    setup: Optional[str] = None
    teardown: Optional[str] = None
    dependencies: List[str] = field(default_factory=list)
    tags: List[str] = field(default_factory=list)


@dataclass
class TestPlan:
    """Represents a test plan"""
    plan_id: str
    name: str
    description: str = ""
    scope: List[str] = field(default_factory=list)
    test_suites: List[str] = field(default_factory=list)
    schedule: Dict[str, Any] = field(default_factory=dict)
    resources: Dict[str, Any] = field(default_factory=dict)
    risks: List[str] = field(default_factory=list)
    status: str = "planned"  # "planned", "in_progress", "completed", "cancelled"


@dataclass
class Defect:
    """Represents a defect"""
    defect_id: str
    title: str
    description: str = ""
    severity: DefectSeverity = DefectSeverity.MEDIUM
    priority: TestPriority = TestPriority.MEDIUM
    status: DefectStatus = DefectStatus.NEW
    test_case_id: Optional[str] = None
    steps_to_reproduce: List[str] = field(default_factory=list)
    expected_behavior: str = ""
    actual_behavior: str = ""
    environment: str = ""
    assigned_to: Optional[str] = None
    reported_by: str = ""
    reported_at: str = ""
    fixed_at: Optional[str] = None
    verified_at: Optional[str] = None
    resolution: str = ""
    related_defects: List[str] = field(default_factory=list)


@dataclass
class TestExecution:
    """Represents a test execution"""
    execution_id: str
    test_case_id: str
    test_plan_id: Optional[str] = None
    status: TestStatus = TestStatus.PENDING
    start_time: str = ""
    end_time: str = ""
    execution_time: float = 0.0
    environment: str = ""
    executed_by: str = ""
    logs: str = ""
    screenshots: List[str] = field(default_factory=list)
    videos: List[str] = field(default_factory=list)


@dataclass
class TestReport:
    """Represents a test report"""
    report_id: str
    name: str
    test_plan_id: Optional[str] = None
    test_execution_id: Optional[str] = None
    start_time: str = ""
    end_time: str = ""
    total_tests: int = 0
    passed_tests: int = 0
    failed_tests: int = 0
    skipped_tests: int = 0
    pass_percentage: float = 0.0
    execution_time: float = 0.0
    environment: str = ""
    summary: str = ""
    defects: List[str] = field(default_factory=list)


@dataclass
class TestingAgent:
    """
    Testing Agent
    
    This agent specializes in software testing, test automation, and quality assurance.
    It manages test cases, test execution, defect tracking, and test reporting.
    """
    
    agent_id: str = "testing_agent_001"
    name: str = "Testing"
    description: str = "Software testing and quality assurance specialist"
    version: str = "1.0.0"
    
    # Test cases
    test_cases: Dict[str, TestCase] = field(default_factory=dict)
    
    # Test suites
    test_suites: Dict[str, TestSuite] = field(default_factory=dict)
    
    # Test plans
    test_plans: Dict[str, TestPlan] = field(default_factory=dict)
    
    # Defects
    defects: Dict[str, Defect] = field(default_factory=dict)
    
    # Test executions
    test_executions: Dict[str, TestExecution] = field(default_factory=dict)
    
    # Test reports
    test_reports: Dict[str, TestReport] = field(default_factory=dict)
    
    # Current state
    current_test_plan: Optional[str] = None
    current_test_case: Optional[str] = None
    current_defect: Optional[str] = None
    
    # Performance metrics
    performance_metrics: Dict[str, float] = field(default_factory=dict)
    
    def __post_init__(self):
        """Initialize the agent"""
        pass
    
    async def create_test_case(self, test_case_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new test case
        
        Args:
            test_case_spec: Test case specification
            
        Returns:
            Dictionary with test case configuration
        """
        print(f"🧪 {self.name}: Creating test case {test_case_spec.get('name', 'Unnamed')}")
        
        test_case_id = test_case_spec.get("test_case_id", f"test_case_{len(self.test_cases) + 1}")
        name = test_case_spec.get("name", "Unnamed Test Case")
        description = test_case_spec.get("description", "")
        test_type_str = test_case_spec.get("test_type", "unit")
        test_level_str = test_case_spec.get("test_level", "component")
        priority_str = test_case_spec.get("priority", "medium")
        steps = test_case_spec.get("steps", [])
        expected_result = test_case_spec.get("expected_result", "")
        preconditions = test_case_spec.get("preconditions", [])
        postconditions = test_case_spec.get("postconditions", [])
        data = test_case_spec.get("data", {})
        tags = test_case_spec.get("tags", [])
        
        # Validate test type
        try:
            test_type = TestType(test_type_str)
        except ValueError:
            test_type = TestType.UNIT
            print(f"⚠️  Test type {test_type_str} not valid, defaulting to UNIT")
        
        # Validate test level
        try:
            test_level = TestLevel(test_level_str)
        except ValueError:
            test_level = TestLevel.COMPONENT
            print(f"⚠️  Test level {test_level_str} not valid, defaulting to COMPONENT")
        
        # Validate priority
        try:
            priority = TestPriority(priority_str)
        except ValueError:
            priority = TestPriority.MEDIUM
            print(f"⚠️  Priority {priority_str} not valid, defaulting to MEDIUM")
        
        # Create test case
        test_case = TestCase(
            test_case_id=test_case_id,
            name=name,
            description=description,
            test_type=test_type,
            test_level=test_level,
            priority=priority,
            steps=steps,
            expected_result=expected_result,
            preconditions=preconditions,
            postconditions=postconditions,
            data=data,
            tags=tags,
            created_at=datetime.now().isoformat(),
            updated_at=datetime.now().isoformat()
        )
        
        self.test_cases[test_case_id] = test_case
        self.current_test_case = test_case_id
        
        # Generate test case code
        test_code = self._generate_test_case_code(test_case)
        
        result = {
            "test_case_id": test_case_id,
            "name": name,
            "description": description,
            "test_type": test_type.value,
            "test_level": test_level.value,
            "priority": priority.value,
            "steps": steps,
            "expected_result": expected_result,
            "preconditions": preconditions,
            "postconditions": postconditions,
            "data": data,
            "tags": tags,
            "code": test_code,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Test case {name} created with ID {test_case_id}")
        return result
    
    def _generate_test_case_code(self, test_case: TestCase) -> str:
        """Generate test case code based on type"""
        if test_case.test_type == TestType.UNIT and test_case.test_level == TestLevel.COMPONENT:
            # Generate Python unit test
            code = f'''
import unittest

class Test{test_case.name.replace(' ', '')}(unittest.TestCase):
    """{test_case.description}"""
    
    def setUp(self):
        """Set up test fixtures"""
        # Setup code
        pass
    
    def test_{test_case.name.lower().replace(' ', '_')}(self):
        """Test: {test_case.name}"""
        # Test steps:
        {chr(10).join([f'        # {step}' for step in test_case.steps])}
        
        # Expected result: {test_case.expected_result}
        # TODO: Implement test assertions
        self.assertTrue(True, "Test not implemented")
    
    def tearDown(self):
        """Clean up test fixtures"""
        # Teardown code
        pass

if __name__ == '__main__':
    unittest.main()
'''
            return code
        elif test_case.test_type == TestType.INTEGRATION and test_case.test_level == TestLevel.API:
            # Generate API test
            code = f'''
import requests
import unittest

class Test{test_case.name.replace(' ', '')}(unittest.TestCase):
    """{test_case.description}"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.base_url = "http://localhost:8000"
        self.headers = {{"Content-Type": "application/json"}}
    
    def test_{test_case.name.lower().replace(' ', '_')}(self):
        """Test: {test_case.name}"""
        # Test steps:
        {chr(10).join([f'        # {step}' for step in test_case.steps])}
        
        # Example API test
        response = requests.get(f"{{self.base_url}}/api/endpoint")
        
        # Assertions
        self.assertEqual(response.status_code, 200)
        
        # Expected result: {test_case.expected_result}
        # TODO: Implement specific assertions
    
    def tearDown(self):
        """Clean up test fixtures"""
        pass

if __name__ == '__main__':
    unittest.main()
'''
            return code
        elif test_case.test_type == TestType.UI and test_case.test_level == TestLevel.UI:
            # Generate UI test (Selenium)
            code = f'''
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
import unittest

class Test{test_case.name.replace(' ', '')}(unittest.TestCase):
    """{test_case.description}"""
    
    def setUp(self):
        """Set up test fixtures"""
        self.driver = webdriver.Chrome()
        self.base_url = "http://localhost:3000"
    
    def test_{test_case.name.lower().replace(' ', '_')}(self):
        """Test: {test_case.name}"""
        driver = self.driver
        
        # Test steps:
        {chr(10).join([f'        # {step}' for step in test_case.steps])}
        
        # Example UI test
        driver.get(f"{{self.base_url}}/")
        
        # Find element and interact
        element = driver.find_element(By.NAME, "username")
        element.send_keys("testuser")
        
        # Expected result: {test_case.expected_result}
        # TODO: Implement specific assertions
        self.assertIn("Welcome", driver.page_source)
    
    def tearDown(self):
        """Clean up test fixtures"""
        self.driver.quit()

if __name__ == '__main__':
    unittest.main()
'''
            return code
        else:
            # Generic test case
            code = f'''
# Test Case: {test_case.name}
# Type: {test_case.test_type.value}
# Level: {test_case.test_level.value}
# Priority: {test_case.priority.value}

# Description: {test_case.description}

# Preconditions:
{chr(10).join([f'# - {pre}' for pre in test_case.preconditions])}

# Test Steps:
{chr(10).join([f'# {i+1}. {step}' for i, step in enumerate(test_case.steps)])}

# Expected Result:
# {test_case.expected_result}

# Postconditions:
{chr(10).join([f'# - {post}' for post in test_case.postconditions])}

# TODO: Implement test case
'''
            return code
    
    async def create_test_suite(self, suite_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new test suite
        
        Args:
            suite_spec: Test suite specification
            
        Returns:
            Dictionary with test suite configuration
        """
        print(f"📦 {self.name}: Creating test suite {suite_spec.get('name', 'Unnamed')}")
        
        suite_id = suite_spec.get("suite_id", f"suite_{len(self.test_suites) + 1}")
        name = suite_spec.get("name", "Unnamed Test Suite")
        description = suite_spec.get("description", "")
        test_cases = suite_spec.get("test_cases", [])
        setup = suite_spec.get("setup")
        teardown = suite_spec.get("teardown")
        dependencies = suite_spec.get("dependencies", [])
        tags = suite_spec.get("tags", [])
        
        # Create test suite
        test_suite = TestSuite(
            suite_id=suite_id,
            name=name,
            description=description,
            test_cases=test_cases,
            setup=setup,
            teardown=teardown,
            dependencies=dependencies,
            tags=tags
        )
        
        self.test_suites[suite_id] = test_suite
        
        # Add test cases to suite
        for test_case_id in test_cases:
            if test_case_id in self.test_cases:
                test_suite.test_cases.append(test_case_id)
        
        result = {
            "suite_id": suite_id,
            "name": name,
            "description": description,
            "test_cases": test_cases,
            "setup": setup,
            "teardown": teardown,
            "dependencies": dependencies,
            "tags": tags,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Test suite {name} created with ID {suite_id}")
        return result
    
    async def create_test_plan(self, plan_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Create a new test plan
        
        Args:
            plan_spec: Test plan specification
            
        Returns:
            Dictionary with test plan configuration
        """
        print(f"📅 {self.name}: Creating test plan {plan_spec.get('name', 'Unnamed')}")
        
        plan_id = plan_spec.get("plan_id", f"plan_{len(self.test_plans) + 1}")
        name = plan_spec.get("name", "Unnamed Test Plan")
        description = plan_spec.get("description", "")
        scope = plan_spec.get("scope", [])
        test_suites = plan_spec.get("test_suites", [])
        schedule = plan_spec.get("schedule", {})
        resources = plan_spec.get("resources", {})
        risks = plan_spec.get("risks", [])
        
        # Create test plan
        test_plan = TestPlan(
            plan_id=plan_id,
            name=name,
            description=description,
            scope=scope,
            test_suites=test_suites,
            schedule=schedule,
            resources=resources,
            risks=risks,
            status="planned"
        )
        
        self.test_plans[plan_id] = test_plan
        self.current_test_plan = plan_id
        
        result = {
            "plan_id": plan_id,
            "name": name,
            "description": description,
            "scope": scope,
            "test_suites": test_suites,
            "schedule": schedule,
            "resources": resources,
            "risks": risks,
            "status": "created"
        }
        
        print(f"✅ {self.name}: Test plan {name} created with ID {plan_id}")
        return result
    
    async def execute_test_case(self, test_case_id: str, execution_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute a test case
        
        Args:
            test_case_id: ID of the test case to execute
            execution_spec: Execution specification
            
        Returns:
            Dictionary with execution results
        """
        print(f"▶️ {self.name}: Executing test case {test_case_id}")
        
        if test_case_id not in self.test_cases:
            raise ValueError(f"Test case {test_case_id} not found")
        
        test_case = self.test_cases[test_case_id]
        
        execution_id = execution_spec.get("execution_id", f"execution_{len(self.test_executions) + 1}")
        test_plan_id = execution_spec.get("test_plan_id")
        environment = execution_spec.get("environment", "local")
        executed_by = execution_spec.get("executed_by", "automated")
        
        # Simulate test execution
        import random
        
        # Randomly determine if test passes or fails (simplified)
        # In real implementation, this would actually run the test
        if test_case.test_type == TestType.UNIT:
            passed = random.random() > 0.1  # 90% pass rate for unit tests
        elif test_case.test_type == TestType.INTEGRATION:
            passed = random.random() > 0.2  # 80% pass rate for integration tests
        elif test_case.test_type == TestType.SYSTEM:
            passed = random.random() > 0.3  # 70% pass rate for system tests
        else:
            passed = random.random() > 0.5  # 50% pass rate for other tests
        
        # Determine status
        if passed:
            status = TestStatus.PASSED
            actual_result = test_case.expected_result
        else:
            status = TestStatus.FAILED
            actual_result = "Test failed - unexpected behavior"
        
        # Update test case
        test_case.status = status
        test_case.actual_result = actual_result
        test_case.executed_at = datetime.now().isoformat()
        test_case.execution_time = random.uniform(0.1, 5.0)  # Random execution time
        test_case.updated_at = datetime.now().isoformat()
        
        # Create test execution
        test_execution = TestExecution(
            execution_id=execution_id,
            test_case_id=test_case_id,
            test_plan_id=test_plan_id,
            status=status,
            start_time=datetime.now().isoformat(),
            end_time=datetime.now().isoformat(),
            execution_time=test_case.execution_time,
            environment=environment,
            executed_by=executed_by,
            logs=f"Test {test_case_id} executed in {environment} environment",
            screenshots=[],
            videos=[]
        )
        
        self.test_executions[execution_id] = test_execution
        self.current_test_case = test_case_id
        
        # Generate execution report
        execution_report = self._generate_execution_report(test_case, test_execution)
        
        result = {
            "execution_id": execution_id,
            "test_case_id": test_case_id,
            "test_plan_id": test_plan_id,
            "status": status.value,
            "expected_result": test_case.expected_result,
            "actual_result": actual_result,
            "execution_time": test_case.execution_time,
            "environment": environment,
            "executed_by": executed_by,
            "report": execution_report
        }
        
        if status == TestStatus.PASSED:
            print(f"✅ {self.name}: Test case {test_case_id} passed")
        else:
            print(f"❌ {self.name}: Test case {test_case_id} failed")
        
        return result
    
    def _generate_execution_report(self, test_case: TestCase, execution: TestExecution) -> Dict[str, Any]:
        """Generate an execution report for a test case"""
        report = {
            "execution_id": execution.execution_id,
            "test_case_id": test_case.test_case_id,
            "test_case_name": test_case.name,
            "status": execution.status.value,
            "start_time": execution.start_time,
            "end_time": execution.end_time,
            "execution_time": execution.execution_time,
            "environment": execution.environment,
            "executed_by": execution.executed_by,
            "summary": {
                "expected": test_case.expected_result,
                "actual": test_case.actual_result,
                "steps_executed": len(test_case.steps),
                "preconditions_met": True,  # Simplified
                "postconditions_met": True  # Simplified
            },
            "logs": execution.logs,
            "screenshots": execution.screenshots,
            "videos": execution.videos
        }
        
        # Add recommendations if test failed
        if execution.status == TestStatus.FAILED:
            report["recommendations"] = [
                "Investigate the root cause of the failure",
                "Check test environment and dependencies",
                "Review test case steps and expected results",
                "Consider adding more detailed assertions"
            ]
        
        return report
    
    async def report_defect(self, defect_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Report a new defect
        
        Args:
            defect_spec: Defect specification
            
        Returns:
            Dictionary with defect report
        """
        print(f"🐛 {self.name}: Reporting defect {defect_spec.get('title', 'Unnamed')}")
        
        defect_id = defect_spec.get("defect_id", f"defect_{len(self.defects) + 1}")
        title = defect_spec.get("title", "Unnamed Defect")
        description = defect_spec.get("description", "")
        severity_str = defect_spec.get("severity", "medium")
        priority_str = defect_spec.get("priority", "medium")
        test_case_id = defect_spec.get("test_case_id")
        steps_to_reproduce = defect_spec.get("steps_to_reproduce", [])
        expected_behavior = defect_spec.get("expected_behavior", "")
        actual_behavior = defect_spec.get("actual_behavior", "")
        environment = defect_spec.get("environment", "")
        assigned_to = defect_spec.get("assigned_to")
        reported_by = defect_spec.get("reported_by", "automated")
        
        # Validate severity
        try:
            severity = DefectSeverity(severity_str)
        except ValueError:
            severity = DefectSeverity.MEDIUM
            print(f"⚠️  Severity {severity_str} not valid, defaulting to MEDIUM")
        
        # Validate priority
        try:
            priority = TestPriority(priority_str)
        except ValueError:
            priority = TestPriority.MEDIUM
            print(f"⚠️  Priority {priority_str} not valid, defaulting to MEDIUM")
        
        # Create defect
        defect = Defect(
            defect_id=defect_id,
            title=title,
            description=description,
            severity=severity,
            priority=priority,
            status=DefectStatus.NEW,
            test_case_id=test_case_id,
            steps_to_reproduce=steps_to_reproduce,
            expected_behavior=expected_behavior,
            actual_behavior=actual_behavior,
            environment=environment,
            assigned_to=assigned_to,
            reported_by=reported_by,
            reported_at=datetime.now().isoformat()
        )
        
        self.defects[defect_id] = defect
        self.current_defect = defect_id
        
        # Update test case if associated
        if test_case_id and test_case_id in self.test_cases:
            test_case = self.test_cases[test_case_id]
            test_case.status = TestStatus.FAILED
            test_case.actual_result = actual_behavior
            test_case.updated_at = datetime.now().isoformat()
        
        # Generate defect report
        defect_report = self._generate_defect_report(defect)
        
        result = {
            "defect_id": defect_id,
            "title": title,
            "description": description,
            "severity": severity.value,
            "priority": priority.value,
            "status": defect.status.value,
            "test_case_id": test_case_id,
            "steps_to_reproduce": steps_to_reproduce,
            "expected_behavior": expected_behavior,
            "actual_behavior": actual_behavior,
            "environment": environment,
            "assigned_to": assigned_to,
            "reported_by": reported_by,
            "reported_at": defect.reported_at,
            "report": defect_report
        }
        
        print(f"✅ {self.name}: Defect {title} reported with ID {defect_id}")
        return result
    
    def _generate_defect_report(self, defect: Defect) -> Dict[str, Any]:
        """Generate a defect report"""
        report = {
            "defect_id": defect.defect_id,
            "title": defect.title,
            "description": defect.description,
            "severity": defect.severity.value,
            "priority": defect.priority.value,
            "status": defect.status.value,
            "reported_by": defect.reported_by,
            "reported_at": defect.reported_at,
            "assigned_to": defect.assigned_to,
            "test_case_id": defect.test_case_id,
            "environment": defect.environment,
            "steps_to_reproduce": defect.steps_to_reproduce,
            "expected_behavior": defect.expected_behavior,
            "actual_behavior": defect.actual_behavior,
            "resolution": defect.resolution,
            "summary": {
                "days_open": 0,  # Would be calculated
                "related_defects": defect.related_defects
            }
        }
        
        # Add recommendations based on severity
        if defect.severity == DefectSeverity.CRITICAL:
            report["recommendations"] = [
                "Address immediately - critical defect",
                "Consider rolling back if already in production",
                "Notify all stakeholders",
                "Conduct root cause analysis"
            ]
        elif defect.severity == DefectSeverity.HIGH:
            report["recommendations"] = [
                "Address in next sprint",
                "Prioritize fix based on impact",
                "Consider workaround if fix will take time"
            ]
        elif defect.severity == DefectSeverity.MEDIUM:
            report["recommendations"] = [
                "Address in upcoming sprint",
                "Include in regular testing"
            ]
        else:
            report["recommendations"] = [
                "Address when resources allow",
                "Consider for future improvements"
            ]
        
        return report
    
    async def update_defect_status(self, defect_id: str, status_str: str, resolution: str = "") -> Dict[str, Any]:
        """
        Update the status of a defect
        
        Args:
            defect_id: ID of the defect
            status_str: New status
            resolution: Resolution description
            
        Returns:
            Dictionary with update results
        """
        print(f"🔄 {self.name}: Updating defect {defect_id} status to {status_str}")
        
        if defect_id not in self.defects:
            raise ValueError(f"Defect {defect_id} not found")
        
        defect = self.defects[defect_id]
        
        # Validate status
        try:
            status = DefectStatus(status_str)
        except ValueError:
            raise ValueError(f"Status {status_str} not valid")
        
        # Update defect
        old_status = defect.status
        defect.status = status
        defect.resolution = resolution
        
        # Update timestamps based on status
        if status == DefectStatus.IN_PROGRESS:
            if not defect.assigned_to:
                raise ValueError("Defect must be assigned before setting to IN_PROGRESS")
        elif status == DefectStatus.FIXED:
            defect.fixed_at = datetime.now().isoformat()
        elif status == DefectStatus.VERIFIED:
            defect.verified_at = datetime.now().isoformat()
        elif status == DefectStatus.CLOSED:
            if not defect.fixed_at:
                raise ValueError("Defect must be fixed before closing")
            if not defect.verified_at:
                raise ValueError("Defect must be verified before closing")
        
        # Generate status change report
        status_report = {
            "defect_id": defect_id,
            "title": defect.title,
            "previous_status": old_status.value,
            "new_status": status.value,
            "resolution": resolution,
            "timestamp": datetime.now().isoformat()
        }
        
        result = {
            "defect_id": defect_id,
            "previous_status": old_status.value,
            "new_status": status.value,
            "resolution": resolution,
            "status_report": status_report
        }
        
        print(f"✅ {self.name}: Defect {defect_id} status updated to {status.value}")
        return result
    
    async def generate_test_report(self, report_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Generate a comprehensive test report
        
        Args:
            report_spec: Report specification
            
        Returns:
            Dictionary with test report
        """
        print(f"📄 {self.name}: Generating test report")
        
        report_id = report_spec.get("report_id", f"report_{len(self.test_reports) + 1}")
        name = report_spec.get("name", "Test Report")
        test_plan_id = report_spec.get("test_plan_id")
        test_execution_id = report_spec.get("test_execution_id")
        
        # Collect test execution data
        if test_execution_id:
            executions = [self.test_executions[test_execution_id]] if test_execution_id in self.test_executions else []
        elif test_plan_id:
            executions = [
                e for e in self.test_executions.values() 
                if e.test_plan_id == test_plan_id
            ]
        else:
            executions = list(self.test_executions.values())
        
        # Calculate statistics
        total_tests = len(executions)
        passed_tests = len([e for e in executions if e.status == TestStatus.PASSED])
        failed_tests = len([e for e in executions if e.status == TestStatus.FAILED])
        skipped_tests = len([e for e in executions if e.status == TestStatus.SKIPPED])
        pass_percentage = (passed_tests / total_tests * 100) if total_tests > 0 else 0
        
        # Calculate execution time
        total_execution_time = sum(e.execution_time for e in executions)
        
        # Create test report
        test_report = TestReport(
            report_id=report_id,
            name=name,
            test_plan_id=test_plan_id,
            test_execution_id=test_execution_id,
            start_time=executions[0].start_time if executions else datetime.now().isoformat(),
            end_time=executions[-1].end_time if executions else datetime.now().isoformat(),
            total_tests=total_tests,
            passed_tests=passed_tests,
            failed_tests=failed_tests,
            skipped_tests=skipped_tests,
            pass_percentage=pass_percentage,
            execution_time=total_execution_time,
            environment=executions[0].environment if executions else "unknown",
            summary=f"Executed {total_tests} tests, {passed_tests} passed, {failed_tests} failed",
            defects=[e.test_case_id for e in executions if e.status == TestStatus.FAILED]
        )
        
        self.test_reports[report_id] = test_report
        
        # Generate detailed report
        detailed_report = self._generate_detailed_report(test_report, executions)
        
        result = {
            "report_id": report_id,
            "name": name,
            "test_plan_id": test_plan_id,
            "test_execution_id": test_execution_id,
            "total_tests": total_tests,
            "passed_tests": passed_tests,
            "failed_tests": failed_tests,
            "skipped_tests": skipped_tests,
            "pass_percentage": pass_percentage,
            "execution_time": total_execution_time,
            "environment": test_report.environment,
            "summary": test_report.summary,
            "detailed_report": detailed_report
        }
        
        print(f"✅ {self.name}: Test report {name} generated")
        return result
    
    def _generate_detailed_report(self, test_report: TestReport, executions: List[TestExecution]) -> Dict[str, Any]:
        """Generate a detailed test report"""
        report = {
            "report_id": test_report.report_id,
            "name": test_report.name,
            "start_time": test_report.start_time,
            "end_time": test_report.end_time,
            "summary": {
                "total_tests": test_report.total_tests,
                "passed": test_report.passed_tests,
                "failed": test_report.failed_tests,
                "skipped": test_report.skipped_tests,
                "pass_percentage": test_report.pass_percentage,
                "execution_time": test_report.execution_time
            },
            "environment": test_report.environment,
            "test_results": [],
            "failure_analysis": {},
            "recommendations": []
        }
        
        # Add test results
        for execution in executions:
            test_case = self.test_cases.get(execution.test_case_id)
            if test_case:
                test_result = {
                    "execution_id": execution.execution_id,
                    "test_case_id": execution.test_case_id,
                    "test_case_name": test_case.name,
                    "test_type": test_case.test_type.value,
                    "test_level": test_case.test_level.value,
                    "priority": test_case.priority.value,
                    "status": execution.status.value,
                    "execution_time": execution.execution_time,
                    "expected_result": test_case.expected_result,
                    "actual_result": test_case.actual_result,
                    "environment": execution.environment
                }
                report["test_results"].append(test_result)
        
        # Generate failure analysis
        failed_executions = [e for e in executions if e.status == TestStatus.FAILED]
        if failed_executions:
            report["failure_analysis"] = {
                "total_failures": len(failed_executions),
                "by_type": {},
                "by_priority": {},
                "common_causes": []
            }
            
            # Group by test type
            for execution in failed_executions:
                test_case = self.test_cases.get(execution.test_case_id)
                if test_case:
                    test_type = test_case.test_type.value
                    if test_type not in report["failure_analysis"]["by_type"]:
                        report["failure_analysis"]["by_type"][test_type] = 0
                    report["failure_analysis"]["by_type"][test_type] += 1
                    
                    priority = test_case.priority.value
                    if priority not in report["failure_analysis"]["by_priority"]:
                        report["failure_analysis"]["by_priority"][priority] = 0
                    report["failure_analysis"]["by_priority"][priority] += 1
        
        # Generate recommendations
        if test_report.pass_percentage < 80:
            report["recommendations"].append("Test pass rate below 80% - investigate root causes")
        
        if failed_executions:
            report["recommendations"].append(f"Address {len(failed_executions)} failed tests")
        
        if test_report.execution_time > 60 * 60:  # More than 1 hour
            report["recommendations"].append("Test execution time is high - consider optimizing tests")
        
        return report
    
    async def run_test_suite(self, suite_id: str, execution_spec: Dict[str, Any]) -> Dict[str, Any]:
        """
        Run all test cases in a test suite
        
        Args:
            suite_id: ID of the test suite
            execution_spec: Execution specification
            
        Returns:
            Dictionary with execution results
        """
        print(f"▶️ {self.name}: Running test suite {suite_id}")
        
        if suite_id not in self.test_suites:
            raise ValueError(f"Test suite {suite_id} not found")
        
        test_suite = self.test_suites[suite_id]
        
        # Execute each test case in the suite
        execution_results = []
        for test_case_id in test_suite.test_cases:
            if test_case_id in self.test_cases:
                result = await self.execute_test_case(test_case_id, execution_spec)
                execution_results.append(result)
        
        # Generate suite report
        suite_report = self._generate_suite_report(test_suite, execution_results)
        
        result = {
            "suite_id": suite_id,
            "name": test_suite.name,
            "test_cases_executed": len(execution_results),
            "execution_results": execution_results,
            "suite_report": suite_report
        }
        
        print(f"✅ {self.name}: Test suite {suite_id} completed with {len(execution_results)} executions")
        return result
    
    def _generate_suite_report(self, test_suite: TestSuite, execution_results: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Generate a report for a test suite execution"""
        report = {
            "suite_id": test_suite.suite_id,
            "name": test_suite.name,
            "description": test_suite.description,
            "total_tests": len(execution_results),
            "passed": len([r for r in execution_results if r["status"] == "passed"]),
            "failed": len([r for r in execution_results if r["status"] == "failed"]),
            "skipped": len([r for r in execution_results if r["status"] == "skipped"]),
            "pass_percentage": 0.0,
            "total_execution_time": 0.0,
            "test_results": execution_results
        }
        
        # Calculate statistics
        if report["total_tests"] > 0:
            report["pass_percentage"] = (report["passed"] / report["total_tests"] * 100)
        
        report["total_execution_time"] = sum(
            r["execution_time"] for r in execution_results
        )
        
        return report
    
    async def get_testing_status(self) -> Dict[str, Any]:
        """
        Get the current testing status
        
        Returns:
            Dictionary with testing status
        """
        return {
            "agent_id": self.agent_id,
            "name": self.name,
            "current_test_plan": self.current_test_plan,
            "current_test_case": self.current_test_case,
            "current_defect": self.current_defect,
            "test_cases_count": len(self.test_cases),
            "test_suites_count": len(self.test_suites),
            "test_plans_count": len(self.test_plans),
            "defects_count": len(self.defects),
            "test_executions_count": len(self.test_executions),
            "test_reports_count": len(self.test_reports),
            "performance_metrics": self.performance_metrics
        }
    
    def reset(self) -> None:
        """Reset agent state"""
        self.current_test_plan = None
        self.current_test_case = None
        self.current_defect = None
        self.test_cases.clear()
        self.test_suites.clear()
        self.test_plans.clear()
        self.defects.clear()
        self.test_executions.clear()
        self.test_reports.clear()
        self.performance_metrics.clear()
        print(f"🔄 {self.name}: Agent state reset")
