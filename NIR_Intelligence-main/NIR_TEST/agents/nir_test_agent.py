#!/usr/bin/env python3
"""
NIR Test Agent for NIR_Mistral DeveloperAgent Framework

This agent demonstrates the functionality of the NIR_Mistral framework
using the test data in the NIR_TEST environment.
"""

import os
import sys
import yaml
import logging
import numpy as np
import pandas as pd
from pathlib import Path
from typing import Dict, List, Tuple, Optional
from dataclasses import dataclass

# Add the framework to the path
framework_path = "/home/martin/Development/vsCode_Environment/NIR_Mistral"
if framework_path not in sys.path:
    sys.path.insert(0, framework_path)

@dataclass
class NIRSpectrum:
    """Class to represent NIR spectroscopy data"""
    wavelengths: np.ndarray
    values: np.ndarray
    sample_id: str
    sample_name: str
    spectral_type: str
    metadata: Dict
    
    def __post_init__(self):
        self.wavelengths = np.array(self.wavelengths)
        self.values = np.array(self.values)
    
    def get_range(self) -> Tuple[float, float]:
        """Get the wavelength range"""
        return (float(np.min(self.wavelengths)), float(np.max(self.wavelengths)))
    
    def get_mean_absorbance(self) -> float:
        """Get mean absorbance value"""
        return float(np.mean(self.values))
    
    def get_max_absorbance(self) -> float:
        """Get maximum absorbance value"""
        return float(np.max(self.values))
    
    def get_min_absorbance(self) -> float:
        """Get minimum absorbance value"""
        return float(np.min(self.values))
    
    def find_peaks(self, threshold: float = None) -> List[Tuple[float, float]]:
        """Find peaks in the spectrum"""
        if threshold is None:
            # Use 10% of the range as threshold if not specified
            threshold = (np.max(self.values) - np.min(self.values)) * 0.1
        
        peaks = []
        for i in range(1, len(self.values) - 1):
            if (self.values[i] > self.values[i-1] and 
                self.values[i] > self.values[i+1] and 
                self.values[i] > threshold):
                peaks.append((float(self.wavelengths[i]), float(self.values[i])))
        return peaks

class NIRTestAgent:
    """Test agent for NIR spectroscopy analysis"""
    
    def __init__(self, config_path: str = None):
        """Initialize the test agent"""
        self.name = "NIR_Test_Agent"
        self.version = "1.0.0"
        self.description = "Test agent for NIR spectroscopy analysis"
        
        # Load configuration
        self.config = self._load_configuration(config_path)
        self._setup_logging()
        self._setup_paths()
        
        # Initialize data storage
        self.spectra = {}
        self.results = {}
        
        self.logger.info(f"NIR Test Agent initialized with config: {config_path}")
    
    def _load_configuration(self, config_path: str = None) -> Dict:
        """Load configuration from YAML file"""
        if config_path is None:
            config_path = os.path.join(
                os.path.dirname(__file__), 
                "..", "config", "test_config.yaml"
            )
        
        try:
            with open(config_path, 'r') as f:
                config = yaml.safe_load(f)
            return config
        except FileNotFoundError:
            self.logger.warning(f"Configuration file not found: {config_path}")
            return {}
        except yaml.YAMLError as e:
            self.logger.error(f"Error parsing YAML configuration: {e}")
            return {}
    
    def _setup_logging(self):
        """Setup logging for the agent"""
        log_config = self.config.get('logging', {})
        log_level = log_config.get('level', 'INFO')
        log_format = log_config.get('format', '%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        
        # Create logs directory if it doesn't exist
        logs_dir = self.config.get('paths', {}).get('logs', './logs')
        os.makedirs(logs_dir, exist_ok=True)
        
        log_file = log_config.get('log_file', os.path.join(logs_dir, 'nir_test_agent.log'))
        
        # Setup logging
        logging.basicConfig(
            level=getattr(logging, log_level.upper(), logging.INFO),
            format=log_format,
            handlers=[
                logging.FileHandler(log_file),
                logging.StreamHandler()
            ]
        )
        
        self.logger = logging.getLogger(self.name)
    
    def _setup_paths(self):
        """Setup and validate paths"""
        paths = self.config.get('paths', {})
        self.paths = {}
        
        for key, path in paths.items():
            if '${root}' in path:
                root = paths.get('root', '')
                path = path.replace('${root}', root)
            self.paths[key] = path
            
            # Create directory if it doesn't exist
            if key not in ['root']:  # Don't create root directory
                try:
                    os.makedirs(path, exist_ok=True)
                except Exception as e:
                    self.logger.warning(f"Could not create directory {path}: {e}")
    
    def load_test_data(self) -> bool:
        """Load test data from files"""
        test_data_config = self.config.get('test_data', {})
        samples = test_data_config.get('samples', [])
        
        data_processing = self.config.get('data_processing', {})
        raw_data_path = self.paths.get('raw_data', './data/raw')
        delimiter = data_processing.get('delimiter', ',')
        
        success = True
        
        for sample in samples:
            sample_id = sample.get('id', '')
            sample_name = sample.get('name', '')
            filename = sample.get('file', '')
            spectral_type = sample.get('type', 'absorbance')
            
            file_path = os.path.join(raw_data_path, filename)
            
            if not os.path.exists(file_path):
                self.logger.error(f"Test data file not found: {file_path}")
                success = False
                continue
            
            try:
                # Read the file line by line to find where data starts
                with open(file_path, 'r') as f:
                    lines = f.readlines()
                
                # Find the first line that doesn't start with #
                data_start_line = 0
                for i, line in enumerate(lines):
                    if not line.strip().startswith('#'):
                        data_start_line = i
                        break
                
                # Load the data starting from the data line
                df = pd.read_csv(
                    file_path, 
                    delimiter=delimiter, 
                    skiprows=data_start_line,
                    header=None,
                    names=['wavelength', 'value']
                )
                
                # Create NIRSpectrum object
                spectrum = NIRSpectrum(
                    wavelengths=df['wavelength'].values,
                    values=df['value'].values,
                    sample_id=sample_id,
                    sample_name=sample_name,
                    spectral_type=spectral_type,
                    metadata=sample.get('expected_properties', {})
                )
                
                self.spectra[sample_id] = spectrum
                self.logger.info(f"Loaded spectrum {sample_id}: {sample_name}")
                
            except Exception as e:
                self.logger.error(f"Error loading spectrum {sample_id}: {e}")
                success = False
        
        return success
    
    def analyze_spectra(self) -> Dict:
        """Analyze all loaded spectra"""
        results = {}
        
        for sample_id, spectrum in self.spectra.items():
            analysis = {
                'sample_id': sample_id,
                'sample_name': spectrum.sample_name,
                'spectral_type': spectrum.spectral_type,
                'wavelength_range': spectrum.get_range(),
                'mean_absorbance': spectrum.get_mean_absorbance(),
                'max_absorbance': spectrum.get_max_absorbance(),
                'min_absorbance': spectrum.get_min_absorbance(),
                'peaks': spectrum.find_peaks(),
                'data_points': len(spectrum.wavelengths),
                'wavelength_step': float(np.mean(np.diff(spectrum.wavelengths)))
            }
            
            results[sample_id] = analysis
            self.logger.info(f"Analyzed spectrum {sample_id}")
        
        self.results = results
        return results
    
    def validate_data_quality(self) -> Dict:
        """Validate data quality"""
        quality_report = {}
        
        nir_settings = self.config.get('nir_settings', {})
        expected_range = nir_settings.get('wavelength_range', [700, 2500])
        expected_resolution = nir_settings.get('resolution', 2)
        
        for sample_id, spectrum in self.spectra.items():
            sample_quality = {
                'sample_id': sample_id,
                'sample_name': spectrum.sample_name,
                'checks': {}
            }
            
            # Check wavelength range
            min_wl, max_wl = spectrum.get_range()
            range_ok = (min_wl <= expected_range[0] and max_wl >= expected_range[1])
            sample_quality['checks']['wavelength_range'] = {
                'expected': expected_range,
                'actual': [min_wl, max_wl],
                'passed': range_ok
            }
            
            # Check resolution
            wl_step = float(np.mean(np.diff(spectrum.wavelengths)))
            resolution_ok = abs(wl_step - expected_resolution) < 0.1
            sample_quality['checks']['resolution'] = {
                'expected': expected_resolution,
                'actual': wl_step,
                'passed': resolution_ok
            }
            
            # Check data integrity
            data_integrity_ok = not np.any(np.isnan(spectrum.values))
            sample_quality['checks']['data_integrity'] = {
                'description': 'No NaN values',
                'passed': data_integrity_ok
            }
            
            # Check signal range
            signal_range_ok = spectrum.get_max_absorbance() > 0
            sample_quality['checks']['signal_range'] = {
                'description': 'Signal above zero',
                'actual_max': spectrum.get_max_absorbance(),
                'passed': signal_range_ok
            }
            
            # Overall quality
            all_passed = all(check['passed'] for check in sample_quality['checks'].values())
            sample_quality['overall_quality'] = all_passed
            
            quality_report[sample_id] = sample_quality
        
        return quality_report
    
    def generate_report(self, output_path: str = None) -> str:
        """Generate a comprehensive test report"""
        if not self.results:
            self.analyze_spectra()
        
        if not output_path:
            output_path = os.path.join(self.paths.get('output', './output'), 'test_report.txt')
        
        report_lines = [
            "=" * 60,
            "NIR_MISTRAL TEST ENVIRONMENT REPORT",
            "=" * 60,
            f"Generated: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}",
            f"Agent: {self.name} v{self.version}",
            "",
            "SPECTRAL ANALYSIS RESULTS",
            "-" * 40
        ]
        
        for sample_id, result in self.results.items():
            report_lines.extend([
                f"\nSample: {result['sample_name']} (ID: {sample_id})",
                f"Type: {result['spectral_type']}",
                f"Wavelength Range: {result['wavelength_range'][0]:.0f}-{result['wavelength_range'][1]:.0f} nm",
                f"Data Points: {result['data_points']}",
                f"Wavelength Step: {result['wavelength_step']:.1f} nm",
                f"Mean Absorbance: {result['mean_absorbance']:.3f}",
                f"Max Absorbance: {result['max_absorbance']:.3f}",
                f"Min Absorbance: {result['min_absorbance']:.3f}",
                f"Peaks Found: {len(result['peaks'])}"
            ])
            
            if result['peaks']:
                report_lines.append("Peak Positions (nm, value):")
                for peak in result['peaks'][:5]:  # Show first 5 peaks
                    report_lines.append(f"  {peak[0]:.0f}: {peak[1]:.3f}")
                if len(result['peaks']) > 5:
                    report_lines.append(f"  ... and {len(result['peaks']) - 5} more peaks")
        
        # Add quality report
        report_lines.extend([
            "",
            "",
            "QUALITY CONTROL REPORT",
            "-" * 40
        ])
        
        quality_report = self.validate_data_quality()
        for sample_id, quality in quality_report.items():
            report_lines.append(f"\nSample: {quality['sample_name']} (ID: {sample_id})")
            report_lines.append(f"Overall Quality: {'PASS' if quality['overall_quality'] else 'FAIL'}")
            
            for check_name, check_result in quality['checks'].items():
                status = "PASS" if check_result['passed'] else "FAIL"
                report_lines.append(f"  {check_name}: {status}")
        
        report_lines.extend([
            "",
            "=" * 60,
            "END OF REPORT",
            "=" * 60
        ])
        
        report_content = "\n".join(report_lines)
        
        # Save to file
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, 'w') as f:
            f.write(report_content)
        
        self.logger.info(f"Report generated: {output_path}")
        return report_content
    
    def run_demonstration(self) -> bool:
        """Run a complete demonstration of the test environment"""
        self.logger.info("Starting NIR Test Environment Demonstration")
        
        try:
            # Step 1: Load test data
            self.logger.info("Step 1: Loading test data...")
            if not self.load_test_data():
                self.logger.error("Failed to load test data")
                return False
            
            # Step 2: Analyze spectra
            self.logger.info("Step 2: Analyzing spectra...")
            analysis_results = self.analyze_spectra()
            self.logger.info(f"Analyzed {len(analysis_results)} spectra")
            
            # Step 3: Validate data quality
            self.logger.info("Step 3: Validating data quality...")
            quality_report = self.validate_data_quality()
            self.logger.info(f"Quality report generated for {len(quality_report)} samples")
            
            # Step 4: Generate report
            self.logger.info("Step 4: Generating comprehensive report...")
            report_content = self.generate_report()
            self.logger.info("Report generated successfully")
            
            # Step 5: Display summary
            self.logger.info("Step 5: Displaying summary...")
            self.display_summary()
            
            self.logger.info("NIR Test Environment Demonstration Completed Successfully!")
            return True
            
        except Exception as e:
            self.logger.error(f"Error during demonstration: {e}")
            return False
    
    def display_summary(self):
        """Display a summary of the test results"""
        print("\n" + "=" * 60)
        print("NIR TEST ENVIRONMENT - DEMONSTRATION SUMMARY")
        print("=" * 60)
        
        print(f"Agent: {self.name} v{self.version}")
        print(f"Test Date: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Configuration: {self.config.get('environment', {}).get('name', 'NIR_TEST')}")
        
        print(f"\nLoaded Spectra: {len(self.spectra)}")
        for sample_id, spectrum in self.spectra.items():
            print(f"  - {spectrum.sample_name} ({sample_id}): {len(spectrum.wavelengths)} data points")
        
        print(f"\nAnalysis Results:")
        for sample_id, result in self.results.items():
            print(f"  - {result['sample_name']}:")
            print(f"    Wavelength Range: {result['wavelength_range'][0]:.0f}-{result['wavelength_range'][1]:.0f} nm")
            print(f"    Mean Absorbance: {result['mean_absorbance']:.3f}")
            print(f"    Peaks Found: {len(result['peaks'])}")
        
        print(f"\nQuality Control:")
        quality_report = self.validate_data_quality()
        for sample_id, quality in quality_report.items():
            status = "PASS" if quality['overall_quality'] else "FAIL"
            print(f"  - {quality['sample_name']}: {status}")
        
        print("\nDemonstration completed successfully!")
        print("Detailed report saved to: output/test_report.txt")
        print("=" * 60 + "\n")

# Main execution
if __name__ == "__main__":
    # Create and run the test agent
    agent = NIRTestAgent()
    
    # Run the demonstration
    success = agent.run_demonstration()
    
    if success:
        print("NIR Test Environment demonstration completed successfully!")
        sys.exit(0)
    else:
        print("NIR Test Environment demonstration failed!")
        sys.exit(1)