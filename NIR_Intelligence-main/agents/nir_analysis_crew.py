# NIR Intelligence Platform - NIR Analysis Crew
# Main CrewAI orchestration for complete NIR spectral analysis workflow

import logging
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
    from crewai import Agent, Crew, Process, Task
    from crewai.tools import tool

    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    print("Warning: CrewAI not available. NIR Analysis Crew will work in standalone mode.")

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity
from .calibration_agent import CalibrationAgent
from .flower_agent import FlowerAgent
from .metadata_quality_agent import MetadataQualityAgent, MetadataQualityResult
from .reporting_agent import GeneratedReport, ReportFormat, ReportingAgent, ReportType
from .spectral_analysis_agent import SpectralAnalysisAgent, SpectralAnalysisResult


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


class NIRAnalysisCrew:
    """
    Main CrewAI orchestration for NIR spectral analysis.

    This crew coordinates multiple agents to perform comprehensive analysis:
    1. Spectral Analysis Agent - Analyzes spectral data quality
    2. Metadata Quality Agent - Assesses metadata completeness and standards compliance
    3. Reporting Agent - Generates Quarto reports
    4. Calibration Agent - Handles spectrometer calibration
    5. Flower Agent - Manages federated learning (optional)
    """

    def __init__(self, config: Optional[CrewConfiguration] = None):
        self.config = config or CrewConfiguration()
        self.logger = logging.getLogger("NIRAnalysisCrew")

        # Initialize agents
        self.spectral_agent = SpectralAnalysisAgent()
        self.metadata_agent = MetadataQualityAgent()
        self.reporting_agent = ReportingAgent(
            output_dir=Path(self.config.output_dir) / "reports", temp_dir=Path(self.config.temp_dir)
        )
        self.calibration_agent = CalibrationAgent()
        self.flower_agent = FlowerAgent() if self.config.enable_federated_learning else None

        # CrewAI components (if available)
        self.crewai_agents = []
        self.crewai_tasks = []
        self.crew = None

        # Initialize CrewAI if available
        if CREWAI_AVAILABLE and self.config.enable_crewai:
            self._initialize_crewai()

        # Analysis tracking
        self.analysis_history = []
        self.current_request_id = None

        self.logger.info("NIRAnalysisCrew initialized")
        self.logger.info(f"CrewAI available: {CREWAI_AVAILABLE and self.config.enable_crewai}")
        self.logger.info(f"Federated learning enabled: {self.config.enable_federated_learning}")

    def _initialize_crewai(self):
        """Initialize CrewAI agents and crew"""
        try:
            # Create CrewAI agents
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
                tools=[],  # Tools will be added dynamically
                verbose=True,
                allow_delegation=False,
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
                tools=[],
                verbose=True,
                allow_delegation=False,
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
                tools=[],
                verbose=True,
                allow_delegation=False,
            )

            calibration_agent = Agent(
                role="Spectrometer Calibration Specialist",
                goal="Perform spectrometer calibration and optimization",
                backstory=(
                    "You are an expert in spectrometer calibration with knowledge of "
                    "various calibration methods (PLS, PCR, SVM, etc.). Your expertise includes "
                    "calibration curve generation, performance validation, and parameter optimization."
                ),
                tools=[],
                verbose=True,
                allow_delegation=False,
            )

            self.crewai_agents = [spectral_agent, metadata_agent, reporting_agent, calibration_agent]

            # Create crew
            self.crew = Crew(agents=self.crewai_agents, tasks=[], process=Process.sequential, verbose=True)

            self.logger.info("CrewAI agents and crew initialized successfully")

        except Exception as e:
            self.logger.error(f"Error initializing CrewAI: {e}")
            self.crewai_agents = []
            self.crew = None

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
                "spectral_data": request.spectral_data,
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
            metadata_context = {
                "metadata": request.metadata,
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
            }

            # Generate main report
            report_context = {
                "report_type": request.report_type.value,
                "format": request.report_format.value,
                "sample_id": request.sample_id,
                "data": report_data,
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
        summary = {
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
        }

        return summary

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
                    "errors": len(result.errors),
                    "warnings": len(result.warnings),
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
