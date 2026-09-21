# NIR Intelligence Platform - Task Definition

## Overview

This document defines the current task for the NIR Intelligence Platform development.

## Current Task: Result Chatbot on Ollama/Mistral with Qdrant RAG (Roadmap Step S6)

### Objective

Provide a chatbot for discussing analysis results (Master Objective 10),
backed by Ollama (mistral:latest) with RAG context from analysis results
and documentation, wired into the Django API.

### Predecessors

- S1-S5: COMPLETED (steering, Qdrant migration, format-agnostic import,
  spectrometer adapters, similarity engine + napari integration)

### Scope

- `services/chatbot_service.py`: ChatbotService (Ollama /api/chat),
  OllamaChatClient, RagContextBuilder, ChatMessage helper
- Django API: `api/chatbot_views.py` (POST message, GET status),
  `api/chatbot_urls.py`, route `api/chatbot/` in `nir_web/urls.py`
- Test matrix `tests/test_s6_chatbot.py` (stubbed Ollama client,
  no network required)

### Out of Scope

- Chat history persistence (turns passed per request)
- Streaming responses
- Frontend chat UI page (API endpoint only in this step)
- Real embedding indexing of Quarto reports into Qdrant (requires a
  running Qdrant instance and embedding model)

### Deliverables

1. `services/chatbot_service.py`
2. `django_project/api/chatbot_views.py` + `chatbot_urls.py`
3. Route registration in `django_project/nir_web/urls.py`
4. Test matrix 17/17 green + regressions S3/S4/S5 green

### Success Criteria

- Message composition: system prompt (NIR-IP identity) + RAG context +
  history + question
- Ollama response parsed correctly (stubbed client)
- Ollama unreachable -> degraded result (503 at the API level), no crash
- Qdrant unreachable -> chatbot answers without RAG context
- Route `api/chatbot/` registered in the Django URL configuration
- No new dependencies (`ollama>=0.1.0` already in requirements.txt)

### Timeline

- S1-S5: COMPLETED
- Chatbot service: COMPLETED
- Django API wiring: COMPLETED
- Verification (17/17 + regressions): COMPLETED

### Dependencies

- Python 3.12+, requests
- Ollama service (docker-compose, port 11434), model mistral:latest
- Qdrant (optional for RAG context; graceful without)

### Notes

- RAG context sources: analysis results (AgentOutput style) and
  documentation (Quarto report texts)
- Qdrant embedding retrieval is wired via QdrantSimilarityService (S5)
