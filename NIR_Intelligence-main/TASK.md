# NIR Intelligence Platform - Task Definition

## Overview
This document defines the current task for the NIR Intelligence Platform development.

## Current Task: Qdrant Migration (Roadmap Step S2)

### Objective
Replace Weaviate with Qdrant as the vector database for embedding storage,
semantic search and similarity search across the entire platform stack.

### Predecessor
S1 (Consolidation & Steering) is COMPLETED: this project is the Single Source of
Truth; the mandatory startup files have been updated to reference Qdrant.

### Scope
- Replace the Weaviate service in `docker-compose.yml` (and prod compose) with a Qdrant service
- Replace `weaviate-client` with `qdrant-client` in `requirements.txt`
- Migrate `agents/weaviate_agent.py` to `agents/qdrant_agent.py`
  (embedding storage, semantic search, similarity search)
- Update all callers of the Weaviate agent to the Qdrant agent
- Review the t2v-transformers container (embedding generation may move to
  Ollama-side or local inference)

### Out of Scope
- No changes to FAISS (spectrum/peak comparison stays on FAISS)
- No changes to PostgreSQL, Django, MCP, Flower or Quarto components
- No refactoring of unrelated code

### Deliverables
1. **docker-compose.yml / docker-compose.prod.yml**: Qdrant service replaces Weaviate
2. **requirements.txt**: `qdrant-client` replaces `weaviate-client`
3. **agents/qdrant_agent.py**: full replacement of the Weaviate agent functionality
4. **Callers updated**: no remaining imports/references to the Weaviate agent
5. **Embedding pipeline decision**: documented handling of embedding generation

### Success Criteria
- No references to Weaviate remain in the active platform stack
  (compose files, requirements, agents, callers)
- Qdrant service starts and is reachable within the Docker network
- Agent can be imported and instantiated without errors
- Embedding storage, semantic search and similarity search work against Qdrant
- System can run in non-Docker mode for testing

### Timeline
- Steering files (S1): COMPLETED
- Compose migration: PENDING
- Python client migration: PENDING
- Agent migration: PENDING
- Caller updates: PENDING
- Verification: PENDING

### Dependencies
- Python 3.12+
- `qdrant-client` (pip)
- Qdrant Docker image
- Agent-specific dependencies as defined in requirements.txt

### Notes
- Weaviate is out of scope per MISSION_STATEMENT.md; Qdrant is the replacement
- Docker is optional for basic testing
- Agents use simulated data for testing purposes
