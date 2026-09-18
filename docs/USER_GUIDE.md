# NIR Intelligence Platform — User Guide

The NIR Intelligence Platform (NIR-IP) lets Open Science participants
analyse near-infrared (NIR) spectra collected with **any** spectrometer —
commercial or DIY. Upload a spectral data file, and the specialist agent
crew runs a full analysis cycle, grades the metadata, detects sensor
issues, builds calibrations, and produces an HTML report.

This version runs **fully local**. Federated Learning and the Ilias
learning platform are **out of scope**.

## The agent crew

Each analysis runs the following specialists in sequence (the "CrewAI
orchestra"):

1. **Data Loader Agent** — parses any spectral file (CSV, wide-NIR
   exports, TXT, JSON), extracts wavelengths, the per-sample intensity
   matrix, Brix/reference columns, and a first metadata-quality rating.
2. **Spectral Analysis Agent** — baseline correction, noise reduction,
   peak detection, spectrometer-type detection, and sensor-issue
   detection (wavelength shift, intensity drift).
3. **Hardware Information Agent** — consolidates everything known about
   the spectrometer from detection, a knowledge base, the file header,
   and the spectral data itself.
4. **Metadata Quality Agent** — grades the metadata against NIR-relevant
   standards (ASTM E131/E1421, NIR-Specific); ISO 19115 / Open Science /
   Federated fields are bonus-only.
5. **Calibration Agent** — PLS and Neural-Network (MLP) calibration of
   NIR → Brix, with SNV/MSC preprocessing, outlier removal, and a
   PLS-vs-MLP comparison.
6. **Quality Assurance Agent** — validates the analysis results.
7. **Reporting Agent** — generates a Quarto report and renders it to HTML
   in the app's report viewer.

## 1. Upload spectral data

1. Open **http://localhost:8000/upload/**.
2. Choose your spectral data file. Accepted: `.csv`, `.txt`, `.json`,
   and wide-NIR exports (one row per sample, with Brix/Temp columns).
   Non-spectral attachments are stored as linked artifacts, not parsed.
3. Optionally select the spectrometer type. Leave it on *Auto-detect*
   and the Data Loader Agent identifies the device.
4. Click **Upload**.

The Data Loader Agent parses the file, stores the spectrum + the
per-sample intensity matrix + the extracted metadata, and creates an
analysis record. You are redirected to the analysis detail page.

## 2. Run the analysis

On the analysis detail page, click **Re-run analysis** (or it starts
automatically after upload). The agent crew runs in order:

```
Data Loader → Spectral Analysis → Hardware Info → Metadata Quality
            → Calibration → QA → Reporting → Qdrant index
```

Progress messages appear in the page header. A run typically takes a
few seconds; the Quarto render may add a few more. If the report is not
ready yet, the page auto-refreshes until it is.

## 3. Read the analysis detail page

The detail page shows, in order:

- **Overview** — quality grade, scores, spectrometer, file info.
- **Data Quality Metrics** — wavelength/intensity quality, outliers,
  SNR, baseline flatness.
- **Spectrometer Health** — the detected device with a confidence badge,
  manufacturer, model, wavelength range, resolution, channels, and the
  sensor issues the Spectral Analysis Agent found (wavelength shift,
  intensity drift) with their severity and a recommendation. A link
  goes to the full **Hardware Information** page.
- **Detected Issues** — all issues with severity, description,
  explanation, and concrete fix steps.
- **Recommendations** — enhancement recommendations with method and
  application steps.
- **Metadata Quality** — grade (A–F), present fields, missing fields,
  per-standard compliance.
- **Calibration Results** — the PLS-vs-MLP **Model Comparison** box
  (which model has the higher cross-validated R²), then PLS details
  (preprocessing, outliers removed + their indices, R²cv, RMSEcv), MLP
  details, and the spectrometer parameter recommendations table.

## 4. Understand the metadata grade

The grade reflects **NIR-relevant metadata completeness**, not generic
geospatial/open-science fields.

| Grade | Meaning                                                  |
|-------|----------------------------------------------------------|
| A     | Excellent — all NIR-required + many optional fields present|
| B     | Good — all required + several optional fields            |
| C     | Fair — required fields present, some optionals            |
| D     | Poor — some required fields missing                       |
| F     | Fail — little or no NIR-relevant metadata                 |

**Required NIR fields** (missing these lowers the grade):
`spectrometer_type`, `wavelength_range`, `sample_type`, `date`.

**Optional NIR fields** (these raise the grade when present):
`resolution`, `sample_preparation`, `measurement_geometry`,
`temperature`, `humidity`, `integration_time`, `scans_averaged`,
`light_source`, `detector_type`.

**Bonus fields** (ISO 19115, Open Science, Federated) can only raise the
score; they never drag it down when absent.

To improve a low grade, add the missing required fields shown on the
detail page and re-run the analysis.

## 5. Interpret the calibration

The **Model Comparison** box shows PLS and MLP side by side:

- **R² (CV)** — cross-validated R² (how well the model generalises).
  Higher is better. The "Best" badge marks the higher one.
- **RMSE (CV)** — cross-validated root-mean-square error in °Brix.
  Lower is better.
- **Outliers removed** — how many samples were excluded as outliers,
  and (for PLS) their indices.

The **predicted-vs-measured** scatter in the report shows kept samples
in blue and removed outliers in red X, so you can see whether the
calibration matches the data.

On small datasets (common with DIY setups), PLS usually generalises
better; MLP can overfit. The "Best" badge uses cross-validated R² to
avoid rewarding overfitting.

## 6. View the full report

Click **View Full Report**. The Reporting Agent generated a Quarto
document and rendered it to HTML, embedded in the app. It contains:

- Spectral analysis (original vs processed spectrum plot)
- Metadata quality assessment
- Calibration results + predicted-vs-measured plot
- PLS-vs-MLP comparison table
- Spectrometer parameter recommendations
- Hardware information section
- Recommendations and conclusion
- Appendix with the Python source code (display-only, not executed)

If the Quarto CLI is unavailable, an in-process Python renderer produces
the HTML instead, with the same figures embedded as images.

## 7. Hardware information

Click the **Hardware** button (or the link on the Spectrometer Health
card). The Hardware Information Agent consolidated what is known about
the device from four sources:

1. The detected spectrometer type from the spectrum.
2. The known-device knowledge base (Ocean Optics, ASD FieldSpec, Bruker,
   DIY Raspberry Pi, DIY Arduino, SparkFun NIR Triad).
3. The uploaded file's header metadata.
4. Characteristics derived from the spectral data (wavelength range,
   resolution, channel count).

Each field shows its source and confidence. Use this to confirm which
device produced the data and whether the parameters match.

## 8. Compare and recall analyses

- **Analyses Overview** (`/analysis/`) lists all past analyses with their
  grades and report links. Indexed analyses are recalled from Qdrant
  (the spectral fingerprint vector index) so the search/comparison works
  without re-indexing on every page load.
- **Compare** lets you select 2+ analyses and view them side by side,
  plus the most similar past measurements found via the vector index.

## 9. Download all data

Click **Download All Data** on the detail page to get the original file,
the processed data, and the analysis results as a package.

## 10. Chat with the analysis (optional)

If Ollama is running, the chat assistant answers questions about the
current analysis using the local Mistral model. If Ollama is offline,
it returns a local canned reply. Ensure Ollama is on port 11435 and the
`mistral` model is pulled (see INSTALL.md).

## Tips

- **First-time user**: just upload a CSV and click Re-run; everything
  else is automatic.
- **Low metadata grade**: add `spectrometer_type`, `wavelength_range`,
  `sample_type`, and `date` to the file header and re-run.
- **Calibration looks off**: check the outliers-removed indices and the
  preprocessing (SNV vs raw) on the detail page; add more samples to
  improve cross-validation.
- **Sensor issues**: the Spectrometer Health card tells you what is
  wrong (shift/drift) and how to fix it (re-measure dark/white
  reference, normalize, etc.).
