# NIR Intelligence Platform - Task Definition

## Overview
This document defines the current task for the NIR Intelligence Platform development.

## Current Task: OP12 - Project Creation UI on the Projects Page

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
