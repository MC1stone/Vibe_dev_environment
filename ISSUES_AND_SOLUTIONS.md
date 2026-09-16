# NIR Platform — Open Issues & Solutions Overview

**Interim goal:** Upload → Evaluation → Analysis → HTML report for the SparkFun
NIR Triad tomato-ripeness dataset (`T4-T5_ALLE_mit_Brix_2.txt`, 18 wavelengths
410–940 nm, Brix reference values).

Branch: `vibe/upload-eval-analysis-quarto-html-0b1bfc` · PR: #1
Last commit: `93577b4`

This document supersedes the earlier `TODO_OPEN_ISSUES.md` (which only covered
the first session). Items are grouped by status with the root cause, the
concrete solution, and how to apply it.

---

## 1. Already fixed (verified in code) — context only

| Issue | Root cause | Fix | Commit |
|---|---|---|---|
| Analysis detail stuck at 75 % | 5-line German preamble swallowed the CSV header; `A_410` columns never parsed (`wl_len=2049, int_len=0`) | Data Loader scans for the first row with multiple `A_xxx` spectral tokens and uses it as `skiprows`/header | `f23fa66` |
| Calibration ignored Brix column | `CalibrationAgent` built a dummy `y=ones(5)` intensity calibration, no NIR→Brix regression | New `AnalyteCalibration` PLS regression (18 channels → Brix), CV-tuned components, surfaced in UI + report | `f23fa66` / `8879937` |
| Report graphs rendered as literal escaped text | Markdown code fences were HTML-escaped instead of executed/embedded | `render_report` executes plot code and embeds base64 PNGs; no-markdown HTML fallback | `5b35e79` / `1206273` |
| Chat bot not working | Not wired to Ollama | `api_chat` calls Ollama `mistral` model at configured `ollama_url` | `1206273` |
| Documentation site broken | TemplateSyntaxError from broken template tags | Fixed template tags | `b7d9ef4` |
| Broken `{{ form.metadata.value }}` textarea tag in upload form | Malformed template tag | Fixed textarea tag | `a5b9653` |
| `NameError: 'Dict' not defined` (runtime crash) | `Dict` used in annotation without import under the agent import chain | Added import / fixed annotation | `ae790b6` |
| Ollama container not reachable / containers not started | `dev-run.sh` did not start data containers | `dev-run.sh` starts postgres, qdrant, ollama via `docker compose up -d` | `5341f1a` |
| Port 8000 stuck (Docker `nir_django` auto-restart shadows local server) | `restart: unless-stopped` re-grabs port 8000 | `dev-run.sh` stops/`docker update --restart=no` those containers; Port Management Agent preflight bails out cleanly when port busy | `be0fa17` |
| Outlier detection weak / Neural-network analysis missing | Calibration had no robust outlier removal or NN path | PCA-Mahalanobis spectral-outlier removal + MLP neural-network calibration added | `8879937` |
| No overview / recall / comparison / recalibration | Only single-analysis detail existed | Analyses overview, compare, and recalibrate views + Qdrant/numpy spectral search | `b88e879` |
| Metadata quality rating disagreed (F vs A) | Three grade scales differed; per-sample data columns scored as metadata | Unified A≥90/B≥75/C≥60/D≥40/F<40; per-sample columns excluded from scoring | `15491c3` |
| Overview grade ~20 % while Data Loader showed 90 % A | Headline `metadata_quality_score` used the harsh MetadataQualityAgent (ISO 19115/Open Science/Federated fields a single NIR run never has) | Use Data Loader's `metadata['metadata_quality'].score` for the headline + blend; standards result kept for reference | `93577b4` |
| Stale failed "F" record could not be removed | No delete path | `delete_analysis` view (POST `/analysis/<id>/delete/`) drops row + reports + vector index; trash buttons in overview & detail | `15491c3` |

**Important caveat on the last two rows:** the score fix only affects
**newly-computed** analyses. Existing DB rows still hold the old blended value.
To see the corrected grade, click **Re-run Analysis** on the affected row (or
re-upload + delete the stale row).

---

## 2. Open — blocking end-to-end usability

### 2.1 Existing rows still show old scores after the grade fix
**Issue:** the grade-source fix (`93577b4`) recomputes on the next analysis
run, but already-processed rows keep their stored `overall_quality_score`.
So "no change yet" until a re-run.
**Solution:** Re-run the analysis (detail page → **Re-run Analysis**) for each
affected row, or delete stale rows and re-upload.
**Apply:** open each analysis detail page, click **Re-run Analysis**. Confirm
the server banner shows commit `93577b4` and started without a traceback
first — an older running process will use old code.
**Optional hardening (not done):** add a one-off management command or a
"Recompute all grades" admin action that re-derives `metadata_quality_score`
from the stored Data Loader rating for every row.

### 2.2 Report still "useless" / graphs missing — UI/UX review
**Issue:** the user reports the printed report is not useful and graphs are
still missing despite the base64-embedding fix.
**Suspected causes to verify:**
- The embedding fix only runs when matplotlib is importable **and** the plot
  code cell executes without error. If a report was generated while matplotlib
  was missing (the earlier `ModuleNotFoundError`), its `html_content` has no
  figures and will not gain them on reload — it must be regenerated.
- The calibration curve / equation block is gated on
  `analyte_calibration` existing in the results; if a stale report predates
  the PLS work it has no curve.
**Solution:**
1. Confirm `pip install matplotlib` in the active `.venv` (already in
   `requirements.txt`).
2. **Re-run Analysis** on the row so the report regenerates with figures.
3. If graphs still missing: capture the server log around
   `Error rendering Quarto report` / the plot-code execution and send it —
   that pinpoints which figure cell fails.
**Apply:** `git pull`, activate `.venv`, `pip install -r requirements.txt`,
restart, then **Re-run Analysis**.
**UI/UX:** the user explicitly asked the UI/UX agent to review and optimize the
report layout. This is a design pass over `reporting_agent.py`
(`_render_markdown_to_html`, CSS in `_html_wrapper`) and `report.html` — not
yet done.

---

## 3. Open — correctness / robustness

### 3.1 Empty-array crash protection in QA / reporting agents
**Issue:** `quality_assurance_agent.py` has guards (`if not wavelengths`,
`if not intensities`), but `reporting_agent.py` still calls
`np.mean(intensities) + 2*np.std(...)` (line ~653) and
`wavelengths[peaks].tolist()` (line ~659) without size checks. An empty or
all-failed path will crash there.
**Solution:** mirror the spectral-analysis agent's guards — early-return
empty/sentinel values before `np.mean`/indexing.
**Apply:** in `reporting_agent.py` peak/plot generation, add
`if len(intensities) == 0 or len(peaks) == 0: return None` before indexing.

### 3.2 `/analysis/<id>/report/` returns 404 when no Report row exists
**Issue:** `analysis_report` (views.py:667) uses
`get_object_or_404(Report, ...)`. Old/stuck records that failed before
creating a Report 404 on "View Report".
**Solution:** render a graceful "report not generated yet — re-run analysis"
page instead of raising 404.
**Apply:** replace `get_object_or_404` with `.first()` + a fallback template
render.

### 3.3 Failed analysis silently marks `is_processed=True`
**Issue:** on exception, `analysis_detail` sets `is_processed=True` to avoid
retry loops (views.py ~602). This is what originally made pages look frozen —
the failed state is indistinguishable from "done with empty results".
**Solution:** keep `is_processed=False` on failure and render a clear
"analysis failed — re-upload / re-run" state with the error message.
**Apply:** in the `except` block of `analysis_detail`, do not set
`is_processed=True`; store the error in `analysis_results` and show it.

---

## 4. Open — architecture / dev-experience

### 4.1 Synchronous analysis in a GET request
**Issue:** `analysis_detail` runs the whole 5-agent pipeline via
`asyncio.run()` inside the GET handler (views.py:526). It blocks the
single-threaded dev server; large files stall the browser.
**Solution:** run analysis in a background task (Celery / `threading` /
`asyncio.create_task`) and poll for status, or push to the existing MCP/n8n
pipeline.
**Apply:** add a `processing` status flag and a small polling endpoint; the
detail page shows progress and refreshes. Lower priority while files stay
small.

### 4.2 Docker `nir_django` restart policy
**Issue:** `restart: unless-stopped` in `docker-compose.yml` keeps re-grabbing
port 8000; `dev-run.sh` works around it with `docker update --restart=no`.
**Solution:** set `restart: "no"` (or `on-failure`) for `nir_django`/`nir_mcp`
in `nir_platform/docker/docker-compose.yml` so the workaround isn't needed.
**Apply:** edit the compose file's restart policy.

### 4.3 `DB_HOST` default mismatch
**Issue:** `settings.py` defaults `DB_HOST` to `postgres` (Docker), but host
runs need `localhost`. `dev-run.sh` sets it; bare `manage.py` does not.
**Solution:** default `DB_HOST` to `localhost` in settings (Docker overrides
via env), or document the requirement in the dev-run banner.
**Apply:** change the default in `settings.py:85`.

### 4.4 Missing `static/` directory warning
**Issue:** `staticfiles.W004` — `nir_platform/django_app/static` does not
exist but is in `STATICFILES_DIRS`.
**Solution:** create the dir (with a `.gitkeep`) or remove the entry.
**Apply:** `mkdir nir_platform/django_app/static && touch .../static/.gitkeep`.

### 4.5 Qdrant client/server version mismatch warning
**Issue:** `qdrant_client 1.19.0` vs server `1.8.0` prints a compatibility
warning on every connect.
**Solution:** pin `qdrant-client` to a 1.8.x-compatible version in
`requirements.txt`, or pass `check_compatibility=False` in the client init.
**Apply:** pin in requirements or set the flag in `spectral_search_agent.py`.

---

## 5. Scientific core — model quality (optional, the actual study goal)

Current measured result on the real Triad file: PLS, 4 components, 5-fold CV —
**R²cv = 0.372, RMSEcv = 0.80 °Brix** (Brix 4.32–8.10, 2049 samples). Modest
but real. To improve:

- **Preprocessing:** add SNV / MSC and 1st-derivative Savitzky-Golay before
  PLS; compare R²cv.
- **Group-aware CV:** split by tomato / Rispe / Reihe instead of random 5-fold
  to avoid optimistic leakage from repeated measurements of the same fruit.
- **Outliers:** the PCA-Mahalanobis removal is in place — report how many were
  removed and the before/after R²cv.
- **Models:** compare PLS vs Ridge vs the new MLP; report VIP scores.
- **Feature importance:** surface per-wavelength coefficients/VIP in the
  report so the customer sees *which* channels drive ripeness.

---

## How to resume next session
1. `git pull` on branch `vibe/upload-eval-analysis-quarto-html-0b1bfc`,
   activate `.venv`, `pip install -r requirements.txt`, `./dev-run.sh`.
2. Confirm the banner shows commit `93577b4` and no startup traceback.
3. **Re-run Analysis** on the existing row (or re-upload) to regenerate the
   report and grades with the new code.
4. If graphs still missing, capture the server log around report rendering.
5. Pick the next open item from §2–§4.
