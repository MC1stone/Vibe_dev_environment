"""
CrewAI Integration for Port Management Agent

This module provides a complete CrewAI agent that can manage ports
and resolve conflicts in the NIR_Mistral Framework.
"""

import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from crewai import Agent, Crew, Process, Task
    from crewai.tools import tool

    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("Warning: CrewAI not available. Port Management Agent will work in standalone mode.")

# Check if we can create proper CrewAI tools
CREWAI_TOOLS_AVAILABLE = False
if CREWAI_AVAILABLE:
    try:
        # Test if we can create a tool
        test_tool = tool(lambda x: x)
        CREWAI_TOOLS_AVAILABLE = True
    except Exception:
        CREWAI_TOOLS_AVAILABLE = False

from .agent import PortManagementAgentCrewAI, create_port_tool, port_agent, port_management_tool
from .docker_port_manager import DockerPortManager
from .exceptions import (
    DockerPortError,
    PortConflictError,
    PortManagerError,
    PortNotAvailableError,
    PortOutOfRangeError,
    PortReleaseError,
    PortReservationError,
    PortScanError,
)
from .integration import PortAgentIntegration
from .port_manager import PortManagementAgent, PortManager


class PortManagerCrewAIAgent:
    """
    CrewAI Agent specialized in Port Management for the NIR_Mistral Framework

    This agent can:
    - Scan and monitor port usage
    - Detect and resolve port conflicts
    - Reserve and assign ports for services
    - Manage Docker container ports
    - Provide comprehensive port status reports
    """

    def __init__(
        self,
        name: str = "Port Manager Agent",
        role: str = "DevOps Port Manager",
        goal: str = "Ensure all services have conflict-free ports",
        backstory: str = None,
        verbose: bool = True,
    ):
        """
        Initialize the Port Manager CrewAI Agent

        Args:
            name: Agent name
            role: Agent role
            goal: Agent goal
            backstory: Agent backstory
            verbose: Whether to be verbose
        """
        self.name = name
        self.role = role
        self.goal = goal
        self.backstory = backstory or self._get_default_backstory()
        self.verbose = verbose
        self.port_agent = PortManagementAgentCrewAI()
        self.crewai_agent = None

        # Initialize if CrewAI is available and tools are working
        if CREWAI_AVAILABLE and CREWAI_TOOLS_AVAILABLE:
            self._create_crewai_agent()

    def _get_default_backstory(self) -> str:
        """Get the default backstory for the port manager agent"""
        return (
            "You are an experienced DevOps engineer specializing in port management "
            "for the NIR_Mistral Framework. Your expertise includes detecting port conflicts, "
            "reserving ports for services, managing Docker container ports, and ensuring "
            "that all framework agents can run without port collisions. You use the Port "
            "Management Tool to perform all port-related operations and provide comprehensive "
            "status reports to help the team understand the current port usage situation."
        )

    def _create_crewai_agent(self):
        """Create the CrewAI agent instance"""
        if not CREWAI_AVAILABLE or not CREWAI_TOOLS_AVAILABLE:
            return

        try:
            # Create the port management tool
            port_tool_func = create_port_tool()

            # Create the agent
            self.crewai_agent = Agent(
                role=self.role,
                goal=self.goal,
                backstory=self.backstory,
                tools=[port_tool_func],
                verbose=self.verbose,
                allow_delegation=False,
            )
        except Exception as e:
            print(f"Warning: Could not create CrewAI agent: {e}")
            self.crewai_agent = None

    def get_agent(self):
        """Get the CrewAI agent instance"""
        return self.crewai_agent

    def execute_task(self, task_description: str, expected_output: str = None) -> Dict[str, Any]:
        """
        Execute a task using the CrewAI agent

        Args:
            task_description: Description of the task to perform
            expected_output: Expected output format

        Returns:
            Dictionary with task execution results
        """
        if not CREWAI_AVAILABLE or not CREWAI_TOOLS_AVAILABLE:
            return self._execute_task_standalone(task_description)

        if not self.crewai_agent:
            self._create_crewai_agent()

        # Create task
        task = Task(
            description=task_description,
            expected_output=expected_output or "Comprehensive port management results",
            agent=self.crewai_agent,
            async_execution=False,
        )

        # Create crew and execute
        crew = Crew(agents=[self.crewai_agent], tasks=[task], process=Process.sequential, verbose=self.verbose)

        try:
            result = crew.kickoff()
            return {"success": True, "result": result, "task": task_description}
        except Exception as e:
            return {"success": False, "error": str(e), "task": task_description}

    def _execute_task_standalone(self, task_description: str) -> Dict[str, Any]:
        """
        Execute a task in standalone mode (without CrewAI)

        Args:
            task_description: Description of the task to perform

        Returns:
            Dictionary with task execution results
        """
        # Parse the task description to determine the action
        task_lower = task_description.lower()

        if "scan" in task_lower:
            return self._handle_scan_task(task_description)
        elif "check" in task_lower:
            return self._handle_check_task(task_description)
        elif "assign" in task_lower or "reserve" in task_lower:
            return self._handle_reserve_task(task_description)
        elif "release" in task_lower:
            return self._handle_release_task(task_description)
        elif "conflict" in task_lower:
            return self._handle_conflict_task(task_description)
        elif "status" in task_lower:
            return self._handle_status_task(task_description)
        else:
            return self._handle_generic_task(task_description)

    def _handle_scan_task(self, task_description: str) -> Dict[str, Any]:
        """Handle port scan tasks"""
        # Extract parameters from task description
        start = 8000
        end = 9000
        host = "127.0.0.1"

        # Look for range in description
        import re

        range_match = re.search(r"(\d+)\s*[-to]\s*(\d+)", task_description)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))

        result = self.port_agent.scan_ports(host, start, end)
        return {"success": True, "action": "scan", "result": result}

    def _handle_check_task(self, task_description: str) -> Dict[str, Any]:
        """Handle port check tasks"""
        import re

        port_match = re.search(r"port\s+(\d+)", task_description)
        if port_match:
            port = int(port_match.group(1))
            result = self.port_agent.check_port(port)
            return {"success": True, "action": "check", "port": port, "result": result}

        return {"success": False, "error": "No port specified in task"}

    def _handle_reserve_task(self, task_description: str) -> Dict[str, Any]:
        """Handle port reservation tasks"""
        import re

        # Look for specific port
        port_match = re.search(r"port\s+(\d+)", task_description)
        if port_match:
            port = int(port_match.group(1))
            result = self.port_agent.reserve_port(port, "127.0.0.1", "crewai_task")
            return {"success": result.get("success", False), "action": "reserve", "port": port, "result": result}

        # Look for range
        range_match = re.search(r"(\d+)\s*[-to]\s*(\d+)", task_description)
        if range_match:
            start = int(range_match.group(1))
            end = int(range_match.group(2))
            result = self.port_agent.assign_port(start, end, "127.0.0.1", "crewai_task")
            return {
                "success": result.get("success", False),
                "action": "assign",
                "range": {"start": start, "end": end},
                "result": result,
            }

        # Default assignment
        result = self.port_agent.assign_port(8000, 9000, "127.0.0.1", "crewai_task")
        return {"success": result.get("success", False), "action": "assign", "result": result}

    def _handle_release_task(self, task_description: str) -> Dict[str, Any]:
        """Handle port release tasks"""
        import re

        port_match = re.search(r"port\s+(\d+)", task_description)
        if port_match:
            port = int(port_match.group(1))
            result = self.port_agent.release_port(port)
            return {"success": result.get("success", False), "action": "release", "port": port, "result": result}

        return {"success": False, "error": "No port specified in task"}

    def _handle_conflict_task(self, task_description: str) -> Dict[str, Any]:
        """Handle conflict detection and resolution tasks"""
        if "resolve" in task_description.lower():
            result = self.port_agent.resolve_framework_conflicts()
            return {"success": True, "action": "resolve_conflicts", "result": result}
        else:
            result = self.port_agent.detect_framework_conflicts()
            return {"success": True, "action": "detect_conflicts", "result": result}

    def _handle_status_task(self, task_description: str) -> Dict[str, Any]:
        """Handle status report tasks"""
        result = self.port_agent.get_port_status_report()
        return {"success": True, "action": "status_report", "result": result}

    def _handle_generic_task(self, task_description: str) -> Dict[str, Any]:
        """Handle generic tasks"""
        # Try to use the port management tool directly
        try:
            # Use the port management tool
            result = self.port_agent.execute_port_action("scan", start=8000, end=9000)
            return {"success": True, "action": "generic", "result": result}
        except Exception as e:
            return {"success": False, "error": str(e), "task": task_description}


class PortManagementCrew:
    """
    Complete CrewAI crew for port management operations

    This crew includes multiple agents that work together to manage ports
    and resolve conflicts in the NIR_Mistral Framework.
    """

    def __init__(self):
        """Initialize the Port Management Crew"""
        self.port_manager_agent = PortManagerCrewAIAgent(
            name="Port Manager Agent",
            role="DevOps Port Manager",
            goal="Ensure all services have conflict-free ports and resolve any port conflicts",
            verbose=True,
        )

        # Additional agents would be added here for more complex scenarios
        self.agents = [self.port_manager_agent]

    def check_system_ports(self) -> Dict[str, Any]:
        """Check all system ports and report usage"""
        task = (
            "Scan all ports from 8000 to 9000 and report which ports are in use. "
            "Identify any ports that might be causing conflicts with our framework services."
        )
        return self.port_manager_agent.execute_task(task)

    def detect_and_resolve_conflicts(self) -> Dict[str, Any]:
        """Detect and resolve all port conflicts"""
        task = (
            "1. Detect all port conflicts in the NIR_Mistral Framework. "
            "2. For each conflict, find an available port in the appropriate range. "
            "3. Reserve the new ports and update the configuration. "
            "4. Provide a comprehensive report of all changes made."
        )
        return self.port_manager_agent.execute_task(task)

    def reserve_port_for_service(self, service_name: str, port: int = None) -> Dict[str, Any]:
        """Reserve a port for a specific service"""
        if port:
            task = f"Reserve port {port} for the {service_name} service."
        else:
            task = f"Find and reserve an available port for the {service_name} service in the range 8000-9000."

        return self.port_manager_agent.execute_task(task)

    def get_port_status_report(self) -> Dict[str, Any]:
        """Get a comprehensive port status report"""
        task = (
            "Generate a comprehensive port status report including: "
            "1. All currently reserved ports and their services "
            "2. System ports that are in use "
            "3. Docker container ports if Docker is available "
            "4. Any detected port conflicts "
            "5. Recommendations for port assignment"
        )
        return self.port_manager_agent.execute_task(task)


# Global instances
port_manager_agent = PortManagerCrewAIAgent()
port_management_crew = PortManagementCrew()


def create_port_manager_crew():
    """Create a complete port management crew with multiple agents"""
    if not CREWAI_AVAILABLE:
        return port_management_crew

    # Create the port management tool
    port_tool_func = create_port_tool()

    # Create agents
    port_manager_agent = Agent(
        role="DevOps Port Manager",
        goal="Ensure all services have conflict-free ports and resolve any port conflicts",
        backstory=(
            "You are an experienced DevOps engineer specializing in port management "
            "for the NIR_Mistral Framework. Your expertise includes detecting port conflicts, "
            "reserving ports for services, managing Docker container ports, and ensuring "
            "that all framework agents can run without port collisions."
        ),
        tools=[port_tool_func],
        verbose=True,
        allow_delegation=False,
    )

    conflict_resolver_agent = Agent(
        role="Port Conflict Resolver",
        goal="Detect and resolve port conflicts automatically",
        backstory=(
            "You are a specialist in detecting and resolving port conflicts. "
            "You analyze the current port usage, identify conflicts, and find "
            "the best available ports to resolve those conflicts."
        ),
        tools=[port_tool_func],
        verbose=True,
        allow_delegation=False,
    )

    port_monitor_agent = Agent(
        role="Port Monitor",
        goal="Monitor port usage and provide real-time status reports",
        backstory=(
            "You are responsible for monitoring port usage across the system. "
            "You provide real-time information about which ports are in use, "
            "which are available, and what services are using each port."
        ),
        tools=[port_tool_func],
        verbose=True,
        allow_delegation=False,
    )

    # Create crew
    crew = Crew(
        agents=[port_manager_agent, conflict_resolver_agent, port_monitor_agent],
        tasks=[],
        process=Process.sequential,
        verbose=True,
    )

    return crew


# Standalone functions for easy use
def check_ports():
    """Check all ports and detect conflicts"""
    return port_manager_agent.execute_task("Scan all ports and detect any conflicts in the NIR_Mistral Framework")


def resolve_conflicts():
    """Detect and resolve all port conflicts"""
    return port_manager_agent.execute_task("Detect and resolve all port conflicts in the NIR_Mistral Framework")


def reserve_port(port=None, service_name="unknown"):
    """Reserve a port for a service"""
    if port:
        return port_manager_agent.execute_task(f"Reserve port {port} for service {service_name}")
    else:
        return port_manager_agent.execute_task(f"Find and reserve an available port for service {service_name}")


def get_port_status():
    """Get comprehensive port status report"""
    return port_manager_agent.execute_task("Generate a comprehensive port status report")


__all__ = [
    "PortManagerCrewAIAgent",
    "PortManagementCrew",
    "port_manager_agent",
    "port_management_crew",
    "create_port_manager_crew",
    "check_ports",
    "resolve_conflicts",
    "reserve_port",
    "get_port_status",
]
