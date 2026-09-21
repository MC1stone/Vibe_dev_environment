# NIR Intelligence Platform - Task Definition

## Overview

This document defines the current task for the NIR Intelligence Platform development.

## Current Task: Self-Optimization & Update Monitoring (Roadmap Step S7)

### Objective

Monitor the open-source components used by the platform (pip packages,
Docker images) for updates and provide an Optuna-based optimization
protocol for calibrations (Master Objective 15, plus MO 8/9).

### Predecessors

- S1-S6: COMPLETED (steering, Qdrant migration, format-agnostic import,
  spectrometer adapters, similarity engine + napari, result chatbot)

### Scope

- `services/update_monitor.py`: UpdateMonitorService - scans
  requirements*.txt manifests and docker-compose images, detects local
  installed versions, flags specifier violations, recommends pinning
  for 'latest' tags
- `scripts/check_updates.py`: CLI for CI jobs and manual runs
  (--json, --no-report, --compose-files); renders a Quarto .qmd report
- `services/calibration_optimization.py`: CalibrationOptimizationService
  with OptimizationProtocol (trials, best params/score, methods PLS/PCR/
  SVM/RandomForest/XGBoost/CNN); Optuna optional (deferred when missing)

### Out of Scope

- Auto-updates of packages or images (updates stay deliberate decisions)
- Network-based registry/PyPI lookups (local-manifest based only)
- GitHub Actions CI workflow (no CI exists in the repo yet)
- Calibration model training itself (protocol only; models follow
  with the calibration agent extension)

### Deliverables

1. `services/update_monitor.py`
2. `scripts/check_updates.py` (CLI)
3. `services/calibration_optimization.py`
4. Test matrix 27/27 green + regressions S3-S6 green

### Success Criteria

- All requirements*.txt manifests parsed (comments/markers skipped)
- Compose images extracted with tag detection ('latest' vs pinned)
- Installed versions detected without network access
- Specifier semantics: satisfied -> no flag, violated -> flag,
  'latest' -> no offline decision
- Quarto .qmd report rendered with summary, tables, recommendations
- CLI runs end-to-end (summary and --json modes)
- Optuna study completes when installed; graceful deferral otherwise
- Default calibration methods match the mission statement

### Timeline

- S1-S6: COMPLETED
- Update monitor + CLI: COMPLETED
- Calibration optimization protocol: COMPLETED
- Verification (27/27 + regressions): COMPLETED

### Dependencies

- Python 3.12+ (packaging, importlib.metadata from stdlib)
- optuna (optional, already in requirements.txt)
- Quarto (optional, for rendering the .qmd report)

### Notes

- No auto-update: the report recommends, deployment decides
- Registry/PyPI online lookups are a target-environment extension
