# Analysis Report: T4-T5_ALLE_mit_Brix_2.txt

## File Overview

**File Path**: `/data/raw/T4-T5_ALLE_mit_Brix_2.txt`  
**File Size**: 2052 lines  
**Format**: CSV with semicolon (`;`) delimiter  
**Encoding**: UTF-8 with Windows line endings (CRLF)  
**Total Spectra**: 2,049 spectral measurements

---

## File Structure

### 1. Metadata Section (Line 1)

The first line contains a German description of the experiment with the following key information:

- **Experiment**: Tomaten Reifegradbestimmung (Tomato ripeness determination)
- **Device**: Dpark fun NIR Triad
- **Wavelength Range**: 410-940 nm
- **Number of Wavelengths**: 18
- **Environment**: Darkened (verdunkelt) and air-conditioned (Klimatisiert) at 22°C
- **Students**: Leonhard, Samuel, Frederik, Luzia
- **Calibration Method**: Refractometer (ein Refraktometer)
- **Measurement Target**: Fruits (Früchte)
- **Goal**: Calibration of NIR sensor to find the best fit for measured data

### 2. Header Section (Line 3)

Contains column names separated by semicolons:

```
Counter;Messobjekt;Kurz;Tomate;Rispe;Reihe;Tag;Brix;Temp0;Temp1;Temp2;A_410;B_435;C_460;D_485;E_510;F_535;G_560;H_585;R_610;I_645;S_680;J_705;T_730;U_760;V_810;W_860;K_900;L_940
```

### 3. Data Section (Lines 4-2052)

Contains 2,049 spectral measurements with the following structure:

- **Columns 0-7**: Metadata fields
  - `Counter`: Unique identifier for each measurement (1000-1309)
  - `Messobjekt`: Measurement object ID (e.g., 10401T5, 20401T5)
  - `Kurz`: Short code (e.g., 1To4Ri2Re5Ta)
  - `Tomate`: Tomato identifier (e.g., 1To, 2To)
  - `Rispe`: Cluster/panicle identifier (e.g., 4Ri, 2Ri)
  - `Reihe`: Row identifier (e.g., 2Re, 5Re)
  - `Tag`: Day identifier (e.g., 5Ta, 4Ta)
  - `Brix`: Sugar content measurement (4.575-6.3)

- **Columns 8-10**: Temperature measurements
  - `Temp0`: Temperature sensor 0
  - `Temp1`: Temperature sensor 1  
  - `Temp2`: Temperature sensor 2

- **Columns 11-28**: Spectral intensity values for 18 wavelengths
  - `A_410`: Intensity at 410 nm
  - `B_435`: Intensity at 435 nm
  - `C_460`: Intensity at 460 nm
  - `D_485`: Intensity at 485 nm
  - `E_510`: Intensity at 510 nm
  - `F_535`: Intensity at 535 nm
  - `G_560`: Intensity at 560 nm
  - `H_585`: Intensity at 585 nm
  - `R_610`: Intensity at 610 nm
  - `I_645`: Intensity at 645 nm
  - `S_680`: Intensity at 680 nm
  - `J_705`: Intensity at 705 nm
  - `T_730`: Intensity at 730 nm
  - `U_760`: Intensity at 760 nm
  - `V_810`: Intensity at 810 nm
  - `W_860`: Intensity at 860 nm
  - `K_900`: Intensity at 900 nm
  - `L_940`: Intensity at 940 nm

---

## Data Characteristics

### Wavelength Information
- **Range**: 410-940 nm (Near-Infrared to Visible range)
- **Number of Wavelengths**: 18 discrete wavelengths
- **Wavelengths**: 410, 435, 460, 485, 510, 535, 560, 585, 610, 645, 680, 705, 730, 760, 810, 860, 900, 940 nm

### Brix Values (Sugar Content)
- **Range**: 4.575 to 6.3
- **Measurement Method**: Refractometer
- **Purpose**: Calibration reference for NIR sensor

### Temperature Data
- **Sensors**: 3 temperature sensors (Temp0, Temp1, Temp2)
- **Range**: Approximately 31-45°C (based on sample data)
- **Units**: Celsius

### Tomato Identifiers
- **Tomato IDs**: 1To, 2To, 15To, etc.
- **Cluster IDs**: 2Ri, 4Ri, etc.
- **Row IDs**: 2Re, 5Re, etc.
- **Day IDs**: 4Ta, 5Ta, etc.

---

## Data Quality Observations

### Anomalies Detected
1. **Extreme Values**: Some spectral intensity values are extremely high (e.g., 4294967300.00), which may indicate:
   - Sensor saturation
   - Measurement errors
   - Data corruption
   - Special calibration measurements

2. **Inconsistent Formatting**: Some tomato identifiers use pipe notation (e.g., "15|2|2") in later entries

3. **Temperature Variations**: Significant temperature differences between sensors may indicate:
   - Different sensor locations
   - Environmental variations
   - Sensor calibration issues

### Data Patterns
- **Measurement Groups**: Data appears to be grouped by tomato, cluster, row, and day
- **Sequential Counter**: Counter values increase sequentially from 1000 to 1309
- **Brix Consistency**: Brix values are relatively consistent within measurement groups

---

## Parsing Implementation

A Python parser (`parse_spectra_file.py`) has been created with the following capabilities:

### Features
1. **Metadata Extraction**: Automatically extracts experiment metadata from the first line
2. **Header Parsing**: Identifies column names and wavelength information
3. **Data Parsing**: Parses all 2,049 spectral measurements
4. **Data Validation**: Handles German decimal format (comma as decimal separator)
5. **Export Capabilities**: Can export to JSON format for further analysis

### Usage Example

```python
from parse_spectra_file import SpectraFileParser

# Parse the file
parser = SpectraFileParser('T4-T5_ALLE_mit_Brix_2.txt')
parser.parse()

# Get summary
summary = parser.get_summary()

# Access spectral data
spectra = parser.spectral_data

# Filter by tomato
 tomato_spectra = parser.get_spectra_by_tomato('1To')

# Filter by Brix range
brix_filtered = parser.get_spectra_by_brix_range(5.0, 6.0)

# Export to JSON
parser.export_to_json('output.json')
```

---

## Integration Recommendations

### For Django Application
1. **Model Design**: Create models for Experiment, Spectrum, and Wavelength
2. **Import Script**: Use the parser to import data into the database
3. **Data Cleaning**: Implement data validation and cleaning for anomalies
4. **API Endpoints**: Create endpoints for accessing spectral data

### For Data Analysis
1. **Preprocessing**: Handle extreme values and missing data
2. **Normalization**: Normalize spectral intensities for comparison
3. **Feature Extraction**: Extract features from spectral data
4. **Calibration**: Use Brix values for NIR sensor calibration

---

## File Format Specification

```
Line 1: Experiment description (German text)
Line 2: Empty line
Line 3: Column headers (semicolon-separated)
Lines 4+: Data rows (semicolon-separated)

Each data row contains:
- 8 metadata fields (Counter, Messobjekt, Kurz, Tomate, Rispe, Reihe, Tag, Brix)
- 3 temperature fields (Temp0, Temp1, Temp2)
- 18 spectral intensity values (A_410 to L_940)
```

---

## Conclusion

The file `T4-T5_ALLE_mit_Brix_2.txt` contains comprehensive NIR spectroscopy data for tomato ripeness determination. The data includes:

- **2,049 spectral measurements**
- **18 wavelength channels** (410-940 nm)
- **Rich metadata** including tomato identifiers, cluster information, and environmental conditions
- **Reference measurements** (Brix values) for calibration
- **Temperature data** for environmental context

The provided parser successfully extracts and structures this data for integration into the NIR_Mistral Django application.