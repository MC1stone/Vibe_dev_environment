# NIR Platform — Open Issues Blocking the Interim Goal

**Interim goal:** Upload → Evaluation → Analysis → HTML report for the SparkFun
NIR Triad tomato-ripeness dataset (`T4-T5_ALLE_mit_Brix_2.txt`, 18 wavelengths
410–940 nm, Brix/fructose reference values from a refractometer).

**Status as of last session:** The previous report guessed the 75 % spinner
freeze was due to stale DB records or a file-encoding mismatch. **Both guesses
were wrong.** The real root cause was found and fixed this session (see A1/A2
below), and the missing scientific core (NIR→Brix calibration) is now
implemented (A3).

Branch: `vibe/upload-eval-analysis-quarto-html-0b1bfc` · PR: #1

---

## A. Must-fix before the interim goal works end-to-end in the browser

### A1. (RESOLVED — root cause found) Analysis detail page stuck at the 75 % progress bar
**Real root cause (verified against the actual `T4-T5_ALLE_mit_Brix_2.txt`):**
the file has a **5-line free-text German preamble** before the real column
header:

```
line 0: "Der Versuch Tomaten Reifegradbestimmung wurde mit dem SparkFun NIR Triad ..."
line 1: (blank)
line 2: Counter;Messobjekt;Kurz;Tomate;Rispe;Reihe;Tag;Brix;Temp0;Temp1;Temp2;A_410;B_435;...;L_940
line 3+: data rows
```

The old loader called `pd.read_csv(... )` with the default header, so line 0
(the prose) became the column names and the `A_410`-style spectral columns were
never found. The parse fell through to two-column mode and produced garbage
(`wl_len=2049, int_len=0`) — so the analysis could never produce a real result
and the page looked frozen. It was **not** a stale DB record and **not** an
encoding problem (the file is plain UTF-8).

**Fix applied:** the Data Loader Agent scans the file for the first line that
contains several `A_410`-style spectral tokens and uses that line index as the
pandas `skiprows`/header, so the real `Counter;...;A_410;...` header is parsed.
Verified output: `wl_len=18, ns=2049, spec_type='sparkfun_nir_triad'`.

**To validate in the browser next time:** upload the Triad file **fresh** and
watch the server log for:
- `Data Loader Agent loading ...` then
- `Loaded ...: wl_len=18 ns=2049 spec_type='sparkfun_nir_triad' format='wide_nir_multisample'`
- `Analysis completed for id=...`
If `wl_len=18` appears, the parse fix took effect and the page should advance
past 75 %.

**Still recommended (not done):** when the analysis fails, do NOT set
`is_processed=True`; keep it False and show a clear "analysis failed —
re-upload" state, so the page never silently freezes. (`views.py` around the
`analysis_detail` GET handler.)

### A2. (RESOLVED) Encoding / 18-wavelength parse
The real file is **UTF-8** (the earlier "try latin-1/cp1252" fix was a red
herring). The actual blocker was the prose preamble swallowing the header
(see A1). The loader now finds the spectral header row regardless of preamble,
so a fresh upload parses as 18 wavelengths. No further action needed unless a
*different* file uses UTF-16 or another delimiter — then extend
`DataLoaderAgent._read_delimited`.

### A3. (RESOLVED — implemented this session) Calibration ignores the Brix/fructose reference data
**Was:** `CalibrationAgent.generate_calibration` only built a synthetic
wavelength calibration from the spectrometer's fixed points and a dummy
intensity calibration (`y=ones(5)`). It never read the `Brix` column and never
built a NIR→Brix regression — the actual goal of the ripeness study.

**Now implemented:**
- `DataLoaderAgent` exposes the **full per-sample intensity matrix**
  (`intensity_matrix`, 2049×18) plus the `Brix` reference column in metadata.
- `views.py` carries `intensity_matrix`, `spectral_columns`, and
  `spectrometer_info` into `SpectralData.metadata` at upload time.
- `CalibrationAgent._generate_analyte_calibration` builds a multivariate
  **PLS regression** of the 18 channels → Brix, standardizing X first, and
  selects the number of components by 5-fold cross-validation on R². Results
  are stored in a new `CalibrationResult.analyte_calibration`
  (`AnalyteCalibration`: coefficients on the raw intensity scale, intercept,
  R²cv, RMSEcv, R²cal, RMSEcal, Brix range, wavelengths).
- Surfaced in the UI (`detail.html`: NIR→Brix quality badge + a full
  "NIR → Brix Calibration" block) and in the Quarto/Markdown report
  (`reporting_agent.py`: a "NIR → Brix Calibration (Ripeness Model)" subsection
  with per-wavelength coefficients).

**Measured result on the real Triad file:**
PLS, 4 components, 5-fold CV: **R²cv = 0.372, RMSEcv = 0.80 °Brix**
(Brix range 4.32–8.10 °Brix, 2049 samples). This is a modest but real
cross-validated ripeness model — the scientific core of the interim goal.

**Next steps to improve the model (optional):**
- Add sample-level preprocessing (SNV / MSC, 1st-derivative Savitzky-Golay) and
  compare R²cv.
- Group-aware CV (split by tomato / Rispe / Reihe) instead of random 5-fold, to
  avoid optimistic leakage from repeated measurements of the same fruit.
- Try Ridge/PLS with more components and outlier removal; report VIP scores.

---

## B. Correctness / robustness (fix alongside A)

### B1. No empty-array crash protection in QA / reporting agents
`quality_assurance_agent.py` and `reporting_agent.py` still call
`np.min/max/mean` and index `wavelengths[peaks]` without size checks. If any
path produces empty data they will crash. Add the same guards the
spectral-analysis agent already has.

### B2. `/analysis/<uuid>/report/` returns 404 when no Report row exists
`analysis_report` uses `get_object_or_404(Report, ...)`. If the analysis
failed before creating a Report (old stuck records), the "View Report" button
404s. Add a graceful "report not generated yet" fallback.

---

## C. Architecture / dev-experience (not blocking)

### C1. Synchronous analysis in a GET request
`analysis_detail` runs the whole 5-agent pipeline via `asyncio.run()` inside
the GET handler. For small files it's fast, but it blocks the single-threaded
dev server. Proper fix: run analysis in a background task and poll for status.
(Only needed if files grow or A1 still stalls.)

### C2. Docker `nir_django` auto-restarts and shadows the local dev server
`restart: unless-stopped` keeps grabbing port 8000. `dev-run.sh` mitigates it;
the root cause is the compose policy. Set `restart: "no"` (or `on-failure`)
for `nir_django`/`nir_mcp` in `docker-compose.yml`.

### C3. `DB_HOST` must be set per environment
Host runs need `DB_HOST=localhost`; Docker needs `postgres`. `dev-run.sh`
sets it; consider defaulting it in `settings.py`.

### C4. Missing `static/` directory warning
`staticfiles.W004`: `nir_platform/django_app/static` does not exist. Harmless
but noisy. Create the dir or remove it from `STATICFILES_DIRS`.

---

## D. Already fixed (for reference)
- PEP 668 venv setup; `agents` import path; `DB_HOST` configurable.
- `_detect_peaks` `.tolist()` on a list; `_calculate_analysis_metrics`
  `initial_quality` NameError; `_fit_polynomial_calibration` degree guard;
  r_squared divide-by-zero; `CalibrationResult.to_dict()`.
- `report.html` legacy `d-none` block removed; `detail.html` duplicate
  `tooltipTriggerList` removed.
- SparkFun NIR Triad added to spectrometer database + detection by exact
  wavelength-set match.
- `dev-run.sh` stops Docker Django/MCP, pulls code, runs migrations, starts
  local server with banner + port-8000 preflight.
- Empty-array guards in the spectral-analysis agent; `[DIAG]` logs cleaned up.
- **NEW: Data Loader Agent** (`agents/data_loader_agent.py`) — owns ingestion
  and structural parsing of every new upload; finds the real spectral header
  row past a free-text preamble; reads utf-8/latin-1/cp1252; parses wide-NIR
  (per-sample matrix + Brix) and two-column formats; detects the spectrometer
  type. `views.py` now calls `data_loader_agent.load(...)` on every upload
  instead of `spectral_agent._load_spectral_data(...)`.
- **NEW: NIR→Brix PLS calibration** (`agents/calibration_agent.py`) —
  `AnalyteCalibration` dataclass + `_generate_analyte_calibration`; surfaced
  in `detail.html` and the report.
