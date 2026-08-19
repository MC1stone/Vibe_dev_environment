"""
Skills Module

This module contains all skill definitions for the multi-agent framework.
Each agent has access to specialized skills for their domain.
"""

from .backend_skills import BackendSkills
from .frontend_skills import FrontendSkills
from .data_analysis_skills import DataAnalysisSkills
from .mcp_skills import MCPSkills
from .n8n_skills import N8NSkills
from .crewai_skills import CrewAISkills
from .faiss_skills import FaissSkills
from .postgresql_skills import PostgreSQLSkills
from .quadrant_skills import QuadrantSkills
from .quarto_skills import QuartoSkills

__all__ = [
    'BackendSkills',
    'FrontendSkills',
    'DataAnalysisSkills',
    'MCPSkills',
    'N8NSkills',
    'CrewAISkills',
    'FaissSkills',
    'PostgreSQLSkills',
    'QuadrantSkills',
    'QuartoSkills',
]
