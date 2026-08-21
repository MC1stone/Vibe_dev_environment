# NIR Intelligence Platform - Quarto Agent
# Comprehensive documentation and report generation with Quarto

import os
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Any, Dict, List, Optional, Union, Tuple
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class ReportType(Enum):
    """Types of reports that can be generated"""
    SPECTRAL_ANALYSIS = "spectral_analysis"
    METADATA_QUALITY = "metadata_quality"
    CALIBRATION = "calibration"
    COMPREHENSIVE = "comprehensive"
    COMPARISON = "comparison"
    CUSTOM = "custom"


class OutputFormat(Enum):
    """Output formats for Quarto reports"""
    HTML = "html"
    PDF = "pdf"
    WORD = "docx"
    MARKDOWN = "md"
    QUARTO = "qmd"


class TemplateType(Enum):
    """Template types for Quarto reports"""
    SCIENTIFIC = "scientific"
    TECHNICAL = "technical"
    BUSINESS = "business"
    EDUCATIONAL = "educational"
    MINIMAL = "minimal"


@dataclass
class ReportTemplate:
    """Template for Quarto report generation"""
    name: str
    template_path: str
    description: str
    required_fields: List[str] = field(default_factory=list)
    optional_fields: List[str] = field(default_factory=list)
    default_data: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GeneratedReport:
    """Information about a generated report"""
    report_id: str
    report_type: ReportType
    format: OutputFormat
    file_path: str
    creation_timestamp: str
    file_size: int = 0
    pages: int = 0
    charts_included: int = 0
    tables_included: int = 0
    status: str = "completed"
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class QuartoConfig:
    """Configuration for Quarto agent"""
    output_format: OutputFormat = OutputFormat.HTML
    include_source: bool = True
    include_charts: bool = True
    template: TemplateType = TemplateType.SCIENTIFIC
    output_dir: str = "output/reports"
    temp_dir: str = "temp/quarto"
    skip_if_unavailable: bool = False
    auto_open: bool = False
    compress_output: bool = False
    image_format: str = "png"
    image_dpi: int = 300
    code_folding: bool = True
    number_sections: bool = True
    toc: bool = True
    toc_depth: int = 3


class QuartoAgent(BaseAgent):
    """
    Enhanced agent for generating comprehensive documentation and reports using Quarto.
    
    Features:
    - Multiple report types and templates
    - Support for multiple output formats (HTML, PDF, Word, Markdown)
    - Automatic template management
    - Report generation with data visualization
    - Report preview and download functionality
    - Error handling and fallback mechanisms
    """

    # Available templates
    AVAILABLE_TEMPLATES = {
        ReportType.SPECTRAL_ANALYSIS: {
            "default": "spectral_analysis",
            "description": "Spectral analysis report with wavelength data and analysis results",
            "required_fields": ["spectral_data", "analysis_results"],
            "optional_fields": ["metadata", "calibration_data", "recommendations"],
        },
        ReportType.METADATA_QUALITY: {
            "default": "metadata_quality",
            "description": "Metadata quality assessment report",
            "required_fields": ["quality_metrics", "completeness_score"],
            "optional_fields": ["metadata_samples", "quality_issues", "recommendations"],
        },
        ReportType.CALIBRATION: {
            "default": "calibration",
            "description": "Calibration results and model performance report",
            "required_fields": ["calibration_results", "model_performance"],
            "optional_fields": ["calibration_methods", "validation_metrics", "recommendations"],
        },
        ReportType.COMPREHENSIVE: {
            "default": "comprehensive",
            "description": "Complete analysis report with all sections",
            "required_fields": ["spectral_analysis", "metadata_quality", "calibration"],
            "optional_fields": ["federated_learning", "comparisons", "recommendations"],
        },
        ReportType.COMPARISON: {
            "default": "comparison",
            "description": "Comparison report for multiple samples or methods",
            "required_fields": ["comparison_data", "metrics"],
            "optional_fields": ["visualizations", "statistical_tests", "conclusions"],
        },
    }

    def __init__(self, **kwargs):
        super().__init__(name="QuartoAgent", version="2.0.0", **kwargs)
        self.dependencies = ["quarto", "pandas", "matplotlib", "seaborn", "plotly"]
        
        # Configuration
        self.config = QuartoConfig(**kwargs.get("config", {}))
        
        # Runtime state
        self.quarto_available = self._check_quarto_installed()
        self.generated_reports: List[GeneratedReport] = []
        self.templates_dir = Path("templates/reports")
        self.output_dir = Path(self.config.output_dir)
        self.temp_dir = Path(self.config.temp_dir)
        
        # Setup directories
        self._setup_directories()
        
        # Load or create default templates
        self._setup_templates()
        
        self.logger.info(f"QuartoAgent initialized - Quarto available: {self.quarto_available}")
        self.logger.info(f"Output format: {self.config.output_format}")
        self.logger.info(f"Template: {self.config.template}")

    def _setup_directories(self):
        """Setup required directories"""
        try:
            directories = [
                self.templates_dir,
                self.output_dir,
                self.temp_dir,
            ]
            
            for directory in directories:
                directory.mkdir(parents=True, exist_ok=True)
                
        except Exception as e:
            self.logger.warning(f"Failed to setup directories: {e}")

    def _setup_templates(self):
        """Setup default templates if they don't exist"""
        try:
            # Create default templates for each report type
            for report_type, template_info in self.AVAILABLE_TEMPLATES.items():
                template_name = template_info["default"]
                template_path = self.templates_dir / f"{template_name}.qmd"
                
                if not template_path.exists():
                    self._create_default_template(report_type, template_path)
                    self.logger.info(f"Created default template: {template_name}")
                    
        except Exception as e:
            self.logger.warning(f"Failed to setup templates: {e}")

    def _create_default_template(self, report_type: ReportType, template_path: Path):
        """Create a default template for a report type"""
        template_content = self._generate_template_content(report_type)
        
        with open(template_path, 'w') as f:
            f.write(template_content)

    def _generate_template_content(self, report_type: ReportType) -> str:
        """Generate default template content for a report type"""
        template_name = self.AVAILABLE_TEMPLATES[report_type]["default"]
        
        # Basic template structure - pure Markdown to avoid R dependency
        template = f"""---
title: """ + "{{title}}" + """
author: """ + "{{author}}" + """
format: """ + "{{format}}" + """
date: """ + "{{date}}" + """
---

# {template_name.replace('_', ' ').title()}

## Summary

""" + "{{summary}}" + """

## Analysis Results

""" + "{{analysis_results}}" + """

## Visualizations

""" + "{{visualizations}}" + """

## Recommendations

""" + "{{recommendations}}" + """

---
{{< include _quarto.yml >}}
"""
        
        return template

    def _check_quarto_installed(self) -> bool:
        """Check if Quarto is installed and available with R support"""
        try:
            # Check Quarto version
            result = subprocess.run(
                ["quarto", "--version"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            if result.returncode != 0:
                self.logger.warning("Quarto not available")
                return False
            
            # Check if R is available (required for Quarto rendering)
            try:
                r_result = subprocess.run(
                    ["Rscript", "--version"], 
                    capture_output=True, 
                    text=True,
                    timeout=10
                )
                if r_result.returncode != 0:
                    self.logger.warning("Quarto available but R not available - using template rendering")
                    return False
            except Exception:
                self.logger.warning("Quarto available but R not available - using template rendering")
                return False
            
            version = result.stdout.strip()
            self.logger.info(f"Quarto version: {version}")
            return True
        except Exception as e:
            self.logger.warning(f"Quarto not available: {e}")
            return False

    def _check_pandoc_installed(self) -> bool:
        """Check if Pandoc is installed (required for some Quarto features)"""
        try:
            result = subprocess.run(
                ["pandoc", "--version"], 
                capture_output=True, 
                text=True,
                timeout=10
            )
            return result.returncode == 0
        except Exception:
            return False

    def get_available_templates(self) -> Dict[str, Dict[str, Any]]:
        """Get information about available templates"""
        templates = {}
        
        for template_path in self.templates_dir.glob("*.qmd"):
            template_name = template_path.stem
            templates[template_name] = {
                "path": str(template_path),
                "description": self.AVAILABLE_TEMPLATES.get(
                    ReportType(template_name), 
                    {"description": "Custom template"}
                ).get("description", "Custom template"),
                "required_fields": self.AVAILABLE_TEMPLATES.get(
                    ReportType(template_name), 
                    {"required_fields": []}
                ).get("required_fields", []),
                "optional_fields": self.AVAILABLE_TEMPLATES.get(
                    ReportType(template_name), 
                    {"optional_fields": []}
                ).get("optional_fields", []),
            }
        
        return templates

    def validate_report_data(self, report_type: ReportType, data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Validate data for a specific report type"""
        template_info = self.AVAILABLE_TEMPLATES.get(report_type, {})
        required_fields = template_info.get("required_fields", [])
        
        missing_fields = []
        for field in required_fields:
            if field not in data:
                missing_fields.append(field)
        
        return len(missing_fields) == 0, missing_fields

    def generate_report(
        self,
        report_type: ReportType,
        data: Dict[str, Any],
        format: OutputFormat = None,
        template: str = None,
        output_filename: str = None,
    ) -> GeneratedReport:
        """Generate a report using Quarto"""
        try:
            self.status = AgentStatus.PROCESSING
            
            # Use provided format or default
            output_format = format or self.config.output_format
            
            # Generate report ID
            report_id = f"{report_type.value}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            if output_filename:
                report_id = output_filename
            
            # Validate data
            is_valid, missing_fields = self.validate_report_data(report_type, data)
            if not is_valid:
                error_msg = f"Missing required fields: {missing_fields}"
                self.logger.warning(error_msg)
                return GeneratedReport(
                    report_id=report_id,
                    report_type=report_type,
                    format=output_format,
                    file_path="",
                    creation_timestamp=datetime.now().isoformat(),
                    status="failed",
                    error_message=error_msg,
                )
            
            # Prepare template data
            template_data = self._prepare_template_data(report_type, data)
            
            # Select template
            template_name = template or report_type.value
            template_path = self.templates_dir / f"{template_name}.qmd"
            
            if not template_path.exists():
                # Try default template
                template_name = self.AVAILABLE_TEMPLATES.get(report_type, {}).get("default", report_type.value)
                template_path = self.templates_dir / f"{template_name}.qmd"
            
            if not template_path.exists():
                error_msg = f"Template not found: {template_name}"
                self.logger.error(error_msg)
                return GeneratedReport(
                    report_id=report_id,
                    report_type=report_type,
                    format=output_format,
                    file_path="",
                    creation_timestamp=datetime.now().isoformat(),
                    status="failed",
                    error_message=error_msg,
                )
            
            # Generate the report
            if self.quarto_available:
                return self._generate_with_quarto(
                    report_id, report_type, template_path, template_data, output_format
                )
            else:
                return self._generate_with_template_rendering(
                    report_id, report_type, template_path, template_data, output_format
                )
                
        except Exception as e:
            self.logger.error(f"Failed to generate report: {e}")
            return GeneratedReport(
                report_id=f"{report_type.value}_error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                report_type=report_type,
                format=output_format or self.config.output_format,
                file_path="",
                creation_timestamp=datetime.now().isoformat(),
                status="failed",
                error_message=str(e),
            )

    def _prepare_template_data(self, report_type: ReportType, data: Dict[str, Any]) -> Dict[str, Any]:
        """Prepare data for template rendering"""
        # Add default values
        template_data = {
            "title": data.get("title", f"{report_type.value.replace('_', ' ').title()} Report"),
            "author": data.get("author", "NIR Intelligence Platform"),
            "date": data.get("date", datetime.now().strftime("%Y-%m-%d")),
            "format": self.config.output_format.value,
            "summary": data.get("summary", ""),
            "analysis_results": data.get("analysis_results", ""),
            "visualizations": data.get("visualizations", ""),
            "recommendations": data.get("recommendations", ""),
            "metadata": data.get("metadata", {}),
        }
        
        # Add report-specific data
        if report_type == ReportType.SPECTRAL_ANALYSIS:
            template_data.update({
                "spectral_data": data.get("spectral_data", {}),
                "wavelength_range": data.get("wavelength_range", ""),
                "signal_quality": data.get("signal_quality", {}),
                "noise_analysis": data.get("noise_analysis", {}),
            })
        
        elif report_type == ReportType.METADATA_QUALITY:
            template_data.update({
                "quality_metrics": data.get("quality_metrics", {}),
                "completeness_score": data.get("completeness_score", 0),
                "quality_issues": data.get("quality_issues", []),
            })
        
        elif report_type == ReportType.CALIBRATION:
            template_data.update({
                "calibration_results": data.get("calibration_results", {}),
                "model_performance": data.get("model_performance", {}),
                "calibration_methods": data.get("calibration_methods", []),
            })
        
        elif report_type == ReportType.COMPREHENSIVE:
            template_data.update({
                "spectral_analysis": data.get("spectral_analysis", {}),
                "metadata_quality": data.get("metadata_quality", {}),
                "calibration": data.get("calibration", {}),
                "federated_learning": data.get("federated_learning", {}),
            })
        
        elif report_type == ReportType.COMPARISON:
            template_data.update({
                "comparison_data": data.get("comparison_data", {}),
                "metrics": data.get("metrics", {}),
                "visualizations": data.get("visualizations", ""),
            })
        
        return template_data

    def _generate_with_quarto(
        self,
        report_id: str,
        report_type: ReportType,
        template_path: Path,
        template_data: Dict[str, Any],
        output_format: OutputFormat,
    ) -> GeneratedReport:
        """Generate report using Quarto CLI"""
        try:
            # Create temporary working directory
            with tempfile.TemporaryDirectory() as temp_dir:
                temp_dir_path = Path(temp_dir)
                
                # Copy template to temp directory
                temp_template = temp_dir_path / template_path.name
                with open(temp_template, 'w') as f:
                    f.write(self._render_template(template_path, template_data))
                
                # Determine output file extension
                output_ext = {
                    OutputFormat.HTML: "html",
                    OutputFormat.PDF: "pdf",
                    OutputFormat.WORD: "docx",
                    OutputFormat.MARKDOWN: "md",
                    OutputFormat.QUARTO: "qmd",
                }.get(output_format, "html")
                
                # Quarto will create output with the same name as template but target format extension
                # So we need to rename the template to the report_id first
                working_template = temp_dir_path / f"{report_id}.qmd"
                temp_template.rename(working_template)
                
                # Build Quarto command
                cmd = [
                    "quarto", "render",
                    str(working_template),
                    "--to", output_format.value,
                ]
                
                # Add additional options
                if self.config.image_format:
                    cmd.extend(["--image-format", self.config.image_format])
                if self.config.image_dpi:
                    cmd.extend(["--dpi", str(self.config.image_dpi)])
                
                # Execute Quarto from temp directory
                result = subprocess.run(
                    cmd,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minutes timeout
                    cwd=str(temp_dir_path),  # Run from temp directory
                )
                
                if result.returncode != 0:
                    error_msg = f"Quarto render failed: {result.stderr}"
                    self.logger.error(error_msg)
                    return GeneratedReport(
                        report_id=report_id,
                        report_type=report_type,
                        format=output_format,
                        file_path="",
                        creation_timestamp=datetime.now().isoformat(),
                        status="failed",
                        error_message=error_msg,
                    )
                
                # Find the output file - Quarto creates it with the same name as input but target format
                output_file = temp_dir_path / f"{report_id}.{output_ext}"
                
                # Move output to final location
                final_output = self.output_dir / f"{report_id}.{output_ext}"
                if output_file.exists():
                    output_file.rename(final_output)
                
                # Get file info
                file_size = final_output.stat().st_size if final_output.exists() else 0
                
                # Create report info
                report = GeneratedReport(
                    report_id=report_id,
                    report_type=report_type,
                    format=output_format,
                    file_path=str(final_output),
                    creation_timestamp=datetime.now().isoformat(),
                    file_size=file_size,
                    status="completed",
                    metadata={"generated_by": "quarto", "template": template_path.name},
                )
                
                self.generated_reports.append(report)
                self.logger.info(f"Report generated: {final_output}")
                
                return report
                
        except Exception as e:
            self.logger.error(f"Quarto generation failed: {e}")
            return GeneratedReport(
                report_id=report_id,
                report_type=report_type,
                format=output_format,
                file_path="",
                creation_timestamp=datetime.now().isoformat(),
                status="failed",
                error_message=str(e),
            )

    def _generate_with_template_rendering(
        self,
        report_id: str,
        report_type: ReportType,
        template_path: Path,
        template_data: Dict[str, Any],
        output_format: OutputFormat,
    ) -> GeneratedReport:
        """Generate report using template rendering (fallback when Quarto is not available)"""
        try:
            # Render the template
            rendered_content = self._render_template(template_path, template_data)
            
            # Determine output file
            output_ext = {
                OutputFormat.HTML: "html",
                OutputFormat.MARKDOWN: "md",
                OutputFormat.QUARTO: "qmd",
            }.get(output_format, "html")
            
            # For PDF and Word, we'll generate HTML and note that conversion is needed
            if output_format in [OutputFormat.PDF, OutputFormat.WORD]:
                output_ext = "html"
                conversion_needed = True
            else:
                conversion_needed = False
            
            output_file = self.output_dir / f"{report_id}.{output_ext}"
            
            # Save rendered content
            with open(output_file, 'w') as f:
                f.write(rendered_content)
            
            # Get file info
            file_size = output_file.stat().st_size
            
            # Create report info
            report = GeneratedReport(
                report_id=report_id,
                report_type=report_type,
                format=output_format,
                file_path=str(output_file),
                creation_timestamp=datetime.now().isoformat(),
                file_size=file_size,
                status="completed",
                metadata={
                    "generated_by": "template_rendering",
                    "template": template_path.name,
                    "conversion_needed": conversion_needed,
                    "conversion_format": output_format.value if conversion_needed else None,
                },
            )
            
            self.generated_reports.append(report)
            self.logger.info(f"Report generated with template rendering: {output_file}")
            
            if conversion_needed:
                self.logger.warning(
                    f"Quarto not available - generated HTML version of {output_format.value} report. "
                    f"Convert manually using: quarto render {output_file} --to {output_format.value}"
                )
            
            return report
            
        except Exception as e:
            self.logger.error(f"Template rendering failed: {e}")
            return GeneratedReport(
                report_id=report_id,
                report_type=report_type,
                format=output_format,
                file_path="",
                creation_timestamp=datetime.now().isoformat(),
                status="failed",
                error_message=str(e),
            )

    def _render_template(self, template_path: Path, data: Dict[str, Any]) -> str:
        """Render a template with the given data"""
        try:
            with open(template_path, 'r') as f:
                template_content = f.read()
            
            # Simple template rendering - replace placeholders
            rendered = template_content
            for key, value in data.items():
                placeholder = f"{{{{{key}}}}}"
                if isinstance(value, dict):
                    # Convert dict to JSON for template
                    rendered = rendered.replace(placeholder, json.dumps(value, indent=2))
                elif isinstance(value, list):
                    # Convert list to JSON for template
                    rendered = rendered.replace(placeholder, json.dumps(value, indent=2))
                else:
                    rendered = rendered.replace(placeholder, str(value))
            
            return rendered
            
        except Exception as e:
            self.logger.error(f"Template rendering error: {e}")
            return f"# Error rendering template\n\n{e}"

    def preview_report(self, report_id: str) -> Optional[str]:
        """Get a preview of a generated report"""
        try:
            # Find the report
            report = next((r for r in self.generated_reports if r.report_id == report_id), None)
            if not report:
                self.logger.warning(f"Report not found: {report_id}")
                return None
            
            # Check if file exists
            report_path = Path(report.file_path)
            if not report_path.exists():
                self.logger.warning(f"Report file not found: {report.file_path}")
                return None
            
            # Read and return content (for text-based formats)
            if report.format in [OutputFormat.HTML, OutputFormat.MARKDOWN, OutputFormat.QUARTO]:
                with open(report_path, 'r') as f:
                    return f.read()
            else:
                # For binary formats, return a message
                return f"Report {report_id} is in {report.format.value} format. Download to view."
                
        except Exception as e:
            self.logger.error(f"Failed to preview report: {e}")
            return None

    def list_reports(self, report_type: ReportType = None) -> List[GeneratedReport]:
        """List all generated reports, optionally filtered by type"""
        if report_type is None:
            return self.generated_reports.copy()
        else:
            return [r for r in self.generated_reports if r.report_type == report_type]

    def delete_report(self, report_id: str) -> bool:
        """Delete a generated report"""
        try:
            # Find the report
            report = next((r for r in self.generated_reports if r.report_id == report_id), None)
            if not report:
                self.logger.warning(f"Report not found: {report_id}")
                return False
            
            # Delete the file
            report_path = Path(report.file_path)
            if report_path.exists():
                report_path.unlink()
            
            # Remove from list
            self.generated_reports = [r for r in self.generated_reports if r.report_id != report_id]
            
            self.logger.info(f"Report deleted: {report_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to delete report: {e}")
            return False

    def create_custom_template(self, template_name: str, content: str) -> bool:
        """Create a custom template"""
        try:
            template_path = self.templates_dir / f"{template_name}.qmd"
            
            with open(template_path, 'w') as f:
                f.write(content)
            
            self.logger.info(f"Custom template created: {template_name}")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to create custom template: {e}")
            return False

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute Quarto operations based on context"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting Quarto agent execution")
            
            # Skip if configured to do so
            if self.config.skip_if_unavailable and not self.quarto_available:
                self.logger.warning("Quarto agent configured to skip if unavailable")
                return self._create_success_output({
                    "status": "skipped",
                    "quarto_available": False,
                    "message": "Quarto not available, skipping execution"
                })
            
            # Determine operation from context
            operation = context.get("operation", "generate")
            
            if operation == "generate":
                report_type = ReportType(context.get("report_type", "spectral_analysis"))
                data = context.get("data", {})
                output_format = OutputFormat(context.get("format", self.config.output_format.value))
                template = context.get("template", None)
                output_filename = context.get("output_filename", None)
                
                report = self.generate_report(
                    report_type=report_type,
                    data=data,
                    format=output_format,
                    template=template,
                    output_filename=output_filename,
                )
                
                result = {
                    "report_generated": report.status == "completed",
                    "report_id": report.report_id,
                    "report_type": report.report_type.value,
                    "format": report.format.value,
                    "file_path": report.file_path,
                    "file_size": report.file_size,
                    "status": report.status,
                    "quarto_available": self.quarto_available,
                }
                
                if report.error_message:
                    result["error"] = report.error_message
                
            elif operation == "preview":
                report_id = context.get("report_id")
                preview = self.preview_report(report_id)
                result = {
                    "preview_available": preview is not None,
                    "report_id": report_id,
                    "preview": preview[:1000] + "..." if preview and len(preview) > 1000 else preview,
                }
            
            elif operation == "list":
                report_type = context.get("report_type")
                reports = self.list_reports(ReportType(report_type) if report_type else None)
                result = {
                    "reports": [
                        {
                            "report_id": r.report_id,
                            "report_type": r.report_type.value,
                            "format": r.format.value,
                            "file_path": r.file_path,
                            "creation_timestamp": r.creation_timestamp,
                            "status": r.status,
                        }
                        for r in reports
                    ],
                    "count": len(reports),
                }
            
            elif operation == "delete":
                report_id = context.get("report_id")
                success = self.delete_report(report_id)
                result = {"report_deleted": success, "report_id": report_id}
            
            elif operation == "templates":
                templates = self.get_available_templates()
                result = {"templates": templates, "count": len(templates)}
            
            elif operation == "create_template":
                template_name = context.get("template_name")
                content = context.get("content", "")
                success = self.create_custom_template(template_name, content)
                result = {"template_created": success, "template_name": template_name}
            
            else:
                # Default operation - generate a basic report
                report = self.generate_report(
                    report_type=ReportType.SPECTRAL_ANALYSIS,
                    data=context,
                    format=self.config.output_format,
                )
                result = {
                    "report_generated": report.status == "completed",
                    "report_id": report.report_id,
                    "format": report.format.value,
                    "quarto_available": self.quarto_available,
                }
            
            self.status = AgentStatus.COMPLETED
            return self._create_success_output(result)
            
        except Exception as e:
            return self._handle_error(e)

    def get_quarto_status(self) -> Dict[str, Any]:
        """Get the current status of Quarto functionality"""
        return {
            "quarto_available": self.quarto_available,
            "pandoc_available": self._check_pandoc_installed(),
            "generated_reports": len(self.generated_reports),
            "available_templates": len(self.get_available_templates()),
            "output_dir": str(self.output_dir),
            "temp_dir": str(self.temp_dir),
            "config": {
                "output_format": self.config.output_format.value,
                "include_source": self.config.include_source,
                "include_charts": self.config.include_charts,
                "template": self.config.template.value,
                "skip_if_unavailable": self.config.skip_if_unavailable,
            },
        }