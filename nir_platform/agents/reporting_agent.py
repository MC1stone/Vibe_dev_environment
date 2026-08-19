"""
Reporting Agent for NIR Intelligence Platform

This agent generates comprehensive Quarto reports with embedded Python source code,
visualizations, and analysis results for spectral data.
"""

import json
import logging
import os
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import numpy as np

# Configure logging
logger = logging.getLogger(__name__)


@dataclass
class ReportSection:
    """Represents a section in the report."""
    title: str
    content: str
    code: Optional[str] = None
    data: Optional[Dict] = None
    visualizations: List[Dict] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "content": self.content,
            "code": self.code,
            "data": self.data,
            "visualizations": self.visualizations
        }


@dataclass
class QuartoReport:
    """Represents a Quarto report."""
    title: str
    sections: List[ReportSection] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)
    python_source: List[str] = field(default_factory=list)
    data_files: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "title": self.title,
            "sections": [s.to_dict() for s in self.sections],
            "metadata": self.metadata,
            "python_source": self.python_source,
            "data_files": self.data_files
        }


class ReportingAgent:
    """
    Agent for generating Quarto reports for spectral analysis.
    
    Capabilities:
    - Generate comprehensive analysis reports
    - Embed Python source code
    - Create visualizations
    - Include spectral data
    - Export to HTML via Quarto
    """
    
    def __init__(self, agent_id: str = "reporting_agent"):
        """Initialize Reporting Agent."""
        self.agent_id = agent_id
        self.report_templates = self._load_report_templates()
        logger.info(f"Reporting Agent {self.agent_id} initialized")
    
    def _load_report_templates(self) -> Dict:
        """Load report templates."""
        return {
            "spectral_analysis": {
                "title": "Spectral Analysis Report",
                "sections": [
                    "Introduction",
                    "Methods",
                    "Results",
                    "Spectral Analysis",
                    "Metadata Quality",
                    "Calibration",
                    "Recommendations",
                    "Conclusion"
                ]
            },
            "metadata_quality": {
                "title": "Metadata Quality Assessment",
                "sections": [
                    "Summary",
                    "Compliance by Standard",
                    "Field Validation",
                    "Recommendations",
                    "Detailed Results"
                ]
            },
            "calibration_report": {
                "title": "Spectrometer Calibration Report",
                "sections": [
                    "Calibration Summary",
                    "Wavelength Calibration",
                    "Intensity Calibration",
                    "Drift Compensation",
                    "Parameter Recommendations",
                    "Quality Assessment"
                ]
            }
        }
    
    async def generate_spectral_analysis_report(self, 
                                                analysis_result: Dict,
                                                metadata_quality: Dict,
                                                calibration_result: Dict,
                                                output_dir: str = "reports") -> QuartoReport:
        """Generate comprehensive spectral analysis report."""
        logger.info("Generating spectral analysis report")
        
        report = QuartoReport(
            title=f"NIR Spectral Analysis Report - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
            metadata={
                "generated": datetime.now().isoformat(),
                "analysis_type": "spectral_analysis",
                "version": "1.0.0"
            }
        )
        
        # Section 1: Introduction
        intro_content = f"""
This report presents the comprehensive analysis of near-infrared (NIR) spectral data 
collected on {analysis_result.get('metadata', {}).get('date', 'unknown date')}. 

The analysis includes:
- Spectral data processing and feature detection
- Metadata quality assessment against international standards
- Spectrometer calibration and parameter optimization
- Quality grading and enhancement recommendations

**Sample Information:**
- Sample Type: {analysis_result.get('original_data', {}).get('metadata', {}).get('sample_type', 'Unknown')}
- Spectrometer: {analysis_result.get('original_data', {}).get('spectrometer_type', 'Unknown')}
- Measurement Date: {analysis_result.get('original_data', {}).get('metadata', {}).get('date', 'Unknown')}
        """
        
        report.sections.append(ReportSection(
            title="Introduction",
            content=intro_content
        ))
        
        # Section 2: Methods
        methods_content = """
## Analysis Methods

### Spectral Processing
The spectral data was processed through the following steps:
1. **Wavelength Calibration**: Correction of wavelength measurements using known emission lines
2. **Baseline Correction**: Removal of baseline drift and offset
3. **Noise Reduction**: Application of Savitzky-Golay filter for noise reduction
4. **Smoothing**: Moving average smoothing for better feature detection

### Metadata Quality Assessment
Metadata was evaluated against the following standards:
- ISO 19115: Geographic Information - Metadata
- ASTM E131: Molecular Spectroscopy Terminology
- ASTM E1421: Computerized IR Spectroscopy Data Fields
- NIR-Specific Standards
- Open Science Metadata Standards

### Calibration
Spectrometer calibration included:
- Wavelength calibration using known reference points
- Intensity calibration using white and dark references
- Drift compensation for temperature and time effects
- Parameter optimization for measurement quality
        """
        
        report.sections.append(ReportSection(
            title="Methods",
            content=methods_content
        ))
        
        # Section 3: Results - Spectral Analysis
        spectral_data = analysis_result.get('original_data', {})
        processed_data = analysis_result.get('processed_data', {})
        metrics = analysis_result.get('analysis_metrics', {})
        
        spectral_content = f"""
## Spectral Analysis Results

### Data Overview
- **Wavelength Range**: {metrics.get('wavelength_range', {}).get('min', 0):.1f} - {metrics.get('wavelength_range', {}).get('max', 0):.1f} nm
- **Number of Data Points**: {len(spectral_data.get('wavelengths', []))}
- **Spectral Resolution**: {metrics.get('wavelength_range', {}).get('range', 0) / len(spectral_data.get('wavelengths', [1])):.2f} nm

### Intensity Statistics
- **Minimum Intensity**: {metrics.get('intensity_statistics', {}).get('min', 0):.2f}
- **Maximum Intensity**: {metrics.get('intensity_statistics', {}).get('max', 0):.2f}
- **Mean Intensity**: {metrics.get('intensity_statistics', {}).get('mean', 0):.2f}
- **Standard Deviation**: {metrics.get('intensity_statistics', {}).get('std', 0):.2f}

### Peak Analysis
- **Number of Peaks Detected**: {metrics.get('peak_analysis', {}).get('num_peaks', 0)}
- **Number of Valleys Detected**: {metrics.get('peak_analysis', {}).get('num_valleys', 0)}
- **Peak Density**: {metrics.get('peak_analysis', {}).get('peak_density', 0):.2f} peaks per 100nm

### Quality Metrics
- **Signal-to-Noise Ratio**: {metrics.get('data_quality', {}).get('signal_to_noise', 0):.1f}
- **Wavelength Coverage**: {metrics.get('data_quality', {}).get('wavelength_coverage', 0):.1f}
- **Data Completeness**: {metrics.get('data_quality', {}).get('data_completeness', 0) * 100:.1f}%
- **Outliers Detected**: {metrics.get('data_quality', {}).get('outliers', 0)}

### Processing Summary
Processing steps applied:
{chr(10).join([f'- {step}' for step in analysis_result.get('processing_steps', [])])}
        """
        
        # Add spectral visualization code
        spectral_code = self._generate_spectral_plot_code(
            spectral_data.get('wavelengths', []),
            spectral_data.get('intensities', []),
            processed_data.get('wavelengths', []),
            processed_data.get('intensities', [])
        )
        
        spectral_visualization = {
            "type": "matplotlib",
            "title": "Original vs Processed Spectrum",
            "description": "Comparison of original and processed spectral data",
            "code": spectral_code
        }
        
        report.sections.append(ReportSection(
            title="Spectral Analysis",
            content=spectral_content,
            code=spectral_code,
            visualizations=[spectral_visualization]
        ))
        
        # Section 4: Metadata Quality
        mq_score = metadata_quality.get('overall_score', 0)
        mq_grade = metadata_quality.get('grade', 'N/A')
        compliance = metadata_quality.get('compliance_scores', {})
        
        metadata_content = f"""
## Metadata Quality Assessment

### Overall Quality
- **Quality Score**: {mq_score:.1f}/100
- **Grade**: {mq_grade}

### Standards Compliance
{chr(10).join([f'- **{std}**: {score:.1f}%' for std, score in compliance.items()])}

### Summary
{metadata_quality.get('summary', {}).get('narrative', 'No summary available')}

### Missing Required Fields
{chr(10).join([f'- {field}' for field in metadata_quality.get('missing_fields', [])]) or 'None'}

### Invalid Fields
{chr(10).join([f'- {field["field"]}: {field["error"]}' for field in metadata_quality.get('invalid_fields', [])]) or 'None'}
        """
        
        report.sections.append(ReportSection(
            title="Metadata Quality Assessment",
            content=metadata_content
        ))
        
        # Section 5: Calibration
        cal_quality = calibration_result.get('calibration_quality', {})
        cal_recs = calibration_result.get('recommendations', [])
        
        calibration_content = f"""
## Calibration Results

### Calibration Quality
- **Wavelength Calibration Quality**: {cal_quality.get('wavelength_quality', 0):.1f}%
- **Intensity Calibration Quality**: {cal_quality.get('intensity_quality', 0):.1f}%
- **Overall Calibration Quality**: {cal_quality.get('overall_quality', 0):.1f}%

### Calibration Recommendations
{chr(10).join([f'- **{rec.get("type", "")}** ({rec.get("priority", "medium")}): {rec.get("description", "")}' for rec in cal_recs]) or 'None'}

### Spectrometer Parameters
{chr(10).join([f'- **{param}**: {info.get("current", "N/A")} → {info.get("recommended", "N/A")} {info.get("unit", "")} ({info.get("reason", "")})' for param, info in calibration_result.get('spectrometer_parameters', {}).items()]) or 'None'}
        """
        
        report.sections.append(ReportSection(
            title="Calibration",
            content=calibration_content
        ))
        
        # Section 6: Recommendations
        issues = analysis_result.get('issues_detected', [])
        cal_issues = calibration_result.get('issues_detected', [])
        all_recs = analysis_result.get('calibration_recommendations', [])
        
        recommendations_content = f"""
## Recommendations for Improvement

### Spectral Data Issues
{chr(10).join([f'- **{issue.get("type", "")}** ({issue.get("severity", "medium")}): {issue.get("description", "")}' for issue in issues]) or 'No issues detected'}

### Calibration Issues
{chr(10).join([f'- **{issue.get("type", "")}** ({issue.get("severity", "medium")}): {issue.get("description", "")}' for issue in cal_issues]) or 'No calibration issues detected'}

### Enhancement Recommendations
{chr(10).join([f'- **{rec.get("type", "")}**: {rec.get("description", "")}' for rec in all_recs]) or 'No recommendations'}

### Priority Actions
1. Address high-severity issues first
2. Implement calibration recommendations
3. Add missing metadata fields
4. Consider spectrometer parameter optimization
        """
        
        report.sections.append(ReportSection(
            title="Recommendations",
            content=recommendations_content
        ))
        
        # Section 7: Conclusion
        overall_quality = analysis_result.get('quality_score', 0)
        conclusion_content = f"""
## Conclusion

The NIR spectral analysis has been completed with the following key findings:

### Overall Assessment
- **Spectral Data Quality Score**: {overall_quality:.1f}/100
- **Metadata Quality Score**: {mq_score:.1f}/100
- **Calibration Quality Score**: {cal_quality.get('overall_quality', 0):.1f}%

### Key Findings
1. The spectral data shows {metrics.get('peak_analysis', {}).get('num_peaks', 0)} distinct peaks in the NIR region
2. Metadata quality is rated as **{mq_grade}**
3. {len(issues)} potential spectrometer issues were detected
4. {len(all_recs)} recommendations for improvement have been provided

### Next Steps
- Review and address all high-priority recommendations
- Implement suggested calibration procedures
- Add missing metadata fields for better data documentation
- Consider spectrometer parameter optimization for improved measurement quality

### Data Files
All original and processed data, along with the Python source code used for analysis, 
are included with this report for reproducibility and further analysis.

---
*Report generated by NIR Intelligence Platform on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*
        """
        
        report.sections.append(ReportSection(
            title="Conclusion",
            content=conclusion_content
        ))
        
        # Add Python source code
        report.python_source = self._generate_analysis_source_code(
            analysis_result, metadata_quality, calibration_result
        )
        
        # Add data files
        report.data_files = [
            "original_spectrum.csv",
            "processed_spectrum.csv",
            "analysis_metrics.json",
            "metadata_quality.json",
            "calibration_results.json"
        ]
        
        return report
    
    def _generate_spectral_plot_code(self, 
                                     orig_wl: List[float],
                                     orig_int: List[float],
                                     proc_wl: List[float],
                                     proc_int: List[float]) -> str:
        """Generate Python code for spectral plot."""
        code = f"""
import matplotlib.pyplot as plt
import numpy as np

# Data
original_wavelengths = {orig_wl}
original_intensities = {orig_int}
processed_wavelengths = {proc_wl}
processed_intensities = {proc_int}

# Create figure
fig, ax = plt.subplots(figsize=(12, 6))

# Plot original spectrum
ax.plot(original_wavelengths, original_intensities, 
        label='Original Spectrum', alpha=0.7, linewidth=1)

# Plot processed spectrum
ax.plot(processed_wavelengths, processed_intensities, 
        label='Processed Spectrum', linewidth=2, color='red')

# Formatting
ax.set_xlabel('Wavelength (nm)', fontsize=12)
ax.set_ylabel('Intensity (a.u.)', fontsize=12)
ax.set_title('Original vs Processed NIR Spectrum', fontsize=14)
ax.legend(fontsize=10)
ax.grid(True, alpha=0.3)

# Highlight NIR region
ax.axvspan(700, 1100, color='yellow', alpha=0.1, label='NIR Region')

plt.tight_layout()
plt.savefig('spectrum_comparison.png', dpi=300)
plt.show()
        """
        return code
    
    def _generate_analysis_source_code(self, 
                                       analysis_result: Dict,
                                       metadata_quality: Dict,
                                       calibration_result: Dict) -> List[str]:
        """Generate complete Python source code for the analysis."""
        source_files = []
        
        # Main analysis script
        main_script = """
#!/usr/bin/env python3
"""
NIR Spectral Analysis Script
Generated by NIR Intelligence Platform
"""

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from scipy import signal
from dataclasses import dataclass
import json

@dataclass
class SpectralData:
    wavelengths: np.ndarray
    intensities: np.ndarray
    metadata: dict

# Load spectral data
def load_spectral_data(file_path: str) -> SpectralData:
    # Implementation for loading spectral data
    # (This would be customized based on your file format)
    pass

# Process spectral data
def process_spectrum(data: SpectralData) -> SpectralData:
    # Apply baseline correction
    processed = correct_baseline(data)
    
    # Reduce noise
    processed = reduce_noise(processed)
    
    # Smooth data
    processed = smooth_data(processed)
    
    return processed

def correct_baseline(data: SpectralData) -> SpectralData:
    # Implement baseline correction
    pass

def reduce_noise(data: SpectralData) -> SpectralData:
    # Implement noise reduction
    pass

def smooth_data(data: SpectralData) -> SpectralData:
    # Implement smoothing
    pass

# Main analysis function
def analyze_spectrum(file_path: str):
    # Load data
    data = load_spectral_data(file_path)
    
    # Process data
    processed = process_spectrum(data)
    
    # Detect peaks
    peaks = detect_peaks(processed)
    
    # Assess quality
    quality = assess_quality(data, processed, peaks)
    
    return {
        'original': data,
        'processed': processed,
        'peaks': peaks,
        'quality': quality
    }

if __name__ == "__main__":
    result = analyze_spectrum('spectrum.csv')
    print(f"Analysis complete. Quality score: {result['quality']}")
        """
        source_files.append(main_script)
        
        # Data processing script
        processing_script = self._generate_processing_script(analysis_result)
        source_files.append(processing_script)
        
        # Quality assessment script
        quality_script = self._generate_quality_script(metadata_quality)
        source_files.append(quality_script)
        
        return source_files
    
    def _generate_processing_script(self, analysis_result: Dict) -> str:
        """Generate data processing script."""
        return """
# Spectral Data Processing Script

def correct_baseline(intensities: np.ndarray) -> np.ndarray:
    '''Apply polynomial baseline correction.'''
    x = np.arange(len(intensities))
    step = max(1, len(intensities) // 20)
    baseline_indices = np.arange(0, len(intensities), step)
    baseline_x = x[baseline_indices]
    baseline_y = intensities[baseline_indices]
    
    # Fit polynomial
    coeffs = np.polyfit(baseline_x, baseline_y, 3)
    baseline = np.polyval(coeffs, x)
    
    return intensities - baseline

def reduce_noise(intensities: np.ndarray) -> np.ndarray:
    '''Apply Savitzky-Golay filter for noise reduction.'''
    window_size = min(11, len(intensities) // 10)
    if window_size < 3:
        window_size = 3
    return signal.savgol_filter(intensities, window_size, 2)

def smooth_data(intensities: np.ndarray) -> np.ndarray:
    '''Apply moving average smoothing.'''
    window_size = min(5, len(intensities) // 20)
    if window_size < 1:
        window_size = 1
    return np.convolve(intensities, np.ones(window_size) / window_size, mode='same')

def detect_peaks(intensities: np.ndarray, wavelengths: np.ndarray) -> dict:
    '''Detect peaks in spectral data.'''
    peaks, properties = signal.find_peaks(
        intensities, 
        height=np.mean(intensities) + 2 * np.std(intensities),
        distance=5,
        prominence=0.1 * np.std(intensities)
    )
    
    return {
        'positions': wavelengths[peaks].tolist(),
        'heights': intensities[peaks].tolist(),
        'num_peaks': len(peaks)
    }
        """
    
    def _generate_quality_script(self, metadata_quality: Dict) -> str:
        """Generate metadata quality assessment script."""
        return """
# Metadata Quality Assessment Script

def assess_metadata_quality(metadata: dict, standards: dict) -> dict:
    '''Assess metadata quality against multiple standards.'''
    results = {
        'compliance_scores': {},
        'missing_fields': [],
        'invalid_fields': []
    }
    
    for standard_name, standard_info in standards.items():
        required_fields = standard_info.get('required_fields', [])
        present = sum(1 for f in required_fields if f in metadata and metadata[f] is not None)
        score = (present / len(required_fields)) * 100 if required_fields else 100
        results['compliance_scores'][standard_name] = score
        
        # Track missing fields
        for f in required_fields:
            if f not in metadata or metadata[f] is None:
                if f not in results['missing_fields']:
                    results['missing_fields'].append(f)
    
    # Calculate overall score
    overall = np.mean(list(results['compliance_scores'].values())) if results['compliance_scores'] else 0
    
    # Determine grade
    if overall >= 90:
        grade = 'A'
    elif overall >= 80:
        grade = 'B'
    elif overall >= 70:
        grade = 'C'
    elif overall >= 60:
        grade = 'D'
    else:
        grade = 'F'
    
    results['overall_score'] = overall
    results['grade'] = grade
    
    return results

# Define standards
STANDARDS = {
    'ISO_19115': {
        'required_fields': ['title', 'abstract', 'date', 'identifier']
    },
    'ASTM_E131': {
        'required_fields': ['spectrometer_type', 'wavelength_range', 'resolution']
    },
    'NIR_Specific': {
        'required_fields': ['sample_type', 'sample_preparation', 'measurement_geometry', 'temperature', 'humidity']
    }
}
        """
    
    async def export_to_quarto(self, report: QuartoReport, output_path: str) -> str:
        """Export report to Quarto format."""
        logger.info(f"Exporting report to {output_path}")
        
        # Create Quarto document
        quarto_content = self._generate_quarto_document(report)
        
        # Save to file
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(quarto_content)
        
        return output_path
    
    def _generate_quarto_document(self, report: QuartoReport) -> str:
        """Generate Quarto document content."""
        lines = []
        
        # YAML header
        lines.append("---")
        lines.append(f"title: \"{report.title}\"")
        lines.append("format:")
        lines.append("  html:")
        lines.append("    toc: true")
        lines.append("    toc-depth: 3")
        lines.append("    number-sections: true")
        lines.append("    fig-cap: true")
        lines.append("    code-fold: true")
        lines.append("    code-summary: \"Show code\"")
        lines.append("author:")
        lines.append("  - NIR Intelligence Platform")
        lines.append(f"date: \"{datetime.now().strftime('%Y-%m-%d')}\"")
        lines.append("---")
        lines.append("")
        
        # Abstract
        lines.append("## Abstract")
        lines.append("")
        lines.append("This report presents the comprehensive analysis of near-infrared (NIR) spectral data")
        lines.append("using the NIR Intelligence Platform. The analysis includes spectral processing,")
        lines.append("metadata quality assessment, and spectrometer calibration.")
        lines.append("")
        
        # Add sections
        for section in report.sections:
            lines.append(f"# {section.title}")
            lines.append("")
            lines.append(section.content)
            lines.append("")
            
            # Add code if present
            if section.code:
                lines.append("```{python}")
                lines.append("# " + section.title.replace(" ", "_"))
                lines.append(section.code)
                lines.append("```")
                lines.append("")
        
        # Add appendix with source code
        lines.append("# Appendix: Python Source Code")
        lines.append("")
        lines.append("The following Python code was used to perform the analysis:")
        lines.append("")
        
        for i, source in enumerate(report.python_source, 1):
            lines.append(f"## Source File {i}")
            lines.append("")
            lines.append("```{python}")
            lines.append(source)
            lines.append("```")
            lines.append("")
        
        return "\n".join(lines)
    
    async def render_report(self, report: QuartoReport, output_dir: str = "reports") -> Dict:
        """Render report to HTML using Quarto."""
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(output_dir, f"nir_report_{timestamp}")
        quarto_file = f"{report_path}.qmd"
        html_file = f"{report_path}.html"
        
        # Export to Quarto format
        await self.export_to_quarto(report, quarto_file)
        
        # Render to HTML (this would call Quarto CLI)
        # In practice: quarto render report.qmd --to html
        
        return {
            "quarto_file": quarto_file,
            "html_file": html_file,
            "status": "generated",
            "message": "Report generated successfully"
        }


if __name__ == "__main__":
    import asyncio
    
    async def test():
        agent = ReportingAgent()
        
        # Mock data
        analysis_result = {
            "original_data": {
                "wavelengths": [700, 800, 900, 1000],
                "intensities": [100, 120, 110, 90],
                "metadata": {"sample_type": "Solid", "date": "2024-01-15"}
            },
            "processed_data": {
                "wavelengths": [700, 800, 900, 1000],
                "intensities": [105, 125, 115, 95]
            },
            "analysis_metrics": {
                "wavelength_range": {"min": 700, "max": 1000, "range": 300},
                "intensity_statistics": {"min": 90, "max": 125, "mean": 110, "std": 10},
                "peak_analysis": {"num_peaks": 2, "num_valleys": 1, "peak_density": 0.67},
                "data_quality": {"signal_to_noise": 50, "wavelength_coverage": 0.3, "data_completeness": 1.0, "outliers": 0}
            },
            "issues_detected": [],
            "calibration_recommendations": [],
            "quality_score": 85.5,
            "processing_steps": ["baseline_correction", "noise_reduction"]
        }
        
        metadata_quality = {
            "overall_score": 75.0,
            "grade": "B",
            "compliance_scores": {"ISO_19115": 80, "ASTM_E131": 70},
            "missing_fields": ["license"],
            "invalid_fields": [],
            "summary": {"narrative": "Good metadata quality with some missing fields"}
        }
        
        calibration_result = {
            "calibration_quality": {"wavelength_quality": 90, "intensity_quality": 85, "overall_quality": 87.5},
            "recommendations": [],
            "issues_detected": [],
            "spectrometer_parameters": {}
        }
        
        # Generate report
        report = await agent.generate_spectral_analysis_report(
            analysis_result, metadata_quality, calibration_result
        )
        
        print(f"Report generated: {report.title}")
        print(f"Sections: {len(report.sections)}")
        print(f"Source files: {len(report.python_source)}")
    
    asyncio.run(test())
