# NIR Intelligence Platform - Task Definition

## Overview

This document defines the current task for the NIR Intelligence Platform development.

## Current Task: Target-Environment Open Points (OP1-OP5)

### Objective

The local verification on the target machine is complete (all services
running, Mistral loaded, ILIAS installed; fixes PR #12-#15 merged). The
remaining target-environment open points are worked through by priority;
OP1 (Qdrant embedding pipeline, PR #16) and OP2 (ILIAS API token flow)
are implemented and verified.

### Predecessors

- S1-S9 + G1-G8: COMPLETED
- Local target-environment verification: COMPLETED (PR #12-#15)
- OP1 Qdrant embedding pipeline: COMPLETED (PR #16)

### Scope

- `services/ilias_api_service.py`: OAuth2 token client
  (`POST /oauth2/token`, configurable grant - client_credentials,
  authorization_code, refresh_token - expiry tracking, refresh) and
  authenticated API client (Bearer header, 401 retry, course lookup by
  title for real course ref_ids)
- `ILIASLearningService` (S8) extended: `sync_learning_path(...,
  course_ref_id=...)` syncs modules into existing courses (real course
  ids), `create_authenticated_ilias_service()` wires the authenticated
  API transport; unauthenticated S8 path unchanged (backwards
  compatible)

### Out of Scope

- OP3 real flwr operation, OP4 online update lookups + CI, OP5 MQTT
  worker + commercial adapters (follow-up tasks)
- Enabling OAuth2/REST in the ILIAS installation itself (target
  environment step: Admin -> Web Services / OAuth2)
- Django view changes (OP2 stays on the service layer)

### Deliverables

1. `services/ilias_api_service.py`
2. `ILIASLearningService` course_ref_id sync + authenticated factory
3. `tests/test_op2_ilias_token_flow.py` (31/31 green)

### Success Criteria

- Token fetch -> Bearer-authenticated API calls -> 401 retry all work
  with injectable transports (offline, no network in tests)
- Learning path sync against real course ref_ids carries the
  Authorization header and skips course creation
- Unauthenticated S8 sync unchanged; S8 tests untouched and green
- No new hard dependencies (requests already declared)
- All test matrices green (S3-S9 + OP1 + OP2: 207 tests)

### Timeline

- S1-S9 + G1-G8: COMPLETED
- Local verification: COMPLETED
- OP1: COMPLETED (PR #16)
- OP2: COMPLETED (this task)
- OP3-OP5: NEXT

### Dependencies

- OAuth2 client registration in the ILIAS installation on the target
  machine for real tokens; stubs cover all offline tests
