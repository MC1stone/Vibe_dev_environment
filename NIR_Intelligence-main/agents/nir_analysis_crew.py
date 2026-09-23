# NIR Intelligence Platform - NIR Analysis Crew
# Main CrewAI orchestration for complete NIR spectral analysis workflow

import logging
import math
import os
import sys
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

# Add project root to path
project_root = Path(__file__).parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

try:
    from .crewai_compat import ensure_crewai_compat
    ensure_crewai_compat()
except ImportError:
    pass

try:
    from crewai import Agent, Crew, Process, Task
    from crewai.tools import tool

    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("Warning: CrewAI not available. NIR Analysis Crew will work in standalone mode.",
          file=sys.stderr)

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity
from .calibration_agent import CalibrationAgent
from .data_preparation_agent import EnhancedDataPreparationAgent as DataPreparationAgent
from .django_agent import DjangoAgent
from .faiss_agent import FaissAgent
from .flower_agent import FlowerAgent
from .ilias_agent import ILIASAgent
from .mcp_agent import MCPAgent
from .metadata_quality_agent import MetadataQualityAgent, MetadataQualityResult
from .neural_network_agent import NeuralNetworkAgent
from .postgresql_agent import PostgreSQLAgent
from .qdrant_agent import QdrantAgent
from .quarto_agent import QuartoAgent
from .reporting_agent import GeneratedReport, ReportFormat, ReportingAgent, ReportType
from .sensor_quality_agent import SensorQualityAgent
from .spectral_analysis_agent import SpectralAnalysisAgent, SpectralAnalysisResult
from .statistical_analysis_agent import StatisticalAnalysisAgent


class AnalysisMode(Enum):
    """Analysis modes for the NIR crew"""

    STANDARD = "standard"
    COMPREHENSIVE = "comprehensive"
    QUICK = "quick"
    BATCH = "batch"


class PrivacyLevel(Enum):
    """Privacy levels for data handling"""

    LOCAL_ONLY = "local_only"
    PUBLIC_FEDERATED = "public_federated"
    PRIVATE_FEDERATED = "private_federated"


@dataclass
class AnalysisRequest:
    """Request for spectral analysis"""

    sample_id: str
    spectral_data: Dict[str, Any]
    metadata: Dict[str, Any] = field(default_factory=dict)
    file_paths: List[str] = field(default_factory=list)
    analysis_mode: AnalysisMode = AnalysisMode.STANDARD
    privacy_level: PrivacyLevel = PrivacyLevel.LOCAL_ONLY
    report_type: ReportType = ReportType.COMPREHENSIVE
    report_format: ReportFormat = ReportFormat.HTML
    include_calibration: bool = True
    include_federated_learning: bool = False
    user_id: Optional[str] = None


@dataclass
class AnalysisResult:
    """Complete analysis result from NIR crew"""

    request_id: str
    sample_id: str
    timestamp: str
    spectral_analysis: Optional[SpectralAnalysisResult] = None
    metadata_quality: Optional[MetadataQualityResult] = None
    generated_reports: List[GeneratedReport] = field(default_factory=list)
    calibration_results: Optional[Dict[str, Any]] = None
    sensor_quality_results: Optional[Dict[str, Any]] = None
    statistical_analysis_results: Optional[Dict[str, Any]] = None
    neural_network_results: Optional[Dict[str, Any]] = None
    federated_learning_results: Optional[Dict[str, Any]] = None
    overall_quality_score: float = 0.0
    recommendations: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    privacy_level: PrivacyLevel = PrivacyLevel.LOCAL_ONLY
    user_id: Optional[str] = None


@dataclass
class CrewConfiguration:
    """Configuration for the NIR Analysis Crew"""

    enable_crewai: bool = True
    enable_federated_learning: bool = True
    default_analysis_mode: AnalysisMode = AnalysisMode.STANDARD
    default_privacy_level: PrivacyLevel = PrivacyLevel.LOCAL_ONLY
    default_report_type: ReportType = ReportType.COMPREHENSIVE
    default_report_format: ReportFormat = ReportFormat.HTML
    max_batch_size: int = 10
    temp_dir: str = "temp/crewai"
    output_dir: str = "output/analysis"
    # Local LLM (mission statement: Ollama + mistral in Docker). When set,
    # CrewAI agents are bound to this Ollama endpoint instead of defaulting
    # to an unreachable OpenAI backend.
    llm_base_url: str = os.environ.get("OLLAMA_URL", "http://localhost:11434")
    llm_model: str = os.environ.get("NIR_LLM_MODEL", "mistral")


class NIRAnalysisCrew:
    """
    Main CrewAI orchestration for NIR spectral analysis.

    This crew coordinates the full agent system of the mission statement:
    1. Spectral Analysis Agent - Analyzes spectral data quality
    2. Sensor Quality Agent - Drift, noise and instrument monitoring
    3. Statistical Analysis Agent - PCA, PLS, PCR, ANOVA, clustering
    4. Neural Network Agent - CNN, MLP, Autoencoder (parallel to statistics)
    5. Metadata Quality Agent - Metadata completeness and standards compliance
    6. Calibration Agent - Spectrometer calibration and optimization
    7. Reporting Agent - Quarto reports
    8. Flower Agent - Federated learning (optional)

    Background service agents (Data Preparation, Qdrant, FAISS, PostgreSQL,
    Django, MCP, ILIAS, Quarto) are wired as CrewAI agents with tools so the
    crew can operate the platform interfaces ("the agents run the application
    in the background").
    """

    def __init__(self, config: Optional[CrewConfiguration] = None):
        self.config = config or CrewConfiguration()
        self.logger = logging.getLogger("NIRAnalysisCrew")

        # Initialize analysis agents
        self.spectral_agent = SpectralAnalysisAgent()
        self.metadata_agent = MetadataQualityAgent()
        self.reporting_agent = ReportingAgent(
            output_dir=Path(self.config.output_dir) / "reports", temp_dir=Path(self.config.temp_dir)
        )
        self.calibration_agent = CalibrationAgent()
        self.flower_agent = FlowerAgent() if self.config.enable_federated_learning else None

        # Background service agents operating the platform interfaces
        self.sensor_quality_agent = SensorQualityAgent()
        self.statistical_analysis_agent = StatisticalAnalysisAgent()
        self.neural_network_agent = NeuralNetworkAgent()
        self.data_preparation_agent = DataPreparationAgent()
        self.qdrant_agent = QdrantAgent()
        self.faiss_agent = FaissAgent()
        self.postgresql_agent = PostgreSQLAgent()
        self.django_agent = DjangoAgent()
        self.mcp_agent = MCPAgent()
        self.ilias_agent = ILIASAgent()
        self.quarto_agent = QuartoAgent()

        # CrewAI components (if available)
        self.crewai_agents = []
        self.crewai_tasks = []
        self.crew = None
        self.crewai_llm = None

        # Initialize CrewAI if available
        if CREWAI_AVAILABLE and self.config.enable_crewai:
            self._initialize_crewai()

        # Analysis tracking
        self.analysis_history = []
        self.current_request_id = None

        self.logger.info("NIRAnalysisCrew initialized")
        self.logger.info(f"CrewAI available: {CREWAI_AVAILABLE and self.config.enable_crewai}")
        self.logger.info(f"Federated learning enabled: {self.config.enable_federated_learning}")

    def _agent_tool(self, base_agent, description):
        """Wrap a real platform agent as a CrewAI-compatible tool.

        crewai >= 0.80 requires tools to be BaseTool instances (pydantic
        validation rejects plain functions). The tool accepts a JSON
        context dict and executes the underlying agent implementation
        (no simulated values). Falls back to a plain function when the
        crewai package is unavailable (standalone mode, offline tests).
        """
        import json as _json

        def _run(context_json: str = "{}") -> str:
            try:
                context = _json.loads(context_json) if context_json else {}
            except (ValueError, TypeError):
                context = {}
            output = base_agent.execute(context)
            return _json.dumps({
                "agent": output.agent_name,
                "status": output.status.name if hasattr(output.status, "name") else str(output.status),
                "data": output.data,
                "errors": [e.message for e in output.errors],
            }, default=str)

        try:
            from crewai.tools import BaseTool
            from pydantic import BaseModel, Field

            tool_name = f"{base_agent.name.lower()}_tool"
            tool_description = description

            class _Context(BaseModel):
                context_json: str = Field(default="{}", description="JSON context for the agent")

            class _WrappedTool(BaseTool):
                name: str = tool_name
                description: str = tool_description
                args_schema: type = _Context

                def _run(self, context_json: str = "{}") -> str:
                    return _run(context_json)

            instance = _WrappedTool()
            instance.name = tool_name
            instance.description = tool_description
            return instance
        except ImportError:
            def tool(context_json: str = "{}") -> str:
                return _run(context_json)
            tool.__doc__ = description
            tool.__name__ = f"{base_agent.name.lower()}_tool"
            return tool

    def _build_llm(self):
        """Bind the local Ollama LLM for CrewAI agents.

        CrewAI defaults to an OpenAI backend that is unreachable in the
        local stack; the mission statement runs Ollama + mistral in Docker.
        Returns None when no binding is possible so callers keep the
        deterministic standalone path.
        """
        try:
            from crewai import LLM
            return LLM(
                model=self.config.llm_model,
                base_url=f"{self.config.llm_base_url.rstrip('/')}",
            )
        except Exception as e:
            self.logger.warning(f"CrewAI LLM binding to Ollama failed: {e}")
            return None

    def _initialize_crewai(self):
        """Initialize the full CrewAI agent crew with real platform tools."""
        try:
            self.crewai_llm = self._build_llm()
            spectral_agent = Agent(
                role="NIR Spectral Analysis Expert",
                goal="Analyze NIR spectral data for quality, issues, and provide parameter recommendations",
                backstory=(
                    "You are an expert in Near-Infrared (NIR) spectroscopy with deep knowledge "
                    "of spectral data analysis, quality assessment, and spectrometer calibration. "
                    "Your expertise includes detecting wavelength shifts, noise analysis, "
                    "signal-to-noise ratio assessment, and providing actionable recommendations "
                    "for improving spectrometer parameters."
                ),
                tools=[self._agent_tool(
                    self.spectral_agent,
                    "Analyze NIR spectral data quality. Input: JSON with spectral_data.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            sensor_quality_agent = Agent(
                role="Sensor Quality Monitor",
                goal="Detect sensor drift, noise, offsets and instrument degradation",
                backstory=(
                    "You are an instrument monitoring specialist for NIR spectrometers. "
                    "You quantify drift, baseline offsets and noise against reference "
                    "spectra and raise warnings before measurements degrade."
                ),
                tools=[self._agent_tool(
                    self.sensor_quality_agent,
                    "Run drift/noise/offset checks. Input: JSON with spectra and thresholds.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            statistical_agent = Agent(
                role="Chemometrics Statistician",
                goal="Run PCA, PLS, PCR, ANOVA and cluster analysis on spectral data",
                backstory=(
                    "You are a chemometrics expert applying multivariate statistics to "
                    "NIR spectra: PCA for structure, PLS/PCR for quantification, ANOVA "
                    "for group differences and clustering for sample grouping."
                ),
                tools=[self._agent_tool(
                    self.statistical_analysis_agent,
                    "Run statistical analyses. Input: JSON with spectra and reference_values.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            neural_network_agent = Agent(
                role="Neural Network Specialist",
                goal="Train CNN, MLP and Autoencoder models in parallel to the statistical analysis",
                backstory=(
                    "You are a deep learning specialist for spectroscopy data. You always "
                    "run your models in parallel to the chemometrics analysis and compare "
                    "model performance (R2) with the statistical methods."
                ),
                tools=[self._agent_tool(
                    self.neural_network_agent,
                    "Train neural network models. Input: JSON with spectra, reference_values, models.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            metadata_agent = Agent(
                role="Metadata Quality Assessment Specialist",
                goal="Extract, validate, and assess metadata quality against established standards",
                backstory=(
                    "You are a metadata expert specializing in scientific data standards. "
                    "Your expertise includes ISO 19115, Dublin Core, and custom NIR metadata standards. "
                    "You can extract metadata from various file formats, validate structure, "
                    "and provide comprehensive quality assessments with recommendations."
                ),
                tools=[self._agent_tool(
                    self.metadata_agent,
                    "Assess metadata quality. Input: JSON with metadata, sample_id, file_paths.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            data_preparation_agent = Agent(
                role="Data Preparation Engineer",
                goal="Import, clean, normalize and perform outlier analysis on spectral data",
                backstory=(
                    "You are a data engineer for spectroscopy pipelines. You import files "
                    "in any format, clean and normalize spectra and flag outliers before "
                    "any analysis runs."
                ),
                tools=[self._agent_tool(
                    self.data_preparation_agent,
                    "Prepare spectral data. Input: JSON with input_directory or file_paths.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            calibration_agent = Agent(
                role="Spectrometer Calibration Specialist",
                goal="Perform spectrometer calibration and optimization",
                backstory=(
                    "You are an expert in spectrometer calibration with knowledge of "
                    "various calibration methods (PLS, PCR, SVM, etc.). Your expertise includes "
                    "calibration curve generation, performance validation, and parameter optimization."
                ),
                tools=[self._agent_tool(
                    self.calibration_agent,
                    "Calibrate models. Input: JSON with spectra and reference_values.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            qdrant_agent = Agent(
                role="Vector Database Operator",
                goal="Store embeddings and answer semantic and similarity searches via Qdrant",
                backstory=(
                    "You operate the Qdrant vector database of the platform: you manage "
                    "the nir_spectra collection, store embeddings and execute semantic "
                    "and similarity searches."
                ),
                tools=[self._agent_tool(
                    self.qdrant_agent,
                    "Check/operate Qdrant. Input: JSON with host, port, collection_name.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            faiss_agent = Agent(
                role="Similarity Search Operator",
                goal="Compare spectra and peaks and run nearest-neighbour searches",
                backstory=(
                    "You operate the FAISS similarity engine: spectrum comparison, peak "
                    "comparison and nearest-neighbour lookups against reference sets."
                ),
                tools=[self._agent_tool(
                    self.faiss_agent,
                    "Find similar spectra. Input: JSON with reference_spectra, query_spectrum, top_k.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            postgresql_agent = Agent(
                role="Relational Database Operator",
                goal="Manage metadata and relational storage in PostgreSQL",
                backstory=(
                    "You operate the platform PostgreSQL database: health checks, "
                    "metadata queries and inserts for the relational storage layer."
                ),
                tools=[self._agent_tool(
                    self.postgresql_agent,
                    "Operate PostgreSQL. Input: JSON with operation (health|query|insert), sql, params.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            django_agent = Agent(
                role="Platform Application Operator",
                goal="Operate the Django UI, backend APIs and user management",
                backstory=(
                    "You operate the Django web application of the platform: health "
                    "checks, endpoint probing and API operations for users and data."
                ),
                tools=[self._agent_tool(
                    self.django_agent,
                    "Operate the Django app. Input: JSON with operation (health|endpoints), base_url.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            mcp_agent = Agent(
                role="Tool Integration and Interface Operator",
                goal="Handle tool integration and external interfaces of the platform",
                backstory=(
                    "You are the MCP integration specialist: you probe and integrate "
                    "the platform tools (Qdrant, FAISS, Ollama, ILIAS, Django) and report "
                    "which interfaces are operational."
                ),
                tools=[self._agent_tool(
                    self.mcp_agent,
                    "Operate platform interfaces and tool integration. Input: JSON with "
                    "operation (status|interfaces|ingest), tools, file_path (for ingest).")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            ilias_agent = Agent(
                role="E-Learning Platform Operator",
                goal="Synchronize NIR learning paths and courses to ILIAS",
                backstory=(
                    "You operate the ILIAS e-learning integration: status checks, course "
                    "listings and learning path synchronization for NIR laboratory teaching."
                ),
                tools=[self._agent_tool(
                    self.ilias_agent,
                    "Operate ILIAS. Input: JSON with operation (status|list_courses|sync_learning_path).")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            reporting_agent = Agent(
                role="Scientific Report Generator",
                goal="Generate comprehensive Quarto reports from analysis results",
                backstory=(
                    "You are an expert in scientific report generation using Quarto. "
                    "Your expertise includes creating detailed analysis reports, "
                    "visualizing spectral data, and presenting complex results in "
                    "clear, professional formats suitable for scientific publication."
                ),
                tools=[self._agent_tool(
                    self.reporting_agent,
                    "Generate reports. Input: JSON with report_type, format, sample_id, data.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )
            quarto_agent = Agent(
                role="Documentation Specialist",
                goal="Produce complete documentation, diagrams and reports with Quarto",
                backstory=(
                    "You are the documentation specialist of the platform: you render "
                    "Quarto documents, diagrams and reports for analyses and workflows."
                ),
                tools=[self._agent_tool(
                    self.quarto_agent,
                    "Render Quarto documents. Input: JSON with operation (generate|preview), report_type, data.")],
                verbose=True,
                allow_delegation=False,
                llm=getattr(self, 'crewai_llm', None),
            )

            self.crewai_agents = [
                data_preparation_agent,
                spectral_agent,
                sensor_quality_agent,
                statistical_agent,
                neural_network_agent,
                metadata_agent,
                calibration_agent,
                qdrant_agent,
                faiss_agent,
                postgresql_agent,
                django_agent,
                mcp_agent,
                ilias_agent,
                reporting_agent,
                quarto_agent,
            ]
            if self.flower_agent is not None:
                flower_agent = Agent(
                    role="Federated Learning Coordinator",
                    goal="Coordinate federated learning rounds and aggregate models",
                    backstory=(
                        "You coordinate Flower federated learning: server/client mode, "
                        "training rounds and privacy-preserving model aggregation."
                    ),
                    tools=[self._agent_tool(
                        self.flower_agent,
                        "Operate federated learning. Input: JSON with operation (status|start_server|...).")],
                    verbose=True,
                    allow_delegation=False,
                )
                self.crewai_agents.append(flower_agent)

            # Create crew
            self.crew = Crew(agents=self.crewai_agents, tasks=[], process=Process.sequential, verbose=True)
            self.logger.info(
                f"CrewAI crew initialized with {len(self.crewai_agents)} agents (real tool bindings)")
        except Exception as e:
            self.logger.error(f"Error initializing CrewAI: {e}")
            self.crewai_agents = []
            self.crew = None
    def _extract_reference_values(self, metadata: Dict[str, Any]):
        """Extract numeric reference values (e.g. Brix) from metadata for
        supervised methods (PLS/PCR/MLP/CNN). Returns None when absent."""
        if not isinstance(metadata, dict):
            return None
        for key in ("reference_values", "brix", "reference", "y", "target"):
            if key in metadata:
                value = metadata[key]
                if isinstance(value, (list, tuple)):
                    return list(value)
                if isinstance(value, (int, float)):
                    return [value]
        return None

    @staticmethod
    def _json_safe(data: Any) -> Any:
        """Replace NaN/Infinity floats with None so results serialize to
        strict JSON for the web API and templates."""
        if isinstance(data, float):
            return data if math.isfinite(data) else None
        if isinstance(data, dict):
            return {key: NIRAnalysisCrew._json_safe(value) for key, value in data.items()}
        if isinstance(data, (list, tuple)):
            return [NIRAnalysisCrew._json_safe(item) for item in data]
        return data

    def _generate_request_id(self) -> str:
        """Generate unique request ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"nir_analysis_{timestamp}"

    def _validate_analysis_request(self, request: AnalysisRequest) -> Tuple[bool, List[str]]:
        """Validate analysis request"""
        errors = []

        if not request.sample_id:
            errors.append("Sample ID is required")

        if not request.spectral_data:
            errors.append("Spectral data is required")
        else:
            # Check required spectral data fields
            required_fields = ["wavelengths", "intensities"]
            for field in required_fields:
                if field not in request.spectral_data:
                    errors.append(f"Spectral data missing required field: {field}")

        # Check privacy level consistency
        if request.include_federated_learning and request.privacy_level == PrivacyLevel.LOCAL_ONLY:
            errors.append("Cannot include federated learning with LOCAL_ONLY privacy level")

        return len(errors) == 0, errors

    def _calculate_overall_quality(
        self, spectral_result: Optional[SpectralAnalysisResult], metadata_result: Optional[MetadataQualityResult]
    ) -> float:
        """Calculate overall quality score from spectral and metadata results"""
        if not spectral_result and not metadata_result:
            return 0.0

        scores = []
        weights = []

        if spectral_result:
            scores.append(spectral_result.quality_score)
            weights.append(0.6)  # Spectral quality has higher weight

        if metadata_result:
            scores.append(metadata_result.overall_quality_score)
            weights.append(0.4)  # Metadata quality weight

        if not scores:
            return 0.0

        # Normalize weights
        total_weight = sum(weights)
        normalized_weights = [w / total_weight for w in weights]

        # Calculate weighted average
        overall_score = sum(score * weight for score, weight in zip(scores, normalized_weights))

        return overall_score

    def _compile_recommendations(
        self,
        spectral_result: Optional[SpectralAnalysisResult],
        metadata_result: Optional[MetadataQualityResult],
        calibration_results: Optional[Dict[str, Any]] = None,
    ) -> List[str]:
        """Compile all recommendations from analysis results"""
        recommendations = []

        if spectral_result:
            # Add spectral recommendations
            recommendations.extend(spectral_result.recommendations)

            # Add parameter recommendations
            if hasattr(spectral_result, "parameter_recommendations"):
                for rec in spectral_result.parameter_recommendations:
                    if isinstance(rec, dict):
                        recommendations.append(f"{rec.get('reason', '')}: {rec.get('recommended_value', '')}")

        if metadata_result:
            # Add metadata recommendations
            recommendations.extend(metadata_result.recommendations)
            recommendations.extend(metadata_result.enhancements)

        if calibration_results:
            # Add calibration recommendations
            if "parameter_recommendations" in calibration_results:
                for rec in calibration_results["parameter_recommendations"]:
                    recommendations.append(f"Calibration: {rec}")

        return recommendations

    def analyze_sample(self, request: AnalysisRequest) -> AnalysisResult:
        """
        Perform complete analysis on a single sample.

        This is the main entry point for spectral analysis.
        """
        import time

        start_time = time.time()
        request_id = self._generate_request_id()
        self.current_request_id = request_id

        # Initialize result
        result = AnalysisResult(
            request_id=request_id,
            sample_id=request.sample_id,
            timestamp=datetime.now().isoformat(),
            privacy_level=request.privacy_level,
            user_id=request.user_id,
        )

        try:
            # Validate request
            is_valid, validation_errors = self._validate_analysis_request(request)
            if not is_valid:
                result.errors.extend(validation_errors)
                result.overall_quality_score = 0.0
                result.processing_time = time.time() - start_time
                return result

            self.logger.info(f"Starting analysis for sample: {request.sample_id} (Request: {request_id})")

            # Step 1: Spectral Analysis
            self.logger.info("Performing spectral analysis...")
            spectral_context = {
                "spectral_data": {
                    **request.spectral_data,
                    "sample_id": request.sample_id,
                },
                "sample_id": request.sample_id,
                "metadata": request.metadata,
            }

            spectral_output = self.spectral_agent.execute(spectral_context)
            if spectral_output.status == AgentStatus.COMPLETED:
                spectral_data = spectral_output.data
                result.spectral_analysis = SpectralAnalysisResult(**spectral_data.get("spectral_analysis", {}))
                self.logger.info(
                    f"Spectral analysis completed - Quality: {result.spectral_analysis.quality_grade.value}"
                )
            else:
                result.errors.append("Spectral analysis failed")
                self.logger.error("Spectral analysis failed")

            # Step 2: Metadata Quality Assessment
            self.logger.info("Performing metadata quality assessment...")
            metadata = dict(request.metadata or {})
            metadata.setdefault("sample_id", request.sample_id)
            if "instrument_type" not in metadata and metadata.get("instrument"):
                metadata["instrument_type"] = metadata["instrument"]
            if "measurement_date" not in metadata:
                for date_field in ("acquisition_time", "date_created", "created_at"):
                    if metadata.get(date_field):
                        metadata["measurement_date"] = metadata[date_field]
                        break
            metadata_context = {
                "metadata": metadata,
                "sample_id": request.sample_id,
                "file_paths": request.file_paths,
            }

            metadata_output = self.metadata_agent.execute(metadata_context)
            if metadata_output.status == AgentStatus.COMPLETED:
                metadata_data = metadata_output.data
                result.metadata_quality = MetadataQualityResult(**metadata_data.get("metadata_quality_result", {}))
                self.logger.info(
                    f"Metadata assessment completed - Quality: {result.metadata_quality.overall_quality_grade.value}"
                )
            else:
                result.warnings.append("Metadata quality assessment failed")
                self.logger.warning("Metadata quality assessment failed")

            # Step 2b: Sensor Quality, Statistical Analysis and Neural Network
            # analysis. The statistical and neural network agents run in
            # parallel per the mission statement rule (MO 7). Reference
            # values from the metadata allow PLS/PCR/MLP calibration targets.
            # Supervised models (MLP/CNN, PLS/PCR) need varying targets:
            # prefer the file-wide calibration samples (one reference value
            # per measured object, e.g. Brix) over the replica block (one
            # object, constant target). The sensor agent keeps the replicas.
            calibration_samples = request.metadata.get("calibration_samples") or []
            parallel_context = {
                "spectra": (request.metadata.get("measurement_samples")
                            or request.spectral_data),
                "reference_values": self._extract_reference_values(request.metadata),
            }
            supervised_context = {
                "spectra": (calibration_samples
                            or request.metadata.get("measurement_samples")
                            or request.spectral_data),
                "reference_values": self._extract_reference_values(request.metadata),
            }
            sensor_output = self.sensor_quality_agent.execute(
                {**parallel_context, "sample_id": request.sample_id}
            )

            sensor_output = self.sensor_quality_agent.execute(
                {**parallel_context, "sample_id": request.sample_id}
            )
            if sensor_output.status == AgentStatus.COMPLETED:
                result.sensor_quality_results = self._json_safe(sensor_output.data)
                for warning in sensor_output.data.get("warnings", []):
                    result.warnings.append(f"Sensor quality: {warning}")
                self.logger.info("Sensor quality assessment completed")
            else:
                result.warnings.append("Sensor quality assessment failed")
                self.logger.warning("Sensor quality assessment failed")

            statistical_output = self.statistical_analysis_agent.execute(
                {**supervised_context, "sample_id": request.sample_id}
            )
            if statistical_output.status == AgentStatus.COMPLETED:
                result.statistical_analysis_results = self._json_safe(statistical_output.data)
                self.logger.info("Statistical analysis completed")
            else:
                result.warnings.append("Statistical analysis failed")
                self.logger.warning("Statistical analysis failed")

            neural_output = self.neural_network_agent.execute(
                {**supervised_context, "sample_id": request.sample_id}
            )
            if neural_output.status == AgentStatus.COMPLETED:
                result.neural_network_results = self._json_safe(neural_output.data)
                self.logger.info("Neural network analysis completed")
            else:
                result.warnings.append("Neural network analysis failed")
                self.logger.warning("Neural network analysis failed")

            # Step 3: Calibration (if requested)
            if request.include_calibration:
                self.logger.info("Performing calibration analysis...")
                calibration_context = {
                    "spectral_data": request.spectral_data,
                    "sample_id": request.sample_id,
                    "metadata": request.metadata,
                }

                calibration_output = self.calibration_agent.execute(calibration_context)
                if calibration_output.status == AgentStatus.COMPLETED:
                    result.calibration_results = calibration_output.data
                    self.logger.info("Calibration analysis completed")
                else:
                    result.warnings.append("Calibration analysis failed")
                    self.logger.warning("Calibration analysis failed")

            # Step 4: Generate Reports
            self.logger.info("Generating reports...")

            # Prepare report data - convert results to dictionaries for JSON serialization
            spectral_analysis_dict = {}
            if spectral_output.status == AgentStatus.COMPLETED and spectral_output.data.get("spectral_analysis"):
                spectral_analysis_result = spectral_output.data["spectral_analysis"]
                # Convert SpectralAnalysisResult to dict, handling enum values
                if isinstance(spectral_analysis_result, dict):
                    spectral_analysis_dict = spectral_analysis_result.copy()
                    # Convert enum values to strings
                    if "quality_grade" in spectral_analysis_dict and hasattr(
                        spectral_analysis_dict["quality_grade"], "value"
                    ):
                        spectral_analysis_dict["quality_grade"] = spectral_analysis_dict["quality_grade"].value
                    if "issues_detected" in spectral_analysis_dict:
                        spectral_analysis_dict["issues_detected"] = [
                            issue.value if hasattr(issue, "value") else str(issue)
                            for issue in spectral_analysis_dict["issues_detected"]
                        ]
                else:
                    # If it's already a SpectralAnalysisResult object
                    spectral_analysis_dict = {
                        k: v.value if hasattr(v, "value") else v for k, v in spectral_analysis_result.__dict__.items()
                    }
                    if "issues_detected" in spectral_analysis_dict:
                        spectral_analysis_dict["issues_detected"] = [
                            issue.value if hasattr(issue, "value") else str(issue)
                            for issue in spectral_analysis_dict["issues_detected"]
                        ]

            metadata_quality_dict = {}
            if metadata_output.status == AgentStatus.COMPLETED and metadata_output.data.get("metadata_quality_result"):
                metadata_quality_result = metadata_output.data["metadata_quality_result"]
                # Convert MetadataQualityResult to dict, handling enum values
                if isinstance(metadata_quality_result, dict):
                    metadata_quality_dict = metadata_quality_result.copy()
                    # Convert enum values to strings
                    if "overall_quality_grade" in metadata_quality_dict and hasattr(
                        metadata_quality_dict["overall_quality_grade"], "value"
                    ):
                        metadata_quality_dict["overall_quality_grade"] = metadata_quality_dict[
                            "overall_quality_grade"
                        ].value
                    if "fields_assessed" in metadata_quality_dict:
                        # Convert MetadataField objects to dicts
                        fields_list = []
                        for field in metadata_quality_dict["fields_assessed"]:
                            if hasattr(field, "__dict__"):
                                field_dict = field.__dict__.copy()
                                if "category" in field_dict and hasattr(field_dict["category"], "value"):
                                    field_dict["category"] = field_dict["category"].value
                                fields_list.append(field_dict)
                            else:
                                fields_list.append(field)
                        metadata_quality_dict["fields_assessed"] = fields_list
                else:
                    # If it's already a MetadataQualityResult object
                    metadata_quality_dict = {
                        k: v.value if hasattr(v, "value") else v for k, v in metadata_quality_result.__dict__.items()
                    }

            report_data = {
                "spectral_analysis": spectral_analysis_dict,
                "metadata_quality_result": metadata_quality_dict,
                "processed_data": (
                    spectral_output.data.get("processed_data", {})
                    if spectral_output.status == AgentStatus.COMPLETED
                    else {}
                ),
                "calibration_results": result.calibration_results or {},
                "sensor_quality_results": result.sensor_quality_results or {},
                "statistical_analysis_results": result.statistical_analysis_results or {},
                "neural_network_results": result.neural_network_results or {},
            }

            # Generate main report
            report_context = {
                "report_type": request.report_type.value,
                "format": request.report_format.value,
                "sample_id": request.sample_id,
                "data": {
                    **report_data,
                    "analysis_mode": request.analysis_mode.value,
                    "privacy_level": request.privacy_level.value,
                    "include_calibration": request.include_calibration,
                },
            }

            report_output = self.reporting_agent.execute(report_context)
            if report_output.status == AgentStatus.COMPLETED:
                report_data = report_output.data
                if "report" in report_data:
                    generated_report = GeneratedReport(**report_data["report"])
                    result.generated_reports.append(generated_report)
                    self.logger.info(f"Report generated: {generated_report.file_path}")
            else:
                result.warnings.append("Report generation failed")
                self.logger.warning("Report generation failed")

            # Step 5: Federated Learning (if requested and privacy allows)
            if (
                request.include_federated_learning
                and request.privacy_level != PrivacyLevel.LOCAL_ONLY
                and self.config.enable_federated_learning
                and self.flower_agent
            ):

                self.logger.info("Processing federated learning...")
                fl_context = {
                    "spectral_data": request.spectral_data,
                    "metadata": request.metadata,
                    "analysis_results": {
                        "spectral_analysis": result.spectral_analysis.__dict__ if result.spectral_analysis else {},
                        "metadata_quality": result.metadata_quality.__dict__ if result.metadata_quality else {},
                    },
                    "user_id": request.user_id,
                    "sample_id": request.sample_id,
                    "privacy_level": request.privacy_level.value,
                }

                fl_output = self.flower_agent.execute(fl_context)
                if fl_output.status == AgentStatus.COMPLETED:
                    result.federated_learning_results = fl_output.data
                    self.logger.info("Federated learning processing completed")
                else:
                    result.warnings.append("Federated learning processing failed")
                    self.logger.warning("Federated learning processing failed")

            # Calculate overall quality score
            result.overall_quality_score = self._calculate_overall_quality(
                result.spectral_analysis, result.metadata_quality
            )

            # Compile recommendations
            result.recommendations = self._compile_recommendations(
                result.spectral_analysis, result.metadata_quality, result.calibration_results
            )

            # Add warnings from individual agents
            if spectral_output.status == AgentStatus.COMPLETED:
                spectral_data = spectral_output.data
                if "validation_warnings" in spectral_data:
                    result.warnings.extend(spectral_data["validation_warnings"])

            if metadata_output.status == AgentStatus.COMPLETED:
                metadata_data = metadata_output.data
                if "validation_errors" in metadata_data:
                    result.warnings.extend(metadata_data["validation_errors"])

            result.processing_time = time.time() - start_time

            # Log completion
            self.logger.info(f"Analysis completed for sample: {request.sample_id}")
            self.logger.info(
                f"  - Spectral quality: {result.spectral_analysis.quality_grade.value if result.spectral_analysis else 'N/A'}"
            )
            self.logger.info(
                f"  - Metadata quality: {result.metadata_quality.overall_quality_grade.value if result.metadata_quality else 'N/A'}"
            )
            self.logger.info(f"  - Overall quality: {result.overall_quality_score:.1f}")
            self.logger.info(f"  - Processing time: {result.processing_time:.2f}s")
            self.logger.info(f"  - Reports generated: {len(result.generated_reports)}")

            # Add to history
            self.analysis_history.append(result)

            return result

        except Exception as e:
            self.logger.error(f"Error during analysis: {e}")
            result.errors.append(f"Analysis failed: {str(e)}")
            result.processing_time = time.time() - start_time
            return result

    def analyze_batch(self, requests: List[AnalysisRequest]) -> List[AnalysisResult]:
        """
        Perform batch analysis on multiple samples.
        """
        results = []

        if len(requests) > self.config.max_batch_size:
            self.logger.warning(f"Batch size {len(requests)} exceeds maximum {self.config.max_batch_size}")
            # Split into chunks
            chunks = [
                requests[i : i + self.config.max_batch_size]
                for i in range(0, len(requests), self.config.max_batch_size)
            ]

            for chunk in chunks:
                chunk_results = self.analyze_batch(chunk)
                results.extend(chunk_results)

            return results

        self.logger.info(f"Starting batch analysis of {len(requests)} samples")

        for i, request in enumerate(requests):
            self.logger.info(f"Processing sample {i+1}/{len(requests)}: {request.sample_id}")
            result = self.analyze_sample(request)
            results.append(result)

        self.logger.info(f"Batch analysis completed. Success: {sum(1 for r in results if not r.errors)}/{len(results)}")

        return results

    def generate_comprehensive_report(self, analysis_result: AnalysisResult) -> Optional[GeneratedReport]:
        """
        Generate a comprehensive report from analysis results.
        """
        try:
            # Prepare data for comprehensive report
            report_data = {
                "spectral_analysis": (
                    analysis_result.spectral_analysis.__dict__ if analysis_result.spectral_analysis else {}
                ),
                "metadata_quality_result": (
                    analysis_result.metadata_quality.__dict__ if analysis_result.metadata_quality else {}
                ),
                "processed_data": (
                    analysis_result.spectral_analysis.processed_data if analysis_result.spectral_analysis else {}
                ),
                "calibration_results": analysis_result.calibration_results or {},
                "overall_quality_score": analysis_result.overall_quality_score,
                "recommendations": analysis_result.recommendations,
                "warnings": analysis_result.warnings,
                "errors": analysis_result.errors,
            }

            # Generate report
            report_context = {
                "report_type": ReportType.COMPREHENSIVE.value,
                "format": ReportFormat.HTML.value,
                "sample_id": analysis_result.sample_id,
                "data": report_data,
            }

            report_output = self.reporting_agent.execute(report_context)

            if report_output.status == AgentStatus.COMPLETED:
                report_data = report_output.data
                if "report" in report_data:
                    return GeneratedReport(**report_data["report"])

            return None

        except Exception as e:
            self.logger.error(f"Error generating comprehensive report: {e}")
            return None

    def get_analysis_summary(self, analysis_result: AnalysisResult) -> Dict[str, Any]:
        """
        Get a summary of analysis results suitable for API responses.
        """
        summary = NIRAnalysisCrew._sanitize_summary_floats({
            "request_id": analysis_result.request_id,
            "sample_id": analysis_result.sample_id,
            "timestamp": analysis_result.timestamp,
            "overall_quality_score": analysis_result.overall_quality_score,
            "processing_time": analysis_result.processing_time,
            "privacy_level": analysis_result.privacy_level.value,
            "user_id": analysis_result.user_id,
            "spectral_analysis": (
                {
                    "quality_score": (
                        analysis_result.spectral_analysis.quality_score if analysis_result.spectral_analysis else 0
                    ),
                    "quality_grade": (
                        analysis_result.spectral_analysis.quality_grade.value
                        if analysis_result.spectral_analysis
                        else "N/A"
                    ),
                    "wavelength_range": (
                        list(analysis_result.spectral_analysis.wavelength_range)
                        if analysis_result.spectral_analysis
                        else [0, 0]
                    ),
                    "data_points": (
                        analysis_result.spectral_analysis.data_points if analysis_result.spectral_analysis else 0
                    ),
                    "issues_detected": (
                        [issue.value for issue in analysis_result.spectral_analysis.issues_detected]
                        if analysis_result.spectral_analysis
                        else []
                    ),
                }
                if analysis_result.spectral_analysis
                else {}
            ),
            "metadata_quality": (
                {
                    "overall_score": (
                        analysis_result.metadata_quality.overall_quality_score
                        if analysis_result.metadata_quality
                        else 0
                    ),
                    "grade": (
                        analysis_result.metadata_quality.overall_quality_grade.value
                        if analysis_result.metadata_quality
                        else "N/A"
                    ),
                    "completeness": (
                        analysis_result.metadata_quality.completeness_score if analysis_result.metadata_quality else 0
                    ),
                    "accuracy": (
                        analysis_result.metadata_quality.accuracy_score if analysis_result.metadata_quality else 0
                    ),
                    "consistency": (
                        analysis_result.metadata_quality.consistency_score if analysis_result.metadata_quality else 0
                    ),
                    "missing_required_fields": (
                        analysis_result.metadata_quality.missing_required_fields
                        if analysis_result.metadata_quality
                        else []
                    ),
                }
                if analysis_result.metadata_quality
                else {}
            ),
            "sensor_quality": analysis_result.sensor_quality_results or {},
            "statistical_analysis": analysis_result.statistical_analysis_results or {},
            "neural_network": analysis_result.neural_network_results or {},
            "recommendations": analysis_result.recommendations,
            "warnings": analysis_result.warnings,
            "errors": analysis_result.errors,
            "reports": [
                {
                    "report_id": report.report_id,
                    "report_type": report.report_type.value,
                    "format": report.format.value,
                    "status": report.status.value,
                    "file_path": report.file_path,
                    "file_size": report.file_size,
                    "preview_available": report.preview_available,
                }
                for report in analysis_result.generated_reports
            ],
        })
        return summary

    @staticmethod
    def _sanitize_summary_floats(summary: Dict[str, Any]) -> Dict[str, Any]:
        """Ensure the summary payload is strict-JSON safe.

        Non-finite floats (NaN/Infinity) are replaced with None so DRF can
        always serialize the response and the browser can always parse it.
        """
        return NIRAnalysisCrew._json_safe(summary)

    def cleanup_resources(self, max_age_days: int = 30) -> Dict[str, int]:
        """
        Clean up old analysis resources.
        """
        cleanup_results = {}

        # Clean up old reports
        reports_cleaned = self.reporting_agent.cleanup_old_reports(max_age_days)
        cleanup_results["reports_cleaned"] = reports_cleaned

        # Clean up analysis history
        if self.analysis_history:
            cutoff_time = datetime.now().timestamp() - (max_age_days * 24 * 60 * 60)
            old_results = [
                r for r in self.analysis_history if datetime.fromisoformat(r.timestamp).timestamp() < cutoff_time
            ]

            if old_results:
                self.analysis_history = [r for r in self.analysis_history if r not in old_results]
                cleanup_results["analysis_history_cleaned"] = len(old_results)

        return cleanup_results

    def get_analysis_history(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Get analysis history summary.
        """
        history = []

        for result in self.analysis_history[-limit:]:
            history.append(
                {
                    "request_id": result.request_id,
                    "sample_id": result.sample_id,
                    "timestamp": result.timestamp,
                    "overall_quality_score": result.overall_quality_score,
                    "processing_time": result.processing_time,
                    "privacy_level": result.privacy_level.value,
                    "reports_generated": len(result.generated_reports),
                    "reports": [
                        {
                            "report_id": report.report_id,
                            "report_type": report.report_type.value,
                            "format": report.format.value,
                            "file_path": report.file_path,
                            "status": report.status.value,
                            "preview_available": report.preview_available,
                        }
                        for report in result.generated_reports
                    ],
                    "errors": len(result.errors),
                    "warnings": len(result.warnings),
                    "sensor_quality_status": (
                        (result.sensor_quality_results or {}).get("status")
                        if result.sensor_quality_results else None
                    ),
                    "statistical_methods_applied": (
                        (result.statistical_analysis_results or {}).get("methods_applied")
                        if result.statistical_analysis_results else None
                    ),
                    "neural_models_trained": (
                        (result.neural_network_results or {}).get("models_trained")
                        if result.neural_network_results else None
                    ),
                }
            )

        return history

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """
        Execute analysis based on context.

        This method allows the crew to be used as a standard agent.
        """
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting NIR Analysis Crew execution")

            # Extract request from context
            request_data = context.get("request", {})

            # Create analysis request
            request = AnalysisRequest(
                sample_id=request_data.get("sample_id", "unknown"),
                spectral_data=request_data.get("spectral_data", {}),
                metadata=request_data.get("metadata", {}),
                file_paths=request_data.get("file_paths", []),
                analysis_mode=AnalysisMode(request_data.get("analysis_mode", "standard")),
                privacy_level=PrivacyLevel(request_data.get("privacy_level", "local_only")),
                report_type=ReportType(request_data.get("report_type", "comprehensive")),
                report_format=ReportFormat(request_data.get("report_format", "html")),
                include_calibration=request_data.get("include_calibration", True),
                include_federated_learning=request_data.get("include_federated_learning", False),
                user_id=request_data.get("user_id", None),
            )

            # Perform analysis
            analysis_result = self.analyze_sample(request)

            # Generate summary
            summary = self.get_analysis_summary(analysis_result)

            # Prepare output
            output_data = {
                "analysis_result": analysis_result.__dict__,
                "summary": summary,
                "success": len(analysis_result.errors) == 0,
                "request_id": analysis_result.request_id,
                "sample_id": analysis_result.sample_id,
            }

            self.status = AgentStatus.COMPLETED
            self.logger.info(f"NIR Analysis Crew execution completed: {analysis_result.request_id}")

            return self._create_success_output(output_data)

        except Exception as e:
            return self._handle_error(e)

    def _create_success_output(self, data: Dict[str, Any] = None) -> AgentOutput:
        """Create a successful AgentOutput"""
        return AgentOutput(
            agent_name=self.__class__.__name__,
            status=AgentStatus.COMPLETED,
            data=data or {},
            version="1.0.0",
            dependencies=["spectral_analysis", "metadata_quality", "reporting"],
        )

    def _handle_error(self, exception: Exception) -> AgentOutput:
        """Handle exceptions and return appropriate AgentOutput"""
        error = {
            "agent_name": self.__class__.__name__,
            "message": f"Execution failed: {str(exception)}",
            "severity": ErrorSeverity.HIGH,
            "details": {"exception_type": type(exception).__name__},
            "suggested_fix": "Check analysis configuration and input data",
        }

        return AgentOutput(
            agent_name=self.__class__.__name__,
            status=AgentStatus.ERROR,
            errors=[error],
            version="1.0.0",
            dependencies=["spectral_analysis", "metadata_quality", "reporting"],
        )


# Global instance
nir_analysis_crew = NIRAnalysisCrew()


def analyze_spectral_data(
    sample_id: str,
    spectral_data: Dict[str, Any],
    metadata: Dict[str, Any] = None,
    file_paths: List[str] = None,
    analysis_mode: str = "standard",
    privacy_level: str = "local_only",
    report_type: str = "comprehensive",
    report_format: str = "html",
    include_calibration: bool = True,
    include_federated_learning: bool = False,
    user_id: str = None,
) -> AnalysisResult:
    """
    Convenience function to analyze spectral data.

    Args:
        sample_id: Unique identifier for the sample
        spectral_data: Dictionary containing spectral data (wavelengths, intensities)
        metadata: Dictionary containing metadata
        file_paths: List of file paths to extract additional metadata from
        analysis_mode: Analysis mode (standard, comprehensive, quick, batch)
        privacy_level: Privacy level (local_only, public_federated, private_federated)
        report_type: Type of report to generate
        report_format: Format of report (html, pdf, docx, md, qmd)
        include_calibration: Whether to include calibration analysis
        include_federated_learning: Whether to include federated learning
        user_id: User identifier for federated learning

    Returns:
        AnalysisResult containing complete analysis results
    """
    request = AnalysisRequest(
        sample_id=sample_id,
        spectral_data=spectral_data,
        metadata=metadata or {},
        file_paths=file_paths or [],
        analysis_mode=AnalysisMode(analysis_mode),
        privacy_level=PrivacyLevel(privacy_level),
        report_type=ReportType(report_type),
        report_format=ReportFormat(report_format),
        include_calibration=include_calibration,
        include_federated_learning=include_federated_learning,
        user_id=user_id,
    )

    return nir_analysis_crew.analyze_sample(request)


def create_analysis_crew(config: CrewConfiguration = None) -> NIRAnalysisCrew:
    """
    Create a new NIR Analysis Crew instance with custom configuration.

    Args:
        config: Custom configuration for the crew

    Returns:
        Configured NIRAnalysisCrew instance
    """
    return NIRAnalysisCrew(config)


if __name__ == "__main__":
    # Example usage
    print("NIR Analysis Crew - Example Usage")
    print("=" * 50)

    # Create sample spectral data
    import numpy as np

    sample_wavelengths = list(range(700, 2500, 10))  # 700-2500 nm, 10 nm steps
    sample_intensities = [
        1000 + 500 * np.sin(i * 0.1) + np.random.normal(0, 50) for i in range(len(sample_wavelengths))
    ]

    spectral_data = {
        "sample_id": "test_sample_001",
        "wavelengths": sample_wavelengths,
        "intensities": sample_intensities,
        "measurement_date": "2026-08-05T10:00:00Z",
    }

    metadata = {
        "sample_id": "test_sample_001",
        "instrument_type": "DIY Spectrometer",
        "instrument_model": "NIR-Mistral v1.0",
        "wavelength_range": "700-2500",
        "spectral_resolution": "10",
        "measurement_date": "2026-08-05T10:00:00Z",
        "operator": "Test User",
        "location": "Laboratory",
        "sample_description": "Test sample for NIR analysis",
        "sample_preparation": "Standard preparation method",
    }

    # Perform analysis
    print("Performing spectral analysis...")
    result = analyze_spectral_data(
        sample_id="test_sample_001",
        spectral_data=spectral_data,
        metadata=metadata,
        analysis_mode="standard",
        privacy_level="local_only",
        report_type="comprehensive",
        report_format="html",
        include_calibration=True,
        include_federated_learning=False,
    )

    print(f"Analysis completed!")
    print(f"Request ID: {result.request_id}")
    print(f"Overall Quality Score: {result.overall_quality_score:.1f}")
    print(f"Spectral Quality: {result.spectral_analysis.quality_grade.value if result.spectral_analysis else 'N/A'}")
    print(
        f"Metadata Quality: {result.metadata_quality.overall_quality_grade.value if result.metadata_quality else 'N/A'}"
    )
    print(f"Processing Time: {result.processing_time:.2f}s")
    print(f"Reports Generated: {len(result.generated_reports)}")
    print(f"Recommendations: {len(result.recommendations)}")

    if result.errors:
        print(f"Errors: {result.errors}")
    if result.warnings:
        print(f"Warnings: {result.warnings}")

    # Show report file path
    if result.generated_reports:
        for report in result.generated_reports:
            print(f"Report: {report.file_path}")
