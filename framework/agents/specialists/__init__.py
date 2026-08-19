"""
Specialist Agents Module

Domain-specific expert agents for various software development areas.
"""

from .backend_agent import BackendAgent
from .frontend_agent import FrontendAgent
from .data_analysis_agent import DataAnalysisAgent
from .mcp_agent import MCPAgent
from .n8n_agent import N8NAgent
from .crewai_agent import CrewAIAgent
from .faiss_agent import FaissAgent
from .postgresql_agent import PostgreSQLAgent
from .quadrant_agent import QuadrantAgent
from .quarto_agent import QuartoAgent

__all__ = [
    'BackendAgent',
    'FrontendAgent',
    'DataAnalysisAgent',
    'MCPAgent',
    'N8NAgent',
    'CrewAIAgent',
    'FaissAgent',
    'PostgreSQLAgent',
    'QuadrantAgent',
    'QuartoAgent',
]
