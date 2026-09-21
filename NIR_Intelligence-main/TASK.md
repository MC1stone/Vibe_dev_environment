# NIR Intelligence Platform - Task Definition

## Overview

This document defines the current task for the NIR Intelligence Platform development.

## Current Task: Target-Environment Open Points (OP1-OP6)

### Objective

The local verification on the target machine is complete (all services
running, Mistral loaded, ILIAS installed; fixes PR #12-#15 merged). The
remaining target-environment open points are worked through by priority;
OP1 (Qdrant embedding pipeline, PR #16), OP2 (ILIAS API token flow,
PR #18), OP3 (platform UI, PR #19), OP6 (CrewAI agent implementation)
and OP4 (online update lookups + CI) are implemented and verified.

### Predecessors

- S1-S9 + G1-G8: COMPLETED
- Local target-environment verification: COMPLETED (PR #12-#15)
- OP1 Qdrant embedding pipeline: COMPLETED (PR #16)
- OP2 ILIAS API token flow: COMPLETED (PR #18)
- OP3 Platform UI: COMPLETED (PR #19)
- OP6 CrewAI agents: COMPLETED - real implementations of the previously
  stubbed agents (sensor quality, statistics, neural networks, calibration,
  metadata, PostgreSQL, Django, MCP, ILIAS), full CrewAI crew (16 agents
  with tool bindings) and the background crew runner
  (`scripts/background_crew_runner.py`, docker-compose service
  `background_crew`) - the agents operate the platform interfaces in
  the background.

### Scope

- `services/update_lookup.py` (new): `UpdateLookupService` - PyPI and
  Docker Hub lookups with an injectable HTTP transport (OP2 pattern);
  yanked/pre-release filtering for PyPI, stable semver tags for Docker
  Hub, registry normalization (library namespace, private registries,
  localhost); every network failure degrades gracefully to the offline
  behaviour (S7 guarantee).
- `services/update_monitor.py`: `ComponentEntry.available` (latest
  upstream version) in the dataclass, `to_dict` and the Quarto report;
  the report column order stays backward compatible with the S7 test
  contract.
- `scripts/check_updates.py`: new `--online` flag enriches the report
  with PyPI/Docker Hub lookups; offline runs keep exit code 0.
- `.github/workflows/ci.yml` (new): CI job running all 12 offline test
  matrices plus `manage.py check` on pushes/PRs to main.
- `.github/workflows/update-monitor.yml` (new): weekly scheduled
  (`workflow_dispatch`-triggerable) online update report; the report is
  uploaded as an artifact.

### Out of Scope

- OP3a real flwr operation, OP5 MQTT worker + commercial adapters
  (follow-up tasks)
- Auto-updates: updates remain deliberate deployment decisions (no
  auto-update, S7 rule)

### Deliverables

1. `services/update_lookup.py` with injectable transport and graceful
   offline degradation
2. `scripts/check_updates.py --online` enriching the update report
3. CI workflow running the 12 test matrices on every push/PR
4. Scheduled online update report workflow
5. `tests/test_op4_update_lookups.py` (34/34 green)

### Success Criteria

- Online lookups produce the latest upstream version per component and
  flag outdated components without touching the offline S7 behaviour
- Every network failure path degrades gracefully (no crash, exit 0)
- CI runs the full offline test suite green on GitHub Actions
- All existing test matrices stay green (no regressions)
