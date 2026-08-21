# NIR Intelligence Platform - Workflow Orchestrator
# Comprehensive workflow management for automated spectral analysis and Quarto report generation

import os
import json
import tempfile
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from enum import Enum

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity
from .data_preparation_agent import EnhancedDataPreparationAgent
from .nir_analysis_crew import NIRAnalysisCrew, AnalysisRequest, AnalysisResult, AnalysisMode, PrivacyLevel
from .quarto_agent import QuartoAgent, ReportType, OutputFormat
from .reporting_agent import ReportingAgent, ReportFormat


class WorkflowStatus(Enum):
    """Status of the workflow execution"""
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class WorkflowType(Enum):
    """Types of workflows available"""
    STANDARD_ANALYSIS = "standard_analysis"
    COMPREHENSIVE_ANALYSIS = "comprehensive_analysis"
    METADATA_ONLY = "metadata_only"
    BATCH_PROCESSING = "batch_processing"
    QUICK_ANALYSIS = "quick_analysis"


@dataclass
class WorkflowResult:
    """Result of a workflow execution"""
    workflow_id: str
    workflow_type: WorkflowType
    status: WorkflowStatus
    start_time: str
    end_time: Optional[str] = None
    analysis_results: List[AnalysisResult] = field(default_factory=list)
    generated_reports: List[Dict[str, Any]] = field(default_factory=list)
    quarto_files: List[str] = field(default_factory=list)
    html_files: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    processing_time: float = 0.0
    input_files: List[str] = field(default_factory=list)
    output_directory: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)


class WorkflowOrchestrator(BaseAgent):
    """
    Main orchestrator for the complete NIR Intelligence workflow.
    
    This class coordinates:
    1. Data preparation and file handling
    2. Spectral analysis
    3. Metadata quality assessment
    4. Quarto report generation
    5. HTML rendering for Django integration
    """

    def __init__(self, **kwargs):
        super().__init__(name="WorkflowOrchestrator", version="1.0.0", **kwargs)
        
        # Configuration
        self.input_directory = kwargs.get("input_directory", "data/uploads")
        self.output_directory = kwargs.get("output_directory", "data/output")
        self.temp_directory = kwargs.get("temp_directory", "data/temp")
        self.report_directory = kwargs.get("report_directory", "reports")
        self.quarto_output_dir = kwargs.get("quarto_output_dir", "output/quarto")
        self.html_output_dir = kwargs.get("html_output_dir", "output/html")
        
        # Initialize agents
        self.data_prep_agent = EnhancedDataPreparationAgent(
            input_directory=self.input_directory,
            output_directory=self.output_directory,
            temp_directory=self.temp_directory
        )
        
        self.analysis_crew = NIRAnalysisCrew()
        self.quarto_agent = QuartoAgent(
            output_dir=self.quarto_output_dir,
            temp_dir=self.temp_directory
        )
        self.reporting_agent = ReportingAgent(
            output_dir=self.report_directory,
            temp_dir=self.temp_directory
        )
        
        # Workflow tracking
        self.workflow_history = []
        self.current_workflow_id = None
        
        # Initialize directories
        self._initialize_directories()
        
        self.logger.info("WorkflowOrchestrator initialized")

    def _initialize_directories(self) -> bool:
        """Initialize all required directories"""
        try:
            directories = [
                self.input_directory,
                self.output_directory,
                self.temp_directory,
                self.report_directory,
                self.quarto_output_dir,
                self.html_output_dir,
                os.path.join(self.output_directory, "processed"),
                os.path.join(self.output_directory, "metadata"),
                os.path.join(self.output_directory, "spectral_data"),
                os.path.join(self.temp_directory, "extracted"),
                os.path.join(self.temp_directory, "quarto_temp"),
            ]
            
            for directory in directories:
                os.makedirs(directory, exist_ok=True)
            
            self.logger.info("All directories initialized")
            return True
            
        except Exception as e:
            self.log_error(f"Failed to initialize directories: {str(e)}", ErrorSeverity.HIGH)
            return False

    def _generate_workflow_id(self) -> str:
        """Generate unique workflow ID"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
        return f"workflow_{timestamp}"

    def _check_quarto_available(self) -> bool:
        """Check if Quarto is available for report generation"""
        try:
            result = subprocess.run(
                ["quarto", "--version"],
                capture_output=True,
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def _render_quarto_to_html(self, quarto_file: str, output_dir: str = None) -> Optional[str]:
        """Render a Quarto file to HTML"""
        try:
            if not self._check_quarto_available():
                self.logger.warning("Quarto not available, skipping HTML rendering")
                return None
            
            output_dir = output_dir or self.html_output_dir
            os.makedirs(output_dir, exist_ok=True)
            
            # Generate output filename
            quarto_path = Path(quarto_file)
            output_file = Path(output_dir) / f"{quarto_path.stem}.html"
            
            # Render using Quarto CLI
            cmd = ["quarto", "render", str(quarto_file), "--to", "html", "--output", str(output_file)]
            
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=120,  # 2 minutes timeout
                cwd=quarto_path.parent
            )
            
            if result.returncode == 0:
                self.logger.info(f"Successfully rendered {quarto_file} to {output_file}")
                return str(output_file)
            else:
                self.logger.error(f"Failed to render Quarto file: {result.stderr}")
                return None
                
        except Exception as e:
            self.logger.error(f"Error rendering Quarto file: {str(e)}")
            return None

    def _create_analysis_request_from_files(self, file_paths: List[str], workflow_type: WorkflowType) -> List[AnalysisRequest]:
        """Create analysis requests from uploaded files"""
        requests = []
        
        for file_path in file_paths:
            try:
                # Load and prepare data using data preparation agent
                file_data = self.data_prep_agent.process_file(file_path)
                
                if file_data and file_data.get("status") == "success":
                    spectral_data = file_data.get("spectral_data", {})
                    metadata = file_data.get("metadata", {})
                    sample_id = file_data.get("sample_id", os.path.splitext(os.path.basename(file_path))[0])
                    
                    # Determine analysis mode based on workflow type
                    if workflow_type == WorkflowType.QUICK_ANALYSIS:
                        analysis_mode = AnalysisMode.QUICK
                    elif workflow_type == WorkflowType.COMPREHENSIVE_ANALYSIS:
                        analysis_mode = AnalysisMode.COMPREHENSIVE
                    else:
                        analysis_mode = AnalysisMode.STANDARD
                    
                    request = AnalysisRequest(
                        sample_id=sample_id,
                        spectral_data=spectral_data,
                        metadata=metadata,
                        file_paths=[file_path],
                        analysis_mode=analysis_mode,
                        privacy_level=PrivacyLevel.LOCAL_ONLY,
                        report_type=ReportType.COMPREHENSIVE,
                        report_format=ReportFormat.HTML,
                        include_calibration=True,
                        include_federated_learning=False
                    )
                    requests.append(request)
                    
            except Exception as e:
                self.logger.error(f"Failed to create analysis request for {file_path}: {str(e)}")
                continue
        
        return requests

    def _generate_quarto_report_from_analysis(self, analysis_result: AnalysisResult) -> Optional[Dict[str, Any]]:
        """Generate a comprehensive Quarto report from analysis results"""
        try:
            # Prepare data for Quarto report
            report_data = {
                "sample_id": analysis_result.sample_id,
                "request_id": analysis_result.request_id,
                "timestamp": analysis_result.timestamp,
                "overall_quality_score": analysis_result.overall_quality_score,
                "processing_time": analysis_result.processing_time,
                "recommendations": analysis_result.recommendations,
                "warnings": analysis_result.warnings,
                "errors": analysis_result.errors,
                "spectral_analysis": {},
                "metadata_quality": {},
                "calibration_results": analysis_result.calibration_results or {},
            }
            
            # Add spectral analysis data
            if analysis_result.spectral_analysis:
                spectral_data = analysis_result.spectral_analysis.__dict__
                # Convert enum values to strings
                report_data["spectral_analysis"] = {
                    k: v.value if hasattr(v, "value") else v 
                    for k, v in spectral_data.items()
                }
            
            # Add metadata quality data
            if analysis_result.metadata_quality:
                metadata_data = analysis_result.metadata_quality.__dict__
                report_data["metadata_quality"] = {
                    k: v.value if hasattr(v, "value") else v 
                    for k, v in metadata_data.items()
                }
            
            # Generate Quarto report
            quarto_context = {
                "report_type": ReportType.COMPREHENSIVE.value,
                "format": OutputFormat.HTML.value,
                "sample_id": analysis_result.sample_id,
                "data": report_data,
                "include_source_code": True,
                "include_visualizations": True,
                "include_analysis_results": True
            }
            
            quarto_output = self.quarto_agent.execute(quarto_context)
            
            if quarto_output.status == AgentStatus.COMPLETED:
                return quarto_output.data
            else:
                self.logger.error("Quarto report generation failed")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating Quarto report: {str(e)}")
            return None

    def execute_workflow(self, file_paths: List[str], workflow_type: WorkflowType = WorkflowType.STANDARD_ANALYSIS) -> WorkflowResult:
        """
        Execute the complete workflow from file upload to report generation.
        
        Args:
            file_paths: List of file paths to process
            workflow_type: Type of workflow to execute
            
        Returns:
            WorkflowResult containing all results and generated files
        """
        import time
        
        start_time = time.time()
        workflow_id = self._generate_workflow_id()
        self.current_workflow_id = workflow_id
        
        result = WorkflowResult(
            workflow_id=workflow_id,
            workflow_type=workflow_type,
            status=WorkflowStatus.PROCESSING,
            start_time=datetime.now().isoformat(),
            input_files=file_paths,
            output_directory=self.output_directory
        )
        
        try:
            self.logger.info(f"Starting workflow {workflow_id} with type {workflow_type.value}")
            self.logger.info(f"Processing {len(file_paths)} files: {file_paths}")
            
            # Step 1: Create analysis requests from files
            self.logger.info("Creating analysis requests from files...")
            analysis_requests = self._create_analysis_request_from_files(file_paths, workflow_type)
            
            if not analysis_requests:
                result.status = WorkflowStatus.FAILED
                result.errors.append("No valid analysis requests could be created from the provided files")
                result.end_time = datetime.now().isoformat()
                result.processing_time = time.time() - start_time
                return result
            
            self.logger.info(f"Created {len(analysis_requests)} analysis requests")
            
            # Step 2: Execute analysis (single or batch)
            self.logger.info("Executing spectral analysis...")
            if len(analysis_requests) == 1:
                # Single sample analysis
                analysis_result = self.analysis_crew.analyze_sample(analysis_requests[0])
                result.analysis_results.append(analysis_result)
            else:
                # Batch analysis
                analysis_results = self.analysis_crew.analyze_batch(analysis_requests)
                result.analysis_results.extend(analysis_results)
            
            self.logger.info(f"Analysis completed for {len(result.analysis_results)} samples")
            
            # Step 3: Generate Quarto reports for each analysis result
            self.logger.info("Generating Quarto reports...")
            for analysis_result in result.analysis_results:
                if not analysis_result.errors:  # Only generate reports for successful analyses
                    quarto_result = self._generate_quarto_report_from_analysis(analysis_result)
                    if quarto_result:
                        result.generated_reports.append(quarto_result)
                        
                        # Extract Quarto file path if available
                        if "quarto_file" in quarto_result:
                            result.quarto_files.append(quarto_result["quarto_file"])
                    
                    # Also generate HTML from Quarto files
                    for quarto_file in result.quarto_files:
                        html_file = self._render_quarto_to_html(quarto_file)
                        if html_file:
                            result.html_files.append(html_file)
            
            # Step 4: Generate comprehensive summary report
            self.logger.info("Generating summary report...")
            summary_report = self._generate_summary_report(result)
            if summary_report:
                result.generated_reports.append(summary_report)
            
            # Update workflow status
            result.status = WorkflowStatus.COMPLETED
            result.end_time = datetime.now().isoformat()
            result.processing_time = time.time() - start_time
            
            self.logger.info(f"Workflow {workflow_id} completed successfully")
            self.logger.info(f"  - Analysis results: {len(result.analysis_results)}")
            self.logger.info(f"  - Generated reports: {len(result.generated_reports)}")
            self.logger.info(f"  - Quarto files: {len(result.quarto_files)}")
            self.logger.info(f"  - HTML files: {len(result.html_files)}")
            self.logger.info(f"  - Processing time: {result.processing_time:.2f}s")
            
            # Add to history
            self.workflow_history.append(result)
            
            return result
            
        except Exception as e:
            self.logger.error(f"Workflow {workflow_id} failed: {str(e)}")
            result.status = WorkflowStatus.FAILED
            result.errors.append(f"Workflow execution failed: {str(e)}")
            result.end_time = datetime.now().isoformat()
            result.processing_time = time.time() - start_time
            return result

    def _generate_summary_report(self, workflow_result: WorkflowResult) -> Optional[Dict[str, Any]]:
        """Generate a summary report for the entire workflow"""
        try:
            # Prepare summary data
            summary_data = {
                "workflow_id": workflow_result.workflow_id,
                "workflow_type": workflow_result.workflow_type.value,
                "start_time": workflow_result.start_time,
                "end_time": workflow_result.end_time,
                "processing_time": workflow_result.processing_time,
                "total_samples": len(workflow_result.analysis_results),
                "successful_analyses": len([r for r in workflow_result.analysis_results if not r.errors]),
                "failed_analyses": len([r for r in workflow_result.analysis_results if r.errors]),
                "generated_reports": len(workflow_result.generated_reports),
                "quarto_files": workflow_result.quarto_files,
                "html_files": workflow_result.html_files,
                "input_files": workflow_result.input_files,
                "errors": workflow_result.errors,
                "warnings": workflow_result.warnings,
                "sample_results": []
            }
            
            # Add individual sample results
            for analysis_result in workflow_result.analysis_results:
                sample_result = {
                    "sample_id": analysis_result.sample_id,
                    "request_id": analysis_result.request_id,
                    "overall_quality_score": analysis_result.overall_quality_score,
                    "processing_time": analysis_result.processing_time,
                    "spectral_quality": (analysis_result.spectral_analysis.quality_grade.value 
                                       if analysis_result.spectral_analysis else "N/A"),
                    "metadata_quality": (analysis_result.metadata_quality.overall_quality_grade.value 
                                       if analysis_result.metadata_quality else "N/A"),
                    "recommendations_count": len(analysis_result.recommendations),
                    "warnings_count": len(analysis_result.warnings),
                    "errors_count": len(analysis_result.errors),
                    "reports_generated": len(analysis_result.generated_reports)
                }
                summary_data["sample_results"].append(sample_result)
            
            # Generate summary report using Quarto
            summary_context = {
                "report_type": ReportType.CUSTOM.value,
                "format": OutputFormat.HTML.value,
                "sample_id": f"summary_{workflow_result.workflow_id}",
                "data": summary_data,
                "template": "summary_report",
                "include_source_code": False,
                "include_visualizations": True
            }
            
            summary_output = self.quarto_agent.execute(summary_context)
            
            if summary_output.status == AgentStatus.COMPLETED:
                return summary_output.data
            else:
                self.logger.error("Summary report generation failed")
                return None
                
        except Exception as e:
            self.logger.error(f"Error generating summary report: {str(e)}")
            return None

    def execute_standard_workflow(self, file_paths: List[str]) -> WorkflowResult:
        """Execute the standard workflow (convenience method)"""
        return self.execute_workflow(file_paths, WorkflowType.STANDARD_ANALYSIS)

    def execute_comprehensive_workflow(self, file_paths: List[str]) -> WorkflowResult:
        """Execute the comprehensive workflow (convenience method)"""
        return self.execute_workflow(file_paths, WorkflowType.COMPREHENSIVE_ANALYSIS)

    def execute_quick_workflow(self, file_paths: List[str]) -> WorkflowResult:
        """Execute the quick workflow (convenience method)"""
        return self.execute_workflow(file_paths, WorkflowType.QUICK_ANALYSIS)

    def get_workflow_status(self, workflow_id: str) -> Optional[WorkflowResult]:
        """Get the status of a specific workflow"""
        for workflow in self.workflow_history:
            if workflow.workflow_id == workflow_id:
                return workflow
        return None

    def get_all_workflows(self) -> List[WorkflowResult]:
        """Get all workflow results"""
        return self.workflow_history

    def cleanup_workflow_files(self, workflow_id: str, keep_reports: bool = True) -> bool:
        """Clean up files associated with a workflow"""
        try:
            workflow = self.get_workflow_status(workflow_id)
            if not workflow:
                self.logger.warning(f"Workflow {workflow_id} not found")
                return False
            
            # Remove temporary files but keep reports if requested
            temp_files_to_remove = []
            
            # Add files from temp directory
            temp_dir = Path(self.temp_directory)
            if temp_dir.exists():
                for temp_file in temp_dir.rglob(f"*{workflow_id}*"):
                    if temp_file.is_file():
                        temp_files_to_remove.append(temp_file)
            
            # Remove files
            for file_path in temp_files_to_remove:
                try:
                    if not keep_reports or not any(
                        str(file_path) in report.get("file_path", "") 
                        for report in workflow.generated_reports
                    ):
                        file_path.unlink()
                        self.logger.info(f"Removed temporary file: {file_path}")
                except Exception as e:
                    self.logger.error(f"Failed to remove file {file_path}: {str(e)}")
            
            return True
            
        except Exception as e:
            self.logger.error(f"Error cleaning up workflow files: {str(e)}")
            return False