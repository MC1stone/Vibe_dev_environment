# NIR Intelligence Platform - Task Definition

## Overview

This document defines the current task for the NIR Intelligence Platform development.

## Current Task: Target-Environment Open Points (OP1-OP5)

### Objective

The local verification on the target machine is complete (all services
running, Mistral loaded, ILIAS installed; fixes PR #12-#15 merged). The
remaining target-environment open points are worked through by priority;
OP1 (Qdrant embedding pipeline, PR #16), OP2 (ILIAS API token flow,
PR #18) and OP3 (platform UI: upload, chatbot, ILIAS) are implemented
and verified.

### Predecessors

- S1-S9 + G1-G8: COMPLETED
- Local target-environment verification: COMPLETED (PR #12-#15)
- OP1 Qdrant embedding pipeline: COMPLETED (PR #16)
- OP2 ILIAS API token flow: COMPLETED (PR #18)

### Scope

- `django_project/templates/files.html`: real upload wiring
  (uploadFiles -> POST /api/files/upload/ with FormData + CSRF,
  loadFiles -> GET /api/files/ with statistics, gallery and table,
  analyze single/multiple, delete single/multiple, download)
- `django_project/templates/chatbot.html` (new): chat UI for the S6
  chatbot (POST /api/chatbot/message/ with question field, degraded
  handling, rag_sources display, status panel)
- `django_project/templates/ilias.html` (new): ILIAS learning path
  sync UI (POST /api/ilias/learning-paths/sync/, status, link to the
  ILIAS container)
- Routes /chatbot/ and /ilias/ plus navigation entries in base.html;
  broken upload_files.html removed; upload_view redirects to /files/

### Out of Scope

- OP3a real flwr operation, OP4 online update lookups + CI, OP5 MQTT
  worker + commercial adapters (follow-up tasks)
- New backend endpoints (existing APIs are used unchanged)
- JS frameworks/build tooling (vanilla JS like the other templates)

### Deliverables

1. Working file upload + analysis + delete/download in files.html
2. Chatbot UI page /chatbot/
3. ILIAS UI page /ilias/
4. tests/test_op3_platform_ui.py (40/40 green)

### Success Criteria

- File upload reaches the Generic File API with CSRF and auth handling
- The files page renders real statistics, gallery and table from the API
- Chatbot page sends question payloads and shows degraded/rag state
- ILIAS page syncs learning paths and shows the sync outcome
- All templates compile with the real Django template engine
- All test matrices green (S3-S9 + OP1-OP3: 287 tests)

### Timeline

- S1-S9 + G1-G8: COMPLETED
- Local verification: COMPLETED
- OP1: COMPLETED (PR #16)
- OP2: COMPLETED (PR #18)
- OP3: COMPLETED (this task)
- OP3a/OP4/OP5: NEXT

### Dependencies

- Logged-in Django user for upload/analyze (API requires
  IsAuthenticated); chatbot UI needs the Mistral model in the Ollama
  container; ILIAS UI needs the ILIAS container reachable
