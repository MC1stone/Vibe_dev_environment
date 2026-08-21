"""
Port Management Agent for NIR_Mistral Framework

This agent provides comprehensive port management capabilities including:
- Thread-safe port reservation system
- Cross-platform port scanning (Windows/Linux/Mac)
- Docker-specific port management
- Port conflict resolution
- Comprehensive error handling and validation

Author: NIR_Mistral Framework Team
Version: 1.0.0
"""

from .agent import PortManagementAgentCrewAI, create_port_tool, port_agent, port_management_tool
from .crewai_integration import (
    PortManagementCrew,
    PortManagerCrewAIAgent,
    create_port_manager_crew,
    port_management_crew,
    port_manager_agent,
)
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

# Global port manager instance
port_manager = PortManager()
docker_port_manager = DockerPortManager()

__all__ = [
    "PortManager",
    "PortManagementAgent",
    "DockerPortManager",
    "PortAgentIntegration",
    "PortManagementAgentCrewAI",
    "PortManagerCrewAIAgent",
    "PortManagementCrew",
    "port_agent",
    "port_manager",
    "docker_port_manager",
    "port_manager_agent",
    "port_management_crew",
    "port_management_tool",
    "create_port_tool",
    "create_port_manager_crew",
    "PortManagerError",
    "PortNotAvailableError",
    "PortOutOfRangeError",
    "PortReservationError",
    "PortReleaseError",
    "PortConflictError",
    "PortScanError",
    "DockerPortError",
]
