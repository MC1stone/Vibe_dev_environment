#!/usr/bin/env python3
"""
Parser for T4-T5_ALLE_mit_Brix_2.txt file format

This script can parse the NIR spectroscopy data file and extract:
- Experiment metadata from the header
- Spectral data with associated metadata
- Wavelength information

File format:
- Line 1: Experiment description (German)
- Line 2: Empty
- Line 3: Column headers (semicolon-separated)
- Lines 4+: Data rows (semicolon-separated)
"""

import csv
import re
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
import json
from pathlib import Path


@dataclass
class SpectralData:
    """Represents a single spectral measurement"""
    counter: int
    messobjekt: str  # Measurement object ID
    kurz: str  # Short code
    tomate: str  # Tomato identifier
    rispe: str  # Cluster/panicle identifier
    reihe: str  # Row identifier
    tag: str  # Day identifier
    brix: float  # Brix value (sugar content)
    temp0: float  # Temperature 0
    temp1: float  # Temperature 1
    temp2: float  # Temperature 2
    wavelengths: Dict[str, float] = field(default_factory=dict)  # Wavelength: intensity
    
    def to_dict(self) -> Dict:
        """Convert to dictionary format"""
        return {
            'counter': self.counter,
            'messobjekt': self.messobjekt,
            'kurz': self.kurz,
            'tomate': self.tomate,
            'rispe': self.rispe,
            'reihe': self.reihe,
            'tag': self.tag,
            'brix': self.brix,
            'temperatures': {'temp0': self.temp0, 'temp1': self.temp1, 'temp2': self.temp2},
            'spectra': self.wavelengths
        }


@dataclass 
class ExperimentMetadata:
    """Represents experiment metadata extracted from the file"""
    description: str
    device: str
    wavelength_range: Tuple[float, float]
    num_wavelengths: int
    environment: Dict[str, str]
    students: List[str]
    calibration_method: str
    measurement_target: str
    goal: str
    
    def to_dict(self) -> Dict:
        return {
            'description': self.description,
            'device': self.device,
            'wavelength_range_nm': self.wavelength_range,
            'num_wavelengths': self.num_wavelengths,
            'environment': self.environment,
            'students': self.students,
            'calibration_method': self.calibration_method,
            'measurement_target': self.measurement_target,
            'goal': self.goal
        }


class SpectraFileParser:
    """Parser for NIR spectroscopy data files"""
    
    def __init__(self, file_path: str):
        self.file_path = Path(file_path)
        self.experiment_metadata: Optional[ExperimentMetadata] = None
        self.column_headers: List[str] = []
        self.spectral_data: List[SpectralData] = []
        self.wavelength_columns: List[str] = []
        
    def parse(self) -> None:
        """Parse the entire file"""
        with open(self.file_path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Clean lines: strip whitespace and handle Windows line endings
        cleaned_lines = []
        for line in lines:
            # Remove Windows carriage return and strip whitespace
            cleaned_line = line.replace('\r', '').strip()
            if cleaned_line:  # Only keep non-empty lines
                cleaned_lines.append(cleaned_line)
        
        # Parse metadata (first line)
        if cleaned_lines:
            self._parse_metadata(cleaned_lines[0])
        
        # Find header line (contains semicolons and column names)
        header_line = None
        for line in cleaned_lines[1:]:
            if ';' in line and 'Counter' in line:
                header_line = line
                break
        
        if header_line:
            self.column_headers = header_line.split(';')
            # Extract wavelength columns (columns after Temp2)
        # The columns are: Counter, Messobjekt, Kurz, Tomate, Rispe, Reihe, Tag, Brix, Temp0, Temp1, Temp2, then wavelengths
        temp_cols = ['Temp0', 'Temp1', 'Temp2']
        temp_indices = [i for i, col in enumerate(self.column_headers) if col in temp_cols]
        if temp_indices:
            last_temp_idx = max(temp_indices)
            self.wavelength_columns = self.column_headers[last_temp_idx + 1:]
        
        # Parse data rows
        data_started = False
        for line in cleaned_lines:
            if not line.strip():
                continue
            
            if line == header_line:
                data_started = True
                continue
                
            if 'Counter' in line or 'Messobjekt' in line:
                data_started = True
                continue
                
            if data_started and ';' in line:
                self._parse_data_row(line)
    
    def _parse_metadata(self, metadata_line: str) -> None:
        """Parse the experiment metadata from the first line"""
        # Extract information using regex patterns
        description = metadata_line
        
        # Device information
        device_match = re.search(r'mit dem (.*?) durchgeführt', metadata_line)
        device = device_match.group(1) if device_match else "Unknown"
        
        # Wavelength information
        wavelength_match = re.search(r'(\d+) wellenlängen von (\d+) bis (\d+) nm', metadata_line)
        if wavelength_match:
            num_wavelengths = int(wavelength_match.group(1))
            start_wl = float(wavelength_match.group(2))
            end_wl = float(wavelength_match.group(3))
        else:
            num_wavelengths = 18  # Default from context
            start_wl = 410.0
            end_wl = 940.0
        
        # Environment information
        env_match = re.search(r'Die Umgebung war (.*?) und (.*?) auf (\d+°C)', metadata_line)
        environment = {}
        if env_match:
            environment['condition1'] = env_match.group(1)
            environment['condition2'] = env_match.group(2)
            environment['temperature'] = env_match.group(3)
        
        # Students
        students_match = re.search(r'Die Studenten (.*?) aheb die Messungen', metadata_line)
        students = []
        if students_match:
            students_str = students_match.group(1)
            students = [s.strip() for s in students_match.group(1).split(',')]
        
        # Calibration method
        calibration_match = re.search(r'Zur Kallibreirung wurde (.*?) benutzt', metadata_line)
        calibration_method = calibration_match.group(1) if calibration_match else "Unknown"
        
        # Measurement target
        measurement_match = re.search(r'Frucktose gehalt der (.*?) gemessen', metadata_line)
        measurement_target = measurement_match.group(1) if measurement_match else "Fruits"
        
        # Goal
        goal_match = re.search(r'Zielsetzung (.*?)$', metadata_line)
        goal = goal_match.group(1) if goal_match else "Calibration of NIR sensor"
        
        self.experiment_metadata = ExperimentMetadata(
            description=description,
            device=device,
            wavelength_range=(start_wl, end_wl),
            num_wavelengths=num_wavelengths,
            environment=environment,
            students=students,
            calibration_method=calibration_method,
            measurement_target=measurement_target,
            goal=goal
        )
    
    def _parse_data_row(self, line: str) -> None:
        """Parse a single data row"""
        values = line.split(';')
        
        if len(values) < 10:  # Minimum expected columns
            return
        
        try:
            # Extract metadata fields
            # Column indices: 0=Counter, 1=Messobjekt, 2=Kurz, 3=Tomate, 4=Rispe, 5=Reihe, 6=Tag, 7=Brix, 8=Temp0, 9=Temp1, 10=Temp2
            counter = int(values[0]) if values[0] else 0
            messobjekt = values[1] if len(values) > 1 else ""
            kurz = values[2] if len(values) > 2 else ""
            tomate = values[3] if len(values) > 3 else ""
            rispe = values[4] if len(values) > 4 else ""
            reihe = values[5] if len(values) > 5 else ""
            tag = values[6] if len(values) > 6 else ""
            
            # Brix value (sugar content) at index 7
            brix = float(values[7].replace(',', '.')) if len(values) > 7 else 0.0
            
            # Temperature values at indices 8, 9, 10
            temp0 = float(values[8].replace(',', '.')) if len(values) > 8 else 0.0
            temp1 = float(values[9].replace(',', '.')) if len(values) > 9 else 0.0
            temp2 = float(values[10].replace(',', '.')) if len(values) > 10 else 0.0
            
            # Spectral data (wavelength intensities) start at index 11
            wavelengths = {}
            for i, wl_col in enumerate(self.wavelength_columns):
                if len(values) > 11 + i:
                    try:
                        intensity = float(values[11 + i].replace(',', '.'))
                        wavelengths[wl_col] = intensity
                    except ValueError:
                        wavelengths[wl_col] = 0.0
            
            spectral_data = SpectralData(
                counter=counter,
                messobjekt=messobjekt,
                kurz=kurz,
                tomate=tomate,
                rispe=rispe,
                reihe=reihe,
                tag=tag,
                brix=brix,
                temp0=temp0,
                temp1=temp1,
                temp2=temp2,
                wavelengths=wavelengths
            )
            
            self.spectral_data.append(spectral_data)
            
        except (ValueError, IndexError) as e:
            print(f"Error parsing line: {line}")
            print(f"Error: {e}")
    
    def get_summary(self) -> Dict:
        """Get a summary of the parsed data"""
        return {
            'file_path': str(self.file_path),
            'total_spectra': len(self.spectral_data),
            'experiment_metadata': self.experiment_metadata.to_dict() if self.experiment_metadata else None,
            'column_headers': self.column_headers,
            'wavelength_columns': self.wavelength_columns,
            'num_wavelengths': len(self.wavelength_columns)
        }
    
    def get_spectra_by_tomato(self, tomato_id: str) -> List[SpectralData]:
        """Get all spectra for a specific tomato"""
        return [s for s in self.spectral_data if s.tomate == tomato_id]
    
    def get_spectra_by_brix_range(self, min_brix: float, max_brix: float) -> List[SpectralData]:
        """Get spectra within a specific Brix range"""
        return [s for s in self.spectral_data if min_brix <= s.brix <= max_brix]
    
    def export_to_json(self, output_path: str) -> None:
        """Export parsed data to JSON file"""
        data = {
            'metadata': self.experiment_metadata.to_dict() if self.experiment_metadata else {},
            'column_headers': self.column_headers,
            'wavelength_columns': self.wavelength_columns,
            'spectra': [s.to_dict() for s in self.spectral_data]
        }
        
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
    
    def get_wavelength_intensities(self) -> Dict[str, List[float]]:
        """Get all intensities for each wavelength across all spectra"""
        intensities = {wl: [] for wl in self.wavelength_columns}
        
        for spectrum in self.spectral_data:
            for wl, intensity in spectrum.wavelengths.items():
                intensities[wl].append(intensity)
        
        return intensities


def main():
    """Main function to demonstrate the parser"""
    # Parse the file
    parser = SpectraFileParser('/home/martin/Development/vsCode_Environment/NIR_Mistral/data/raw/T4-T5_ALLE_mit_Brix_2.txt')
    parser.parse()
    
    # Get summary
    summary = parser.get_summary()
    print("=== FILE ANALYSIS SUMMARY ===")
    print(f"File: {summary['file_path']}")
    print(f"Total spectra: {summary['total_spectra']}")
    print(f"Number of wavelengths: {summary['num_wavelengths']}")
    print(f"Wavelength columns: {summary['wavelength_columns']}")
    
    # Display experiment metadata
    if summary['experiment_metadata']:
        print("\n=== EXPERIMENT METADATA ===")
        meta = summary['experiment_metadata']
        print(f"Device: {meta['device']}")
        print(f"Wavelength range: {meta['wavelength_range_nm']} nm")
        print(f"Number of wavelengths: {meta['num_wavelengths']}")
        print(f"Environment: {meta['environment']}")
        print(f"Students: {meta['students']}")
        print(f"Calibration method: {meta['calibration_method']}")
        print(f"Measurement target: {meta['measurement_target']}")
        print(f"Goal: {meta['goal']}")
    
    # Sample data
    if parser.spectral_data:
        print("\n=== SAMPLE SPECTRUM ===")
        sample = parser.spectral_data[0]
        print(f"Counter: {sample.counter}")
        print(f"Messobjekt: {sample.messobjekt}")
        print(f"Tomate: {sample.tomate}")
        print(f"Brix: {sample.brix}")
        print(f"Temperatures: {sample.temp0}, {sample.temp1}, {sample.temp2}")
        print(f"First 5 wavelengths: {dict(list(sample.wavelengths.items())[:5])}")
    
    # Export to JSON
    parser.export_to_json('/home/martin/Development/vsCode_Environment/NIR_Mistral/data/raw/T4-T5_ALLE_mit_Brix_2_parsed.json')
    print("\nData exported to JSON file.")


if __name__ == "__main__":
    main()