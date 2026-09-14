# NIR Platform — Open Issues Blocking the Interim Goal

**Interim goal:** Upload → Evaluation → Analysis → HTML report for the SparkFun
NIR Triad tomato-ripeness dataset (`T4-T5_ALLE_mit_Brix_2.txt`, 18 wavelengths
410–940 nm, Brix/fructose reference values from a refractometer).

**Status as of last session:** Upload and parsing are now fixed for the Triad
file. The analysis pipeline runs end-to-end in offline tests. **The web UI
still showed the 75% "Processing" spinner and did not change** after the last
fix — this is the top priority for next time.

Branch: `vibe/upload-eval-analysis-quarto-html-0b1bfc` · PR: #1

---

## A. Must-fix before the interim goal works end-to-end in the browser

### A1. (CRITICAL) Analysis detail page stuck at the 75% progress bar
**Symptom:** After uploading the Triad file, the detail page shows the animated
"Processing Your Data" spinner at 75% and never advances. No results, no
report.

**Likely cause — the database still holds the OLD failed record:**
`analysis_detail` only runs the analysis when `is_processed == False`. The
previous buggy attempts already set `is_processed = True` (the error branch
marks it processed to avoid retry loops). Reloading that same URL therefore
re-renders the already-processed record — but the *results are empty* because
the earlier analysis failed, so the results sections render blank and the page
looks frozen. The fix I pushed fixes *new* uploads, not the stale records.

**To confirm:** Check the server log for these lines on the upload + first GET:
- `Uploaded spectral data saved id=... wl_len=18 int_len=18 spec_type='sparkfun_nir_triad'`
  → if `wl_len` is NOT 18, the file is still parsed as two-column (see A2).
- `Analysis pending for id=... wl_len=18 int_len=18` then
  `Starting analysis for id=...` then `Analysis completed for id=...`
  → if you never see "Analysis completed", the pipeline still fails (paste the
  `Error performing analysis:` traceback).

**Action:**
1. Upload the Triad file **fresh** (do not reload an old analysis URL). Open the
   *new* `/analysis/<new-uuid>/` URL the upload redirects to.
2. If still stuck: in the Django shell, check
   `SpectralData.objects.get(id=<uuid>).is_processed` and
   `.analysis_results`. If `is_processed=True` with empty results, delete that
   record and re-upload.
3. Consider: when the analysis fails, do NOT set `is_processed=True`; instead
   keep it False and show a clear "analysis failed — re-upload" state, so the
   page never silently freezes. (views.py around line 327.)

### A2. Verify the Triad file is actually encoded as Latin-1/cp1252
My fix makes the loader try `utf-8 → latin-1 → cp1252`. It works on synthetic
copies of your data, but I could not read your *real* file. If your real file is
yet another encoding (e.g. UTF-16, or has a different delimiter), parsing still
falls through to two-column mode.

**Action:** Run on your machine and paste the output:
```bash
cd ~/Vibe_dev_environment/nir_platform
file django_app/uploads/*.txt            # shows encoding hints
DB_HOST=localhost ../.venv/bin/python -c "
import sys; sys.path.insert(0, '.')
from agents.spectral_analysis_agent import SpectralAnalysisAgent
import asyncio, glob
a = SpectralAnalysisAgent()
for f in sorted(glob.glob('django_app/uploads/*.txt')):
    try:
        l = asyncio.run(a._load_spectral_data(f))
        print(f.split('/')[-1], 'wl=', len(l.wavelengths), 'ns=', l.metadata.get('num_samples'))
    except Exception as e:
        print(f.split('/')[-1], 'FAIL', e)
"
```
The Triad file should print `wl=18 ns=<row count>`. If it prints `wl=` something
else, send me the file (or the `file` output) and I will extend the loader.

### A3. (CRITICAL) Calibration ignores the Brix/fructose reference data
This is the **core scientific gap** for the interim goal. The Triad file
contains per-sample `Brix` (and temps) in metadata, plus 18 intensity channels
per sample — the whole point is to calibrate NIR → Brix. Today
`CalibrationAgent.generate_calibration` only builds a *wavelength* calibration
from the spectrometer's fixed points and a dummy intensity calibration
(`y_data = ones(5)`). It never reads the `Brix` column and never builds a
NIR→Brix regression.

**Action:**
- In `calibration_agent.py`, build a multivariate regression
  (18 channels → Brix) using the per-sample rows: X = intensity matrix
  (from `_load_wide_nir`'s `intensity_matrix`, not just the column means),
  y = the `Brix` column. Store it in a new `CalibrationResult` field (e.g.
  `analyte_calibration`) and surface it in the report.
- This requires `_load_wide_nir` to also expose the full per-sample intensity
  matrix (currently only the column-wise mean is kept). Add it to metadata or
  as a field on `SpectralData`.

---

## B. Correctness / robustness (fix alongside A)

### B1. No empty-array crash protection in QA / reporting agents
I guarded the spectral-analysis agent. `quality_assurance_agent.py` and
`reporting_agent.py` still call `np.min/max/mean` and index
`wavelengths[peaks]` without size checks. If any path produces empty data
they will crash. Add the same guards.

### B2. `detail.html` still references `info.unit|default:"",` template bug history
Already fixed in earlier commits, but verify the template renders on a real
processed record (the `cal.spectrometer_parameters.items` loop).

### B3. `/analysis/<uuid>/report/` returns 404 when no Report row exists
`analysis_report` uses `get_object_or_404(Report, ...)`. If the analysis failed
before creating a Report (the old stuck records), the "View Report" button 404s.
Add a graceful "report not generated yet" fallback.

---

## C. Architecture / dev-experience (not blocking, but causes the "server keeps coming back" pain)

### C1. Synchronous analysis in a GET request
`analysis_detail` runs the whole 5-agent pipeline via `asyncio.run()` inside
the GET handler. For small files it's fast, but it blocks the single-threaded
dev server and times out on larger files. Proper fix: run analysis in a
background task (Celery/thread) and have the detail page poll for status.
(Larger change — only do this if A1 persists or files grow.)

### C2. Docker `nir_django` auto-restarts and shadows the local dev server
`restart: unless-stopped` + baked-in image code on port 8000 keeps grabbing
the port. `dev-run.sh` mitigates it, but the root cause is the compose policy.
Set `restart: "no"` (or `on-failure`) for `nir_django`/`nir_mcp` in
`docker-compose.yml` so the local server isn't constantly fought over.

### C3. `DB_HOST` must be set per environment
Host runs need `DB_HOST=localhost`; Docker needs `postgres`. It's an env var
now, but easy to forget. `dev-run.sh` sets it; document it or default it in
`settings.py` (`os.environ.get("DB_HOST", "localhost")`).

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
- Wide-format loader now tries utf-8/latin-1/cp1252 (so German-umlaut exports
  parse) — **the fix that should make the Triad file parse as 18 wavelengths.**
- Empty-array guards in the spectral-analysis agent; `[DIAG]` logs cleaned up.

---

## Recommended order for next session
1. **A1 + A2** — confirm a *fresh* Triad upload parses as 18 wavelengths and
   completes analysis (use the log lines above). This validates my last fix
   actually took effect in the browser.
2. **A3** — implement NIR→Brix calibration. This is the scientific core of the
   interim goal; without it the report has no ripeness result.
3. **B1, B3** — harden QA/reporting + report 404 so the pipeline can't freeze
   the UI again.
4. **C2** — set Docker restart policy to `no` to end the port-8000 fight.
