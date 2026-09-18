"""
Reporting Agent for NIR Intelligence Platform

This agent generates comprehensive Quarto reports with embedded Python source code,
visualizations, and analysis results for spectral data.
"""

import asyncio
import base64
import io
import json
import logging
import os
import re
import tempfile
from datetime import datetime
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
import numpy as np

try:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
except ImportError:  # graceful degrade: reports render without figures
    matplotlib = None
    plt = None

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
                                                output_dir: str = "reports",
                                                hardware_info: Optional[Dict] = None) -> QuartoReport:
        """Generate comprehensive spectral analysis report.

        ``hardware_info`` (collected by the HardwareInfoAgent) is optional;
        when present a Hardware Information section is appended to the
        report so the spectrometer provenance travels with the report.
        """
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
        analyte_cal = calibration_result.get('analyte_calibration')

        analyte_block = ""
        if analyte_cal:
            wl_coef = list(zip(analyte_cal.get('wavelengths', []),
                              analyte_cal.get('coefficients', [])))
            coef_lines = (chr(10).join(
                [f"  - {w:.0f} nm: {c:+.4e}" for w, c in wl_coef])
                or '  None')
            intercept_ = analyte_cal.get('intercept', 0.0)
            # Build a human-readable regression equation.
            eq_terms = []
            for w, c in wl_coef:
                eq_terms.append(f"({c:+.4e})\u00b7I_{{{int(w)}}}")
            equation = (
                f"Brix = {intercept_:.4f} + "
                + " + ".join(eq_terms)
                if eq_terms else f"Brix = {intercept_:.4f}")
            outliers_removed = analyte_cal.get('outliers_removed', 0)
            outlier_method = analyte_cal.get('outlier_method', 'none')
            outlier_line = (
                f"\n- **Outliers removed**: {outliers_removed} "
                f"({outlier_method})"
                if outliers_removed else "\n- **Outliers removed**: 0")
            analyte_block = f"""
### NIR \u2192 Brix Calibration (Ripeness Model) - PLS
- **Analyte**: {analyte_cal.get('analyte', 'Brix')}
- **Method**: {analyte_cal.get('method', 'N/A')}
- **Samples**: {analyte_cal.get('num_samples', 0)}
- **Features**: {analyte_cal.get('num_features', 0)} channels
- **Components**: {analyte_cal.get('num_components', 0)}
- **Brix range**: {analyte_cal.get('brix_range', [0, 0])[0]:.2f} \u2013 {analyte_cal.get('brix_range', [0, 0])[1]:.2f} \u00b0Brix
- **R\u00b2 (cross-validated)**: {analyte_cal.get('r_squared_cv', 0):.4f}
- **RMSE (cross-validated)**: {analyte_cal.get('rmse_cv', 0):.4f} \u00b0Brix
- **R\u00b2 (calibration)**: {analyte_cal.get('r_squared_cal', 0):.4f}
- **RMSE (calibration)**: {analyte_cal.get('rmse_cal', 0):.4f} \u00b0Brix{outlier_line}
- **Intercept**: {analyte_cal.get('intercept', 0):.4f}
- **Notes**: {analyte_cal.get('notes', '')}

#### Regression equation (raw intensity scale)
```
{equation}
```

#### Regression coefficients (raw intensity scale)
{coef_lines}
"""

        # Neural-network (MLP) calibration, fitted in parallel to PLS.
        neural_cal = calibration_result.get('neural_calibration')
        neural_block = ""
        if neural_cal:
            neural_block = f"""
### NIR \u2192 Brix Calibration - Neural Network (MLP)
- **Analyte**: {neural_cal.get('analyte', 'Brix')}
- **Method**: {neural_cal.get('method', 'N/A')}
- **Architecture**: {tuple(neural_cal.get('hidden_layer_sizes', []))} hidden layers (ReLU, Adam)
- **Samples**: {neural_cal.get('num_samples', 0)}
- **Features**: {neural_cal.get('num_features', 0)} channels
- **R\u00b2 (cross-validated)**: {neural_cal.get('r_squared_cv', 0):.4f}
- **RMSE (cross-validated)**: {neural_cal.get('rmse_cv', 0):.4f} \u00b0Brix
- **R\u00b2 (calibration)**: {neural_cal.get('r_squared_cal', 0):.4f}
- **RMSE (calibration)**: {neural_cal.get('rmse_cal', 0):.4f} \u00b0Brix
- **Outliers removed**: {neural_cal.get('outliers_removed', 0)}
- **Notes**: {neural_cal.get('notes', '')}
"""

        # Side-by-side PLS vs MLP comparison so the user can see which model
        # generalises best at a glance (higher R^2_cv / lower RMSE_cv wins).
        comparison_block = ""
        if analyte_cal and neural_cal:
            pls_r2 = float(analyte_cal.get('r_squared_cv', 0) or 0)
            pls_rmse = float(analyte_cal.get('rmse_cv', 0) or 0)
            nn_r2 = float(neural_cal.get('r_squared_cv', 0) or 0)
            nn_rmse = float(neural_cal.get('rmse_cv', 0) or 0)
            if pls_r2 > nn_r2:
                best, best_note = "PLS", "Higher cross-validated R\u00b2 (less overfitting risk on small datasets)"
            elif nn_r2 > pls_r2:
                best, best_note = "MLP", "Higher cross-validated R\u00b2 (captures non-linearity)"
            else:
                best, best_note = "Tie", "Both models perform equally on cross-validation"
            comparison_block = f"""
### Model Comparison: PLS vs Neural Network (MLP)

| Model | R\u00b2 (CV) | RMSE (CV, \u00b0Brix) | Samples | Outliers removed |
|-------|-----------|------------------|---------|------------------|
| **PLS** | {pls_r2:.4f} | {pls_rmse:.4f} | {analyte_cal.get('num_samples', 0)} | {analyte_cal.get('outliers_removed', 0)} |
| **MLP** | {nn_r2:.4f} | {nn_rmse:.4f} | {neural_cal.get('num_samples', 0)} | {neural_cal.get('outliers_removed', 0)} |

**Best model (cross-validated): {best}.** {best_note}.
"""


        calibration_content = f"""
## Calibration Results

### Calibration Quality
- **Wavelength Calibration Quality**: {cal_quality.get('wavelength_quality', 0):.1f}%
- **Intensity Calibration Quality**: {cal_quality.get('intensity_quality', 0):.1f}%
- **Analyte (NIR\u2192Brix) Quality (PLS)**: {cal_quality.get('analyte_quality', 0):.1f}%
- **Neural-Network Quality (MLP)**: {cal_quality.get('neural_quality', 0):.1f}%
- **Overall Calibration Quality**: {cal_quality.get('overall_quality', 0):.1f}%
{analyte_block}{neural_block}{comparison_block}
### Calibration Recommendations
{chr(10).join([f'- **{rec.get("type", "")}** ({rec.get("priority", "medium")}): {rec.get("description", "")}' for rec in cal_recs]) or 'None'}

### Spectrometer Parameters
{chr(10).join([f'- **{param}**: {info.get("current", "N/A")} → {info.get("recommended", "N/A")} {info.get("unit", "")} ({info.get("reason", "")})' for param, info in calibration_result.get('spectrometer_parameters', {}).items()]) or 'None'}
        """
        
        calibration_plot_code = ""
        if analyte_cal:
            calibration_plot_code = self._generate_calibration_plot_code(
                analyte_cal, analysis_result)
            # Attach the data the plot code reads from __cal_data__ so the
            # fallback renderer can execute it without embedding huge lists.
            # Prefer the model's own predictions (kept vs removed outliers)
            # so the plot matches the fitted model; keep the legacy raw
            # coefficients/matrix as a fallback when no plot data exists.
            orig_meta = analysis_result.get('original_data', {}).get('metadata', {})
            report.metadata['cal_plot_data'] = {
                'coefficients': analyte_cal.get('coefficients', []),
                'intercept': analyte_cal.get('intercept', 0.0),
                'brix': orig_meta.get('Brix', []) or orig_meta.get('brix', []),
                'intensity_matrix': orig_meta.get('intensity_matrix', []),
                'plot_measured': analyte_cal.get('plot_measured'),
                'plot_predicted_kept': analyte_cal.get('plot_predicted_kept'),
                'plot_predicted_removed': analyte_cal.get('plot_predicted_removed'),
                'r_squared_cv': analyte_cal.get('r_squared_cv', 0.0),
                'rmse_cv': analyte_cal.get('rmse_cv', 0.0),
                'preprocessing': analyte_cal.get('preprocessing', 'raw'),
                'outliers_removed': analyte_cal.get('outliers_removed', 0),
            }

        report.sections.append(ReportSection(
            title="Calibration",
            content=calibration_content,
            code=calibration_plot_code or None
        ))
        
        # Section 6: Recommendations
        issues = analysis_result.get('issues_detected', [])
        cal_issues = calibration_result.get('issues_detected', [])
        all_recs = analysis_result.get('calibration_recommendations', [])
        
        def _issue_block(title: str, items: list) -> str:
            if not items:
                return f"### {title}\nNo issues detected.\n"
            lines = [f"### {title}"]
            for it in items:
                sev = it.get("severity", it.get("priority", "medium"))
                lines.append(
                    f"#### {it.get('type', '').replace('_', ' ').title()} "
                    f"({sev})\n{it.get('description', '')}"
                )
                if it.get("explanation"):
                    lines.append(f"\n{it['explanation']}")
                if it.get("solutions"):
                    lines.append("\n**How to fix / apply it:**")
                    for sol in it["solutions"]:
                        lines.append(f"- **{sol['title']}.** {sol['steps']}")
                lines.append("")
            return "\n".join(lines)

        def _rec_block(title: str, items: list) -> str:
            if not items:
                return f"### {title}\nNo recommendations.\n"
            lines = [f"### {title}"]
            for it in items:
                lines.append(
                    f"#### {it.get('type', '').replace('_', ' ').title()} "
                    f"({it.get('priority', 'medium')})\n{it.get('description', '')}"
                )
                if it.get("method"):
                    lines.append(f"\n*Method:* {it['method']}")
                if it.get("explanation"):
                    lines.append(f"\n{it['explanation']}")
                if it.get("solutions"):
                    lines.append("\n**How to apply it:**")
                    for sol in it["solutions"]:
                        lines.append(f"- **{sol['title']}.** {sol['steps']}")
                lines.append("")
            return "\n".join(lines)

        recommendations_content = f"""
## Recommendations for Improvement

{_issue_block('Spectral Data Issues', issues)}
{_issue_block('Calibration Issues', cal_issues)}
{_rec_block('Enhancement Recommendations', all_recs)}

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
        
        # Hardware Information section (optional): surface the consolidated
        # spectrometer / sensor info collected by the HardwareInfoAgent so the
        # report records what hardware produced the data.
        if hardware_info:
            hw_content = self._generate_hardware_content(hardware_info)
            if hw_content:
                report.sections.append(ReportSection(
                    title="Hardware Information",
                    content=hw_content
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
        """Generate Python code for spectral plot.

        The cell is executed by the Quarto jupyter kernel (and by the
        in-process fallback). It must NOT call plt.show() (the Agg backend
        is non-interactive and Quarto captures the figure itself) nor
        plt.savefig() to a hard-coded path (that litters a file in the CWD
        and can fail on a read-only working dir). Quarto renders the last
        figure produced in the cell automatically.
        """
        code = f"""
import matplotlib.pyplot as plt
import numpy as np
plt.close('all')

# Data
original_wavelengths = {orig_wl}
original_intensities = {orig_int}
processed_wavelengths = {proc_wl}
processed_intensities = {proc_int}

if not original_wavelengths and not processed_wavelengths:
    fig, ax = plt.subplots(figsize=(7, 2))
    ax.text(0.5, 0.5, 'Spectral plot unavailable (no wavelength data)',
            ha='center', va='center', transform=ax.transAxes, color='#888')
    ax.axis('off')
else:
    fig, ax = plt.subplots(figsize=(12, 6))
    if original_wavelengths:
        ax.plot(original_wavelengths, original_intensities,
                label='Original Spectrum', alpha=0.7, linewidth=1)
    if processed_wavelengths:
        ax.plot(processed_wavelengths, processed_intensities,
                label='Processed Spectrum', linewidth=2, color='red')
    ax.set_xlabel('Wavelength (nm)', fontsize=12)
    ax.set_ylabel('Intensity (a.u.)', fontsize=12)
    ax.set_title('Original vs Processed NIR Spectrum', fontsize=14)
    ax.legend(fontsize=10)
    ax.grid(True, alpha=0.3)
    ax.axvspan(700, 1100, color='yellow', alpha=0.1, label='NIR Region')
    plt.tight_layout()
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
\"\"\"
NIR Spectral Analysis Script
Generated by NIR Intelligence Platform
\"\"\"

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
    
    def _validate_executable_cells(self, quarto_content: str,
                                   report: QuartoReport) -> str:
        """Pre-validate every ```{python}``` cell so a broken cell cannot
        crash the Quarto jupyter kernel and abort the whole render.

        Mirrors the __cal_data__ inlining done by _generate_quarto_document,
        compile()s each executable cell (catching SyntaxError / unbound
        names early), and runs plot cells through the in-process Agg
        renderer to catch runtime errors. Cells that fail are rewritten to a
        display-only ```` ```{.python eval=false}```` block with the error,
        so Quarto still renders the report and the user sees what failed
        instead of an opaque subprocess rc=1.
        """
        cal_data = (report.metadata or {}).get("cal_plot_data") or {}
        cal_literal = ("__cal_data__ = "
                       + repr(self._to_py_literal(cal_data))
                       if "__cal_data__" in quarto_content else None)
        lines = quarto_content.splitlines(keepends=True)
        out: List[str] = []
        i = 0
        n = len(lines)
        while i < n:
            line = lines[i]
            stripped = line.strip()
            if stripped.startswith("```{python}"):
                block_start = i
                body: List[str] = []
                i += 1
                while i < n and not lines[i].strip().startswith("```"):
                    body.append(lines[i])
                    i += 1
                fence = lines[i] if i < n else "```\n"
                i += 1
                full_code = "".join(body)
                test_code = full_code
                if cal_literal and "__cal_data__" in full_code:
                    test_code = cal_literal + "\n" + full_code
                ok = True
                err_msg = ""
                try:
                    compile(test_code, "<quarto_cell>", "exec")
                except SyntaxError as se:
                    ok = False
                    err_msg = f"SyntaxError: {se.msg} (line {se.lineno})"
                if ok and ("matplotlib" in full_code or "plt." in full_code):
                    rendered = self._execute_plot_code_to_b64(
                        test_code, extra_ns={})
                    if rendered is None:
                        try:
                            ns = {"plt": plt, "np": np,
                                  "matplotlib": matplotlib}
                            if cal_literal and "__cal_data__" in full_code:
                                exec(compile(cal_literal, "<cal>", "exec"), ns)
                            exec(compile(full_code, "<quarto_cell>", "exec"), ns)
                        except Exception as re_exc:
                            ok = False
                            err_msg = f"{type(re_exc).__name__}: {re_exc}"
                if ok:
                    out.append(line)
                    out.extend(body)
                    out.append(fence)
                else:
                    logger.warning(f"Quarto cell failed pre-validation: {err_msg}")
                    out.append("```{.python eval=false}\n")
                    out.append("# This analysis cell could not be executed safely\n")
                    out.append(f"# and is shown for reference only.\n# Error: {err_msg}\n\n")
                    out.extend(body)
                    out.append("```\n")
            else:
                out.append(line)
                i += 1
        return "".join(out)

    async def export_to_quarto(self, report: QuartoReport, output_path: str) -> str:
        """Export report to Quarto format."""
        logger.info(f"Exporting report to {output_path}")
        
        # Create Quarto document
        quarto_content = self._generate_quarto_document(report)
        # Validate executable cells in-process so a broken cell degrades to a
        # display-only block instead of aborting the Quarto jupyter kernel.
        quarto_content = self._validate_executable_cells(quarto_content, report)
        
        # Save to file
        os.makedirs(os.path.dirname(output_path) or '.', exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(quarto_content)
        
        return output_path
    
    @staticmethod
    def _to_py_literal(obj):
        """Recursively coerce a JSON-ish object into plain Python literals.

        numpy scalars / arrays, tuples and other non-repr-safe values are
        downcast to int/float/list/None so repr() then yields valid Python
        source (and therefore a valid Quarto-jupyter cell assignment). This
        avoids the JSON-vs-Python mismatch (null/true) that previously made
        Quarto's jupyter kernel NameError on ``__cal_data__``.
        """
        import numpy as _np
        if obj is None:
            return None
        if isinstance(obj, _np.generic):
            return obj.item()
        if isinstance(obj, _np.ndarray):
            return [ReportingAgent._to_py_literal(v) for v in obj.tolist()]
        if isinstance(obj, (list, tuple)):
            return [ReportingAgent._to_py_literal(v) for v in obj]
        if isinstance(obj, dict):
            return {k: ReportingAgent._to_py_literal(v) for k, v in obj.items()}
        if isinstance(obj, (str, int, float, bool)):
            return obj
        return str(obj)

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
                # The Quarto jupyter kernel executes each cell in a fresh-ish
                # namespace, so code that reads execution variables set only by
                # the in-process fallback (e.g. __cal_data__) would NameError.
                # Inline-define those vars from report.metadata so the cell is
                # self-contained when Quarto runs it.
                code_to_emit = section.code
                if "__cal_data__" in code_to_emit:
                    cal_data = (report.metadata or {}).get("cal_plot_data") or {}
                    # Emit a valid PYTHON literal (not JSON) so the cell,
                    # which executes as Python in Quarto's jupyter kernel,
                    # does not NameError on JSON-only tokens like null/true.
                    # repr() converts None->None, True->True, floats/ints and
                    # nested lists/dicts to valid Python source. Values that
                    # are not plain literals (numpy scalars, etc.) are str()-
                    # coerced first via _to_py_literal below.
                    lines.append("__cal_data__ = "
                                 + repr(self._to_py_literal(cal_data)))
                lines.append(code_to_emit)
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
            # Display-only: the appendix is documentation/template code
            # with undefined functions and a __main__ block, so it must NOT
            # be executed by the Quarto jupyter kernel (it would NameError).
            # ```{.python eval=false} renders the code without running it.
            lines.append("```{.python eval=false}")
            lines.append(source)
            lines.append("```")
            lines.append("")
        
        return "\n".join(lines)
    
    async def render_report(self, report: QuartoReport, output_dir: str = "reports") -> Dict:
        """Render report to HTML using Quarto, with a Python fallback."""
        import shutil
        import subprocess
        try:
            import markdown
        except ImportError:
            markdown = None
        
        # Generate unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        report_path = os.path.join(output_dir, f"nir_report_{timestamp}")
        quarto_file = f"{report_path}.qmd"
        html_file = f"{report_path}.html"
        
        # Export to Quarto format
        await self.export_to_quarto(report, quarto_file)
        
        # Render to HTML. Two renderers are available:
        #   1. The Quarto CLI (`quarto render`), which spins up a jupyter
        #      kernel to execute the python cells and produces a 'native'
        #      Quarto HTML document. This is slow (kernel spinup + cell exec)
        #      and fragile in a local single-user setup: a kernel that hangs
        #      blocks the whole analysis request for up to the 120s timeout
        #      before falling back, which the user experiences as the report
        #      page polling for two minutes on every run.
        #   2. The in-process Python renderer, which converts the .qmd to HTML
        #      directly (executing the matplotlib plot cells with the Agg
        #      backend and embedding the figures as base64 PNGs). It is fast,
        #      dependency-light, and produces a complete report.
        #
        # Default to the fast in-process renderer; opt into the Quarto CLI with
        # the NIR_USE_QUARTO_CLI env var or the Django setting of the same name
        # (for users who specifically want the native Quarto render / toolchain).
        rendered = False
        use_quarto_cli = os.environ.get("NIR_USE_QUARTO_CLI", "").lower() in ("1", "true", "yes")
        if not use_quarto_cli:
            try:
                from django.conf import settings as _dj_settings
                use_quarto_cli = bool(getattr(_dj_settings, "NIR_USE_QUARTO_CLI", False))
            except Exception:
                pass
        quarto_bin = shutil.which("quarto") if use_quarto_cli else None
        if quarto_bin:
            try:
                # Quarto runs a Python kernel to execute ```{python}`` cells;
                # by default it picks the system /usr/bin/python3, which usually
                # lacks jupyter/nbformat and matplotlib. Pin it to the *current*
                # interpreter (the project venv) so the kernel can import the
                # same deps as the app. Still requires jupyter in that venv.
                import sys
                env = dict(os.environ)
                env.setdefault("QUARTO_PYTHON", sys.executable)
                proc = await asyncio.create_subprocess_exec(
                    quarto_bin, "render", quarto_file, "--to", "html",
                    stdout=asyncio.subprocess.PIPE,
                    stderr=asyncio.subprocess.PIPE,
                    env=env,
                )
                # Bound the Quarto render so a hung jupyter kernel cannot
                # block the whole analysis request forever ('stops processing
                # without error or result'). On timeout, kill the process and
                # fall through to the in-process Python renderer.
                try:
                    _stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
                except asyncio.TimeoutError:
                    logger.warning("Quarto render timed out after 120s; killing process and using Python fallback.")
                    try:
                        proc.kill()
                    except ProcessLookupError:
                        pass
                    await proc.wait()
                    stderr = b''
                if proc.returncode == 0 and os.path.exists(html_file):
                    rendered = True
                else:
                    logger.warning(
                        f"Quarto render failed (rc={proc.returncode}): "
                        f"{stderr.decode('utf-8', errors='replace') if stderr else ''}"
                    )
            except Exception as qe:
                logger.warning(f"Quarto render subprocess error: {qe}")
        elif use_quarto_cli:
            logger.info("Quarto CLI requested (NIR_USE_QUARTO_CLI) but `quarto` not found on PATH; using Python HTML fallback renderer.")
        
        # Fallback: convert the generated Quarto document to HTML in pure Python
        # so a full HTML report is produced even without Quarto installed.
        html_fragment = ""
        if not rendered:
            try:
                with open(quarto_file, "r", encoding="utf-8") as f:
                    quarto_content = f.read()
                html_body = self._markdown_to_html(quarto_content, report)
                full_html = self._wrap_html_document(report.title, html_body)
                with open(html_file, "w", encoding="utf-8") as f:
                    f.write(full_html)
                html_fragment = self._report_fragment(report.title, html_body)
                rendered = os.path.exists(html_file)
            except Exception as fe:
                logger.error(f"Python HTML fallback render failed: {fe}", exc_info=True)
        else:
            # Quarto succeeded: derive an embeddable fragment from the body.
            try:
                with open(html_file, "r", encoding="utf-8") as f:
                    full_html = f.read()
                m = re.search(r"<body[^>]*>(.*)</body>", full_html, re.DOTALL)
                body_inner = m.group(1) if m else full_html
                html_fragment = self._report_fragment(report.title, body_inner)
            except Exception:
                html_fragment = ""
        
        return {
            "quarto_file": quarto_file,
            "html_file": html_file,
            "html_content": html_fragment,
            "status": "generated" if rendered else "failed",
            "message": "Report rendered to HTML" if rendered else "Report rendering failed"
        }

    def _execute_plot_code_to_b64(self, code: str,
                                  extra_ns: Optional[Dict] = None) -> Optional[str]:
        """Execute matplotlib plot code in an isolated namespace and return
        the rendered figure as a base64-encoded PNG string, or None on failure.

        Quarto would execute ```{python}`` cells to produce figures; this
        fallback runs the same code with the Agg backend and captures the
        figure so the graph is embedded even without Quarto.
        """
        if plt is None or matplotlib is None:
            return None
        try:
            ns = {"plt": plt, "np": np, "matplotlib": matplotlib}
            if extra_ns:
                ns.update(extra_ns)
            plt.close("all")
            exec(compile(code, "<plot_code>", "exec"), ns)
            fig = plt.gcf()
            if not fig.get_size_inches().tolist() == [0.0, 0.0] and len(fig.axes) > 0:
                buf = io.BytesIO()
                fig.savefig(buf, format="png", dpi=120, bbox_inches="tight")
                plt.close(fig)
                buf.seek(0)
                return base64.b64encode(buf.read()).decode("ascii")
            plt.close("all")
        except Exception as e:
            logger.warning(f"Plot code execution failed: {e}")
            plt.close("all")
        return None

    @staticmethod
    def _generate_hardware_content(hardware_info: Dict) -> str:
        """Render the consolidated hardware info as a Markdown section."""
        if not hardware_info or not hardware_info.get("spectrometer_type"):
            return ""
        lines = ["## Hardware Information", ""]
        lines.append(
            "All available information about the spectrometer / sensor that "
            "produced this measurement, consolidated by the Hardware "
            "Information Agent from spectral detection, the known-device "
            "knowledge base, the uploaded file header, and spectral-derived "
            "characteristics.")
        lines.append("")
        spec_type = hardware_info.get("spectrometer_type", "unknown")
        conf = hardware_info.get("spectrometer_type_confidence", "low")
        lines.append(f"- **Detected spectrometer type**: `{spec_type}` "
                     f"(confidence: {conf})")
        for label, key in [
            ("Manufacturer", "manufacturer"), ("Model", "model"),
            ("Detector / sensor", "detector"), ("Light source", "light_source"),
        ]:
            v = hardware_info.get(key)
            if v:
                lines.append(f"- **{label}**: {v}")
        wr = hardware_info.get("wavelength_range") or []
        if wr and len(wr) >= 2:
            lines.append(f"- **Wavelength range**: {wr[0]:.1f}\u2013{wr[1]:.1f} nm")
        if hardware_info.get("resolution_nm") is not None:
            lines.append(f"- **Resolution**: {float(hardware_info['resolution_nm']):.2f} nm")
        if hardware_info.get("num_channels"):
            lines.append(f"- **Channels**: {hardware_info['num_channels']}")
        if hardware_info.get("num_data_points"):
            lines.append(f"- **Data points (measured)**: {hardware_info['num_data_points']}")
        it = hardware_info.get("integration_time")
        if it:
            lines.append(f"- **Integration time**: {it}")
        sa = hardware_info.get("scans_to_average")
        if sa:
            lines.append(f"- **Scans to average**: {sa}")
        sn = hardware_info.get("serial_number")
        if sn:
            lines.append(f"- **Serial number**: `{sn}`")
        fw = hardware_info.get("firmware_version")
        if fw:
            lines.append(f"- **Firmware version**: {fw}")
        feats = hardware_info.get("features") or []
        if feats:
            lines.append(f"- **Features**: {', '.join(f.title() for f in feats)}")
        cp = hardware_info.get("calibration_points") or []
        if cp:
            lines.append(f"- **Recommended calibration points**: {', '.join(str(p) for p in cp)} nm")
        comps = hardware_info.get("diy_components") or []
        if comps:
            lines.append(f"- **DIY components**: {', '.join(comps)}")
            if hardware_info.get("cost"):
                lines.append(f"- **Estimated cost**: {hardware_info['cost']}")
            if hardware_info.get("difficulty"):
                lines.append(f"- **Difficulty**: {hardware_info['difficulty'].title()}")
        notes = hardware_info.get("notes")
        if notes:
            lines.append("")
            lines.append(f"_{notes}_")
        return "\n".join(lines)

    def _generate_calibration_plot_code(self, analyte_cal: Dict,
                                        analysis_result: Dict) -> str:
        """Generate matplotlib code for the NIR->Brix calibration curve.

        Plots predicted vs measured Brix (1:1 line) from the fitted PLS
        model. ``__cal_data__`` (set by _execute_plot_code_to_b64 or inlined
        by the Quarto export) carries the model's own predictions on the
        full (pre-outlier-removal) sample ordering, so the scatter matches
        the fitted model exactly: kept samples are shown in blue and the
        removed outliers in red, rather than re-computing predictions from
        raw intensities (which mixes outliers back into a cleaned fit and
        makes the curve look 'off'). Falls back to the legacy raw-X@coef
        path only when the model did not record plot data.
        """
        return """
import numpy as np
import matplotlib.pyplot as plt

cal = __cal_data__
measured = cal.get('plot_measured')
pred_kept = cal.get('plot_predicted_kept')
pred_removed = cal.get('plot_predicted_removed')
coef = cal.get('coefficients', [])
r2 = float(cal.get('r_squared_cv', 0.0) or 0.0)
rmse = float(cal.get('rmse_cv', 0.0) or 0.0)
prep = cal.get('preprocessing', 'raw') or 'raw'
n_out = int(cal.get('outliers_removed', 0) or 0)

have_model_plot = (measured and pred_kept and len(measured) == len(pred_kept)
                   and any(p is not None for p in pred_kept))

fig, ax = plt.subplots(figsize=(7, 7))
if have_model_plot:
    y = np.array([float(v) for v in measured], dtype=float)
    kept_y = [y[i] for i in range(len(y)) if pred_kept[i] is not None]
    kept_p = [float(pred_kept[i]) for i in range(len(y)) if pred_kept[i] is not None]
    ax.scatter(kept_y, kept_p, s=22, alpha=0.6, edgecolor='none',
               color='#1a3c5e', label='Kept samples')
    if pred_removed and len(pred_removed) == len(y):
        rem_y = [y[i] for i in range(len(y)) if pred_kept[i] is None]
        ax.scatter(rem_y, [float(v) for v in pred_removed], s=36, alpha=0.8,
                   edgecolor='#7b1d1d', facecolor='#d9534f', marker='X',
                   label=f'Outliers removed ({n_out})')
    all_vals = list(kept_y) + list(kept_p) + (list(pred_removed) if pred_removed else [])
    lo = float(min(all_vals)) - 0.3
    hi = float(max(all_vals)) + 0.3
    ax.plot([lo, hi], [lo, hi], 'r--', lw=1.5, label='1:1 line')
    ax.set_xlabel('Measured Brix (\u00b0Brix)', fontsize=12)
    ax.set_ylabel('Predicted Brix (\u00b0Brix)', fontsize=12)
    ax.set_title(f'NIR \u2192 Brix Calibration (PLS, {prep.upper()}): '
                 f'R\u00b2cv={r2:.3f}, RMSEcv={rmse:.3f} \u00b0Brix', fontsize=12)
    ax.legend(loc='upper left', fontsize=9)
    ax.grid(True, alpha=0.3)
    ax.axis('equal')
    plt.tight_layout()
elif coef and cal.get('brix') and cal.get('intensity_matrix'):
    X = np.array(cal['intensity_matrix'], dtype=float)
    y = np.array([float(v) for v in cal['brix'] if v not in (None, '')], dtype=float)
    c = np.array(coef, dtype=float)
    n = min(len(X), len(y))
    X = X[:n]; y = y[:n]
    y_pred = X @ c + float(cal.get('intercept', 0.0))
    ax.scatter(y, y_pred, s=18, alpha=0.45, edgecolor='none', color='#1a3c5e')
    lo = float(min(y.min(), y_pred.min())) - 0.2
    hi = float(max(y.max(), y_pred.max())) + 0.2
    ax.plot([lo, hi], [lo, hi], 'r--', lw=1.5, label='1:1 line')
    ax.set_xlabel('Measured Brix (\u00b0Brix)', fontsize=12)
    ax.set_ylabel('Predicted Brix (\u00b0Brix)', fontsize=12)
    ax.set_title('NIR \u2192 Brix Calibration: Predicted vs Measured', fontsize=13)
    ax.legend()
    ax.grid(True, alpha=0.3)
    ax.axis('equal')
    plt.tight_layout()
else:
    ax.text(0.5, 0.5, 'Calibration curve unavailable (no per-sample matrix / Brix reference)',
            ha='center', va='center', transform=ax.transAxes, color='#888')
    ax.axis('off')
"""

    def _markdown_to_html(self, quarto_content: str, report: QuartoReport) -> str:
        """Convert a generated Quarto (.qmd) document to an HTML body fragment.
        
        Strips the YAML front-matter and renders the remaining Markdown to HTML.
        Quarto python code cells (```{python} ... ```) are preserved as syntax-
        highlighted code blocks so the source code remains visible in the report.
        """
        try:
            import markdown as md
        except ImportError:
            md = None
        
        body = quarto_content
        # Remove YAML front matter
        if body.startswith("---"):
            end = body.find("\n---", 3)
            if end != -1:
                body = body[end + 4:]
        
        # Convert Quarto python code fences ```{python} ... ``` to standard ```python
        body = re.sub(r"```\{python\}", "```python", body)

        import html as html_mod
        import uuid as _uuid
        cal_data = report.metadata.get('cal_plot_data') if report else None
        _plot_placeholders: Dict[str, str] = {}

        # Display-only Quarto fences (```{.python eval=false}) are
        # documentation/template source, not executable plots: render them
        # as escaped code blocks WITHOUT executing (they contain undefined
        # functions / a __main__ block that would NameError).
        def _replace_display_block(match: "re.Match") -> str:
            code = match.group(1)
            escaped = html_mod.escape(code)
            token = f"DISPPH{_uuid.uuid4().hex}DISPPH"
            _plot_placeholders[token] = (
                "<details class=\"code-details\"><summary>"
                "Show Python source</summary><pre><code class=\"language-python\">"
                f"{escaped}</code></pre></details>")
            return token
        body = re.sub(r"```\{\.python\s+eval=false\}\n(.*?)```",
                      _replace_display_block, body, flags=re.DOTALL)

        # Execute matplotlib plot code blocks and replace them with an
        # embedded base64 PNG figure, keeping the source in a collapsible
        # <details> block so graphs render without the Quarto CLI.
        # The injected HTML is stored via placeholder tokens so the later
        # text-escaping pass (markdown fallback) cannot escape the tags.
        cal_data = report.metadata.get('cal_plot_data') if report else None
        _plot_placeholders: Dict[str, str] = {}

        def _replace_plot_block(match: "re.Match") -> str:
            code = match.group(1)
            is_plot = ("matplotlib" in code or "plt." in code)
            img_html = ""
            if is_plot:
                extra_ns = None
                if cal_data and "__cal_data__" in code:
                    extra_ns = {"__cal_data__": cal_data}
                b64 = self._execute_plot_code_to_b64(code, extra_ns=extra_ns)
                if b64:
                    img_html = (
                        f"<div class=\"figure\"><img alt=\"figure\" "
                        f"src=\"data:image/png;base64,{b64}\" "
                        f"style=\"max-width:100%;height:auto;\"/></div>")
            escaped = html_mod.escape(code)
            details = (
                "<details class=\"code-details\"><summary>"
                "Show Python source</summary><pre><code class=\"language-python\">"
                f"{escaped}</code></pre></details>")
            block_html = img_html + details if img_html else details
            token = f"PLOTPH{_uuid.uuid4().hex}PLOTPH"
            _plot_placeholders[token] = block_html
            return token

        body = re.sub(r"```python\n(.*?)```", _replace_plot_block, body,
                      flags=re.DOTALL)
        
        if md is not None:
            # Render the remaining (non-code) Markdown to HTML. The fenced
            # code blocks were already substituted above, so disable the
            # fenced_code extension to avoid double-processing.
            html_body = md.markdown(
                body,
                extensions=["tables", "toc"],
            )
        else:
            # Minimal-but-readable HTML conversion if the markdown package is
            # unavailable. Escape the text, render headings/bold, turn markdown
            # bullet and numbered lists into <ul>/<ol>, wrap loose paragraphs
            # in <p>, and preserve line breaks within list items. Plot-block
            # HTML is restored from placeholders afterwards.
            lines = body.split(chr(10))
            out: List[str] = []
            list_type: Optional[str] = None  # 'ul' | 'ol' | None
            para: List[str] = []

            def flush_para() -> None:
                nonlocal para
                if para:
                    text = chr(10).join(para)
                    text = html_mod.escape(text)
                    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
                    text = re.sub(r"\[(.+?)\]\((https?://[^\)]+)\)",
                                  r'<a href="\2">\1</a>', text)
                    out.append(f"<p>{text}</p>")
                    para = []

            def close_list() -> None:
                nonlocal list_type
                if list_type:
                    out.append(f"</{list_type}>")
                    list_type = None

            for ln in lines:
                if ln.startswith("### "):
                    flush_para(); close_list()
                    out.append(f"<h3>{html_mod.escape(ln[4:])}</h3>")
                elif ln.startswith("## "):
                    flush_para(); close_list()
                    out.append(f"<h2>{html_mod.escape(ln[3:])}</h2>")
                elif ln.startswith("# "):
                    flush_para(); close_list()
                    out.append(f"<h1>{html_mod.escape(ln[2:])}</h1>")
                elif re.match(r"^\s*[-*]\s+", ln):
                    flush_para()
                    if list_type != "ul":
                        close_list(); out.append("<ul>"); list_type = "ul"
                    item = re.sub(r"^\s*[-*]\s+", "", ln)
                    item = html_mod.escape(item)
                    item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item)
                    out.append(f"<li>{item}</li>")
                elif re.match(r"^\s*\d+\.\s+", ln):
                    flush_para()
                    if list_type != "ol":
                        close_list(); out.append("<ol>"); list_type = "ol"
                    item = re.sub(r"^\s*\d+\.\s+", "", ln)
                    item = html_mod.escape(item)
                    item = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", item)
                    out.append(f"<li>{item}</li>")
                elif ln.strip() == "":
                    flush_para(); close_list()
                else:
                    close_list()
                    para.append(ln)
            flush_para(); close_list()
            html_body = chr(10).join(out)
            html_body = f"<div class=\"md-body\">{html_body}</div>"
        
        # Restore plot-block HTML (now safe from the escaping pass).
        for token, block_html in _plot_placeholders.items():
            html_body = html_body.replace(token, block_html)
        
        return html_body
    
    _REPORT_STYLE_CSS = """
        .md-body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; color: #222; line-height: 1.6; }
        .md-body h1, .md-body h2, .md-body h3, .md-body h4 { color: #1a3c5e; margin-top: 1.5rem; }
        .md-body h1 { border-bottom: 2px solid #1a3c5e; padding-bottom: 0.3rem; }
        .md-body table { border-collapse: collapse; width: 100%; margin: 1rem 0; }
        .md-body th, .md-body td { border: 1px solid #ccc; padding: 0.5rem 0.75rem; text-align: left; }
        .md-body th { background: #f2f6fa; }
        .md-body pre { background: #f7f7f9; padding: 1rem; border-radius: 6px; overflow-x: auto; }
        .md-body code { font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace; font-size: 0.9em; }
        .md-body pre code { background: none; }
        .md-body :not(pre) > code { background: #f0f0f2; padding: 0.1em 0.3em; border-radius: 3px; }
        .md-body blockquote { border-left: 4px solid #1a3c5e; margin: 1rem 0; padding: 0.5rem 1rem; color: #555; background: #f9fbfd; }
        .md-body .codehilite { background: #f7f7f9; border-radius: 6px; }
        .md-body .figure { margin: 1.2rem 0; text-align: center; border: 1px solid #e5e5e5; border-radius: 6px; padding: 0.6rem; background: #fff; }
        .md-body .figure img { max-width: 100%; height: auto; }
        .md-body .code-details { margin: 0.5rem 0 1rem; }
        .md-body .code-details summary { cursor: pointer; color: #1a3c5e; font-size: 0.9em; }
        .md-body h1, .md-body h2, .md-body h3 { color: #1a3c5e; }
    """

    def _report_fragment(self, title: str, body: str) -> str:
        """Return an embeddable report fragment: scoped <style> + body, no
        document wrapper. Safe to inject into another HTML page via |safe."""
        return (
            f"<div class=\"nir-report\">"
            f"<style>{self._REPORT_STYLE_CSS}</style>"
            f"{body}"
            f"</div>"
        )

    def _wrap_html_document(self, title: str, body: str) -> str:
        """Wrap an HTML body fragment into a complete, styled HTML document."""
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="utf-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{ font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif; max-width: 1100px; margin: 2rem auto; padding: 0 1.5rem; color: #222; line-height: 1.6; }}
        h1, h2, h3, h4 {{ color: #1a3c5e; margin-top: 1.5rem; }}
        h1 {{ border-bottom: 2px solid #1a3c5e; padding-bottom: 0.3rem; }}
        table {{ border-collapse: collapse; width: 100%; margin: 1rem 0; }}
        th, td {{ border: 1px solid #ccc; padding: 0.5rem 0.75rem; text-align: left; }}
        th {{ background: #f2f6fa; }}
        pre {{ background: #f7f7f9; padding: 1rem; border-radius: 6px; overflow-x: auto; }}
        code {{ font-family: SFMono-Regular, Consolas, "Liberation Mono", Menlo, monospace; font-size: 0.9em; }}
        pre code {{ background: none; }}
        :not(pre) > code {{ background: #f0f0f2; padding: 0.1em 0.3em; border-radius: 3px; }}
        blockquote {{ border-left: 4px solid #1a3c5e; margin: 1rem 0; padding: 0.5rem 1rem; color: #555; background: #f9fbfd; }}
        .codehilite {{ background: #f7f7f9; border-radius: 6px; }}
        .figure {{ margin: 1.2rem 0; text-align: center; border: 1px solid #e5e5e5; border-radius: 6px; padding: 0.6rem; background: #fff; }}
        .figure img {{ max-width: 100%; height: auto; }}
        .code-details {{ margin: 0.5rem 0 1rem; }}
        .code-details summary {{ cursor: pointer; color: #1a3c5e; font-size: 0.9em; }}
        .md-body h1, .md-body h2, .md-body h3 {{ color: #1a3c5e; }}
    </style>
</head>
<body>
{body}
</body>
</html>"""

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
