"""
Port Management Agent Integration with NIR_Mistral Framework

This module provides integration between the Port Management Agent and the existing
NIR_Mistral Framework agents to resolve port conflicts and provide dynamic port assignment.
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

import yaml

# Add the project root to the path
project_root = Path(__file__).parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

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
from .port_manager import PortManagementAgent, PortManager

# Configure logging
logger = logging.getLogger(__name__)


class FrameworkPortConfig:
    """Port configuration for the NIR_Mistral Framework"""

    # Default ports from agent_config.yaml
    DEFAULT_PORTS = {
        "django": 8000,
        "weaviate": 8080,
        "postgresql": 5432,
        "mcp_server": 8081,
        "flower": 5555,
        "redis": 6379,
        "elasticsearch": 9200,
        "kibana": 5601,
        "prometheus": 9090,
        "grafana": 3000,
    }

    # Port ranges for different service types
    PORT_RANGES = {
        "django": {"start": 8000, "end": 8050, "description": "Django Services"},
        "weaviate": {"start": 8080, "end": 8090, "description": "Weaviate/HTTP Services"},
        "database": {"start": 5432, "end": 5450, "description": "Database Services"},
        "monitoring": {"start": 9000, "end": 9100, "description": "Monitoring Services"},
        "api": {"start": 8500, "end": 8600, "description": "API Services"},
        "general": {"start": 10000, "end": 11000, "description": "General Services"},
    }

    def __init__(self, config_path: Optional[str] = None):
        """
        Initialize framework port configuration

        Args:
            config_path: Path to agent_config.yaml (optional)
        """
        self.config_path = config_path
        self.agent_config = {}
        self._load_config()

    def _load_config(self):
        """Load agent configuration from YAML file"""
        if not self.config_path:
            # Try default locations
            possible_paths = [
                str(project_root / "config" / "agent_config.yaml"),
                str(project_root / "config" / "agent_config.yml"),
                str(project_root / "agent_config.yaml"),
                "/etc/nir_mistral/agent_config.yaml",
            ]

            for path in possible_paths:
                if os.path.exists(path):
                    self.config_path = path
                    break

        if self.config_path and os.path.exists(self.config_path):
            try:
                with open(self.config_path, "r") as f:
                    self.agent_config = yaml.safe_load(f) or {}
                logger.info(f"Loaded agent configuration from {self.config_path}")
            except Exception as e:
                logger.error(f"Failed to load agent config: {str(e)}")
                self.agent_config = {}

    def get_agent_ports(self) -> Dict[str, int]:
        """Get port configurations from all agents"""
        ports = {}

        if "agents" not in self.agent_config:
            return ports

        for agent_name, agent_config in self.agent_config["agents"].items():
            if agent_config.get("enabled", False) and "params" in agent_config:
                params = agent_config["params"]
                if "port" in params:
                    ports[agent_name] = params["port"]

        return ports

    def get_service_port_ranges(self) -> Dict[str, Dict[str, int]]:
        """Get port ranges for different service types"""
        return self.PORT_RANGES.copy()

    def get_port_for_service_type(self, service_type: str) -> Dict[str, int]:
        """Get port range for a specific service type"""
        return self.PORT_RANGES.get(service_type, self.PORT_RANGES["general"]).copy()


class PortConflictResolver:
    """
    Port Conflict Resolver for NIR_Mistral Framework

    This class detects and resolves port conflicts between framework agents
    and provides dynamic port assignment.
    """

    def __init__(
        self,
        port_manager: PortManager = None,
        docker_port_manager: DockerPortManager = None,
        framework_config: FrameworkPortConfig = None,
    ):
        """
        Initialize the Port Conflict Resolver

        Args:
            port_manager: PortManager instance
            docker_port_manager: DockerPortManager instance
            framework_config: FrameworkPortConfig instance
        """
        self.port_manager = port_manager or PortManager()
        self.docker_port_manager = docker_port_manager or DockerPortManager(self.port_manager)
        self.framework_config = framework_config or FrameworkPortConfig()

        # Track original vs assigned ports
        self.port_mappings: Dict[str, Dict[str, Any]] = {}
        self.conflicts_resolved: List[str] = []

    def detect_conflicts(self) -> Dict[str, Any]:
        """
        Detect port conflicts in the framework configuration

        Returns:
            Dictionary with conflict information
        """
        agent_ports = self.framework_config.get_agent_ports()
        used_ports: Dict[int, List[str]] = {}
        conflicts: Dict[str, List[str]] = {}

        # Check for duplicate ports
        for agent_name, port in agent_ports.items():
            if port not in used_ports:
                used_ports[port] = []
            used_ports[port].append(agent_name)

        # Identify conflicts (ports used by multiple agents)
        for port, agents in used_ports.items():
            if len(agents) > 1:
                for agent in agents:
                    if agent not in conflicts:
                        conflicts[agent] = []
                    conflicts[agent].extend([a for a in agents if a != agent])

        # Check against system ports
        system_ports = self.port_manager._scanner.get_system_used_ports()
        for agent_name, port in agent_ports.items():
            if port in system_ports:
                if agent_name not in conflicts:
                    conflicts[agent_name] = []
                conflicts[agent_name].append(f"system:{port}")

        # Check against Docker ports
        if self.docker_port_manager.is_docker_available():
            docker_ports = self.docker_port_manager.get_used_docker_ports()
            for agent_name, port in agent_ports.items():
                if port in docker_ports:
                    if agent_name not in conflicts:
                        conflicts[agent_name] = []
                    conflicts[agent_name].append(f"docker:{port}")

        return {
            "has_conflicts": len(conflicts) > 0,
            "conflicts": conflicts,
            "conflict_count": len(conflicts),
            "conflicted_agents": list(conflicts.keys()),
        }

    def resolve_conflicts(self, auto_assign: bool = True) -> Dict[str, Any]:
        """
        Resolve port conflicts by assigning new ports to conflicting agents

        Args:
            auto_assign: Whether to automatically assign new ports

        Returns:
            Dictionary with resolution information
        """
        conflict_info = self.detect_conflicts()

        if not conflict_info["has_conflicts"]:
            return {
                "success": True,
                "message": "No port conflicts detected",
                "conflicts_resolved": [],
                "port_mappings": {},
            }

        # Clear previous mappings
        self.port_mappings.clear()
        self.conflicts_resolved.clear()

        agent_ports = self.framework_config.get_agent_ports()
        used_ports: Set[int] = set()
        new_mappings: Dict[str, Dict[str, Any]] = {}

        # First, add system ports to used_ports
        system_ports = self.port_manager._scanner.get_system_used_ports()
        used_ports.update(system_ports)

        # Add Docker ports if available
        if self.docker_port_manager.is_docker_available():
            docker_ports = self.docker_port_manager.get_used_docker_ports()
            used_ports.update(docker_ports)

        # Process each agent
        for agent_name, original_port in agent_ports.items():
            # Check if this agent has conflicts
            if agent_name in conflict_info["conflicts"]:
                # Get service type to determine port range
                service_type = self._get_agent_service_type(agent_name)
                port_range = self.framework_config.get_port_for_service_type(service_type)

                # Find new port
                new_port = None

                if auto_assign:
                    try:
                        new_port = self.port_manager.find_and_reserve_port(
                            port_range["start"], port_range["end"], "127.0.0.1", f"agent:{agent_name}"
                        )
                        used_ports.add(new_port)
                    except PortReservationError as e:
                        logger.error(f"Failed to assign port for {agent_name}: {str(e)}")
                        # Try a broader range
                        try:
                            new_port = self.port_manager.find_and_reserve_port(
                                8000, 9000, "127.0.0.1", f"agent:{agent_name}"
                            )
                            used_ports.add(new_port)
                        except PortReservationError:
                            logger.error(f"Failed to assign port for {agent_name} in extended range")

                if new_port:
                    new_mappings[agent_name] = {
                        "original_port": original_port,
                        "new_port": new_port,
                        "service_type": service_type,
                        "status": "resolved",
                    }
                    self.conflicts_resolved.append(agent_name)
                else:
                    new_mappings[agent_name] = {
                        "original_port": original_port,
                        "new_port": None,
                        "service_type": service_type,
                        "status": "failed",
                    }
            else:
                # No conflict, use original port
                new_mappings[agent_name] = {
                    "original_port": original_port,
                    "new_port": original_port,
                    "service_type": self._get_agent_service_type(agent_name),
                    "status": "unchanged",
                }

        self.port_mappings = new_mappings

        return {
            "success": True,
            "conflicts_detected": conflict_info["conflict_count"],
            "conflicts_resolved": len(self.conflicts_resolved),
            "port_mappings": new_mappings,
            "resolved_agents": self.conflicts_resolved.copy(),
        }

    def _get_agent_service_type(self, agent_name: str) -> str:
        """Determine the service type for an agent"""
        service_types = {
            "django_agent": "django",
            "weaviate_agent": "weaviate",
            "postgresql_agent": "database",
            "mcp_agent": "api",
            "flower_agent": "monitoring",
            "docker_agent": "general",
            "ansible_agent": "general",
            "data_preparation_agent": "general",
            "metadata_agent": "general",
            "sensor_quality_agent": "general",
            "statistical_analysis_agent": "general",
            "neural_network_agent": "general",
            "calibration_agent": "general",
            "faiss_agent": "general",
            "quarto_agent": "general",
            "ilias_agent": "general",
        }

        return service_types.get(agent_name, "general")

    def get_port_mapping_for_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """Get port mapping for a specific agent"""
        return self.port_mappings.get(agent_name)

    def get_agent_port(self, agent_name: str) -> int:
        """
        Get the current port for an agent (original or assigned)

        Args:
            agent_name: Name of the agent

        Returns:
            Port number for the agent
        """
        mapping = self.get_port_mapping_for_agent(agent_name)
        if mapping:
            return mapping.get("new_port", mapping.get("original_port"))

        # Fallback to original configuration
        agent_ports = self.framework_config.get_agent_ports()
        return agent_ports.get(agent_name)

    def update_agent_config(self, output_path: Optional[str] = None) -> Dict[str, Any]:
        """
        Update agent configuration with resolved ports

        Args:
            output_path: Path to save updated configuration (optional)

        Returns:
            Dictionary with update information
        """
        if not self.port_mappings:
            return {"success": False, "message": "No port mappings available. Run resolve_conflicts() first."}

        # Load current configuration
        config = self.framework_config.agent_config.copy()

        # Update ports in configuration
        updated_agents = []

        if "agents" in config:
            for agent_name, mapping in self.port_mappings.items():
                if mapping.get("new_port") and mapping["new_port"] != mapping.get("original_port"):
                    if agent_name in config["agents"]:
                        config["agents"][agent_name]["params"]["port"] = mapping["new_port"]
                        updated_agents.append(agent_name)

        # Save updated configuration if path provided
        if output_path:
            try:
                with open(output_path, "w") as f:
                    yaml.dump(config, f, default_flow_style=False, sort_keys=False)
                logger.info(f"Updated configuration saved to {output_path}")
            except Exception as e:
                logger.error(f"Failed to save updated configuration: {str(e)}")
                return {"success": False, "message": f"Failed to save configuration: {str(e)}"}

        return {
            "success": True,
            "updated_agents": updated_agents,
            "config": config,
            "message": f"Updated {len(updated_agents)} agent configurations",
        }

    def get_port_status_report(self) -> Dict[str, Any]:
        """
        Generate a comprehensive port status report

        Returns:
            Dictionary with port status information
        """
        agent_ports = self.framework_config.get_agent_ports()

        report = {
            "agents": {},
            "system_ports": list(self.port_manager._scanner.get_system_used_ports()),
            "reserved_ports": list(self.port_manager.get_reserved_ports().keys()),
            "docker_available": self.docker_port_manager.is_docker_available(),
        }

        if report["docker_available"]:
            report["docker_ports"] = list(self.docker_port_manager.get_used_docker_ports())

        # Check each agent's port status
        for agent_name, port in agent_ports.items():
            status = {
                "configured_port": port,
                "current_port": self.get_agent_port(agent_name),
                "is_available": self.port_manager.check_port_available(port),
                "is_reserved": port in self.port_manager.get_reserved_ports(),
                "conflicts": [],
            }

            # Check for conflicts
            if not status["is_available"]:
                conflicts = self.port_manager.get_port_conflicts(port)
                status["conflicts"] = conflicts
                status["has_conflicts"] = len(conflicts) > 0

            report["agents"][agent_name] = status

        return report


class PortAgentIntegration:
    """
    Main integration class for Port Management Agent with NIR_Mistral Framework

    This class provides the primary interface for integrating port management
    with the existing framework agents.
    """

    def __init__(self):
        """Initialize the Port Agent Integration"""
        self.port_manager = PortManager()
        self.docker_port_manager = DockerPortManager(self.port_manager)
        self.framework_config = FrameworkPortConfig()
        self.conflict_resolver = PortConflictResolver(
            self.port_manager, self.docker_port_manager, self.framework_config
        )
        self.port_agent = PortManagementAgent(self.port_manager)

    def initialize(self) -> Dict[str, Any]:
        """
        Initialize the port management system

        Returns:
            Dictionary with initialization information
        """
        # Check Docker availability
        docker_available = self.docker_port_manager.is_docker_available()

        # Detect initial conflicts
        conflict_info = self.conflict_resolver.detect_conflicts()

        # Get system information
        system_ports = self.port_manager._scanner.get_system_used_ports()

        return {
            "success": True,
            "docker_available": docker_available,
            "docker_version": self.docker_port_manager.get_docker_version(),
            "system_ports_count": len(system_ports),
            "has_conflicts": conflict_info["has_conflicts"],
            "conflict_count": conflict_info["conflict_count"],
            "message": "Port Management Agent initialized successfully",
        }

    def resolve_framework_conflicts(self, auto_assign: bool = True) -> Dict[str, Any]:
        """
        Resolve port conflicts in the NIR_Mistral Framework

        Args:
            auto_assign: Whether to automatically assign new ports

        Returns:
            Dictionary with conflict resolution information
        """
        return self.conflict_resolver.resolve_conflicts(auto_assign)

    def get_agent_port(self, agent_name: str) -> int:
        """
        Get the port for a specific agent (resolved if conflicts exist)

        Args:
            agent_name: Name of the agent

        Returns:
            Port number for the agent
        """
        return self.conflict_resolver.get_agent_port(agent_name)

    def reserve_port_for_agent(self, agent_name: str, port: int = None, host: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Reserve a port for a specific agent

        Args:
            agent_name: Name of the agent
            port: Specific port to reserve (optional, will auto-assign)
            host: Host address for binding

        Returns:
            Dictionary with reservation information
        """
        if port is None:
            # Get service type and port range
            service_type = self.conflict_resolver._get_agent_service_type(agent_name)
            port_range = self.framework_config.get_port_for_service_type(service_type)

            # Find and reserve a port
            port = self.port_manager.find_and_reserve_port(
                port_range["start"], port_range["end"], host, f"agent:{agent_name}"
            )
        else:
            # Reserve the specific port
            self.port_manager.reserve_port(port, host, f"agent:{agent_name}")

        # Update the conflict resolver's mappings
        self.conflict_resolver.port_mappings[agent_name] = {
            "original_port": self.framework_config.get_agent_ports().get(agent_name),
            "new_port": port,
            "service_type": self.conflict_resolver._get_agent_service_type(agent_name),
            "status": "reserved",
        }

        return {
            "success": True,
            "agent_name": agent_name,
            "port": port,
            "host": host,
            "message": f"Port {port} reserved for agent {agent_name}",
        }

    def release_agent_port(self, agent_name: str, host: str = "127.0.0.1") -> Dict[str, Any]:
        """
        Release the port for a specific agent

        Args:
            agent_name: Name of the agent
            host: Host address

        Returns:
            Dictionary with release information
        """
        # Get the current port for the agent
        port = self.get_agent_port(agent_name)

        if port is None:
            return {"success": False, "agent_name": agent_name, "message": f"No port assigned for agent {agent_name}"}

        # Release the port
        success = self.port_manager.release_port(port, host)

        # Remove from mappings
        if agent_name in self.conflict_resolver.port_mappings:
            del self.conflict_resolver.port_mappings[agent_name]

        return {
            "success": success,
            "agent_name": agent_name,
            "port": port,
            "host": host,
            "message": (
                f"Port {port} released for agent {agent_name}"
                if success
                else f"Port {port} was not reserved for agent {agent_name}"
            ),
        }

    def execute_port_action(self, action: str, **kwargs) -> Dict[str, Any]:
        """
        Execute a port management action

        Args:
            action: Action to perform
            **kwargs: Additional parameters

        Returns:
            Dictionary with action result
        """
        return self.port_agent.execute(action, **kwargs)

    def get_port_status_report(self) -> Dict[str, Any]:
        """
        Get comprehensive port status report

        Returns:
            Dictionary with port status information
        """
        return self.conflict_resolver.get_port_status_report()

    def cleanup(self) -> Dict[str, Any]:
        """
        Clean up all reserved ports

        Returns:
            Dictionary with cleanup information
        """
        count = self.port_manager.release_all_ports()
        self.conflict_resolver.port_mappings.clear()
        self.conflict_resolver.conflicts_resolved.clear()

        return {"success": True, "ports_released": count, "message": f"Released {count} reserved ports"}


# Global instance for easy access
port_integration = PortAgentIntegration()


def get_port_manager() -> PortManager:
    """Get the global PortManager instance"""
    return port_integration.port_manager


def get_docker_port_manager() -> DockerPortManager:
    """Get the global DockerPortManager instance"""
    return port_integration.docker_port_manager


def get_port_integration() -> PortAgentIntegration:
    """Get the global PortAgentIntegration instance"""
    return port_integration
