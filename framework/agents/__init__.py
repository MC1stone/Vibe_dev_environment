"""
Agent Framework - Agents Module

This module contains all agent definitions for the multi-agent software development team.
"""

from .specialists import (
    BackendAgent,
    FrontendAgent,
    DataAnalysisAgent,
    MCPAgent,
    N8NAgent,
    CrewAIAgent,
    FaissAgent,
    PostgreSQLAgent,
    QuadrantAgent,
    QuartoAgent,
)

from .overview import (
    TeamLeadAgent,
    ProjectManagerAgent,
    TaskCoordinatorAgent,
)

from .quality import (
    QualityAssuranceAgent,
    CodeReviewAgent,
    TestingAgent,
)

__all__ = [
    # Specialist Agents
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
    # Overview Agents
    'TeamLeadAgent',
    'ProjectManagerAgent',
    'TaskCoordinatorAgent',
    # Quality Agents
    'QualityAssuranceAgent',
    'CodeReviewAgent',
    'TestingAgent',
]
