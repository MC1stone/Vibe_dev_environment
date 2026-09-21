# NIR Intelligence Platform - Task Definition

## Overview

This document defines the current task for the NIR Intelligence Platform development.

## Current Task: Target-Environment Open Points (OP1-OP5)

### Objective

The local verification on the target machine is complete (all services
running, Mistral loaded, ILIAS installed; fixes PR #12-#15 merged). The
remaining target-environment open points are worked through by priority;
OP1 (Qdrant embedding pipeline) is implemented and verified.

### Predecessors

- S1-S9 + G1-G8: COMPLETED
- Local target-environment verification: COMPLETED (PR #12-#15)
- OP1 Qdrant embedding pipeline: COMPLETED (this task)

### Scope

- `services/embedding_service.py`: Ollama embeddings + Qdrant store
  (collection management, upsert, top-k search), EmbeddingService
  pipeline, InMemoryEmbeddingStore for offline tests
- `RagContextBuilder` (S6) wired to the pipeline: real Qdrant RAG as
  chat context, graceful degradation when unreachable

### Out of Scope

- OP2 ILIAS API token flow, OP3 real flwr operation, OP4 online update
  lookups + CI, OP5 MQTT worker + commercial adapters (follow-up tasks)
- Embedding of raw spectra (text only - analysis results, docs)
- Frontend chat UI

### Deliverables

1. `services/embedding_service.py`
2. `tests/test_op1_embedding_pipeline.py` (29/29 green)
3. RagContextBuilder integration with regression coverage

### Success Criteria

- Text -> vector -> Qdrant upsert -> top-k search roundtrip works
- RagContextBuilder uses `qdrant_rag` source when the pipeline is
  available and degrades gracefully when it is not
- No new hard dependencies (requests + qdrant-client already declared)
- All test matrices green (S3-S9 + OP1: 186 tests)

### Timeline

- S1-S9 + G1-G8: COMPLETED
- Local verification: COMPLETED
- OP1: COMPLETED
- OP2-OP5: NEXT

### Dependencies

- Ollama embedding model (`nomic-embed-text`) on the target machine for
  real embeddings; stubs cover all offline tests
