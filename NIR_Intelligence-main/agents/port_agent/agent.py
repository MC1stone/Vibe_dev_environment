"""
Port Management Agent for CrewAI Integration

This module provides the main Port Management Agent that can be integrated
with CrewAI or used standalone. It provides comprehensive port management
capabilities for the NIR_Mistral Framework.

Features:
- Thread-safe port reservation and management
- Cross-platform support (Windows/Linux/Mac)
- Docker container port management
- Framework integration with conflict resolution
- Comprehensive error handling
- CrewAI tool compatibility

Usage:
    # As a CrewAI tool
    from agents.port_agent import port_management_tool

    # Standalone usage
    from agents.port_agent import port_agent
    port = port_agent.assign_port(8000, 9000, '127.0.0.1', 'my_service')
    port_agent.release_port(port)
"""

import json
import logging
import os
import sys
from functools import wraps
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from .docker_port_manager import DockerContainerInfo, DockerPortManager, DockerPortMapping
from .exceptions import (
    DockerPortError,
    PortManagerError,
    PortNotAvailableError,
    PortOutOfRangeError,
    PortReleaseError,
    PortReservationError,
)
from .integration import FrameworkPortConfig, PortAgentIntegration, PortConflictResolver
from .port_manager import PortInfo, PortManagementAgent, PortManager

# Configure logging
logger = logging.getLogger(__name__)


def handle_port_errors(func):
    """Decorator to handle port management errors consistently"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except PortManagerError as e:
            logger.error(f"Port management error in {func.__name__}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "port": getattr(e, "port", None),
                "host": getattr(e, "host", None),
                "details": getattr(e, "details", None),
            }
        except DockerPortError as e:
            logger.error(f"Docker port error in {func.__name__}: {e}")
            return {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "container_name": getattr(e, "container_name", None),
                "host_port": getattr(e, "host_port", None),
                "container_port": getattr(e, "container_port", None),
                "details": getattr(e, "details", None),
            }
        except Exception as e:
            logger.error(f"Unexpected error in {func.__name__}: {e}", exc_info=True)
            return {"success": False, "error": str(e), "error_type": type(e).__name__}

    return wrapper


def validate_port_range(func):
    """Decorator to validate port range parameters"""

    @wraps(func)
    def wrapper(*args, **kwargs):
        start = kwargs.get("start", 1)
        end = kwargs.get("end", 65535)
        port = kwargs.get("port")

        # Validate port if provided
        if port is not None:
            if not isinstance(port, int) or port < 1 or port > 65535:
                return {
                    "success": False,
                    "error": f"Invalid port number: {port}. Must be between 1-65535",
                    "error_type": "PortValidationError",
                }

        # Validate range
        if start is not None and (not isinstance(start, int) or start < 1 or start > 65535):
            return {
                "success": False,
                "error": f"Invalid start port: {start}. Must be between 1-65535",
                "error_type": "PortValidationError",
            }

        if end is not None and (not isinstance(end, int) or end < 1 or end > 65535):
            return {
                "success": False,
                "error": f"Invalid end port: {end}. Must be between 1-65535",
                "error_type": "PortValidationError",
            }

        if start is not None and end is not None and start > end:
            return {
                "success": False,
                "error": f"Invalid port range: start ({start}) > end ({end})",
                "error_type": "PortValidationError",
            }

        return func(*args, **kwargs)

    return wrapper


class PortManagementAgentCrewAI:
    """
    Port Management Agent for CrewAI Integration

    This class provides a CrewAI-compatible interface for the Port Management Agent.
    It can be used as a tool within CrewAI agents to manage ports dynamically.

    Features:
    - Thread-safe port operations
    - Comprehensive error handling
    - Input validation
    - Docker integration
    - Framework conflict resolution

    Example:
        agent = PortManagementAgentCrewAI()
        port = agent.assign_port(8000, 9000, '127.0.0.1', 'my_service')
        agent.release_port(port)
    """

    def __init__(self):
        """Initialize the CrewAI-compatible Port Management Agent"""
        self.port_integration = PortAgentIntegration()
        self.port_manager = self.port_integration.port_manager
        self.docker_port_manager = self.port_integration.docker_port_manager
        self.conflict_resolver = self.port_integration.conflict_resolver
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Ensure the agent is initialized"""
        if not self._initialized:
            result = self.initialize()
            self._initialized = result.get("success", False)
            if not self._initialized:
                logger.warning(f"Port agent initialization failed: {result.get('error', 'Unknown error')}")
        return self._initialized

    @handle_port_errors
    @validate_port_range
    def scan_ports(self, host: str = "127.0.0.1", start: int = 1, end: int = 65535) -> Dict[str, Any]:
        """
        Scan a range of ports and return their availability

        Args:
            host: Host address to scan (default: 127.0.0.1)
            start: Start port number (1-65535)
            end: End port number (1-65535)

        Returns:
            Dictionary with scan results including:
            - success: bool indicating operation success
            - ports: list of port information
            - scanned_range: the range that was scanned
            - available_count: number of available ports
            - error: error message if any
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Port agent not initialized"}

        return self.port_integration.execute_port_action("scan", host=host, start=start, end=end)

    @handle_port_errors
    @validate_port_range
    def check_port(self, port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Check if a specific port is available

        Args:
            port: Port number to check (1-65535)
            host: Host address (default: 127.0.0.1)

        Returns:
            Dictionary with port availability information
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Port agent not initialized"}

        return self.port_integration.execute_port_action("check", port=port, host=host)

    @handle_port_errors
    @validate_port_range
    def assign_port(
        self, start: int = 8000, end: int = 9000, host: str = "127.0.0.1", service_name: str = None
    ) -> Dict[str, Any]:
        """
        Assign and reserve a free port in the specified range

        Args:
            start: Start of port range (1-65535)
            end: End of port range (1-65535)
            host: Host address (default: 127.0.0.1)
            service_name: Name of service for logging

        Returns:
            Dictionary with assigned port information including:
            - success: bool indicating operation success
            - port: the assigned port number
            - host: the host address
            - service_name: the service name
            - error: error message if any
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Port agent not initialized"}

        return self.port_integration.execute_port_action(
            "assign", start=start, end=end, host=host, service_name=service_name
        )

    @handle_port_errors
    @validate_port_range
    def reserve_port(self, port: int, host: str = "127.0.0.1", service_name: str = None) -> Dict[str, Any]:
        """
        Reserve a specific port

        Args:
            port: Port number to reserve (1-65535)
            host: Host address (default: 127.0.0.1)
            service_name: Name of service for logging

        Returns:
            Dictionary with reservation information
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Port agent not initialized"}

        return self.port_integration.execute_port_action("reserve", port=port, host=host, service_name=service_name)

    @handle_port_errors
    @validate_port_range
    def release_port(self, port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Release a previously reserved port

        Args:
            port: Port number to release (1-65535)
            host: Host address (default: 127.0.0.1)

        Returns:
            Dictionary with release information
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Port agent not initialized"}

        return self.port_integration.execute_port_action("release", port=port, host=host)

    @handle_port_errors
    @validate_port_range
    def find_free_port(self, start: int = 8000, end: int = 9000, host: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Find a free port without reserving it

        Args:
            start: Start of port range (1-65535)
            end: End of port range (1-65535)
            host: Host address (default: 127.0.0.1)

        Returns:
            Dictionary with free port information
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Port agent not initialized"}

        return self.port_integration.execute_port_action("find", start=start, end=end, host=host)

    @handle_port_errors
    def get_port_status(self) -> Dict[str, Any]:
        """
        Get status of all reserved ports

        Returns:
            Dictionary with port status information including:
            - success: bool indicating operation success
            - reserved_ports: list of reserved port information
            - total_reserved: count of reserved ports
            - error: error message if any
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Port agent not initialized"}

        return self.port_integration.execute_port_action("status")

    @handle_port_errors
    @validate_port_range
    def get_port_conflicts(self, port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Get information about what's using a port

        Args:
            port: Port number to check (1-65535)
            host: Host address (default: 127.0.0.1)

        Returns:
            Dictionary with conflict information
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Port agent not initialized"}

        return self.port_integration.execute_port_action("conflicts", port=port, host=host)

    @handle_port_errors
    @validate_port_range
    def get_port_info(self, port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Get detailed information about a port

        Args:
            port: Port number to get info for (1-65535)
            host: Host address (default: 127.0.0.1)

        Returns:
            Dictionary with port information
        """
        if not self._ensure_initialized():
            return {"success": False, "error": "Port agent not initialized"}

        return self.port_integration.execute_port_action("info", port=port, host=host)

    # Docker-specific methods
    @handle_port_errors
    def is_docker_available(self) -> Dict[str, Any]:
        """
        Check if Docker is available

        Returns:
            Dictionary with Docker availability status
        """
        try:
            available = self.docker_port_manager.is_docker_available()
            return {
                "success": True,
                "docker_available": available,
                "message": "Docker available" if available else "Docker not available",
            }
        except Exception as e:
            logger.error(f"Error checking Docker availability: {e}")
            return {"success": False, "error": str(e), "docker_available": False}

    @handle_port_errors
    def get_docker_version(self) -> Dict[str, Any]:
        """
        Get Docker version

        Returns:
            Dictionary with Docker version information
        """
        try:
            version = self.docker_port_manager.get_docker_version()
            return {
                "success": True,
                "version": version,
                "message": f"Docker version: {version}" if version else "Docker not available",
            }
        except Exception as e:
            logger.error(f"Error getting Docker version: {e}")
            return {"success": False, "error": str(e)}

    @handle_port_errors
    def get_running_containers(self) -> Dict[str, Any]:
        """
        Get list of running Docker containers

        Returns:
            Dictionary with container information including:
            - success: bool indicating operation success
            - containers: list of container information
            - count: number of running containers
            - error: error message if any
        """
        try:
            containers = self.docker_port_manager.get_running_containers()
            container_list = [
                {
                    "container_id": c.container_id,
                    "name": c.name,
                    "status": c.status,
                    "image": c.image,
                    "host_ports": list(c.get_host_ports()),
                    "container_ports": list(c.get_container_ports()),
                }
                for c in containers
            ]
            return {"success": True, "containers": container_list, "count": len(container_list)}
        except DockerPortError as e:
            logger.error(f"Error getting running containers: {e}")
            return {"success": False, "error": str(e), "containers": [], "count": 0}
        except Exception as e:
            logger.error(f"Unexpected error getting containers: {e}")
            return {"success": False, "error": str(e), "containers": [], "count": 0}

    @handle_port_errors
    def get_container_port_mappings(self) -> Dict[str, Any]:
        """
        Get all Docker port mappings

        Returns:
            Dictionary with port mapping information including:
            - success: bool indicating operation success
            - mappings: list of port mapping information
            - count: number of port mappings
            - error: error message if any
        """
        try:
            mappings = self.docker_port_manager.get_container_port_mappings()
            mapping_list = [
                {
                    "container_id": m.container_id,
                    "container_name": m.container_name,
                    "container_port": m.container_port,
                    "container_protocol": m.container_protocol,
                    "host_port": m.host_port,
                    "host_ip": m.host_ip,
                    "mapping": str(m),
                }
                for m in mappings
            ]
            return {"success": True, "mappings": mapping_list, "count": len(mapping_list)}
        except DockerPortError as e:
            logger.error(f"Error getting container port mappings: {e}")
            return {"success": False, "error": str(e), "mappings": [], "count": 0}
        except Exception as e:
            logger.error(f"Unexpected error getting port mappings: {e}")
            return {"success": False, "error": str(e), "mappings": [], "count": 0}

    @handle_port_errors
    @validate_port_range
    def reserve_docker_port(
        self,
        container_port: int,
        host_port: int = None,
        start: int = 8000,
        end: int = 9000,
        host: str = "127.0.0.1",
        service_name: str = None,
    ) -> Dict[str, Any]:
        """
        Reserve a port for Docker container mapping

        Args:
            container_port: The container port to map (1-65535)
            host_port: Specific host port to reserve (optional, 1-65535)
            start: Start of host port range if host_port not specified (1-65535)
            end: End of host port range if host_port not specified (1-65535)
            host: Host address for binding (default: 127.0.0.1)
            service_name: Name of service for logging

        Returns:
            Dictionary with reservation information
        """
        try:
            result = self.docker_port_manager.reserve_docker_port(
                container_port, host_port, start, end, host, service_name
            )
            return {"success": True, **result}
        except DockerPortError as e:
            logger.error(f"Error reserving Docker port: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error reserving Docker port: {e}")
            return {"success": False, "error": str(e)}

    @handle_port_errors
    @validate_port_range
    def release_docker_port(self, host_port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Release a previously reserved Docker host port

        Args:
            host_port: The host port to release (1-65535)
            host: Host address (default: 127.0.0.1)

        Returns:
            Dictionary with release information
        """
        try:
            success = self.docker_port_manager.release_docker_port(host_port, host)
            return {
                "success": success,
                "host_port": host_port,
                "host": host,
                "message": f"Port {host_port} released" if success else f"Port {host_port} was not reserved",
            }
        except DockerPortError as e:
            logger.error(f"Error releasing Docker port: {e}")
            return {"success": False, "error": str(e)}
        except Exception as e:
            logger.error(f"Unexpected error releasing Docker port: {e}")
            return {"success": False, "error": str(e)}

    # Framework-specific methods
    @handle_port_errors
    def detect_framework_conflicts(self) -> Dict[str, Any]:
        """
        Detect port conflicts in the NIR_Mistral Framework

        Returns:
            Dictionary with conflict information including:
            - success: bool indicating operation success
            - conflicts: list of detected conflicts
            - count: number of conflicts
            - error: error message if any
        """
        try:
            conflicts = self.conflict_resolver.detect_conflicts()
            return {"success": True, "conflicts": conflicts.get("conflicts", []), "count": conflicts.get("count", 0)}
        except Exception as e:
            logger.error(f"Error detecting framework conflicts: {e}")
            return {"success": False, "error": str(e), "conflicts": [], "count": 0}

    @handle_port_errors
    def resolve_framework_conflicts(self, auto_assign: bool = True) -> Dict[str, Any]:
        """
        Resolve port conflicts in the NIR_Mistral Framework

        Args:
            auto_assign: Whether to automatically assign new ports (default: True)

        Returns:
            Dictionary with conflict resolution information
        """
        try:
            result = self.conflict_resolver.resolve_conflicts(auto_assign)
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"Error resolving framework conflicts: {e}")
            return {"success": False, "error": str(e)}

    @handle_port_errors
    def get_agent_port(self, agent_name: str) -> Dict[str, Any]:
        """
        Get the port for a specific agent (resolved if conflicts exist)

        Args:
            agent_name: Name of the agent

        Returns:
            Dictionary with port information including:
            - success: bool indicating operation success
            - agent_name: the agent name
            - port: the port number
            - error: error message if any
        """
        try:
            port = self.conflict_resolver.get_agent_port(agent_name)
            return {"success": True, "agent_name": agent_name, "port": port}
        except Exception as e:
            logger.error(f"Error getting agent port for {agent_name}: {e}")
            return {"success": False, "error": str(e), "agent_name": agent_name}

    @handle_port_errors
    def reserve_port_for_agent(self, agent_name: str, port: int = None, host: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Reserve a port for a specific agent

        Args:
            agent_name: Name of the agent
            port: Specific port to reserve (optional, will auto-assign)
            host: Host address for binding (default: 127.0.0.1)

        Returns:
            Dictionary with reservation information
        """
        try:
            result = self.port_integration.reserve_port_for_agent(agent_name, port, host)
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"Error reserving port for agent {agent_name}: {e}")
            return {"success": False, "error": str(e), "agent_name": agent_name}

    @handle_port_errors
    def release_agent_port(self, agent_name: str, host: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Release the port for a specific agent

        Args:
            agent_name: Name of the agent
            host: Host address (default: 127.0.0.1)

        Returns:
            Dictionary with release information
        """
        try:
            result = self.port_integration.release_agent_port(agent_name, host)
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"Error releasing port for agent {agent_name}: {e}")
            return {"success": False, "error": str(e), "agent_name": agent_name}

    @handle_port_errors
    def get_port_status_report(self) -> Dict[str, Any]:
        """
        Get comprehensive port status report for the framework

        Returns:
            Dictionary with port status information
        """
        try:
            report = self.port_integration.get_port_status_report()
            return {"success": True, **report}
        except Exception as e:
            logger.error(f"Error getting port status report: {e}")
            return {"success": False, "error": str(e)}

    @handle_port_errors
    def cleanup(self) -> Dict[str, Any]:
        """
        Clean up all reserved ports

        Returns:
            Dictionary with cleanup information including:
            - success: bool indicating operation success
            - released_count: number of ports released
            - message: cleanup status message
            - error: error message if any
        """
        try:
            result = self.port_integration.cleanup()
            return {"success": True, **result}
        except Exception as e:
            logger.error(f"Error during cleanup: {e}")
            return {"success": False, "error": str(e)}

    @handle_port_errors
    def initialize(self) -> Dict[str, Any]:
        """
        Initialize the port management system

        Returns:
            Dictionary with initialization information including:
            - success: bool indicating operation success
            - message: initialization status message
            - error: error message if any
        """
        try:
            result = self.port_integration.initialize()
            self._initialized = result.get("success", False)
            return result
        except Exception as e:
            logger.error(f"Error during initialization: {e}")
            return {"success": False, "error": str(e)}


# Create a tool decorator for CrewAI integration
def create_port_tool(agent: PortManagementAgentCrewAI = None):
    """
    Create a CrewAI-compatible tool decorator for port management

    Args:
        agent: PortManagementAgentCrewAI instance (optional, will create new one)

    Returns:
        Tool function that can be used with CrewAI
    """
    agent = agent or PortManagementAgentCrewAI()

    def port_tool(action: str, **kwargs) -> str:
        """
        Port Management Tool for CrewAI

        This tool provides comprehensive port management capabilities for the NIR_Mistral Framework.

        Actions:
        - 'scan': Scan a range of ports (parameters: host, start, end)
        - 'check': Check if a port is available (parameters: port, host)
        - 'assign': Assign and reserve a free port (parameters: start, end, host, service_name)
        - 'reserve': Reserve a specific port (parameters: port, host, service_name)
        - 'release': Release a reserved port (parameters: port, host)
        - 'find': Find a free port without reserving (parameters: start, end, host)
        - 'status': Get status of reserved ports
        - 'conflicts': Get port conflict information (parameters: port, host)
        - 'info': Get detailed port information (parameters: port, host)

        Docker Actions:
        - 'docker_available': Check if Docker is available
        - 'docker_version': Get Docker version
        - 'docker_containers': Get running Docker containers
        - 'docker_mappings': Get Docker port mappings
        - 'docker_reserve': Reserve Docker port (parameters: container_port, host_port, start, end, host, service_name)
        - 'docker_release': Release Docker port (parameters: host_port, host)

        Framework Actions:
        - 'detect_conflicts': Detect framework port conflicts
        - 'resolve_conflicts': Resolve framework port conflicts (parameters: auto_assign)
        - 'agent_port': Get port for agent (parameters: agent_name)
        - 'reserve_agent_port': Reserve port for agent (parameters: agent_name, port, host)
        - 'release_agent_port': Release agent port (parameters: agent_name, host)
        - 'status_report': Get comprehensive port status report
        - 'cleanup': Clean up all reserved ports
        - 'initialize': Initialize port management system

        Returns:
            JSON string with action result
        """
        try:
            # Handle framework-specific actions
            if action == "detect_conflicts":
                result = agent.detect_framework_conflicts()
            elif action == "resolve_conflicts":
                auto_assign = kwargs.get("auto_assign", True)
                result = agent.resolve_framework_conflicts(auto_assign)
            elif action == "agent_port":
                agent_name = kwargs.get("agent_name")
                result = agent.get_agent_port(agent_name)
            elif action == "reserve_agent_port":
                agent_name = kwargs.get("agent_name")
                port = kwargs.get("port")
                host = kwargs.get("host", "127.0.0.1")
                result = agent.reserve_port_for_agent(agent_name, port, host)
            elif action == "release_agent_port":
                agent_name = kwargs.get("agent_name")
                host = kwargs.get("host", "127.0.0.1")
                result = agent.release_agent_port(agent_name, host)
            elif action == "status_report":
                result = agent.get_port_status_report()
            elif action == "cleanup":
                result = agent.cleanup()
            elif action == "initialize":
                result = agent.initialize()

            # Handle Docker-specific actions
            elif action == "docker_available":
                result = agent.is_docker_available()
            elif action == "docker_version":
                result = agent.get_docker_version()
            elif action == "docker_containers":
                result = agent.get_running_containers()
            elif action == "docker_mappings":
                result = agent.get_container_port_mappings()
            elif action == "docker_reserve":
                container_port = kwargs.get("container_port")
                host_port = kwargs.get("host_port")
                start = kwargs.get("start", 8000)
                end = kwargs.get("end", 9000)
                host = kwargs.get("host", "127.0.0.1")
                service_name = kwargs.get("service_name")
                result = agent.reserve_docker_port(container_port, host_port, start, end, host, service_name)
            elif action == "docker_release":
                host_port = kwargs.get("host_port")
                host = kwargs.get("host", "127.0.0.1")
                result = agent.release_docker_port(host_port, host)

            # Handle general port actions
            else:
                # Map action names to method names
                method_map = {
                    "scan": agent.scan_ports,
                    "check": agent.check_port,
                    "assign": agent.assign_port,
                    "reserve": agent.reserve_port,
                    "release": agent.release_port,
                    "find": agent.find_free_port,
                    "status": agent.get_port_status,
                    "conflicts": agent.get_port_conflicts,
                    "info": agent.get_port_info,
                }

                if action in method_map:
                    result = method_map[action](**kwargs)
                else:
                    result = {
                        "success": False,
                        "error": f"Unknown action: {action}",
                        "available_actions": list(method_map.keys())
                        + [
                            "docker_available",
                            "docker_version",
                            "docker_containers",
                            "docker_mappings",
                            "docker_reserve",
                            "docker_release",
                            "detect_conflicts",
                            "resolve_conflicts",
                            "agent_port",
                            "reserve_agent_port",
                            "release_agent_port",
                            "status_report",
                            "cleanup",
                            "initialize",
                        ],
                    }

            # Convert result to JSON string
            return json.dumps(result, default=str, indent=2)

        except Exception as e:
            error_result = {
                "success": False,
                "error": str(e),
                "error_type": type(e).__name__,
                "action": action,
                "parameters": kwargs,
            }
            logger.error(f"Error in port_tool for action {action}: {e}")
            return json.dumps(error_result, default=str)

    # Set tool metadata for CrewAI
    port_tool.__name__ = "Port Management Tool"
    port_tool.__doc__ = """
    Comprehensive port management tool for the NIR_Mistral Framework.
    
    This tool provides capabilities for:
    - Port scanning and availability checking
    - Dynamic port assignment and reservation
    - Docker container port management
    - Framework port conflict detection and resolution
    - Cross-platform support (Windows/Linux/Mac)
    
    Use this tool to manage ports for Django, Docker, and other services
    in the NIR_Mistral Framework to avoid port conflicts.
    
    All actions return JSON results with success status and detailed information.
    """

    return port_tool


# Global agent instance
port_agent = PortManagementAgentCrewAI()

# Create the CrewAI tool
port_management_tool = create_port_tool(port_agent)


# Standalone usage functions
def scan_ports(host: str = "127.0.0.1", start: int = 1, end: int = 65535) -> Dict[str, Any]:
    """Scan ports (standalone function)"""
    return port_agent.scan_ports(host, start, end)


def check_port(port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
    """Check port availability (standalone function)"""
    return port_agent.check_port(port, host)


def assign_port(
    start: int = 8000, end: int = 9000, host: str = "127.0.0.1", service_name: str = None
) -> Dict[str, Any]:
    """Assign a free port (standalone function)"""
    return port_agent.assign_port(start, end, host, service_name)


def reserve_port(port: int, host: str = "127.0.0.1", service_name: str = None) -> Dict[str, Any]:
    """Reserve a specific port (standalone function)"""
    return port_agent.reserve_port(port, host, service_name)


def release_port(port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
    """Release a port (standalone function)"""
    return port_agent.release_port(port, host)


def find_free_port(start: int = 8000, end: int = 9000, host: str = "127.0.0.1") -> Dict[str, Any]:
    """Find a free port (standalone function)"""
    return port_agent.find_free_port(start, end, host)


def get_port_status() -> Dict[str, Any]:
    """Get port status (standalone function)"""
    return port_agent.get_port_status()


def get_port_conflicts(port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
    """Get port conflicts (standalone function)"""
    return port_agent.get_port_conflicts(port, host)


def get_port_info(port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
    """Get port info (standalone function)"""
    return port_agent.get_port_info(port, host)


# Docker standalone functions
def is_docker_available() -> Dict[str, Any]:
    """Check if Docker is available (standalone function)"""
    return port_agent.is_docker_available()


def get_docker_version() -> Dict[str, Any]:
    """Get Docker version (standalone function)"""
    return port_agent.get_docker_version()


def get_running_containers() -> Dict[str, Any]:
    """Get running Docker containers (standalone function)"""
    return port_agent.get_running_containers()


def get_container_port_mappings() -> Dict[str, Any]:
    """Get Docker port mappings (standalone function)"""
    return port_agent.get_container_port_mappings()


def reserve_docker_port(
    container_port: int,
    host_port: int = None,
    start: int = 8000,
    end: int = 9000,
    host: str = "127.0.0.1",
    service_name: str = None,
) -> Dict[str, Any]:
    """Reserve Docker port (standalone function)"""
    return port_agent.reserve_docker_port(container_port, host_port, start, end, host, service_name)


def release_docker_port(host_port: int, host: str = "127.0.0.1") -> Dict[str, Any]:
    """Release Docker port (standalone function)"""
    return port_agent.release_docker_port(host_port, host)


# Framework standalone functions
def detect_framework_conflicts() -> Dict[str, Any]:
    """Detect framework conflicts (standalone function)"""
    return port_agent.detect_framework_conflicts()


def resolve_framework_conflicts(auto_assign: bool = True) -> Dict[str, Any]:
    """Resolve framework conflicts (standalone function)"""
    return port_agent.resolve_framework_conflicts(auto_assign)


def get_agent_port(agent_name: str) -> Dict[str, Any]:
    """Get agent port (standalone function)"""
    return port_agent.get_agent_port(agent_name)


def reserve_port_for_agent(agent_name: str, port: int = None, host: str = "127.0.0.1") -> Dict[str, Any]:
    """Reserve port for agent (standalone function)"""
    return port_agent.reserve_port_for_agent(agent_name, port, host)


def release_agent_port(agent_name: str, host: str = "127.0.0.1") -> Dict[str, Any]:
    """Release agent port (standalone function)"""
    return port_agent.release_agent_port(agent_name, host)


def get_port_status_report() -> Dict[str, Any]:
    """Get port status report (standalone function)"""
    return port_agent.get_port_status_report()


def cleanup() -> Dict[str, Any]:
    """Clean up all reserved ports (standalone function)"""
    return port_agent.cleanup()


def initialize() -> Dict[str, Any]:
    """Initialize port management system (standalone function)"""
    return port_agent.initialize()


# Export all functions and classes
__all__ = [
    # Main classes
    "PortManagementAgentCrewAI",
    # Global instances
    "port_agent",
    "port_management_tool",
    # Factory function
    "create_port_tool",
    # Standalone functions - Port management
    "scan_ports",
    "check_port",
    "assign_port",
    "reserve_port",
    "release_port",
    "find_free_port",
    "get_port_status",
    "get_port_conflicts",
    "get_port_info",
    # Docker functions
    "is_docker_available",
    "get_docker_version",
    "get_running_containers",
    "get_container_port_mappings",
    "reserve_docker_port",
    "release_docker_port",
    # Framework functions
    "detect_framework_conflicts",
    "resolve_framework_conflicts",
    "get_agent_port",
    "reserve_port_for_agent",
    "release_agent_port",
    "get_port_status_report",
    "cleanup",
    "initialize",
]
