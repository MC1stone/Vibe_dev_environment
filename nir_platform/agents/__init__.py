"""NIR Intelligence Platform - Agents Package

This package contains all specialized agents for the NIR Intelligence Platform:

- MCP Server for orchestration
- Data Loader Agent (ingests/parses every new upload)
- Spectral Analysis Agent
- Spectral Search Agent (Qdrant/numpy vector index for comparable measurements)
- Metadata Quality Agent
- Calibration Agent
- Reporting Agent
- Quality Assurance Agent
"""

from .mcp_server import MCPServer
from .data_loader_agent import DataLoaderAgent
from .spectral_analysis_agent import SpectralAnalysisAgent
from .spectral_search_agent import SpectralSearchAgent
from .metadata_quality_agent import MetadataQualityAgent
from .calibration_agent import CalibrationAgent
from .reporting_agent import ReportingAgent
from .quality_assurance_agent import QualityAssuranceAgent
from .hardware_info_agent import HardwareInfoAgent

__all__ = [
    'MCPServer',
    'DataLoaderAgent',
    'SpectralAnalysisAgent',
    'SpectralSearchAgent',
    'MetadataQualityAgent',
    'CalibrationAgent',
    'ReportingAgent',
    'QualityAssuranceAgent',
    'HardwareInfoAgent',
]
