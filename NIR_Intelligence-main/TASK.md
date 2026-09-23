# NIR Intelligence Platform - Task Definition

## Overview
This document defines the current task for the NIR Intelligence Platform development.

## Current Task: OP10 - Project Workflow (Upload -> Preparation -> Release -> Crew -> Quarto Report)

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
