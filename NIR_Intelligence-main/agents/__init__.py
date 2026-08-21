# NIR Intelligence Platform - Agents Package
# This package contains all agent implementations for the NIR platform

__version__ = "1.0.0"
__author__ = "NIR Intelligence Platform Team"
__license__ = "MIT"

from .ansible_agent import AnsibleAgent
from .calibration_agent import CalibrationAgent
from .data_preparation_agent import EnhancedDataPreparationAgent as DataPreparationAgent
from .django_agent import DjangoAgent
from .docker_agent import DockerAgent
from .faiss_agent import FaissAgent

# Import additional agents
from .finalization_agent import FinalizationAgent
from .flower_agent import FlowerAgent
from .ilias_agent import ILIASAgent
from .mcp_agent import MCPAgent
from .metadata_agent import MetadataAgent
from .metadata_quality_agent import MetadataQualityAgent
from .neural_network_agent import NeuralNetworkAgent
from .nir_analysis_crew import NIRAnalysisCrew
from .postgresql_agent import PostgreSQLAgent
from .project_finalization_agent import ProjectFinalizationAgent
from .quarto_agent import QuartoAgent
from .reporting_agent import ReportingAgent
from .sensor_quality_agent import SensorQualityAgent

# Import new Crew AI agents
from .spectral_analysis_agent import SpectralAnalysisAgent
from .statistical_analysis_agent import StatisticalAnalysisAgent

# Import all agent classes for easy access
from .uvx_agent import UVXAgent
from .weaviate_agent import WeaviateAgent
from .generic_file_handler_agent import GenericFileHandlerAgent

# Agent registry for dynamic loading
AGENT_REGISTRY = {
    "uvx_agent": UVXAgent,
    "docker_agent": DockerAgent,
    "ansible_agent": AnsibleAgent,
    "data_preparation_agent": DataPreparationAgent,
    "metadata_agent": MetadataAgent,
    "sensor_quality_agent": SensorQualityAgent,
    "statistical_analysis_agent": StatisticalAnalysisAgent,
    "neural_network_agent": NeuralNetworkAgent,
    "calibration_agent": CalibrationAgent,
    "weaviate_agent": WeaviateAgent,
    "faiss_agent": FaissAgent,
    "postgresql_agent": PostgreSQLAgent,
    "django_agent": DjangoAgent,
    "mcp_agent": MCPAgent,
    "ilias_agent": ILIASAgent,
    "quarto_agent": QuartoAgent,
    "flower_agent": FlowerAgent,
    "finalization_agent": FinalizationAgent,
    "project_finalization_agent": ProjectFinalizationAgent,
    "spectral_analysis_agent": SpectralAnalysisAgent,
    "metadata_quality_agent": MetadataQualityAgent,
    "reporting_agent": ReportingAgent,
    "nir_analysis_crew": NIRAnalysisCrew,
    "generic_file_handler_agent": GenericFileHandlerAgent,
}


def get_agent_class(agent_name: str):
    """Get agent class by name from registry"""
    return AGENT_REGISTRY.get(agent_name)


def list_available_agents():
    """List all available agent classes"""
    return list(AGENT_REGISTRY.keys())
from .ilias_integration_agent import ILIASIntegrationAgent
from .hswt_styling_agent import HSWTStylingAgent
from .onboarding_agent import OnboardingAgent
from .audio_processor_agent import AudioProcessorAgent
from .image_processor_agent import ImageProcessorAgent
from .shift_detector_agent import ShiftDetectorAgent
from .parameter_recommender_agent import ParameterRecommenderAgent

# Update agent registry with new agents
AGENT_REGISTRY.update({
    "hswt_styling_agent": HSWTStylingAgent,
    "onboarding_agent": OnboardingAgent,
    "audio_processor_agent": AudioProcessorAgent,
    "image_processor_agent": ImageProcessorAgent,
    "shift_detector_agent": ShiftDetectorAgent,
    "parameter_recommender_agent": ParameterRecommenderAgent,
    "ilias_integration_agent": ILIASIntegrationAgent
})
