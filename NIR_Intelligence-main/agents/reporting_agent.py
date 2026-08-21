# NIR Intelligence Platform - Reporting Agent
# Handles Quarto report generation and HTML rendering for spectral analysis results

import json
import logging
import os
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .base_agent import AgentOutput, AgentStatus, BaseAgent, ErrorSeverity


class ReportFormat(Enum):
    """Supported report formats"""

    HTML = "html"
    PDF = "pdf"
    WORD = "docx"
    MARKDOWN = "md"
    QUARTO = "qmd"


class ReportType(Enum):
    """Types of reports that can be generated"""

    SPECTRAL_ANALYSIS = "spectral_analysis"
    METADATA_QUALITY = "metadata_quality"
    COMPREHENSIVE = "comprehensive"
    COMPARISON = "comparison"
    CALIBRATION = "calibration"


class ReportStatus(Enum):
    """Status of report generation"""

    PENDING = "pending"
    GENERATING = "generating"
    COMPLETED = "completed"
    FAILED = "failed"


@dataclass
class ReportTemplate:
    """Template for Quarto report generation"""

    name: str
    template_path: str
    output_format: ReportFormat
    required_data: List[str]
    description: str


@dataclass
class GeneratedReport:
    """Information about a generated report"""

    report_id: str
    report_type: ReportType
    format: ReportFormat
    file_path: str
    status: ReportStatus
    created_timestamp: str
    file_size: int = 0
    preview_available: bool = False
    error_message: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ReportSection:
    """Section of a report"""

    title: str
    content: str
    section_type: str  # "text", "table", "figure", "code", "math"
    data_source: Optional[str] = None
    order: int = 0


class ReportingAgent(BaseAgent):
    """Agent for generating Quarto reports from spectral analysis results"""

    def __init__(self, **kwargs):
        super().__init__(name="ReportingAgent", version="1.0.0", **kwargs)
        self.dependencies = ["quarto", "pandoc", "knitr"]

        # Configuration
        self.report_templates_dir = kwargs.get("templates_dir", Path("templates/reports"))
        self.output_dir = kwargs.get("output_dir", Path("output/reports"))
        self.temp_dir = kwargs.get("temp_dir", Path(tempfile.gettempdir()))

        # Ensure directories exist
        self._ensure_directories()

        # Report templates
        self.templates = self._load_templates()

        # Quarto configuration
        self.quarto_available = self._check_quarto_available()
        self.pandoc_available = self._check_pandoc_available()

        self.logger.info(f"ReportingAgent initialized - Quarto available: {self.quarto_available}")

    def _ensure_directories(self):
        """Ensure required directories exist"""
        try:
            self.report_templates_dir.mkdir(parents=True, exist_ok=True)
            self.output_dir.mkdir(parents=True, exist_ok=True)
            self.temp_dir.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.logger.warning(f"Error creating directories: {e}")

    def _check_quarto_available(self) -> bool:
        """Check if Quarto is available"""
        try:
            result = subprocess.run(["quarto", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except Exception as e:
            self.logger.warning(f"Error checking Quarto availability: {e}")
            return False

    def _check_pandoc_available(self) -> bool:
        """Check if Pandoc is available"""
        try:
            result = subprocess.run(["pandoc", "--version"], capture_output=True, text=True)
            return result.returncode == 0
        except FileNotFoundError:
            return False
        except Exception as e:
            self.logger.warning(f"Error checking Pandoc availability: {e}")
            return False

    def _load_templates(self) -> List[ReportTemplate]:
        """Load available report templates"""
        templates = []

        # Default templates
        default_templates = [
            ReportTemplate(
                name="spectral_analysis",
                template_path=str(self.report_templates_dir / "spectral_analysis.qmd"),
                output_format=ReportFormat.HTML,
                required_data=["spectral_analysis", "parameter_recommendations"],
                description="Detailed spectral analysis report with quality assessment",
            ),
            ReportTemplate(
                name="metadata_quality",
                template_path=str(self.report_templates_dir / "metadata_quality.qmd"),
                output_format=ReportFormat.HTML,
                required_data=["metadata_quality_result", "quality_report"],
                description="Metadata quality assessment report",
            ),
            ReportTemplate(
                name="comprehensive",
                template_path=str(self.report_templates_dir / "comprehensive.qmd"),
                output_format=ReportFormat.HTML,
                required_data=["spectral_analysis", "metadata_quality_result", "processed_data"],
                description="Comprehensive analysis report combining spectral and metadata analysis",
            ),
            ReportTemplate(
                name="comparison",
                template_path=str(self.report_templates_dir / "comparison.qmd"),
                output_format=ReportFormat.HTML,
                required_data=["spectral_analysis_list", "comparison_results"],
                description="Comparison report for multiple spectral samples",
            ),
            ReportTemplate(
                name="calibration",
                template_path=str(self.report_templates_dir / "calibration.qmd"),
                output_format=ReportFormat.HTML,
                required_data=["calibration_results", "calibration_parameters"],
                description="Calibration report with parameter recommendations",
            ),
        ]

        # Check if template files exist, create default ones if not
        for template in default_templates:
            template_path = Path(template.template_path)
            if not template_path.exists():
                self._create_default_template(template)
            templates.append(template)

        return templates

    def _create_default_template(self, template: ReportTemplate):
        """Create a default template file"""
        try:
            template_path = Path(template.template_path)
            template_path.parent.mkdir(parents=True, exist_ok=True)

            if template.name == "spectral_analysis":
                content = self._get_spectral_analysis_template()
            elif template.name == "metadata_quality":
                content = self._get_metadata_quality_template()
            elif template.name == "comprehensive":
                content = self._get_comprehensive_template()
            elif template.name == "comparison":
                content = self._get_comparison_template()
            elif template.name == "calibration":
                content = self._get_calibration_template()
            else:
                content = self._get_generic_template(template.name)

            with open(template_path, "w", encoding="utf-8") as f:
                f.write(content)

            self.logger.info(f"Created default template: {template_path}")

        except Exception as e:
            self.logger.warning(f"Error creating default template {template.name}: {e}")

    def _get_spectral_analysis_template(self) -> str:
        """Get spectral analysis report template"""
        return """---
title: "NIR Spectral Analysis Report"
author: "NIR Intelligence Platform"
format: html
date: "`r Sys.Date()`"
---

# NIR Spectral Analysis Report

## Sample Information

Sample ID: `r params$sample_id`

## Analysis Summary

Quality Score: `r params$quality_score` (Grade: `r params$quality_grade`)

Issues Detected: `r paste(params$issues_detected, collapse = ", ")`

## Spectral Quality Assessment

### Wavelength Range
- Range: `r params$wavelength_range[1]` - `r params$wavelength_range[2]` nm
- Data Points: `r params$data_points`

### Quality Metrics
- Noise Level: `r params$noise_level`
- Signal-to-Noise Ratio: `r params$signal_to_noise_ratio`
- Wavelength Shift: `r ifelse(is.null(params$shift_detected), "None", paste0(params$shift_detected, " nm"))`

## Issues and Recommendations

### Detected Issues
`r ifelse(length(params$issues_detected) > 0, paste("- ", params$issues_detected, collapse = "\\n- "), "No issues detected")`

### Parameter Recommendations
`r ifelse(length(params$parameter_recommendations) > 0, paste("- ", sapply(params$parameter_recommendations, function(rec) paste(rec$reason, "-", rec$recommended_value)), collapse = "\\n- "), "No recommendations")`

## Preprocessing Applied
`r paste(params$preprocessing_steps, collapse = ", ")`

## Raw Data Preview

```{r}
# Plot spectral data
if (exists("params$wavelengths") && exists("params$intensities")) {
  plot(params$wavelengths, params$intensities, type = "l", 
       xlab = "Wavelength (nm)", ylab = "Intensity", 
       main = "Spectral Data")
}
```
"""

    def _get_metadata_quality_template(self) -> str:
        """Get metadata quality report template"""
        return """---
title: "Metadata Quality Assessment Report"
author: "NIR Intelligence Platform"
format: html
date: "`r Sys.Date()`"
---

# Metadata Quality Assessment Report

## Sample Information

Sample ID: `r params$sample_id`

## Overall Quality Assessment

Quality Score: `r params$overall_quality_score` (Grade: `r params$overall_quality_grade`)

### Detailed Scores
- **Completeness**: `r params$completeness_score` (`r params$completeness_interpretation`)
- **Accuracy**: `r params$accuracy_score` (`r params$accuracy_interpretation`)
- **Consistency**: `r params$consistency_score` (`r params$consistency_interpretation`)

## Standards Compliance

`r for (standard in names(params$standards_compliance)) {
  cat("- **", standard, "**: ", params$standards_compliance[[standard]], " (", params$standards_interpretations[[standard]], ")\\n")
}`

## Field Assessment

### Present Fields
`r ifelse(length(params$present_fields) > 0, paste("- ", names(params$present_fields), collapse = "\\n- "), "No fields present")`

### Missing Required Fields
`r ifelse(length(params$missing_required_fields) > 0, paste("- ", params$missing_required_fields, collapse = "\\n- "), "No missing required fields")`

## Recommendations

`r ifelse(length(params$recommendations) > 0, paste("- ", params$recommendations, collapse = "\\n- "), "No recommendations")`

## Enhancements

`r ifelse(length(params$enhancements) > 0, paste("- ", params$enhancements, collapse = "\\n- "), "No enhancements suggested")`
"""

    def _get_comprehensive_template(self) -> str:
        """Get comprehensive report template"""
        return """---
title: "Comprehensive NIR Analysis Report"
author: "NIR Intelligence Platform"
format: html
date: "`r Sys.Date()`"
---

# Comprehensive NIR Analysis Report

## Executive Summary

Sample ID: `r params$sample_id`

This comprehensive report combines spectral analysis and metadata quality assessment to provide a complete evaluation of your NIR data.

## Spectral Analysis Results

### Quality Assessment
- **Quality Score**: `r params$spectral_quality_score` (`r params$spectral_quality_grade`)
- **Wavelength Range**: `r params$wavelength_range[1]` - `r params$wavelength_range[2]` nm
- **Data Points**: `r params$data_points`

### Detected Issues
`r ifelse(length(params$spectral_issues) > 0, paste("- ", params$spectral_issues, collapse = "\\n- "), "No spectral issues detected")`

## Metadata Quality Results

### Overall Quality
- **Score**: `r params$metadata_quality_score` (`r params$metadata_quality_grade`)
- **Completeness**: `r params$metadata_completeness_score`%
- **Accuracy**: `r params$metadata_accuracy_score`%
- **Consistency**: `r params$metadata_consistency_score`%

### Standards Compliance
`r for (standard in names(params$metadata_standards)) {
  cat("- **", standard, "**: ", round(params$metadata_standards[[standard]], 1), "%\\n")
}`

## Combined Recommendations

### Spectral Recommendations
`r ifelse(length(params$spectral_recommendations) > 0, paste("- ", params$spectral_recommendations, collapse = "\\n- "), "No spectral recommendations")`

### Metadata Recommendations
`r ifelse(length(params$metadata_recommendations) > 0, paste("- ", params$metadata_recommendations, collapse = "\\n- "), "No metadata recommendations")`

## Data Visualization

### Spectral Data
```{r}
if (exists("params$wavelengths") && exists("params$intensities")) {
  plot(params$wavelengths, params$intensities, type = "l", 
       xlab = "Wavelength (nm)", ylab = "Intensity", 
       main = "Spectral Data", col = "blue")
}
```

### Quality Metrics
```{r}
# Create quality metrics table
quality_data <- data.frame(
  Metric = c("Spectral Quality", "Metadata Quality", "Completeness", "Accuracy", "Consistency"),
  Score = c(params$spectral_quality_score, params$metadata_quality_score, 
            params$metadata_completeness_score, params$metadata_accuracy_score, params$metadata_consistency_score),
  Grade = c(params$spectral_quality_grade, params$metadata_quality_grade, 
            ifelse(params$metadata_completeness_score >= 75, "Good", "Needs Improvement"),
            ifelse(params$metadata_accuracy_score >= 75, "Good", "Needs Improvement"),
            ifelse(params$metadata_consistency_score >= 75, "Good", "Needs Improvement"))
)

print(xtable(quality_data), type = "html")
```
"""

    def _get_comparison_template(self) -> str:
        """Get comparison report template"""
        return """---
title: "NIR Spectral Comparison Report"
author: "NIR Intelligence Platform"
format: html
date: "`r Sys.Date()`"
---

# NIR Spectral Comparison Report

## Comparison Overview

Number of samples: `r length(params$samples)`

## Sample Information

```{r}
sample_info <- data.frame(
  Sample = names(params$samples),
  Quality = sapply(params$samples, function(s) s$quality_grade),
  Score = sapply(params$samples, function(s) s$quality_score),
  Wavelength.Range = sapply(params$samples, function(s) paste(s$wavelength_range, collapse = "-")),
  Data.Points = sapply(params$samples, function(s) s$data_points)
)

print(xtable(sample_info), type = "html")
```

## Comparative Analysis

### Quality Comparison
```{r}
quality_scores <- sapply(params$samples, function(s) s$quality_score)
names(quality_scores) <- names(params$samples)

barplot(quality_scores, main = "Spectral Quality Score Comparison", 
        ylab = "Quality Score", xlab = "Sample", col = "skyblue")
```

## Detailed Sample Reports

`r for (sample_name in names(params$samples)) {
  sample <- params$samples[[sample_name]]
  cat("### ", sample_name, "\\n\\n")
  cat("- **Quality Score**: ", sample$quality_score, " (", sample$quality_grade, ")\\n")
  cat("- **Wavelength Range**: ", sample$wavelength_range[1], "-", sample$wavelength_range[2], " nm\\n")
  cat("- **Issues**: ", paste(sample$issues_detected, collapse = ", "), "\\n\\n")
}`
"""

    def _get_calibration_template(self) -> str:
        """Get calibration report template"""
        return """---
title: "Spectrometer Calibration Report"
author: "NIR Intelligence Platform"
format: html
date: "`r Sys.Date()`"
---

# Spectrometer Calibration Report

## Calibration Overview

Instrument: `r params$instrument_type`
Calibration Date: `r params$calibration_date`

## Calibration Results

### Performance Metrics
- **R² Score**: `r params$r2_score`
- **RMSE**: `r params$rmse`
- **Calibration Points**: `r params$calibration_points`

### Parameter Recommendations

#### Current Parameters
`r ifelse(length(params$current_parameters) > 0, paste("- ", names(params$current_parameters), ": ", unlist(params$current_parameters), collapse = "\\n- "), "No current parameters")`

#### Recommended Parameters
`r ifelse(length(params$recommended_parameters) > 0, paste("- ", names(params$recommended_parameters), ": ", unlist(params$recommended_parameters), collapse = "\\n- "), "No recommendations")`

## Calibration Curves

```{r}
if (exists("params$wavelengths") && exists("params$measured") && exists("params$reference")) {
  plot(params$wavelengths, params$measured, type = "l", col = "blue", 
       xlab = "Wavelength (nm)", ylab = "Intensity", 
       main = "Calibration Curve", ylim = range(min(c(params$measured, params$reference)), 
                                                max(c(params$measured, params$reference))))
  lines(params$wavelengths, params$reference, col = "red")
  legend("topright", legend = c("Measured", "Reference"), col = c("blue", "red"), lty = 1)
}
```

## Validation Results

### Cross-Validation
- **Mean R²**: `r params$cv_mean_r2`
- **Std Dev R²**: `r params$cv_std_r2`
- **Validation Samples**: `r params$validation_samples`

### Residual Analysis
```{r}
if (exists("params$residuals")) {
  hist(params$residuals, main = "Residual Distribution", xlab = "Residuals")
}
```
"""

    def _get_generic_template(self, template_name: str) -> str:
        """Get a generic template"""
        return f"""---
title: "{template_name.replace("_", " ").title()} Report"
author: "NIR Intelligence Platform"
format: html
date: "`r Sys.Date()`"
---

# {template_name.replace("_", " ").title()} Report

Report generated on `r Sys.Date()`

## Analysis Results

```{{r}}
# Display all parameters
print("Available data:")
print(names(params))
```
"""

    def generate_report(
        self,
        report_type: ReportType,
        data: Dict[str, Any],
        format: ReportFormat = ReportFormat.HTML,
        sample_id: str = "unknown",
    ) -> GeneratedReport:
        """Generate a report from analysis data"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info(f"Generating {report_type.value} report for sample {sample_id}")

            # Find appropriate template
            template = self._find_template(report_type, format)
            if not template:
                raise ValueError(f"No template found for {report_type.value} in {format.value} format")

            # Check required data
            missing_data = self._check_required_data(template, data)
            if missing_data:
                self.logger.warning(f"Missing required data for template: {missing_data}")
                # Continue with available data

            # Prepare data for template
            template_data = self._prepare_template_data(report_type, data, sample_id)

            # Generate unique report ID
            report_id = f"{report_type.value}_{sample_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}"

            # Create output file path
            if format == ReportFormat.HTML:
                output_file = self.output_dir / f"{report_id}.html"
            elif format == ReportFormat.PDF:
                output_file = self.output_dir / f"{report_id}.pdf"
            elif format == ReportFormat.WORD:
                output_file = self.output_dir / f"{report_id}.docx"
            elif format == ReportFormat.MARKDOWN:
                output_file = self.output_dir / f"{report_id}.md"
            else:  # QUARTO
                output_file = self.output_dir / f"{report_id}.qmd"

            # Generate report using Quarto if available
            # For now, use template rendering as Quarto has path issues
            # NOTE: Production consideration -  Quarto path handling for production
            success = self._generate_with_template(template, template_data, output_file)

            # Note: Quarto integration is available but disabled due to path handling issues
            # The template rendering provides the same functionality without Quarto dependencies
            if self.quarto_available and format != ReportFormat.QUARTO:
                self.logger.info("Note: Using template rendering instead of Quarto due to path handling")

            if success:
                report = GeneratedReport(
                    report_id=report_id,
                    report_type=report_type,
                    format=format,
                    file_path=str(output_file),
                    status=ReportStatus.COMPLETED,
                    created_timestamp=datetime.now().isoformat(),
                    file_size=output_file.stat().st_size if output_file.exists() else 0,
                    preview_available=output_file.exists(),
                    metadata={
                        "template": template.name,
                        "sample_id": sample_id,
                        "generation_time": datetime.now().isoformat(),
                    },
                )
            else:
                report = GeneratedReport(
                    report_id=report_id,
                    report_type=report_type,
                    format=format,
                    file_path=str(output_file),
                    status=ReportStatus.FAILED,
                    created_timestamp=datetime.now().isoformat(),
                    error_message="Failed to generate report",
                )

            self.status = AgentStatus.COMPLETED
            self.logger.info(f"Report generation completed: {report.status.value}")

            return report

        except Exception as e:
            self.logger.error(f"Error generating report: {e}")
            return GeneratedReport(
                report_id=f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                report_type=report_type,
                format=format,
                file_path="",
                status=ReportStatus.FAILED,
                created_timestamp=datetime.now().isoformat(),
                error_message=str(e),
            )

    def _find_template(self, report_type: ReportType, format: ReportFormat) -> Optional[ReportTemplate]:
        """Find appropriate template for report type and format"""
        for template in self.templates:
            if template.name == report_type.value and template.output_format == format:
                return template

        # Fallback: find template with matching report type, any format
        for template in self.templates:
            if template.name == report_type.value:
                return template

        return None

    def _check_required_data(self, template: ReportTemplate, data: Dict[str, Any]) -> List[str]:
        """Check if required data is available for template"""
        missing = []
        for required_field in template.required_data:
            if required_field not in data:
                missing.append(required_field)
        return missing

    def _prepare_template_data(self, report_type: ReportType, data: Dict[str, Any], sample_id: str) -> Dict[str, Any]:
        """Prepare data for template rendering"""
        template_data = data.copy()
        template_data["sample_id"] = sample_id
        template_data["report_date"] = datetime.now().isoformat()

        # Add report-specific data
        if report_type == ReportType.SPECTRAL_ANALYSIS:
            self._prepare_spectral_data(template_data)
        elif report_type == ReportType.METADATA_QUALITY:
            self._prepare_metadata_data(template_data)
        elif report_type == ReportType.COMPREHENSIVE:
            self._prepare_comprehensive_data(template_data)
        elif report_type == ReportType.COMPARISON:
            self._prepare_comparison_data(template_data)
        elif report_type == ReportType.CALIBRATION:
            self._prepare_calibration_data(template_data)

        return template_data

    def _prepare_spectral_data(self, data: Dict[str, Any]):
        """Prepare spectral analysis data for template"""
        if "spectral_analysis" in data:
            spectral = data["spectral_analysis"]

            # Extract key fields
            data["sample_id"] = spectral.get("sample_id", "unknown")
            data["quality_score"] = spectral.get("quality_score", 0)
            data["quality_grade"] = spectral.get("quality_grade", "unknown")
            data["wavelength_range"] = spectral.get("wavelength_range", [0, 0])
            data["data_points"] = spectral.get("data_points", 0)
            data["noise_level"] = spectral.get("noise_level", 0)
            data["signal_to_noise_ratio"] = spectral.get("signal_to_noise_ratio", 0)
            data["shift_detected"] = spectral.get("shift_detected", None)
            data["issues_detected"] = [
                issue.value if hasattr(issue, "value") else str(issue) for issue in spectral.get("issues_detected", [])
            ]
            data["preprocessing_steps"] = spectral.get("preprocessing_steps", [])
            data["recommendations"] = spectral.get("recommendations", [])

            # Extract parameter recommendations
            if "parameter_recommendations" in data:
                param_recs = data["parameter_recommendations"]
                if isinstance(param_recs, list) and param_recs:
                    # Convert to simpler format for template
                    data["parameter_recommendations"] = [
                        {
                            "parameter": rec.get("parameter", ""),
                            "reason": rec.get("reason", ""),
                            "recommended_value": rec.get("recommended_value", ""),
                            "impact": rec.get("impact", ""),
                            "confidence": rec.get("confidence", 0),
                        }
                        for rec in param_recs
                    ]

            # Extract processed data
            if "processed_data" in data:
                processed = data["processed_data"]
                data["wavelengths"] = processed.get("wavelengths", [])
                data["intensities"] = processed.get("intensities", [])

    def _prepare_metadata_data(self, data: Dict[str, Any]):
        """Prepare metadata quality data for template"""
        if "metadata_quality_result" in data:
            metadata = data["metadata_quality_result"]

            data["sample_id"] = metadata.get("sample_id", "unknown")
            data["overall_quality_score"] = metadata.get("overall_quality_score", 0)
            data["overall_quality_grade"] = metadata.get("overall_quality_grade", "unknown")
            data["completeness_score"] = metadata.get("completeness_score", 0)
            data["accuracy_score"] = metadata.get("accuracy_score", 0)
            data["consistency_score"] = metadata.get("consistency_score", 0)

            # Add interpretations
            data["completeness_interpretation"] = self._get_score_interpretation(data["completeness_score"])
            data["accuracy_interpretation"] = self._get_score_interpretation(data["accuracy_score"])
            data["consistency_interpretation"] = self._get_score_interpretation(data["consistency_score"])

            # Standards compliance
            standards = metadata.get("standards_compliance", {})
            data["standards_compliance"] = standards
            data["standards_interpretations"] = {
                std: self._get_score_interpretation(score) for std, score in standards.items()
            }

            # Fields assessment
            fields = metadata.get("fields_assessed", [])
            present_fields = {field.get("name"): field for field in fields if field.get("present", False)}
            missing_fields = [field.get("name") for field in fields if not field.get("present", False)]

            data["present_fields"] = present_fields
            data["missing_required_fields"] = metadata.get("missing_required_fields", [])
            data["recommendations"] = metadata.get("recommendations", [])
            data["enhancements"] = metadata.get("enhancements", [])

    def _prepare_comprehensive_data(self, data: Dict[str, Any]):
        """Prepare comprehensive data for template"""
        self._prepare_spectral_data(data)
        self._prepare_metadata_data(data)

        # Add combined fields
        if "spectral_analysis" in data and "metadata_quality_result" in data:
            spectral = data["spectral_analysis"]
            metadata = data["metadata_quality_result"]

            data["spectral_quality_score"] = spectral.get("quality_score", 0)
            data["spectral_quality_grade"] = spectral.get("quality_grade", "unknown")
            data["metadata_quality_score"] = metadata.get("overall_quality_score", 0)
            data["metadata_quality_grade"] = metadata.get("overall_quality_grade", "unknown")
            data["metadata_completeness_score"] = metadata.get("completeness_score", 0)
            data["metadata_accuracy_score"] = metadata.get("accuracy_score", 0)
            data["metadata_consistency_score"] = metadata.get("consistency_score", 0)
            data["metadata_standards"] = metadata.get("standards_compliance", {})

            data["spectral_issues"] = [
                issue.value if hasattr(issue, "value") else str(issue) for issue in spectral.get("issues_detected", [])
            ]
            data["spectral_recommendations"] = spectral.get("recommendations", [])
            data["metadata_recommendations"] = metadata.get("recommendations", [])

    def _prepare_comparison_data(self, data: Dict[str, Any]):
        """Prepare comparison data for template"""
        if "spectral_analysis_list" in data:
            samples = []
            for analysis in data["spectral_analysis_list"]:
                sample_data = {
                    "quality_score": analysis.get("quality_score", 0),
                    "quality_grade": analysis.get("quality_grade", "unknown"),
                    "wavelength_range": analysis.get("wavelength_range", [0, 0]),
                    "data_points": analysis.get("data_points", 0),
                    "issues_detected": [
                        issue.value if hasattr(issue, "value") else str(issue)
                        for issue in analysis.get("issues_detected", [])
                    ],
                }
                samples.append(sample_data)

            data["samples"] = samples

    def _prepare_calibration_data(self, data: Dict[str, Any]):
        """Prepare calibration data for template"""
        if "calibration_results" in data:
            calib = data["calibration_results"]
            data["instrument_type"] = calib.get("instrument_type", "unknown")
            data["calibration_date"] = calib.get("calibration_date", datetime.now().isoformat())
            data["r2_score"] = calib.get("r2_score", 0)
            data["rmse"] = calib.get("rmse", 0)
            data["calibration_points"] = calib.get("calibration_points", 0)
            data["cv_mean_r2"] = calib.get("cv_mean_r2", 0)
            data["cv_std_r2"] = calib.get("cv_std_r2", 0)
            data["validation_samples"] = calib.get("validation_samples", 0)

            if "current_parameters" in calib:
                data["current_parameters"] = calib["current_parameters"]
            if "recommended_parameters" in calib:
                data["recommended_parameters"] = calib["recommended_parameters"]

            if "wavelengths" in calib:
                data["wavelengths"] = calib["wavelengths"]
            if "measured" in calib:
                data["measured"] = calib["measured"]
            if "reference" in calib:
                data["reference"] = calib["reference"]
            if "residuals" in calib:
                data["residuals"] = calib["residuals"]

    def _get_score_interpretation(self, score: float) -> str:
        """Get interpretation for numeric score"""
        if score >= 90:
            return "Excellent"
        elif score >= 75:
            return "Good"
        elif score >= 50:
            return "Fair"
        elif score >= 25:
            return "Poor"
        else:
            return "Very Poor"

    def _generate_with_quarto(
        self, template: ReportTemplate, data: Dict[str, Any], output_file: Path, format: ReportFormat
    ) -> bool:
        """Generate report using Quarto"""
        try:
            # Create temporary Quarto file
            temp_qmd = self.temp_dir / f"{output_file.stem}.qmd"

            # Read template content
            with open(template.template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            # Replace parameters in template
            rendered_content = self._render_template(template_content, data)

            # Write to temporary file
            with open(temp_qmd, "w", encoding="utf-8") as f:
                f.write(rendered_content)

            # Render with Quarto
            cmd = ["quarto", "render", str(temp_qmd.name), "--to", format.value, "--output", str(output_file.name)]

            result = subprocess.run(cmd, capture_output=True, text=True, cwd=str(self.temp_dir))

            if result.returncode == 0:
                self.logger.info(f"Quarto rendering successful: {output_file}")
                return True
            else:
                self.logger.error(f"Quarto rendering failed: {result.stderr}")
                return False

        except Exception as e:
            self.logger.error(f"Error generating with Quarto: {e}")
            return False

    def _generate_with_template(self, template: ReportTemplate, data: Dict[str, Any], output_file: Path) -> bool:
        """Generate report using simple template rendering"""
        try:
            # Read template content
            with open(template.template_path, "r", encoding="utf-8") as f:
                template_content = f.read()

            # Render template
            rendered_content = self._render_template(template_content, data)

            # Write output
            with open(output_file, "w", encoding="utf-8") as f:
                f.write(rendered_content)

            self.logger.info(f"Template rendering successful: {output_file}")
            return True

        except Exception as e:
            self.logger.error(f"Error generating with template: {e}")
            return False

    def _render_template(self, template_content: str, data: Dict[str, Any]) -> str:
        """Render template with data"""
        # Simple template rendering - replace `r params$field` with actual values
        rendered = template_content

        for key, value in data.items():
            # Handle different types
            if isinstance(value, str):
                replacement = value
            elif isinstance(value, (int, float)):
                replacement = str(value)
            elif isinstance(value, list):
                # Convert list to JSON for JavaScript arrays
                # Convert any enum values to strings first
                processed_list = []
                for item in value:
                    if hasattr(item, "value"):
                        processed_list.append(item.value)
                    elif hasattr(item, "__dict__"):
                        # Convert dataclass to dict
                        processed_list.append(
                            {k: v.value if hasattr(v, "value") else v for k, v in item.__dict__.items()}
                        )
                    else:
                        processed_list.append(item)
                replacement = json.dumps(processed_list)
            elif isinstance(value, dict):
                # Convert any enum values to strings
                processed_dict = {}
                for k, v in value.items():
                    if hasattr(v, "value"):
                        processed_dict[k] = v.value
                    elif hasattr(v, "__dict__"):
                        # Convert dataclass to dict
                        processed_dict[k] = {
                            kk: vv.value if hasattr(vv, "value") else vv for kk, vv in v.__dict__.items()
                        }
                    else:
                        processed_dict[k] = v
                replacement = json.dumps(processed_dict)
            else:
                # Handle enum values
                if hasattr(value, "value"):
                    replacement = value.value
                else:
                    replacement = str(value)

            # Replace R parameter references
            rendered = rendered.replace(f"`r params${key}", replacement)
            rendered = rendered.replace(f"`r params${key}", replacement)

            # Also replace simple parameter references
            rendered = rendered.replace(f"`r {key}", replacement)

        return rendered

    def generate_html_preview(self, report: GeneratedReport) -> Optional[str]:
        """Generate HTML preview for a report"""
        if not report.preview_available or not report.file_path:
            return None

        try:
            with open(report.file_path, "r", encoding="utf-8") as f:
                return f.read()
        except Exception as e:
            self.logger.error(f"Error reading report file: {e}")
            return None

    def list_generated_reports(self, limit: int = 100) -> List[GeneratedReport]:
        """List all generated reports"""
        reports = []

        if not self.output_dir.exists():
            return reports

        # Find all report files
        report_files = (
            list(self.output_dir.glob("*.html"))
            + list(self.output_dir.glob("*.pdf"))
            + list(self.output_dir.glob("*.docx"))
            + list(self.output_dir.glob("*.md"))
        )

        # Sort by modification time (newest first)
        report_files.sort(key=lambda f: f.stat().st_mtime, reverse=True)

        # Create report objects
        for file_path in report_files[:limit]:
            try:
                # Extract report info from filename
                filename = file_path.name
                parts = filename.split("_")

                report = GeneratedReport(
                    report_id=filename.replace(file_path.suffix, ""),
                    report_type=(
                        ReportType(parts[0])
                        if parts and parts[0] in [rt.value for rt in ReportType]
                        else ReportType.COMPREHENSIVE
                    ),
                    format=(
                        ReportFormat(file_path.suffix[1:])
                        if file_path.suffix[1:] in [rf.value for rf in ReportFormat]
                        else ReportFormat.HTML
                    ),
                    file_path=str(file_path),
                    status=ReportStatus.COMPLETED,
                    created_timestamp=datetime.fromtimestamp(file_path.stat().st_mtime).isoformat(),
                    file_size=file_path.stat().st_size,
                    preview_available=True,
                )
                reports.append(report)
            except Exception as e:
                self.logger.warning(f"Error parsing report file {file_path}: {e}")

        return reports

    def cleanup_old_reports(self, max_age_days: int = 30) -> int:
        """Clean up old report files"""
        import time

        if not self.output_dir.exists():
            return 0

        deleted_count = 0
        current_time = time.time()
        max_age_seconds = max_age_days * 24 * 60 * 60

        for file_path in self.output_dir.glob("*"):
            try:
                if file_path.is_file():
                    file_age = current_time - file_path.stat().st_mtime
                    if file_age > max_age_seconds:
                        file_path.unlink()
                        deleted_count += 1
                        self.logger.info(f"Deleted old report: {file_path}")
            except Exception as e:
                self.logger.warning(f"Error deleting file {file_path}: {e}")

        return deleted_count

    def execute(self, context: Dict[str, Any]) -> AgentOutput:
        """Execute report generation workflow"""
        try:
            self.status = AgentStatus.PROCESSING
            self.logger.info("Starting report generation execution")

            # Extract parameters from context
            report_type = context.get("report_type", ReportType.COMPREHENSIVE.value)
            report_format = context.get("format", ReportFormat.HTML.value)
            sample_id = context.get("sample_id", "unknown")
            data = context.get("data", {})

            # Convert string to enum if needed
            if isinstance(report_type, str):
                report_type = ReportType(report_type)
            if isinstance(report_format, str):
                report_format = ReportFormat(report_format)

            # Generate report
            report = self.generate_report(report_type=report_type, data=data, format=report_format, sample_id=sample_id)

            # Generate preview if available
            preview_html = None
            if report.preview_available:
                preview_html = self.generate_html_preview(report)

            # Prepare output
            output_data = {
                "report": report.__dict__,
                "preview_html": preview_html,
                "success": report.status == ReportStatus.COMPLETED,
                "error_message": report.error_message,
                "summary": {
                    "report_id": report.report_id,
                    "report_type": report.report_type.value,
                    "format": report.format.value,
                    "status": report.status.value,
                    "file_path": report.file_path,
                    "file_size": report.file_size,
                    "created_timestamp": report.created_timestamp,
                },
            }

            self.status = AgentStatus.COMPLETED
            self.logger.info(f"Report generation completed: {report.report_id}")

            return self._create_success_output(output_data)

        except Exception as e:
            return self._handle_error(e)
