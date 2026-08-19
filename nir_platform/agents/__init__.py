"""
NIR Intelligence Platform - Agents Package

This package contains all specialized agents for the NIR Intelligence Platform:
- MCP Server for orchestration
- Spectral Analysis Agent
- Metadata Quality Agent
- Calibration Agent
- Reporting Agent
- Quality Assurance Agent
"""

from .mcp_server import MCPServer
from .spectral_analysis_agent import SpectralAnalysisAgent
from .metadata_quality_agent import MetadataQualityAgent
from .calibration_agent import CalibrationAgent
from .reporting_agent import ReportingAgent
from .quality_assurance_agent import QualityAssuranceAgent

__all__ = [
    'MCPServer',
    'SpectralAnalysisAgent',
    'MetadataQualityAgent',
    'CalibrationAgent',
    'ReportingAgent',
    'QualityAssuranceAgent',
]
