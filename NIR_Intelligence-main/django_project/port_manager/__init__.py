"""
Port Manager Django App for NIR_Mistral Framework

This app provides Django integration for the Port Management Agent,
including middleware, management commands, and API endpoints for
port conflict resolution and dynamic port assignment.
"""

# Import the port agent modules
import sys
import os
from pathlib import Path

# Import path configuration
from path_config import setup_project_paths
setup_project_paths()

# Initialize the port management system with error handling
try:
    from agents.port_agent import PortAgentIntegration
    # Global port integration instance
    port_integration = PortAgentIntegration()
except ImportError as e:
    # Fallback if there are import issues (e.g., missing yaml module)
    print(f"Warning: Could not import PortAgentIntegration: {e}")
    print("Port Management Agent will be initialized on first use")
    port_integration = None

__all__ = ['port_integration']