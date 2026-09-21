# NIR Intelligence Platform - Task Definition

## Overview

This document defines the current task for the NIR Intelligence Platform development.

## Current Task: OP7 - Upload -> Crew Analysis -> Quarto Report Pipeline

### Objective

Make the end-to-end pipeline work in the leading project using the OP6
CrewAI agents: an uploaded spectral file is loaded via the S3
format-agnostic loader, analyzed by the full NIRAnalysisCrew (spectral,
metadata, quality, statistics, calibration agents) and a comprehensive
Quarto report is generated. PR #1 pursued the same goal but in the
frozen legacy approach `nir_platform/` (S1/G3); OP7 delivers it in
`NIR_Intelligence-main/` (single source of truth).

### Predecessors

- S1-S9 + G1-G8: COMPLETED
- OP1-OP4, OP6: COMPLETED

### Scope

- Fixed `agents/spectral_analysis_agent.py`: `SpectrometerIssue.INVALID`
  enum member added (quality-assessment error path crashed without it)
- Fixed `agents/nir_analysis_crew.py`: `sample_id` is now injected into
  the spectral_data contract (spectral agent validation previously failed)
- New `FileCrewAnalysisView` (`django_project/api/file_views.py`) + route
  `files/<uuid:file_id>/crew-analysis/`: bridges the Generic File API
  (upload) with the OP6 crew (analysis + report), persists crew results
  on the GenericFile record, 422 for non-spectral files
- `django_project/templates/files.html`: crew analysis button per file

### Out of Scope

- OP3a real flwr operation, OP5 MQTT worker + commercial adapters
- PR #1 (legacy `nir_platform/` approach) - remains open, owner decision
- Live container verification (target machine: upload a CSV via /files/,
  click the crew button, open the generated report)

### Deliverables

1. Working upload -> crew analysis -> comprehensive Quarto report pipeline
   in the leading project
2. `tests/test_op7_crew_pipeline_bridge.py` (23/23 green)
3. CI workflow extended with the OP7 matrix

### Success Criteria

- The S3 loader feeds the crew contract for every supported format
- Crew analysis completes without errors and produces a Quarto report
- Existing test matrices stay green (no regressions)
