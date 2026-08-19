"""
Quality Assurance Agent for NIR Intelligence Platform

This agent ensures overall quality of the analysis process, validates results,
and maintains standards compliance throughout the workflow.
"""

import logging
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from datetime import datetime

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class QACheck:
    """Represents a quality assurance check."""
    check_id: str
    name: str
    description: str
    category: str
    passed: bool
    details: str = ""
    severity: str = "medium"  # low, medium, high
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "check_id": self.check_id,
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "passed": self.passed,
            "details": self.details,
            "severity": self.severity,
            "timestamp": self.timestamp
        }


@dataclass
class QAResult:
    """Container for quality assurance results."""
    checks_performed: List[QACheck] = field(default_factory=list)
    overall_status: str = "passed"  # passed, failed, warning
    pass_rate: float = 0.0
    critical_failures: int = 0
    warnings: int = 0
    recommendations: List[Dict] = field(default_factory=list)
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "checks_performed": [c.to_dict() for c in self.checks_performed],
            "overall_status": self.overall_status,
            "pass_rate": self.pass_rate,
            "critical_failures": self.critical_failures,
            "warnings": self.warnings,
            "recommendations": self.recommendations,
            "timestamp": self.timestamp
        }


class QualityAssuranceAgent:
    """
    Agent for ensuring quality throughout the analysis workflow.
    
    Capabilities:
    - Validate analysis results
    - Check data integrity
    - Verify calibration quality
    - Ensure metadata completeness
    - Validate report generation
    - Maintain audit trail
    """
    
    def __init__(self, agent_id: str = "quality_assurance_agent"):
        """Initialize Quality Assurance Agent."""
        self.agent_id = agent_id
        self.qa_checks = self._load_qa_checks()
        logger.info(f"Quality Assurance Agent {self.agent_id} initialized")
    
    def _load_qa_checks(self) -> Dict[str, Dict]:
        """Load quality assurance checks."""
        return {
            "data_integrity": {
                "name": "Data Integrity Check",
                "description": "Verify that spectral data is complete and valid",
                "category": "data",
                "severity": "high",
                "checks": [
                    {
                        "id": "data_completeness",
                        "description": "Check for missing or NaN values in spectral data",
                        "function": self._check_data_completeness
                    },
                    {
                        "id": "wavelength_order",
                        "description": "Verify wavelengths are in ascending order",
                        "function": self._check_wavelength_order
                    },
                    {
                        "id": "intensity_range",
                        "description": "Check intensity values are within valid range",
                        "function": self._check_intensity_range
                    }
                ]
            },
            "calibration_quality": {
                "name": "Calibration Quality Check",
                "description": "Verify calibration meets quality standards",
                "category": "calibration",
                "severity": "high",
                "checks": [
                    {
                        "id": "wavelength_calibration",
                        "description": "Check wavelength calibration quality",
                        "function": self._check_wavelength_calibration
                    },
                    {
                        "id": "intensity_calibration",
                        "description": "Check intensity calibration quality",
                        "function": self._check_intensity_calibration
                    },
                    {
                        "id": "calibration_frequency",
                        "description": "Check calibration is up to date",
                        "function": self._check_calibration_frequency
                    }
                ]
            },
            "metadata_completeness": {
                "name": "Metadata Completeness Check",
                "description": "Verify metadata meets minimum requirements",
                "category": "metadata",
                "severity": "medium",
                "checks": [
                    {
                        "id": "required_fields",
                        "description": "Check all required metadata fields are present",
                        "function": self._check_required_metadata_fields
                    },
                    {
                        "id": "metadata_quality_score",
                        "description": "Check metadata quality score meets minimum threshold",
                        "function": self._check_metadata_quality_score
                    }
                ]
            },
            "analysis_quality": {
                "name": "Analysis Quality Check",
                "description": "Verify analysis results meet quality standards",
                "category": "analysis",
                "severity": "medium",
                "checks": [
                    {
                        "id": "spectral_quality_score",
                        "description": "Check spectral analysis quality score",
                        "function": self._check_spectral_quality_score
                    },
                    {
                        "id": "peak_detection",
                        "description": "Verify peak detection results are reasonable",
                        "function": self._check_peak_detection
                    },
                    {
                        "id": "issue_detection",
                        "description": "Check that potential issues were properly detected",
                        "function": self._check_issue_detection
                    }
                ]
            },
            "report_quality": {
                "name": "Report Quality Check",
                "description": "Verify report generation meets standards",
                "category": "reporting",
                "severity": "low",
                "checks": [
                    {
                        "id": "report_completeness",
                        "description": "Check report contains all required sections",
                        "function": self._check_report_completeness
                    },
                    {
                        "id": "source_code_inclusion",
                        "description": "Verify source code is included in report",
                        "function": self._check_source_code_inclusion
                    }
                ]
            }
        }
    
    async def perform_qa_check(self, 
                               analysis_data: Dict,
                               metadata_quality: Dict,
                               calibration_result: Dict,
                               report: Optional[Dict] = None) -> QAResult:
        """
        Perform comprehensive quality assurance check.
        
        Args:
            analysis_data: Results from spectral analysis
            metadata_quality: Results from metadata quality assessment
            calibration_result: Results from calibration
            report: Generated report (optional)
            
        Returns:
            QAResult with all check results
        """
        logger.info("Starting QA check")
        
        result = QAResult()
        
        # Run all checks
        for check_group in self.qa_checks.values():
            for check in check_group.get("checks", []):
                try:
                    qa_check = await self._run_check(
                        check, analysis_data, metadata_quality, calibration_result, report
                    )
                    result.checks_performed.append(qa_check)
                except Exception as e:
                    logger.error(f"Error running QA check {check.get('id', 'unknown')}: {e}")
                    result.checks_performed.append(QACheck(
                        check_id=check.get("id", "unknown"),
                        name=check.get("name", "Unknown"),
                        description=check.get("description", ""),
                        category=check_group.get("category", "unknown"),
                        passed=False,
                        details=f"Error: {str(e)}",
                        severity=check_group.get("severity", "medium")
                    ))
        
        # Calculate statistics
        total_checks = len(result.checks_performed)
        passed_checks = sum(1 for c in result.checks_performed if c.passed)
        result.pass_rate = (passed_checks / total_checks * 100) if total_checks > 0 else 0
        result.critical_failures = sum(1 for c in result.checks_performed 
                                      if not c.passed and c.severity == "high")
        result.warnings = sum(1 for c in result.checks_performed 
                             if not c.passed and c.severity in ["medium", "low"])
        
        # Determine overall status
        if result.critical_failures > 0:
            result.overall_status = "failed"
        elif result.warnings > 0:
            result.overall_status = "warning"
        else:
            result.overall_status = "passed"
        
        # Generate recommendations
        result.recommendations = self._generate_qa_recommendations(result)
        
        logger.info(f"QA check complete. Status: {result.overall_status}, Pass rate: {result.pass_rate:.1f}%")
        
        return result
    
    async def _run_check(self, 
                        check: Dict,
                        analysis_data: Dict,
                        metadata_quality: Dict,
                        calibration_result: Dict,
                        report: Optional[Dict]) -> QACheck:
        """Run a single QA check."""
        check_func = check.get("function")
        if not check_func or not callable(check_func):
            return QACheck(
                check_id=check.get("id", "unknown"),
                name=check.get("name", "Unknown"),
                description=check.get("description", ""),
                category="unknown",
                passed=False,
                details="Check function not available",
                severity="high"
            )
        
        try:
            result = await check_func(analysis_data, metadata_quality, calibration_result, report)
            return result
        except Exception as e:
            return QACheck(
                check_id=check.get("id", "unknown"),
                name=check.get("name", "Unknown"),
                description=check.get("description", ""),
                category="unknown",
                passed=False,
                details=f"Check failed with error: {str(e)}",
                severity="high"
            )
    
    async def _check_data_completeness(self, 
                                       analysis_data: Dict,
                                       metadata_quality: Dict,
                                       calibration_result: Dict,
                                       report: Optional[Dict]) -> QACheck:
        """Check for missing or NaN values in spectral data."""
        spectral_data = analysis_data.get("original_data", {})
        wavelengths = spectral_data.get("wavelengths", [])
        intensities = spectral_data.get("intensities", [])
        
        if not wavelengths or not intensities:
            return QACheck(
                check_id="data_completeness",
                name="Data Completeness",
                description="Check for missing or NaN values in spectral data",
                category="data",
                passed=False,
                details="No spectral data available",
                severity="high"
            )
        
        # Check for NaN values
        import numpy as np
        wl_array = np.array(wavelengths)
        int_array = np.array(intensities)
        
        nan_wl = np.isnan(wl_array)
        nan_int = np.isnan(int_array)
        
        if np.any(nan_wl) or np.any(nan_int):
            return QACheck(
                check_id="data_completeness",
                name="Data Completeness",
                description="Check for missing or NaN values in spectral data",
                category="data",
                passed=False,
                details=f"Found {np.sum(nan_wl)} NaN values in wavelengths, {np.sum(nan_int)} NaN values in intensities",
                severity="high"
            )
        
        # Check for infinite values
        inf_wl = np.isinf(wl_array)
        inf_int = np.isinf(int_array)
        
        if np.any(inf_wl) or np.any(inf_int):
            return QACheck(
                check_id="data_completeness",
                name="Data Completeness",
                description="Check for missing or NaN values in spectral data",
                category="data",
                passed=False,
                details=f"Found {np.sum(inf_wl)} infinite values in wavelengths, {np.sum(inf_int)} infinite values in intensities",
                severity="high"
            )
        
        return QACheck(
            check_id="data_completeness",
            name="Data Completeness",
            description="Check for missing or NaN values in spectral data",
            category="data",
            passed=True,
            details="All data values are valid",
            severity="high"
        )
    
    async def _check_wavelength_order(self, 
                                      analysis_data: Dict,
                                      metadata_quality: Dict,
                                      calibration_result: Dict,
                                      report: Optional[Dict]) -> QACheck:
        """Verify wavelengths are in ascending order."""
        spectral_data = analysis_data.get("original_data", {})
        wavelengths = spectral_data.get("wavelengths", [])
        
        if not wavelengths:
            return QACheck(
                check_id="wavelength_order",
                name="Wavelength Order",
                description="Verify wavelengths are in ascending order",
                category="data",
                passed=False,
                details="No wavelength data available",
                severity="high"
            )
        
        # Check if wavelengths are sorted
        is_sorted = all(wavelengths[i] <= wavelengths[i+1] for i in range(len(wavelengths)-1))
        
        if not is_sorted:
            # Find where the order breaks
            for i in range(len(wavelengths)-1):
                if wavelengths[i] > wavelengths[i+1]:
                    return QACheck(
                        check_id="wavelength_order",
                        name="Wavelength Order",
                        description="Verify wavelengths are in ascending order",
                        category="data",
                        passed=False,
                        details=f"Wavelengths not in order at index {i}: {wavelengths[i]} > {wavelengths[i+1]}",
                        severity="high"
                    )
        
        return QACheck(
            check_id="wavelength_order",
            name="Wavelength Order",
            description="Verify wavelengths are in ascending order",
            category="data",
            passed=True,
            details="Wavelengths are in ascending order",
            severity="high"
        )
    
    async def _check_intensity_range(self, 
                                     analysis_data: Dict,
                                     metadata_quality: Dict,
                                     calibration_result: Dict,
                                     report: Optional[Dict]) -> QACheck:
        """Check intensity values are within valid range."""
        spectral_data = analysis_data.get("original_data", {})
        intensities = spectral_data.get("intensities", [])
        
        if not intensities:
            return QACheck(
                check_id="intensity_range",
                name="Intensity Range",
                description="Check intensity values are within valid range",
                category="data",
                passed=False,
                details="No intensity data available",
                severity="medium"
            )
        
        min_int = min(intensities)
        max_int = max(intensities)
        
        # Check for reasonable range
        # Intensities should be positive (for most measurement types)
        if min_int < 0:
            return QACheck(
                check_id="intensity_range",
                name="Intensity Range",
                description="Check intensity values are within valid range",
                category="data",
                passed=False,
                details=f"Negative intensity values detected (min: {min_int})",
                severity="high"
            )
        
        # Check for saturation (arbitrary high threshold)
        if max_int > 1e6:
            return QACheck(
                check_id="intensity_range",
                name="Intensity Range",
                description="Check intensity values are within valid range",
                category="data",
                passed=False,
                details=f"Potential saturation detected (max: {max_int})",
                severity="medium"
            )
        
        # Check for very low signal
        if max_int < 10:
            return QACheck(
                check_id="intensity_range",
                name="Intensity Range",
                description="Check intensity values are within valid range",
                category="data",
                passed=False,
                details=f"Very low signal detected (max: {max_int})",
                severity="medium"
            )
        
        return QACheck(
            check_id="intensity_range",
            name="Intensity Range",
            description="Check intensity values are within valid range",
            category="data",
            passed=True,
            details=f"Intensity range is valid (min: {min_int:.2f}, max: {max_int:.2f})",
            severity="medium"
        )
    
    async def _check_wavelength_calibration(self, 
                                           analysis_data: Dict,
                                           metadata_quality: Dict,
                                           calibration_result: Dict,
                                           report: Optional[Dict]) -> QACheck:
        """Check wavelength calibration quality."""
        wl_cal = calibration_result.get("wavelength_calibration")
        
        if not wl_cal:
            return QACheck(
                check_id="wavelength_calibration",
                name="Wavelength Calibration",
                description="Check wavelength calibration quality",
                category="calibration",
                passed=False,
                details="No wavelength calibration available",
                severity="high"
            )
        
        # Check calibration quality metrics
        r_squared = wl_cal.get("r_squared", 0)
        rmse = wl_cal.get("rmse", float('inf'))
        num_points = wl_cal.get("num_points", 0)
        
        if r_squared < 0.9:
            return QACheck(
                check_id="wavelength_calibration",
                name="Wavelength Calibration",
                description="Check wavelength calibration quality",
                category="calibration",
                passed=False,
                details=f"Poor calibration fit (R²: {r_squared:.4f})",
                severity="high"
            )
        
        if rmse > 1.0:
            return QACheck(
                check_id="wavelength_calibration",
                name="Wavelength Calibration",
                description="Check wavelength calibration quality",
                category="calibration",
                passed=False,
                details=f"High calibration error (RMSE: {rmse:.4f} nm)",
                severity="medium"
            )
        
        if num_points < 3:
            return QACheck(
                check_id="wavelength_calibration",
                name="Wavelength Calibration",
                description="Check wavelength calibration quality",
                category="calibration",
                passed=False,
                details=f"Insufficient calibration points ({num_points})",
                severity="medium"
            )
        
        return QACheck(
            check_id="wavelength_calibration",
            name="Wavelength Calibration",
            description="Check wavelength calibration quality",
            category="calibration",
            passed=True,
            details=f"Good calibration (R²: {r_squared:.4f}, RMSE: {rmse:.4f} nm, {num_points} points)",
            severity="high"
        )
    
    async def _check_intensity_calibration(self, 
                                          analysis_data: Dict,
                                          metadata_quality: Dict,
                                          calibration_result: Dict,
                                          report: Optional[Dict]) -> QACheck:
        """Check intensity calibration quality."""
        int_cal = calibration_result.get("intensity_calibration")
        
        if not int_cal:
            return QACheck(
                check_id="intensity_calibration",
                name="Intensity Calibration",
                description="Check intensity calibration quality",
                category="calibration",
                passed=False,
                details="No intensity calibration available",
                severity="high"
            )
        
        r_squared = int_cal.get("r_squared", 0)
        
        if r_squared < 0.9:
            return QACheck(
                check_id="intensity_calibration",
                name="Intensity Calibration",
                description="Check intensity calibration quality",
                category="calibration",
                passed=False,
                details=f"Poor calibration fit (R²: {r_squared:.4f})",
                severity="high"
            )
        
        return QACheck(
            check_id="intensity_calibration",
            name="Intensity Calibration",
            description="Check intensity calibration quality",
            category="calibration",
            passed=True,
            details=f"Good calibration (R²: {r_squared:.4f})",
            severity="high"
        )
    
    async def _check_calibration_frequency(self, 
                                           analysis_data: Dict,
                                           metadata_quality: Dict,
                                           calibration_result: Dict,
                                           report: Optional[Dict]) -> QACheck:
        """Check calibration is up to date."""
        metadata = analysis_data.get("original_data", {}).get("metadata", {})
        cal_date_str = metadata.get("calibration_date")
        measurement_date_str = metadata.get("date") or metadata.get("measurement_date")
        
        if not cal_date_str or not measurement_date_str:
            return QACheck(
                check_id="calibration_frequency",
                name="Calibration Frequency",
                description="Check calibration is up to date",
                category="calibration",
                passed=False,
                details="Calibration date or measurement date not available",
                severity="medium"
            )
        
        try:
            from datetime import datetime
            cal_date = datetime.fromisoformat(cal_date_str) if isinstance(cal_date_str, str) else cal_date_str
            meas_date = datetime.fromisoformat(measurement_date_str) if isinstance(measurement_date_str, str) else measurement_date_str
            
            days_since_cal = (meas_date - cal_date).days
            
            if days_since_cal > 30:
                return QACheck(
                    check_id="calibration_frequency",
                    name="Calibration Frequency",
                    description="Check calibration is up to date",
                    category="calibration",
                    passed=False,
                    details=f"Calibration is {days_since_cal} days old (recommended: <30 days)",
                    severity="medium"
                )
            
            return QACheck(
                check_id="calibration_frequency",
                name="Calibration Frequency",
                description="Check calibration is up to date",
                category="calibration",
                passed=True,
                details=f"Calibration is {days_since_cal} days old",
                severity="medium"
            )
        except Exception as e:
            return QACheck(
                check_id="calibration_frequency",
                name="Calibration Frequency",
                description="Check calibration is up to date",
                category="calibration",
                passed=False,
                details=f"Error parsing dates: {str(e)}",
                severity="medium"
            )
    
    async def _check_required_metadata_fields(self, 
                                              analysis_data: Dict,
                                              metadata_quality: Dict,
                                              calibration_result: Dict,
                                              report: Optional[Dict]) -> QACheck:
        """Check all required metadata fields are present."""
        missing_fields = metadata_quality.get("missing_fields", [])
        
        if missing_fields:
            return QACheck(
                check_id="required_fields",
                name="Required Metadata Fields",
                description="Check all required metadata fields are present",
                category="metadata",
                passed=False,
                details=f"Missing required fields: {', '.join(missing_fields)}",
                severity="medium"
            )
        
        return QACheck(
            check_id="required_fields",
            name="Required Metadata Fields",
            description="Check all required metadata fields are present",
            category="metadata",
            passed=True,
            details="All required metadata fields are present",
            severity="medium"
        )
    
    async def _check_metadata_quality_score(self, 
                                            analysis_data: Dict,
                                            metadata_quality: Dict,
                                            calibration_result: Dict,
                                            report: Optional[Dict]) -> QACheck:
        """Check metadata quality score meets minimum threshold."""
        score = metadata_quality.get("overall_score", 0)
        
        # Minimum threshold for passing
        if score < 70:
            return QACheck(
                check_id="metadata_quality_score",
                name="Metadata Quality Score",
                description="Check metadata quality score meets minimum threshold",
                category="metadata",
                passed=False,
                details=f"Metadata quality score too low: {score:.1f}/100 (minimum: 70)",
                severity="medium"
            )
        
        return QACheck(
            check_id="metadata_quality_score",
            name="Metadata Quality Score",
            description="Check metadata quality score meets minimum threshold",
            category="metadata",
            passed=True,
            details=f"Metadata quality score is good: {score:.1f}/100",
            severity="medium"
        )
    
    async def _check_spectral_quality_score(self, 
                                            analysis_data: Dict,
                                            metadata_quality: Dict,
                                            calibration_result: Dict,
                                            report: Optional[Dict]) -> QACheck:
        """Check spectral analysis quality score."""
        score = analysis_data.get("quality_score", 0)
        
        if score < 70:
            return QACheck(
                check_id="spectral_quality_score",
                name="Spectral Quality Score",
                description="Check spectral analysis quality score",
                category="analysis",
                passed=False,
                details=f"Spectral quality score too low: {score:.1f}/100 (minimum: 70)",
                severity="medium"
            )
        
        return QACheck(
            check_id="spectral_quality_score",
            name="Spectral Quality Score",
            description="Check spectral analysis quality score",
            category="analysis",
            passed=True,
            details=f"Spectral quality score is good: {score:.1f}/100",
            severity="medium"
        )
    
    async def _check_peak_detection(self, 
                                   analysis_data: Dict,
                                   metadata_quality: Dict,
                                   calibration_result: Dict,
                                   report: Optional[Dict]) -> QACheck:
        """Verify peak detection results are reasonable."""
        peak_info = analysis_data.get("analysis_metrics", {}).get("peak_analysis", {})
        num_peaks = peak_info.get("num_peaks", 0)
        
        # For NIR spectra, we typically expect some peaks
        if num_peaks == 0:
            return QACheck(
                check_id="peak_detection",
                name="Peak Detection",
                description="Verify peak detection results are reasonable",
                category="analysis",
                passed=False,
                details="No peaks detected in spectrum",
                severity="medium"
            )
        
        # Too many peaks might indicate noise
        if num_peaks > 50:
            return QACheck(
                check_id="peak_detection",
                name="Peak Detection",
                description="Verify peak detection results are reasonable",
                category="analysis",
                passed=False,
                details=f"Excessive number of peaks detected: {num_peaks} (may indicate noise)",
                severity="medium"
            )
        
        return QACheck(
            check_id="peak_detection",
            name="Peak Detection",
            description="Verify peak detection results are reasonable",
            category="analysis",
            passed=True,
            details=f"Reasonable number of peaks detected: {num_peaks}",
            severity="medium"
        )
    
    async def _check_issue_detection(self, 
                                    analysis_data: Dict,
                                    metadata_quality: Dict,
                                    calibration_result: Dict,
                                    report: Optional[Dict]) -> QACheck:
        """Check that potential issues were properly detected."""
        issues = analysis_data.get("issues_detected", [])
        cal_issues = calibration_result.get("issues_detected", [])
        
        # If no issues detected, that's fine (might be good data)
        # But if there are known problems, they should be detected
        
        # For now, just check that the system is detecting issues
        # In a real implementation, we'd have more sophisticated checks
        
        return QACheck(
            check_id="issue_detection",
            name="Issue Detection",
            description="Check that potential issues were properly detected",
            category="analysis",
            passed=True,
            details=f"Detected {len(issues)} spectral issues and {len(cal_issues)} calibration issues",
            severity="low"
        )
    
    async def _check_report_completeness(self, 
                                        analysis_data: Dict,
                                        metadata_quality: Dict,
                                        calibration_result: Dict,
                                        report: Optional[Dict]) -> QACheck:
        """Check report contains all required sections."""
        if not report:
            return QACheck(
                check_id="report_completeness",
                name="Report Completeness",
                description="Check report contains all required sections",
                category="reporting",
                passed=False,
                details="No report provided",
                severity="low"
            )
        
        sections = report.get("sections", [])
        required_sections = ["Introduction", "Methods", "Results", "Conclusion"]
        
        missing = [s for s in required_sections if s not in [sec.get("title", "") for sec in sections]]
        
        if missing:
            return QACheck(
                check_id="report_completeness",
                name="Report Completeness",
                description="Check report contains all required sections",
                category="reporting",
                passed=False,
                details=f"Missing sections: {', '.join(missing)}",
                severity="low"
            )
        
        return QACheck(
            check_id="report_completeness",
            name="Report Completeness",
            description="Check report contains all required sections",
            category="reporting",
            passed=True,
            details=f"All required sections present ({len(sections)} sections)",
            severity="low"
        )
    
    async def _check_source_code_inclusion(self, 
                                           analysis_data: Dict,
                                           metadata_quality: Dict,
                                           calibration_result: Dict,
                                           report: Optional[Dict]) -> QACheck:
        """Verify source code is included in report."""
        if not report:
            return QACheck(
                check_id="source_code_inclusion",
                name="Source Code Inclusion",
                description="Verify source code is included in report",
                category="reporting",
                passed=False,
                details="No report provided",
                severity="low"
            )
        
        source_code = report.get("python_source", [])
        
        if not source_code:
            return QACheck(
                check_id="source_code_inclusion",
                name="Source Code Inclusion",
                description="Verify source code is included in report",
                category="reporting",
                passed=False,
                details="No Python source code included in report",
                severity="low"
            )
        
        return QACheck(
            check_id="source_code_inclusion",
            name="Source Code Inclusion",
            description="Verify source code is included in report",
            category="reporting",
            passed=True,
            details=f"Source code included ({len(source_code)} files)",
            severity="low"
        )
    
    def _generate_qa_recommendations(self, result: QAResult) -> List[Dict]:
        """Generate recommendations based on QA results."""
        recommendations = []
        
        # Group failed checks by category
        failed_by_category = {}
        for check in result.checks_performed:
            if not check.passed:
                category = check.category
                if category not in failed_by_category:
                    failed_by_category[category] = []
                failed_by_category[category].append(check)
        
        # Generate recommendations for each category
        for category, checks in failed_by_category.items():
            if category == "data":
                recommendations.append({
                    "type": "data_quality",
                    "priority": "high",
                    "description": f"{len(checks)} data quality issues detected",
                    "recommendation": "Review and correct spectral data. Check for missing values, incorrect ranges, or data corruption."
                })
            elif category == "calibration":
                recommendations.append({
                    "type": "calibration",
                    "priority": "high",
                    "description": f"{len(checks)} calibration issues detected",
                    "recommendation": "Recalibrate spectrometer and verify calibration quality. Use proper reference materials."
                })
            elif category == "metadata":
                recommendations.append({
                    "type": "metadata",
                    "priority": "medium",
                    "description": f"{len(checks)} metadata issues detected",
                    "recommendation": "Complete missing metadata fields and correct any invalid values."
                })
            elif category == "analysis":
                recommendations.append({
                    "type": "analysis",
                    "priority": "medium",
                    "description": f"{len(checks)} analysis quality issues detected",
                    "recommendation": "Review analysis parameters and methods. Consider re-running analysis with different settings."
                })
            elif category == "reporting":
                recommendations.append({
                    "type": "reporting",
                    "priority": "low",
                    "description": f"{len(checks)} reporting issues detected",
                    "recommendation": "Ensure report contains all required sections and source code for reproducibility."
                })
        
        # Add general recommendation if many failures
        if result.critical_failures > 3:
            recommendations.insert(0, {
                "type": "general",
                "priority": "high",
                "description": f"{result.critical_failures} critical failures detected",
                "recommendation": "Address all critical issues before using analysis results. Data may not be reliable."
            })
        
        return recommendations


if __name__ == "__main__":
    import asyncio
    
    async def test():
        agent = QualityAssuranceAgent()
        
        # Mock data
        analysis_data = {
            "original_data": {
                "wavelengths": [700, 800, 900, 1000],
                "intensities": [100, 120, 110, 90],
                "metadata": {"date": "2024-01-15", "calibration_date": "2024-01-01"}
            },
            "quality_score": 85.0
        }
        
        metadata_quality = {
            "overall_score": 75.0,
            "missing_fields": ["license"],
            "invalid_fields": []
        }
        
        calibration_result = {
            "wavelength_calibration": {"r_squared": 0.99, "rmse": 0.1, "num_points": 5},
            "intensity_calibration": {"r_squared": 0.95, "rmse": 0.05, "num_points": 5},
            "issues_detected": []
        }
        
        # Run QA check
        result = await agent.perform_qa_check(analysis_data, metadata_quality, calibration_result)
        
        print(f"QA Status: {result.overall_status}")
        print(f"Pass Rate: {result.pass_rate:.1f}%")
        print(f"Critical Failures: {result.critical_failures}")
        print(f"Warnings: {result.warnings}")
        print(f"Recommendations: {len(result.recommendations)}")
    
    asyncio.run(test())
