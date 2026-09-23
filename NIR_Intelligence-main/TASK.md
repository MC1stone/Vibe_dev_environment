# NIR Intelligence Platform - Task Definition

## Overview
This document defines the current task for the NIR Intelligence Platform development.

## Current Task: OP14 - Truthful Agent Statements in the Project Report

### Objective

The report for the Dpark fun NIR Triad file (18 channels, 410-940 nm, 2049
measurements) contained wrong agent statements: the wide-format export went
through the two-column fallback loader (garbled wavelength axis), the spectral
agent called the valid VIS range 'outside expected range (700, 2500)', the
sensor agent derived noise 0.71 from the genuine channel shape, FAISS failed
with 'no usable intensity vector' despite 18 intensities (schema mismatch),
and the metadata agent complained about fields the platform itself knows.
OP14 fixes each statement at the root cause so the report describes the data
truthfully.

### Scope

- `services/project_ingest.py`: wide-format detection now survives preamble
  blank lines (skip_blank_lines=False + dropna), channel conversion without
  the thousands-separator heuristic, median per channel (robust against ADC
  overflow markers), replicate extraction from the longest same-object run,
  saturated-measurement count
- `agents/spectral_analysis_agent.py`: expected wavelength range is opt-in
  (None default) - spectrometer agnostic, no false VIS/NIR complaint
- `agents/sensor_quality_agent.py`: replica-based noise (std across
  measurements, not channel-shape differences), trend-based drift,
  no false offset against the replicates' own mean
- `agents/nir_analysis_crew.py`: known sample_id/instrument/acquisition_time
  aliases fed into the metadata assessment; measurement replicas passed to
  the sensor agent
- `services/project_crew.py`: FAISS query in the unified schema, skipped
  when the project has no other datasets; saturation warning surfaced in
  the crew result; timezone-aware timestamps
- `tests/test_op14_agent_truthfulness.py` (31 checks) + CI matrix extended

### Out of Scope

- Persistent spectral database comparison (OP15+, user explicitly deferred)
- Editing the agent thresholds per project (defaults stay)

### Success Criteria

- Triad file: 18 channels 410-940 nm, 2049 measurements, Brix 4.3-8.1 reported
- All seven agent sections complete; no false range/noise/FAISS statements
- Saturated measurements (ADC overflow) reported as their own warning
- Existing test matrices stay green (no regressions)

## Completed Task: OP13 - Online Metadata Editing in the Project Report

### Objective

The phase-1 report showed missing metadata fields with recommendations,
but the only adaptation path was editing files externally and re-uploading
them. OP13 adds the online path per MO 2-4: a metadata editor per dataset on
the project page (drafted phase only) - recommended fields prefilled from the
assessment, custom fields addable - the overrides are stored on the project
(metadata_overrides), the preparation report is rebuilt and the metadata
quality score updates immediately. No external file versions, no re-upload.

### Predecessors

- OP10: COMPLETED (project workflow)
- OP11: COMPLETED (rendered final report)
- OP12: COMPLETED (project creation UI)

### Scope

- `core/models.py`: `metadata_overrides` JSON field + migration 0005
- `services/project_ingest.py`: apply_metadata_overrides (empty values ignored,
  user-entered fields tracked for the report)
- `api/project_views.py` + `project_urls.py`: ProjectMetadataView (POST
  /projects/<id>/metadata/, drafted phase only, 409 after release)
- `templates/project_report.html`: per-dataset metadata editor (accordion,
  prefilled recommended fields, custom field add, inline status)
- `tests/test_op13_online_metadata_editing.py` (28 checks) + CI matrix extended

### Out of Scope

- Editing the measurement data itself (still re-upload, by design)
- Metadata editing after release (phase guard 409)

### Success Criteria

- Metadata editable online in the drafted phase; score updates immediately
- Overrides persisted on the project and visible in the rebuilt report
- Metadata editing rejected after release (409)
- Existing test matrices stay green (no regressions)

## Completed Task: OP12 - Project Creation UI on the Projects Page

### Objective

The projects page linked 'Dateien hochladen' to the legacy files page - files
were uploaded there but no project was created; the OP10 project workflow was
reachable only via the API. OP12 closes the UI gap per MO 1: the projects page
gets its own upload modal (multi-file, optional project name) that uploads
the files via /api/files/upload/, creates the project via
/api/projects/create/ with the returned file ids and navigates to the
preparation report (phase 1).

### Predecessors

- OP10: COMPLETED (project workflow, API)
- OP11: COMPLETED (rendered final report)

### Scope

- `django_project/templates/projects.html`: upload modal replaces the legacy
  /files/ link; upload -> create -> navigate flow with error paths
- `tests/test_op12_project_upload_ui.py` (19 checks) + CI matrix extended

### Out of Scope

- The legacy files page itself (stays as-is for single-file analysis)
- Inline metadata editing

### Success Criteria

- Upload on the projects page creates a project and lands on the preparation
  report without leaving the page flow
- Upload and project-creation error paths are visible to the user
- Existing test matrices stay green (no regressions)

## Completed Task: OP11 - Rendered Final Project Report (Charts, Original Data, Source Code)

### Objective

Replace the raw quarto-markdown project final report (found in the OP10 local
test: unrendered R fragments in a .html file, no charts) with a rendered,
self-contained HTML report: overview KPIs, embedded spectrum chart of the
full measurement series (matplotlib PNG as data URLs), per-agent quality bar
chart (evaluation), one section per agent (content + metrics + status),
original data tables, recommendations, warnings and the analysis source
code. The legacy reporting-agent template rendering stays as fallback;
matplotlib stays optional (charts degrade gracefully, anti-code-creep).

### Predecessors

- OP10: COMPLETED (project workflow upload -> preparation -> release -> crew)
- The local end-to-end test of OP10 exposed the raw-markdown final report

### Scope

- `services/project_report.py`: new OP11 report builder (rendered HTML with
  embedded charts, per-agent sections, original data, source code)
- `services/project_crew.py`: `_generate_final_report` uses the OP11 builder
  and passes the full measurement series; legacy template rendering kept
  as `_generate_final_report_legacy` fallback
- `tests/test_op11_rendered_final_report.py` (30 checks) + CI matrix extended

### Out of Scope

- Quarto binary integration (separate step; the OP7 single-file path is
  unchanged)
- PDF/Word export formats
- Per-agent charts beyond the spectrum and quality bar chart

### Success Criteria

- The project final report is a rendered HTML document without raw quarto/
  R fragments
- The report contains embedded spectrum + quality charts, original data,
  recommendations and source code
- Charts degrade gracefully without matplotlib; the legacy fallback stays
- Existing test matrices stay green (no regressions)

## Completed Task: OP10 - Project Workflow (Upload -> Preparation -> Release -> Crew -> Quarto Report)

### Objective
Structure the end-to-end workflow as an analysis project: uploaded files open a
new project (file-type agnostic), phase 1 turns the files into usable datasets
(measurement data + metadata) with a preparation report, quality assessment and
improvement recommendations for the user. The user adapts the data (re-ingest)
and releases the project; phase 2 runs the full NIRAnalysisCrew over every
usable dataset with one report section per agent (content + charts), renders
the project overview page and generates the final comprehensive Quarto report
(original data, source code, evaluation and graphics).

### Predecessors
- S1-S9 + G1-G8: COMPLETED
- OP1-OP4, OP6, OP7: COMPLETED (OP7 delivers the single-file crew bridge)

### Scope
- `core/models.py`: new `AnalysisProject` model (phases drafted/released/
  completed, preparation report, crew results, final report path) + migration
  `0004_analysisproject.py`
- `services/project_ingest.py`: phase 1 - files -> datasets (measurement data,
  metadata) + metadata quality assessment + improvement recommendations
- `services/project_crew.py`: phase 2 - full crew run per dataset, per-agent
  report sections, final comprehensive report generation
- `django_project/api/project_views.py` + `project_urls.py`: project list,
  create, detail (phase 1 report + phase 2 overview), re-ingest, release,
  final report download
- Templates `projects.html`, `project_report.html` (datasets, recommendations,
  per-agent sections, release/re-ingest buttons, final report link)
- `tests/test_op10_project_workflow.py` (56 checks) + CI matrix extended

### Out of Scope
- Inline metadata editing (adaptation = re-upload / re-ingest of adapted files)
- Federated learning, chatbot and ILIAS changes
- Live container verification (target machine)

### Success Criteria
- Upload opens a project; preparation report shows datasets, metadata quality
  and improvement recommendations
- User can re-ingest adapted data and release for analysis
- Phase 2 produces per-agent report sections and the final comprehensive report
- Existing test matrices stay green (no regressions)
